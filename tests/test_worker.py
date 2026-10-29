"""Exercise the actual container worker HTTP implementation as a local process.
This is not Docker network isolation evidence.
"""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path

class WorkerHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Worker port configurable only for local integration test, not from operator HTTP API.
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));cls.port=sock.getsockname()[1]
        grants={'red-token':{'run_id':'test-run','role':'red','expires':time.time()+300},
                'expired-token':{'run_id':'test-run','role':'red','expires':0},
                'other-token':{'run_id':'other-run','role':'red','expires':time.time()+300},
                'blue-token':{'run_id':'test-run','role':'blue','expires':time.time()+300}}
        env=dict(os.environ,BL_ROLE='broker',BL_RUN='test-run',BL_GRANTS=json.dumps(grants),BL_PORT=str(cls.port),BL_BIND='127.0.0.1')
        cls.process=subprocess.Popen([sys.executable,str(Path(__file__).parents[1]/'container_worker.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen('http://127.0.0.1:'+str(cls.port)+'/health',timeout=.2).close();return
            except OSError:time.sleep(.05)
        cls.process.terminate();raise RuntimeError('Worker failed to start')
    @classmethod
    def tearDownClass(cls):cls.process.terminate();cls.process.wait(timeout=5)
    def request(self,path,token,body):
        req=urllib.request.Request('http://127.0.0.1:'+str(self.port)+path,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=2) as response:return response.status
        except urllib.error.HTTPError as error:
            with error:
                return error.code
    def test_actual_worker_auth(self):
        self.assertEqual(self.request('/submit_test','red-token',{'run_id':'test-run'}),200)
        self.assertEqual(self.request('/set_defence','blue-token',{'run_id':'test-run'}),200)
        for path,token,run in [('/set_defence','red-token','test-run'),('/submit_test','expired-token','test-run'),('/submit_test','other-token','test-run'),('/submit_test','invalid','test-run'),('/submit_test','red-token','other-run')]:
            self.assertEqual(self.request(path,token,{'run_id':run}),403)
    def test_worker_schema_and_arbitrary_destinations(self):
        self.assertEqual(self.request('/submit_test','red-token',{'run_id':'test-run','url':'http://anywhere'}),400)
        self.assertEqual(self.request('/arbitrary','red-token',{'run_id':'test-run'}),403)
