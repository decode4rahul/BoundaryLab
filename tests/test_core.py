import copy
import unittest
from core import Broker, Evidence, demo, verify, verdict

class SecurityTests(unittest.TestCase):
    def test_authorization_controls(self):
        b=Broker('a'); red=b.issue('red'); blue=b.issue('blue'); foreign=b.issue('red','b')
        self.assertTrue(b.request(red,'submit_test'))
        self.assertTrue(b.request(blue,'set_defence'))
        for token, action in [(red,'set_defence'),(foreign,'submit_test'),('bad','submit_test'),(red,'arbitrary')]:
            self.assertFalse(b.request(token,action))

    def test_evidence_tamper_reorder_truncate_rewrite(self):
        e=Evidence('a'); e.append('one',{}); e.append('two',{}); checkpoint=e.checkpoint()
        self.assertTrue(verify(e.events,checkpoint))
        changed=copy.deepcopy(e.events); changed[0]['details']['injected']=True
        for bad in [changed,list(reversed(e.events)),e.events[:-1],[]]:
            self.assertFalse(verify(bad,checkpoint))
        replacement=Evidence('a'); replacement.append('new',{}); replacement.append('new',{})
        self.assertFalse(verify(replacement.events,checkpoint))

    def test_fail_closed_gate(self):
        self.assertEqual(verdict({}),'INCONCLUSIVE')
        self.assertEqual(verdict({'authorization':'FAIL'}),'INVALID')
        checks=dict.fromkeys(('authorization','network','real_model','fresh_session','evidence'),'PASS')
        self.assertEqual(verdict(checks),'VALID_UNDER_TESTED_MANIFEST')
        checks['network']='ERROR'; self.assertEqual(verdict(checks),'INCONCLUSIVE')

    def test_positive_control_and_honest_missing_checks(self):
        self.assertEqual(demo('weak')['verdict'],'INVALID')
        self.assertEqual(demo('hardened')['verdict'],'INCONCLUSIVE')
        self.assertEqual(demo()['model_outcome'],'NOT_RUN')

if __name__=='__main__': unittest.main()
