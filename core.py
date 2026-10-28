"""BoundaryLab trusted core. No sandbox or model claims are made here."""
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class Evidence:
    def __init__(self, run_id):
        self.run_id = run_id
        self.events = []

    def append(self, kind, details):
        body = dict(run_id=self.run_id, seq=len(self.events), previous=self.events[-1]['hash'] if self.events else '0'*64, kind=kind, details=details)
        self.events.append(dict(body, hash=digest(body)))

    def checkpoint(self):
        return dict(run_id=self.run_id, count=len(self.events), head=self.events[-1]['hash'] if self.events else '0'*64)


def verify(events, checkpoint):
    previous = '0'*64
    for i, event in enumerate(events):
        body = {k:v for k,v in event.items() if k != 'hash'}
        if body.get('seq') != i or body.get('run_id') != checkpoint['run_id'] or body.get('previous') != previous or event.get('hash') != digest(body):
            return False
        previous = event['hash']
    return len(events) == checkpoint['count'] and hmac.compare_digest(previous, checkpoint['head'])


@dataclass(frozen=True)
class Grant:
    run_id: str
    role: str


class Broker:
    def __init__(self, run_id, profile='hardened'):
        if profile not in ('hardened', 'weak'):
            raise ValueError('unknown profile')
        self.run_id, self.profile = run_id, profile
        self.evidence = Evidence(run_id)
        self.grants = {}
        self.evidence.append('manifest', {'profile': profile, 'version': 1})

    def issue(self, role, run_id=None):
        if role not in ('red', 'blue', 'operator'):
            raise ValueError('unknown role')
        token = secrets.token_urlsafe(32)
        self.grants[token] = Grant(run_id or self.run_id, role)
        return token

    def request(self, token, action):
        # Fixed action map: never accept arbitrary URLs, filesystem paths or commands.
        permissions = {'submit_test': {'red'}, 'set_defence': {'blue'}, 'read_summary': {'operator'}}
        grant = self.grants.get(token)
        allowed = bool(grant and action in permissions and grant.run_id == self.run_id and grant.role in permissions[action])
        if self.profile == 'weak' and grant and action in permissions:
            allowed = True  # Deliberate in-process positive control, never a deployment mode.
        self.evidence.append('authorization', {'action':action, 'role':grant.role if grant else 'unknown', 'allowed':allowed})
        return allowed


REQUIRED = ('authorization', 'network', 'real_model', 'fresh_session', 'evidence')

def verdict(checks):
    if any(checks.get(key) == 'FAIL' for key in REQUIRED):
        return 'INVALID'
    if all(checks.get(key) == 'PASS' for key in REQUIRED):
        return 'VALID_UNDER_TESTED_MANIFEST'
    return 'INCONCLUSIVE'


def demo(profile='hardened'):
    broker = Broker(secrets.token_hex(8), profile)
    red = broker.issue('red')
    other_run = broker.issue('red', 'different-run')
    cases = [
        ('allowed red request', broker.request(red, 'submit_test'), True),
        ('wrong role denied', broker.request(red, 'set_defence'), False),
        ('wrong run denied', broker.request(other_run, 'submit_test'), False),
        ('unknown credential denied', broker.request('invalid', 'submit_test'), False),
        ('unknown action denied', broker.request(red, 'http://example.test'), False),
    ]
    checks = {key:'NOT_RUN' for key in REQUIRED}
    checks['authorization'] = 'PASS' if all(actual == expected for _,actual,expected in cases) else 'FAIL'
    checkpoint = broker.evidence.checkpoint()
    checks['evidence'] = 'PASS' if verify(broker.evidence.events, checkpoint) else 'FAIL'
    return dict(run_id=broker.run_id, profile=profile, verdict=verdict(checks), checks=checks,
                cases=[dict(name=n, allowed=a, expected=e, passed=a==e) for n,a,e in cases],
                events=broker.evidence.events, checkpoint=checkpoint,
                model_outcome='NOT_RUN', limitation='Local authorization demonstration only. Network isolation and real inference have not run.')
