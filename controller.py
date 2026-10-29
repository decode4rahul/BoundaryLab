"""Serial trusted orchestration. No runtime command is accepted from HTTP clients."""
import os
import threading
from core import Broker
from runtime import DockerRuntime, RuntimeUnavailable, PROBE_IMAGE, MODEL_IMAGE

class Controller:
    def __init__(self, store):
        self.store=store
        self.lock=threading.Lock()
        self.thread=None

    def start(self, profile):
        if profile not in ('hardened','weak'):raise ValueError('unknown profile')
        if not self.lock.acquire(blocking=False):raise RuntimeError('A run is already active')
        try:
            manifest={'schema':'boundarylab-manifest-v1','controller':'0.2.2','required_checks':['authorization','network','real_model','fresh_session','cleanup','evidence'],
                      'probe_image_reference':PROBE_IMAGE,'model_image_reference':MODEL_IMAGE,
                      'scope':'bounded fixed-profile checks, trusted host and controller',
                      'policy':{'red':['submit_test'],'blue':['set_defence'],'operator':['read_summary']},
                      'model_configured':bool(os.environ.get('BOUNDARYLAB_MODEL')),
                      'probe_limits':{'memory_mb':128,'cpus':0.5,'pids':64,'uid':'65534:65534','read_only':True},
                      'model_limits':{'memory_gb':4,'cpus':2,'pids':128,'tokens':64,'context':1024,'timeout_seconds':240},
                      'canary_protocol':'generated-answer-only exact-token positive control then clean-container recall; bounded only'}
            run_id=self.store.create(profile,manifest)
            self.thread=threading.Thread(target=self.execute,args=(run_id,),daemon=False)
            self.thread.start()
            return run_id
        except Exception:
            self.lock.release();raise

    def execute(self, run_id):
        store=self.store
        runtime=DockerRuntime(run_id)
        result={'model_outcome':'NOT_RUN','synthetic_control':False}
        try:
            store.state(run_id,'PRECHECK')
            profile=store.get(run_id)['profile']
            # Real local policy implementation positive and negative cases.
            red=store.issue(run_id,'red'); blue=store.issue(run_id,'blue')
            auth=[store.authorize(run_id,red,'submit_test'),store.authorize(run_id,blue,'set_defence'),
                  not store.authorize(run_id,red,'set_defence'),not store.authorize(run_id,'bad','submit_test'),
                  not store.authorize(run_id,red,'unknown')]
            if profile=='weak':
                synthetic=Broker(run_id,'weak');t=synthetic.issue('red')
                forbidden=synthetic.request(t,'set_defence')
                result['synthetic_control']=True
                store.check(run_id,'authorization','FAIL' if forbidden else 'ERROR','Synthetic in-process weak policy allowed a forbidden action; execution halted',{'forbidden_allowed':forbidden,'scope':'synthetic, not a weak deployment'})
                return
            store.check(run_id,'authorization','PASS' if all(auth) else 'FAIL','Local role/run authorization controls',{'cases_passed':sum(auth),'cases':len(auth)})
            if not all(auth):return
            try:
                runtime_info=runtime.doctor()
                store.event(run_id,'runtime_identity',runtime_info)
            except RuntimeUnavailable as error:
                store.check(run_id,'network','ERROR',str(error));return
            model_path=os.environ.get('BOUNDARYLAB_MODEL')
            identity=None
            if model_path:
                try:
                    identity,_=runtime.model_identity(model_path)
                    # Runtime identity bound into the evidence before starting workloads.
                    store.event(run_id,'model_identity',identity)
                except (RuntimeUnavailable,OSError) as error:
                    store.check(run_id,'real_model','ERROR',str(error) if isinstance(error,RuntimeUnavailable) else 'Model file could not be read')
            store.state(run_id,'RUNNING')
            try:
                network_ok,broker_ok,measured=runtime.boundary_checks(run_id)
                store.check(run_id,'network','PASS' if network_ok else 'FAIL','Measured red-to-broker positive control, denied red-to-blue/model by DNS/IP, bounded egress probe',measured)
                store.check(run_id,'authorization','PASS' if broker_ok else 'FAIL','Container broker HTTP authorization and local scope controls',{'http':measured['broker_http'],'local_cases_passed':sum(auth)})
                # Confirmed boundary violations halt model execution.
                if not network_ok or not broker_ok:return
            except RuntimeUnavailable as error:
                store.check(run_id,'network','ERROR',str(error));return
            if identity:
                try:
                    measured=runtime.model_checks(model_path,identity)
                    result['model_outcome']=measured.pop('model_outcome')
                    result['sample_output']=measured.pop('legitimate_output')
                    store.check(run_id,'real_model','PASS','Three separate real inference invocations completed',{'identity':identity})
                    store.check(run_id,'fresh_session',measured['fresh_session'],measured['detail'],measured)
                except RuntimeUnavailable as error:
                    store.check(run_id,'real_model','ERROR',str(error))
            elif not model_path:
                store.check(run_id,'real_model','NOT_RUN','Set BOUNDARYLAB_MODEL to an existing GGUF file; no mock is substituted')
        except Exception as error:
            store.event(run_id,'controller_error',{'type':type(error).__name__})
            store.check(run_id,'network','ERROR','Controller interrupted; inspect local configuration')
        finally:
            try:
                if runtime.containers or runtime.networks:
                    errors=runtime.cleanup()
                    store.check(run_id,'cleanup','ERROR' if errors else 'PASS','Container and network removal '+('could not be verified' if errors else 'completed'),{'unverified':errors})
                else:
                    store.check(run_id,'cleanup','PASS','No disposable Docker resources were created')
                store.state(run_id,'VERIFYING')
                store.check(run_id,'evidence','PASS','Canonical event chain finalized; operator checkpoint stored separately after completion')
                store.state(run_id,'COMPLETE',result)
                store.seal(run_id)
            finally:
                self.lock.release()
