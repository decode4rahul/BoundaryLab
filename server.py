"""Loopback-only local demonstrator; not an internet-facing service."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from core import demo

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            data = Path(__file__).with_name('dashboard.html').read_bytes()
            kind = 'text/html; charset=utf-8'
        elif self.path in ('/api/demo/hardened', '/api/demo/weak'):
            data = json.dumps(demo(self.path.rsplit('/',1)[-1])).encode()
            kind = 'application/json'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type',kind)
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'")
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    print('BoundaryLab local demo: http://127.0.0.1:8080', flush=True)
    ThreadingHTTPServer(('127.0.0.1',8080),Handler).serve_forever()
