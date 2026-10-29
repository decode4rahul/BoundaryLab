import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
from core import verify
from storage import Store, REQUIRED
from controller import Controller
from runtime import DockerRuntime, RuntimeUnavailable
from server import AppServer

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
        self.run=self.store.create('hardened',{'test':True})
    def tearDown(self):self.temp.cleanup()
    def complete(self):
        self.store.state(self.run,'PRECHECK');self.store.state(self.run,'VERIFYING')
        for key in REQUIRED:self.store.check(self.run,key,'PASS','test fixture only')
        self.store.state(self.run,'COMPLETE',{'model_outcome':'TEST_FIXTURE'})
        self.store.seal(self.run)
    def test_restart_and_scope(self):
        t=self.store.issue(self.run,'red')
        other=self.store.create('hardened',{})
        reopened=Store(self.temp.name)
        self.assertTrue(reopened.authorize(self.run,t,'submit_test'))
        self.assertFalse(reopened.authorize(other,t,'submit_test'))
        self.assertFalse(reopened.authorize(self.run,t,'set_defence'))
        self.assertFalse(reopened.authorize(self.run,t,'unknown'))
    def test_expiry_and_completed_run_denied(self):
        t=self.store.issue(self.run,'red')
        with self.store.connect() as db:db.execute('UPDATE grants SET expires=0')
        self.assertFalse(self.store.authorize(self.run,t,'submit_test'))
        t=self.store.issue(self.run,'red');self.complete()
        self.assertFalse(self.store.authorize(self.run,t,'submit_test'))
        with self.assertRaises(ValueError):self.store.issue(self.run,'red')
    def test_manifest_and_result_reconstructed_after_db_row_tamper(self):
        self.complete()
        with self.store.connect() as db:
            db.execute('UPDATE runs SET result=?,manifest=?,checks=? WHERE id=?',('{}','{}','{}',self.run))
        exported=self.store.export(self.run)
        self.assertEqual(exported['run']['manifest']['test'],True)
        self.assertEqual(exported['run']['result']['model_outcome'],'TEST_FIXTURE')
        self.assertEqual(exported['run']['verdict'],'VALID_UNDER_TESTED_MANIFEST')
    def test_anchor_never_overwritten_and_mutation_invalidates(self):
        self.complete();exported=self.store.export(self.run)
        self.assertTrue(exported['verified'])
        with self.assertRaises(FileExistsError):self.store.seal(self.run)
        self.store.event(self.run,'injected',{})
        self.assertFalse(self.store.export(self.run)['verified'])
        self.assertEqual(self.store.export(self.run)['run']['verdict'],'INVALID')
    def test_illegal_transition_and_partial_gate(self):
        with self.assertRaises(ValueError):self.store.state(self.run,'COMPLETE')
        self.assertEqual(self.store.export(self.run)['run']['verdict'],'INCONCLUSIVE')
    def test_malformed_external_evidence(self):
        for events,checkpoint in [(None,{}),([None],{}),([],{'count':False,'run_id':'a','head':None}),([{}],{'count':1,'run_id':'a','head':'x'})]:
            self.assertFalse(verify(events,checkpoint))

class ControllerTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_weak_control_halts_and_seals(self):
        controller=Controller(self.store)
        with patch.object(DockerRuntime,'doctor',side_effect=AssertionError('must not execute Docker')):
            run=controller.start('weak');controller.thread.join(5)
        result=self.store.export(run)
        self.assertTrue(result['verified'])
        self.assertEqual(result['run']['verdict'],'INVALID')
        self.assertEqual(result['run']['result']['model_outcome'],'NOT_RUN')
    def test_missing_runtime_never_passes(self):
        controller=Controller(self.store)
        with patch.object(DockerRuntime,'doctor',side_effect=RuntimeUnavailable('test missing runtime')):
            run=controller.start('hardened');controller.thread.join(5)
        result=self.store.export(run)
        self.assertEqual(result['run']['verdict'],'INCONCLUSIVE')
        self.assertEqual(result['run']['checks']['network']['status'],'ERROR')
        self.assertTrue(result['verified'])
    def test_boundary_failure_halts_model_and_cleans(self):
        controller=Controller(self.store)
        def failed(runtime,run_id):
            runtime.containers.append('fixture');return False,True,{'broker_http':[]}
        with patch.object(DockerRuntime,'doctor',return_value={'engine':'test'}),patch.object(DockerRuntime,'boundary_checks',failed),patch.object(DockerRuntime,'cleanup',return_value=[]) as cleanup,patch.object(DockerRuntime,'model_checks',side_effect=AssertionError('model must not run')):
            run=controller.start('hardened');controller.thread.join(5)
        cleanup.assert_called_once()
        self.assertEqual(self.store.export(run)['run']['verdict'],'INVALID')

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
        self.server=AppServer(('127.0.0.1',0),self.store,token='test-operator-token')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):
        if self.server.controller.thread:self.server.controller.thread.join(5)
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,body=None,token='test-operator-token',headers=None):
        h={'Authorization':'Bearer '+token,**(headers or {})}
        if body is not None:h['Content-Type']='application/json'
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
        try:
            with urllib.request.urlopen(req,timeout=5) as response:return response.status,response.read()
        except urllib.error.HTTPError as error:
            with error:
                return error.code,error.read()
    def test_public_assets_and_protected_api(self):
        self.assertEqual(self.request('/')[0],200)
        self.assertEqual(self.request('/app.js')[0],200)
        self.assertEqual(self.request('/api/runs',token='wrong')[0],401)
        self.assertEqual(self.request('/api/runs',headers={'Host':'attacker.test'})[0],403)
    def test_origin_schema_and_unknown_routes(self):
        self.assertEqual(self.request('/api/runs',{'profile':'weak'},headers={'Origin':'https://attacker.test'})[0],403)
        self.assertEqual(self.request('/api/runs',{'profile':'anything'})[0],400)
        self.assertEqual(self.request('/api/runs',{'profile':'weak','command':'touch x'})[0],400)
        self.assertEqual(self.request('/api/unknown',{})[0],404)
    def test_run_export_tamper_and_persistence(self):
        code,body=self.request('/api/runs',{'profile':'weak'});self.assertEqual(code,202)
        run=json.loads(body)['run_id'];self.server.controller.thread.join(5)
        code,body=self.request('/api/runs/'+run);bundle=json.loads(body)
        self.assertTrue(bundle['verified']);self.assertEqual(bundle['run']['verdict'],'INVALID')
        code,body=self.request('/api/verify',{'run_id':run,'events':bundle['events']});self.assertTrue(json.loads(body)['verified'])
        changed=copy.deepcopy(bundle['events']);changed[0]['details']={}
        code,body=self.request('/api/verify',{'run_id':run,'events':changed});self.assertFalse(json.loads(body)['verified'])
        self.assertTrue(Store(self.temp.name).export(run)['verified'])

if __name__=='__main__':unittest.main()
