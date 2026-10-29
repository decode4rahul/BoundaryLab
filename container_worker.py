"""Disposable network fixtures and scoped broker. No Docker access."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import time

ROLE = os.environ.get('BL_ROLE','fixture')
RUN = os.environ.get('BL_RUN','')
GRANTS = json.loads(os.environ.get('BL_GRANTS','{}'))

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def reply(self, status, payload):
        data=json.dumps(payload).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path=='/health':self.reply(200,{'role':ROLE,'run':RUN})
        else:self.reply(404,{'error':'unknown route'})
    def do_POST(self):
        if ROLE!='broker':self.reply(404,{'error':'unknown route'});return
        token=self.headers.get('Authorization','').removeprefix('Bearer ')
        grant=GRANTS.get(token)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4096:raise ValueError()
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict) or set(body)!={'run_id'}:raise ValueError()
        except (ValueError,TypeError):self.reply(400,{'error':'invalid schema'});return
        policy={'/submit_test':'red','/set_defence':'blue'}
        allowed=bool(grant and self.path in policy and grant['role']==policy[self.path] and grant['run_id']==RUN==body['run_id'] and grant['expires']>time.time())
        self.reply(200 if allowed else 403,{'allowed':allowed,'run_id':RUN})

HTTPServer((os.environ.get('BL_BIND','0.0.0.0'),int(os.environ.get('BL_PORT','8080'))),Handler).serve_forever()
