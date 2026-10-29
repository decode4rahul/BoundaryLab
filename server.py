"""Authenticated loopback operator UI. Not a public multi-user deployment."""
import argparse
import hmac
import json
import os
from pathlib import Path
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from controller import Controller
from core import verify
from storage import Store

ROOT=Path(__file__).parent
MAX_BODY=1024*1024

class AppServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,store,token=None):
        self.store=store
        self.controller=Controller(store)
        self.token=token or secrets.token_urlsafe(32)
        super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(15)
    def log_message(self,*args):pass
    def send(self,status,payload,kind='application/json'):
        data=json.dumps(payload).encode() if kind=='application/json' else payload
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(data)
    def valid_host(self):
        return self.headers.get('Host') in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port))
    def authenticated(self):
        value=self.headers.get('Authorization','')
        return value.startswith('Bearer ') and hmac.compare_digest(value[7:].encode('utf-8'),self.server.token.encode('utf-8'))
    def body(self):
        if self.headers.get_content_type()!='application/json':raise ValueError('Expected application/json')
        length=int(self.headers.get('Content-Length','0'))
        if not 0<length<=MAX_BODY:raise ValueError('Invalid body size')
        value=json.loads(self.rfile.read(length))
        if not isinstance(value,dict):raise ValueError('Expected an object')
        return value
    def do_GET(self):
        if not self.valid_host():self.send(403,{'error':'Invalid Host'});return
        path=urlsplit(self.path).path
        assets={'/':('dashboard.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if path in assets:
            file,kind=assets[path];self.send(200,(ROOT/file).read_bytes(),kind);return
        if not self.authenticated():self.send(401,{'error':'Operator token required'});return
        try:
            if path=='/api/runs':self.send(200,{'runs':[self.server.store.export(r['id'])['run'] for r in self.server.store.list()]})
            elif path=='/api/status':
                import shutil
                self.send(200,{'docker_cli':bool(shutil.which('docker')),'model_configured':bool(os.environ.get('BOUNDARYLAB_MODEL')),'active':self.server.controller.lock.locked(),'version':'0.2.2'})
            elif path.startswith('/api/runs/'):
                parts=path.split('/')
                if len(parts)==4:self.send(200,self.server.store.export(parts[3]))
                else:self.send(404,{'error':'Unknown route'})
            else:self.send(404,{'error':'Unknown route'})
        except KeyError:self.send(404,{'error':'Run not found'})
    def do_POST(self):
        if not self.valid_host():self.send(403,{'error':'Invalid Host'});return
        origin=self.headers.get('Origin')
        if origin and origin not in ('http://127.0.0.1:'+str(self.server.server_port),'http://localhost:'+str(self.server.server_port)):
            self.send(403,{'error':'Cross-origin request denied'});return
        if not self.authenticated():self.send(401,{'error':'Operator token required'});return
        path=urlsplit(self.path).path
        try:
            body=self.body()
            if path=='/api/runs':
                if set(body)!={'profile'} or body['profile'] not in ('hardened','weak'):raise ValueError('Choose hardened or weak')
                self.send(202,{'run_id':self.server.controller.start(body['profile'])})
            elif path=='/api/verify':
                if set(body)!={'run_id','events'} or not isinstance(body['run_id'],str):raise ValueError('Expected run_id and events')
                original=self.server.store.export(body['run_id'])
                checkpoint=original['checkpoint']
                self.send(200,{'verified':bool(checkpoint and verify(body['events'],checkpoint)), 'checkpoint_source':'retained operator checkpoint','run_id':body['run_id']})
            else:self.send(404,{'error':'Unknown route'})
        except (ValueError,TypeError):self.send(400,{'error':'Invalid request schema'})
        except KeyError:self.send(404,{'error':'Run not found'})
        except RuntimeError as error:self.send(409,{'error':str(error)})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8080);parser.add_argument('--data',default='data')
    args=parser.parse_args()
    server=AppServer(('127.0.0.1',args.port),Store(args.data))
    print('BoundaryLab: http://127.0.0.1:'+str(server.server_port),flush=True)
    print('Operator token (paste into local UI): '+server.token,flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        server.server_close()
        if server.controller.thread:server.controller.thread.join()
