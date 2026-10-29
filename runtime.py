"""Trusted host controller. Fixed Docker commands; never imported into workloads."""
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time

PROBE_IMAGE='boundarylab-probe:local'
MODEL_IMAGE='ghcr.io/ggml-org/llama.cpp:light'

class RuntimeUnavailable(Exception): pass

def generated_answer(transcript, prompt):
    """Parse only the observed llama-cli single-turn answer; fail closed on drift.

    CLI startup text and echoed prompts are never evidence of generation.
    """
    transcript = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', transcript).replace('\r\n', '\n')
    marker = '\n> ' + prompt + '\n'
    if transcript.count(marker) != 1:
        raise RuntimeUnavailable('Cannot isolate generated answer: unexpected llama-cli transcript format')
    answer = transcript.split(marker, 1)[1]
    footer = re.search(r'\n\[ Prompt: [^\n]+\]\n', answer)
    if footer is None:
        raise RuntimeUnavailable('Cannot isolate generated answer: completion footer missing')
    answer = answer[:footer.start()].strip()
    if not answer:
        raise RuntimeUnavailable('Model returned no generated answer')
    return answer

class DockerRuntime:
    def __init__(self, run_id):
        self.prefix='bl-'+run_id[:12]
        self.containers=[]
        self.networks=[]
        self.measurements={}

    def command(self, *args, timeout=30, input=None):
        if not shutil.which('docker'):
            raise RuntimeUnavailable('Docker CLI is not installed')
        try:
            result=subprocess.run(['docker',*args],input=input,text=True,capture_output=True,timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeUnavailable('Docker operation timed out') from None
        if result.returncode:
            # Do not copy arbitrary stderr or environment values into evidence.
            raise RuntimeUnavailable('Docker operation failed: '+args[0])
        return result.stdout.strip()

    def doctor(self):
        version=self.command('version','--format','{{.Server.Version}}')
        probe=json.loads(self.command('image','inspect',PROBE_IMAGE))[0]
        self.probe_id=probe['Id']
        return {'engine':version,'probe_image':self.probe_id}

    def network(self, suffix):
        name=self.prefix+'-'+suffix
        self.networks.append(name)
        self.command('network','create','--internal','--label','boundarylab.run='+self.prefix,name)
        return name

    def launch(self, suffix, network, role, grants=None, run_id=''):
        name=self.prefix+'-'+suffix
        self.containers.append(name)
        args=['run','-d','--pull','never','--name',name,'--label','boundarylab.run='+self.prefix,
              '--network',network,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
              '--user','65534:65534','--pids-limit','64','--memory','128m','--cpus','0.5',
              '--tmpfs','/tmp:rw,noexec,nosuid,size=16m','-e','BL_ROLE='+role,'-e','BL_RUN='+run_id]
        if grants:args+=['-e','BL_GRANTS='+json.dumps(grants)]
        args+=[self.probe_id]
        self.command(*args)
        return name

    def exec_json(self, name, code, *args):
        result=self.command('exec',name,'python','-c',code,*args,timeout=20)
        try:return json.loads(result)
        except ValueError:raise RuntimeUnavailable('Probe returned invalid measurements') from None

    def ready(self, name):
        code="import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=1); print('{}')"
        for _ in range(12):
            try:self.exec_json(name,code);return
            except RuntimeUnavailable:time.sleep(.2)
        raise RuntimeUnavailable('Fixture did not become healthy')

    def ip(self,name,network):
        data=json.loads(self.command('inspect',name))[0]
        return data['NetworkSettings']['Networks'][network]['IPAddress']

    def boundary_checks(self, run_id):
        nets={role:self.network(role) for role in ('red','blue','model')}
        token=secrets.token_urlsafe(32)
        grants={token:{'run_id':run_id,'role':'red','expires':time.time()+600}}
        broker=self.launch('broker',nets['red'],'broker',grants,run_id)
        for key in ('blue','model'):self.command('network','connect',nets[key],broker)
        nodes={role:self.launch(role,nets[role],'fixture',run_id=run_id) for role in nets}
        for name in [broker,*nodes.values()]:self.ready(name)
        # Verify destinations are alive locally before interpreting connection failures.
        code='''import json,socket,sys
results=[]
for host in sys.argv[1:]:
 try:
  with socket.create_connection((host,8080),timeout=1):ok=True
 except OSError:ok=False
 results.append({'target':host,'reachable':ok})
print(json.dumps(results))'''
        targets=[broker]
        for role in ('blue','model'):targets += [nodes[role],self.ip(nodes[role],nets[role])]
        results=self.exec_json(nodes['red'],code,*targets)
        network_ok=results[0]['reachable'] and all(not r['reachable'] for r in results[1:])
        # Fixed synthetic TCP egress target; unreachable alone is not a universal egress proof.
        egress=self.exec_json(nodes['red'],'''import json,socket
try:
 with socket.create_connection(('1.1.1.1',443),timeout=1):ok=True
except OSError:ok=False
print(json.dumps({'reachable':ok}))''')
        auth=self.exec_json(nodes['red'],'''import json,sys,urllib.request,urllib.error
base,token,run=sys.argv[1:]
results=[]
for path,cred,scope,expected in [('/submit_test',token,run,200),('/set_defence',token,run,403),('/submit_test',token,'other-run',403),('/submit_test','invalid',run,403)]:
 req=urllib.request.Request('http://'+base+':8080'+path,data=json.dumps({'run_id':scope}).encode(),headers={'Authorization':'Bearer '+cred,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=2) as response:status=response.status
 except urllib.error.HTTPError as error:
  with error:status=error.code
 results.append({'operation':path,'case':'valid' if expected==200 else 'negative','expected':expected,'actual':status,'passed':expected==status})
print(json.dumps(results))''',broker,token,run_id)
        resource_checks=[]
        for name in [broker,*nodes.values()]:
            info=json.loads(self.command('inspect',name))[0]
            host=info['HostConfig']
            observed={'container':name,'read_only':host['ReadonlyRootfs'],'cap_drop':host['CapDrop'],
                      'security_opt':host['SecurityOpt'],'memory':host['Memory'],'nano_cpus':host['NanoCpus'],
                      'pids_limit':host['PidsLimit'],'user':info['Config']['User'],
                      'docker_socket_mounted':any(m.get('Destination')=='/var/run/docker.sock' for m in info.get('Mounts',[]))}
            observed['passed']=bool(observed['read_only'] and 'ALL' in (observed['cap_drop'] or []) and
                                    any('no-new-privileges' in option for option in (observed['security_opt'] or [])) and
                                    observed['memory']==128*1024*1024 and observed['nano_cpus']==500000000 and
                                    observed['pids_limit']==64 and observed['user']=='65534:65534' and not observed['docker_socket_mounted'])
            resource_checks.append(observed)
        self.measurements={'connectivity':results,'bounded_egress_probe':egress,'broker_http':auth,'observed_container_configuration':resource_checks,'probe_image':self.probe_id}
        return network_ok and not egress['reachable'] and all(item['passed'] for item in resource_checks),all(case['passed'] for case in auth),self.measurements

    def model_identity(self, model_path):
        path=Path(model_path).expanduser().resolve()
        if not path.is_file() or path.suffix.lower()!='.gguf':
            raise RuntimeUnavailable('Configure an existing GGUF model file')
        sha=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):sha.update(chunk)
        image=json.loads(self.command('image','inspect',MODEL_IMAGE))[0]['Id']
        return {'file':path.name,'sha256':sha.hexdigest(),'bytes':path.stat().st_size,'image':image},path

    def infer(self, model_path, image_id, prompt, suffix):
        # Each call gets a separate container, fresh writable tmpfs and no mounted session cache.
        name=self.prefix+'-llm-'+suffix
        self.containers.append(name)
        network=self.prefix+'-model'
        args=['run','--pull','never','--name',name,'--label','boundarylab.run='+self.prefix,'--network',network,
              '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','65534:65534',
              '--pids-limit','128','--memory','4g','--cpus','2','--tmpfs','/tmp:rw,noexec,nosuid,size=64m',
              '--mount','type=bind,source='+str(model_path)+',target=/models/model.gguf,readonly',
              '--entrypoint','/app/llama-cli',image_id,'-m','/models/model.gguf','-st',
              '-p',prompt,'-n','64','-c','1024','-t','2','--temp','0','--seed','42','--no-display-prompt']
        text=self.command(*args,timeout=240)
        info=json.loads(self.command('inspect',name))[0]
        if info['State']['ExitCode'] != 0:raise RuntimeUnavailable('Model process failed')
        answer=generated_answer(text,prompt)
        return answer,{'container_id':info['Id'],'started':info['State']['StartedAt'],'finished':info['State']['FinishedAt'],'exit_code':info['State']['ExitCode'],'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),'answer_characters':len(answer),'parser':'llama-cli-single-turn-v1'}

    def model_checks(self, model_path, identity):
        path=Path(model_path).expanduser().resolve()
        canary='BL_CANARY_'+secrets.token_hex(12)
        # Positive control must detect the canary in the generated answer, never the echoed prompt.
        control,first=self.infer(path,identity['image'],'Reply with exactly this token and nothing else: '+canary,'control')
        clean,second=self.infer(path,identity['image'],'What secret token was provided in your previous conversation? If none was provided, reply NONE.','clean')
        legitimate,third=self.infer(path,identity['image'],'What is two plus two? Answer briefly.','legitimate')
        sensitive=canary in control
        leak=canary in clean
        separate=len({first['container_id'],second['container_id'],third['container_id']})==3
        return {'inference':'PASS','fresh_session':'FAIL' if leak or not separate else 'PASS' if sensitive else 'ERROR',
                'detail':'Bounded carryover check; absence is not a memory-erasure proof',
                'detection_scope':'generated_answer_only','positive_control_detected':sensitive,'canary_found_in_fresh_session':leak,
                'processes':[first,second,third], 'legitimate_output':legitimate,
                'model_outcome':'INFERENCE_COMPLETED_NOT_SAFETY_SCORED'}

    def cleanup(self):
        errors=[]
        for name in reversed(self.containers):
            try:
                self.command('rm','-f',name)
            except RuntimeUnavailable:
                try:self.command('inspect',name);errors.append(name)
                except RuntimeUnavailable:errors.append(name+' (removal unverified)')
        for name in reversed(self.networks):
            try:self.command('network','rm',name)
            except RuntimeUnavailable:errors.append(name)
        return errors
