"""Operator-owned SQLite state plus separately retained checkpoints."""
import json
from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from core import Evidence, digest, verify, verdict

REQUIRED = ('authorization', 'network', 'real_model', 'fresh_session', 'cleanup', 'evidence')

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.anchors = self.root / 'operator-checkpoints'
        self.anchors.mkdir(exist_ok=True)
        self.path = self.root / 'runs.sqlite3'
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created REAL, state TEXT, profile TEXT, manifest TEXT, checks TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS events (run_id TEXT, seq INTEGER, value TEXT, PRIMARY KEY(run_id, seq));
            CREATE TABLE IF NOT EXISTS grants (token_hash TEXT PRIMARY KEY, run_id TEXT, role TEXT, expires REAL);
            ''')
        if os.name != 'nt':
            os.chmod(self.root, 0o700)
            os.chmod(self.anchors, 0o700)
            os.chmod(self.path, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.row_factory = sqlite3.Row
            with db:
                yield db
        finally:
            db.close()

    def create(self, profile, manifest):
        if profile not in ('hardened', 'weak'):
            raise ValueError('unknown profile')
        run_id = secrets.token_hex(12)
        checks = {key: {'status':'NOT_RUN', 'detail':'Waiting for controller'} for key in REQUIRED}
        manifest = dict(manifest, profile=profile)
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?)', (run_id,time.time(),'CREATED',profile,json.dumps(manifest),json.dumps(checks),'{}'))
        self.event(run_id, 'manifest', {'sha256':digest(manifest), 'manifest':manifest})
        return run_id

    def get(self, run_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        run = dict(row)
        for key in ('manifest','checks','result'):
            run[key] = json.loads(run[key])
        run['manifest_hash'] = digest(run['manifest'])
        statuses = {key:value['status'] for key,value in run['checks'].items()}
        run['verdict'] = ('INVALID' if 'FAIL' in statuses.values() else
                          'VALID_UNDER_TESTED_MANIFEST' if all(statuses.get(k)=='PASS' for k in REQUIRED) else 'INCONCLUSIVE')
        if run['state'] != 'COMPLETE' and run['verdict'] != 'INVALID':
            run['verdict'] = 'INCONCLUSIVE'
        return run

    def list(self):
        with self.connect() as db:
            ids = [r[0] for r in db.execute('SELECT id FROM runs ORDER BY created DESC LIMIT 100')]
        return [self.get(i) for i in ids]

    def event(self, run_id, kind, details):
        with self.lock, self.connect() as db:
            if not db.execute('SELECT 1 FROM runs WHERE id=?',(run_id,)).fetchone():
                raise KeyError(run_id)
            last = db.execute('SELECT seq,value FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1',(run_id,)).fetchone()
            seq = last['seq']+1 if last else 0
            body = dict(run_id=run_id,seq=seq,previous=json.loads(last['value'])['hash'] if last else '0'*64,kind=kind,details=details)
            event = dict(body,hash=digest(body))
            db.execute('INSERT INTO events VALUES(?,?,?)',(run_id,seq,json.dumps(event)))
        return event

    def events(self, run_id):
        self.get(run_id)
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT value FROM events WHERE run_id=? ORDER BY seq',(run_id,))]

    def check(self, run_id, key, status, detail, measurements=None):
        if key not in REQUIRED or status not in ('PASS','FAIL','ERROR','NOT_RUN'):
            raise ValueError('invalid check')
        with self.lock:
            run = self.get(run_id)
            run['checks'][key] = {'status':status,'detail':detail,'measurements':measurements or {}}
            with self.connect() as db:
                db.execute('UPDATE runs SET checks=? WHERE id=?',(json.dumps(run['checks']),run_id))
            self.event(run_id, 'check', {'name':key,**run['checks'][key]})

    def state(self, run_id, state, result=None):
        allowed = {'CREATED':('PRECHECK',), 'PRECHECK':('RUNNING','VERIFYING'), 'RUNNING':('VERIFYING',), 'VERIFYING':('COMPLETE',)}
        with self.lock:
            current = self.get(run_id)['state']
            if state not in allowed.get(current,()):
                raise ValueError('illegal run transition')
            with self.connect() as db:
                db.execute('UPDATE runs SET state=?,result=COALESCE(?,result) WHERE id=?',(state,json.dumps(result) if result is not None else None,run_id))
            self.event(run_id,'state',{'from':current,'to':state, 'result':result} if result is not None else {'from':current,'to':state})

    def issue(self, run_id, role, ttl=900):
        if role not in ('red','blue','operator') or not 0 < ttl <= 3600:
            raise ValueError('invalid credential scope')
        if self.get(run_id)['state'] not in ('CREATED','PRECHECK','RUNNING'):
            raise ValueError('run closed')
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('INSERT INTO grants VALUES(?,?,?,?)',(digest(token),run_id,role,time.time()+ttl))
        return token

    def authorize(self, run_id, token, action):
        permissions = {'submit_test':('red',), 'set_defence':('blue',), 'read_summary':('operator',)}
        with self.connect() as db:
            grant = db.execute('SELECT * FROM grants WHERE token_hash=?',(digest(token),)).fetchone()
        run = self.get(run_id)
        allowed = bool(grant and grant['run_id']==run_id and grant['expires']>time.time() and
                       grant['role'] in permissions.get(action,()) and run['state'] in ('CREATED','PRECHECK','RUNNING'))
        if run['state'] in ('CREATED','PRECHECK','RUNNING'):
            self.event(run_id,'broker_request',{'action':action if action in permissions else 'unknown','role':grant['role'] if grant else 'unknown','allowed':allowed})
        return allowed

    def seal(self, run_id):
        if self.get(run_id)['state'] != 'COMPLETE':
            raise ValueError('only complete runs may be sealed')
        events = self.events(run_id)
        checkpoint = dict(run_id=run_id,count=len(events),head=events[-1]['hash'] if events else '0'*64)
        path = self.anchors / (run_id+'.json')
        # Never overwrite an existing anchor after evidence is modified.
        with path.open('x', encoding='utf-8') as f:
            json.dump(checkpoint,f,sort_keys=True)
            f.flush(); os.fsync(f.fileno())
        return checkpoint

    def export(self, run_id):
        path = self.anchors/(run_id+'.json')
        checkpoint = json.loads(path.read_text()) if path.exists() else None
        run = self.get(run_id)
        events = self.events(run_id)
        good = bool(checkpoint and verify(events,checkpoint))
        # Reconstruct result fields from the anchored event stream, not mutable run rows.
        if good:
            manifest_event = events[0]
            manifest = manifest_event['details']['manifest']
            if digest(manifest) != manifest_event['details']['sha256']:
                good = False
            else:
                run['manifest'] = manifest
                run['manifest_hash'] = digest(manifest)
                run['profile'] = manifest['profile']
                checks = {key:{'status':'NOT_RUN','detail':'No recorded check'} for key in REQUIRED}
                for event in events:
                    if event['kind']=='check':
                        detail=event['details']
                        if detail.get('name') in checks:
                            checks[detail['name']]={k:v for k,v in detail.items() if k!='name'}
                    elif event['kind']=='state':
                        run['state']=event['details']['to']
                        if 'result' in event['details']:
                            run['result']=event['details']['result']
                run['checks']=checks
                statuses=[checks[key]['status'] for key in REQUIRED]
                run['verdict']='INVALID' if 'FAIL' in statuses else 'VALID_UNDER_TESTED_MANIFEST' if run['state']=='COMPLETE' and all(s=='PASS' for s in statuses) else 'INCONCLUSIVE'
        if checkpoint and not good:
            run['verdict'] = 'INVALID'
        elif not checkpoint:
            run['verdict'] = 'INCONCLUSIVE'
        return dict(format='boundarylab-evidence-v1',run=run,events=events,checkpoint=checkpoint,verified=good)
