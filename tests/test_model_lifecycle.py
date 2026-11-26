"""Deterministic lifecycle/integration checks, never actual GPU allocation/signals."""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import threading
import time

import httpx
import pytest

from iam_sra.assessment import AssessmentError
from iam_sra.model_lifecycle import OnDemandModel, ProjectA2


class Backend:
    def __init__(self):
        self.starts=0;self.stops=0;self.running=False;self.busy=False;self.release_ok=True
    def owns_running_model(self):return self.running
    def start(self,deadline):
        self.starts+=1
        if self.busy:raise AssessmentError('Unavailable',code='gpu_unavailable')
        self.running=True
    def stop(self):
        self.stops+=1
        if self.release_ok:self.running=False
        return self.release_ok


def controller():
    now=[100.0];b=Backend();m=OnDemandModel(b,60,clock=lambda:now[0])
    return m,b,now


def test_no_gpu_for_status_and_model_restarts_after_idle_release():
    m,b,now=controller()
    for _ in range(10):assert m.status()['state']=='idle'
    assert b.starts==0
    with m.lease(1000):assert b.starts==1 and m.active==1
    now[0]+=59;m.release_if_idle();assert b.stops==0
    now[0]+=1;m.release_if_idle();assert b.stops==1 and m.status()['state']=='idle'
    with m.lease(1000):assert b.starts==2
    m.close();assert b.stops==2


def test_review_manager_selects_isolated_davinci_v100_profile(monkeypatch):
    import iam_sra.model_lifecycle as module
    class V100:
        def __init__(self,port,*,remote_dir,variant):
            self.port=port;self.remote_dir=remote_dir;self.variant=variant
            self.starts=0;self.stops=0
        def owns_running_model(self):return False
        def start(self,deadline):self.starts+=1
        def stop(self):self.stops+=1;return True
    monkeypatch.setattr(module,'_manager',None)
    monkeypatch.setattr(module,'ProjectDavinciV100',V100)
    monkeypatch.setenv('IAM_SRA_ON_DEMAND_GPU','1')
    monkeypatch.setenv('IAM_BASE_URL','http://127.0.0.1:18020')
    monkeypatch.setenv('IAM_SRA_GPU_IDLE_SECONDS','300')
    monkeypatch.setenv('IAM_SRA_GPU_PROFILE','davinci-v100')
    monkeypatch.setenv('IAM_SRA_REMOTE_DIR','iam-sra-v100-fn-review-test')
    monkeypatch.setenv('IAM_MODEL_VARIANT','fp16')
    monkeypatch.setenv('IAM_MODEL_THINKING','0')
    managed=module.manager()
    assert managed.backend.port==18020
    assert managed.backend.remote_dir=='iam-sra-v100-fn-review-test'
    assert managed.backend.variant=='fp16' and managed.status()['state']=='idle'
    assert managed.backend.starts==0
    managed.close()


def test_v100_review_manager_preserves_thinking_setting_without_starting_gpu(monkeypatch):
    import iam_sra.model_lifecycle as module
    monkeypatch.setattr(module,'_manager',None)
    for key,value in {
        'IAM_SRA_ON_DEMAND_GPU':'1','IAM_BASE_URL':'http://127.0.0.1:18021',
        'IAM_SRA_GPU_IDLE_SECONDS':'300','IAM_SRA_GPU_PROFILE':'davinci-v100',
        'IAM_SRA_REMOTE_DIR':'iam-sra-v100-final-test','IAM_MODEL_VARIANT':'fp16',
        'IAM_MODEL_THINKING':'1',
    }.items():monkeypatch.setenv(key,value)
    manager=module.manager()
    assert manager.backend.thinking is True
    assert manager.backend.variant=='fp16'
    assert manager.backend.port==18021
    assert manager.status()['state']=='idle'
    manager.close()


def test_v100_remote_start_command_carries_thinking_settings(monkeypatch,tmp_path):
    from iam_sra.model_lifecycle import ProjectDavinciV100
    from types import SimpleNamespace
    monkeypatch.setenv('IAM_MODEL_THINKING','1')
    monkeypatch.setenv('IAM_MODEL_VARIANT','fp16')
    calls=[]
    def run(command,**kwargs):
        calls.append((command,kwargs));return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess,'run',run)
    backend=ProjectDavinciV100(18021,root=tmp_path,remote_dir='iam-sra-v100-final-test',variant='fp16')
    assert backend._remote_command('prepare','lease')
    command,kwargs=calls[0]
    assert '--thinking' in command
    assert kwargs['env']['IAM_MODEL_THINKING']=='1'


def test_inflight_inference_is_never_unloaded_even_after_idle_interval():
    m,b,now=controller()
    with m.lease(1000):
        now[0]+=1000;m.release_if_idle();assert b.stops==0
    m.release_if_idle();assert b.stops==0
    now[0]+=60;m.release_if_idle();assert b.stops==1


def test_job_failure_still_releases_after_inactivity():
    m,b,now=controller()
    with pytest.raises(RuntimeError):
        with m.lease(1000):raise RuntimeError('Synthetic inference failure')
    assert m.active==0
    now[0]+=60;m.release_if_idle();assert b.stops==1


def test_busy_gpu_never_preempts_any_workload_and_retry_can_succeed():
    m,b,now=controller();b.busy=True
    with pytest.raises(AssessmentError,match='unavailable'): 
        with m.lease(1000):pytest.fail('Inference started on busy device')
    assert m.status()['state']=='unavailable' and b.stops==0 and not b.running
    with pytest.raises(AssessmentError):
        with m.lease(1000):pass
    assert b.starts==1  # Short cooldown, no hot-looping launch attempts.
    now[0]+=16;b.busy=False
    with m.lease(1000):assert b.starts==2
    m.close()


def test_close_waits_for_active_request_to_return_then_releases():
    m,b,now=controller()
    with m.lease(1000):
        m.close();assert b.stops==0
    assert b.stops==1
    with pytest.raises(AssessmentError):
        with m.lease(1000):pass


def test_release_failure_is_visible_and_never_claims_gpu_idle():
    m,b,now=controller()
    with m.lease(1000):pass
    b.release_ok=False;now[0]+=61;m.release_if_idle()
    assert m.status()['state']=='unavailable' and m.running
    with pytest.raises(AssessmentError):
        with m.lease(1000):pass
    b.release_ok=True;now[0]+=16;m.release_if_idle()
    assert m.status()['state']=='idle' and not m.running


def test_parallel_calls_share_a_start_and_wait_until_both_complete():
    m,b,now=controller();started=threading.Barrier(3);release=threading.Event()
    def inference():
        with m.lease(1000):started.wait(timeout=3);release.wait(timeout=3)
    threads=[threading.Thread(target=inference) for _ in range(2)]
    for t in threads:t.start()
    started.wait(timeout=3);assert m.active==2 and b.starts==1
    now[0]+=1000;m.release_if_idle();assert b.stops==0
    release.set()
    for t in threads:t.join(timeout=3);assert not t.is_alive()
    m.close();assert b.stops==1


def project(monkeypatch,tmp_path):
    import iam_sra.model_lifecycle as module
    root=tmp_path/'project';(root/'.runtime').mkdir(parents=True)
    proc=tmp_path/'proc';entry=proc/'123';entry.mkdir(parents=True)
    command=['/existing/python',str(root/'scripts/supervise.py'),'vllm','synthetic launch']
    fields=['0']*20;fields[19]='start-123'
    (entry/'stat').write_text('123 (python) '+' '.join(fields))
    (entry/'cmdline').write_bytes(b'\0'.join(s.encode() for s in command)+b'\0')
    row={'pid':123,'root':str(root),'start_time':'start-123','command':command,
         'environment':{'IAM_GPU_PROFILE':'liono-a2','IAM_BASE_URL':'http://127.0.0.1:18003','IAM_SRA_MODEL_LEASE_ID':'ours'}}
    monkeypatch.setattr(module,'Path',lambda v:proc if v=='/proc' else Path(v))
    monkeypatch.setattr(module.os,'getpgid',lambda pid:pid)
    monkeypatch.setattr(module.socket,'gethostname',lambda:'liono')
    backend=ProjectA2(18003,root=root)
    monkeypatch.setattr(backend,'_idle_gpu_uuid',lambda:'GPU-A2')
    backend.record.write_text(json.dumps(row))
    backend._write_marker({'port':18003,'lease_id':'ours'})
    signals=[]
    def kill(pid,sig):
        if sig==0:raise ProcessLookupError
        signals.append((pid,sig))
    monkeypatch.setattr(module.os,'killpg',kill)
    return backend,row,signals,module


@pytest.mark.parametrize('fault',['other_lease','wrong_gpu','different_port','pid_reuse','another_command'])
def test_cleanup_refuses_every_unverified_or_nonreview_process(monkeypatch,tmp_path,fault):
    b,row,signals,module=project(monkeypatch,tmp_path)
    if fault=='other_lease':row['environment']['IAM_SRA_MODEL_LEASE_ID']='someone-else'
    if fault=='wrong_gpu':row['environment']['IAM_GPU_PROFILE']='liono-v100s'
    if fault=='different_port':row['environment']['IAM_BASE_URL']='http://127.0.0.1:18002'
    if fault=='pid_reuse':row['start_time']='old-start'
    if fault=='another_command':row['command']=['another model']
    b.record.write_text(json.dumps(row))
    assert not b.stop() and not signals
    assert b.record.exists() and b.marker.exists()


def test_cleanup_signals_only_our_verified_group_and_clears_only_our_records(monkeypatch,tmp_path):
    b,row,signals,module=project(monkeypatch,tmp_path)
    assert b.stop() and signals==[(123,signal.SIGTERM)]
    assert not b.marker.exists() and not b.record.exists()


def test_record_replaced_during_stop_is_retained(monkeypatch,tmp_path):
    b,row,signals,module=project(monkeypatch,tmp_path);replacement={**row,'pid':456}
    def kill(pid,sig):
        if sig==0:raise ProcessLookupError
        signals.append((pid,sig));b.record.write_text(json.dumps(replacement))
    monkeypatch.setattr(module.os,'killpg',kill)
    assert b.stop() and json.loads(b.record.read_text())==replacement


def test_legacy_release_requires_explicit_adoption_of_exact_a2(monkeypatch,tmp_path):
    b,row,signals,module=project(monkeypatch,tmp_path)
    b.marker.unlink();row['environment'].pop('IAM_SRA_MODEL_LEASE_ID');b.record.write_text(json.dumps(row))
    assert not b.stop() and not signals  # No automatic adoption of an unmarked model.
    assert b.release_existing() and signals==[(123,signal.SIGTERM)]


@pytest.mark.parametrize('kind',['busy','partial_start'])
def test_failed_start_cleans_our_partial_model_but_never_another_launch(monkeypatch,tmp_path,kind):
    b,row,signals,module=project(monkeypatch,tmp_path);b.marker.unlink()
    def run(cmd,**kwargs):
        if kind=='partial_start':row['environment']['IAM_SRA_MODEL_LEASE_ID']=kwargs['env']['IAM_SRA_MODEL_LEASE_ID']
        b.record.write_text(json.dumps(row))
        raise subprocess.CalledProcessError(1,cmd)
    monkeypatch.setattr(module.subprocess,'run',run)
    with pytest.raises(AssessmentError):b.start(time.monotonic()+100)
    assert len(signals)==(1 if kind=='partial_start' else 0)
    assert not b.marker.exists()


def test_invalid_marker_is_retained_without_signals(monkeypatch,tmp_path):
    b,row,signals,module=project(monkeypatch,tmp_path);b.marker.write_text('corrupt marker')
    assert not b.stop() and not signals
    with pytest.raises(AssessmentError):b.start(time.monotonic()+100)


def test_model_guard_is_disabled_by_default_and_rejects_remote_endpoint(monkeypatch):
    import iam_sra.model_lifecycle as module
    monkeypatch.delenv('IAM_SRA_ON_DEMAND_GPU',raising=False)
    assert module.public_status()=={'mode':'always_on','state':'unmanaged'}
    monkeypatch.setenv('IAM_SRA_ON_DEMAND_GPU','1');monkeypatch.setattr(module,'_manager',None)
    monkeypatch.setenv('IAM_BASE_URL','http://remote.invalid:18003')
    with pytest.raises(ValueError):module.manager()


def test_real_client_lifecycle_clear_answers_idle_restart_and_busy_recovery(monkeypatch):
    import iam_sra.model_lifecycle as module
    from iam_sra.chat_client import ChatClient
    from test_fn_interpretation import opening,install_http,DEFINITION,USES
    from fn_fixture import reply
    m,b,now=controller();monkeypatch.setattr(module,'manager',lambda:m)
    monkeypatch.setenv('IAM_BASE_URL','http://127.0.0.1:18003')
    calls=install_http(monkeypatch,lambda request,attempt:reply(request))
    s=opening();assert b.starts==0  # Profile/city/depth/recognition need no model.
    client=ChatClient(base_url='http://127.0.0.1:18003')
    s.send(DEFINITION,client)
    assert s.objective=='drone_uses' and b.starts==1 and not s.failed_turn_id
    now[0]+=61;m.release_if_idle();assert b.stops==1
    b.busy=True;s.send(USES,client)
    assert s.objective=='drone_uses' and s.failed_turn_id
    assert 'shared GPU' in s.messages[-1]['text'] and 'saved' in s.messages[-1]['text']
    assert sum(path=='/v1/chat/completions' for path,_ in calls)==1
    b.busy=False;now[0]+=16;s.send('retry',client)
    assert s.objective=='healthcare_awareness' and not s.failed_turn_id
    assert len([e for e in s.active_evidence() if e['text']==USES])==1
    assert sum(path=='/v1/chat/completions' for path,_ in calls)==2
    m.close()


def test_unscreened_private_input_cannot_wake_the_gpu(monkeypatch):
    import iam_sra.model_lifecycle as module
    from iam_sra.chat_client import ChatClient
    from test_fn_interpretation import opening
    from iam_sra.privacy import PrivacyError
    m,b,now=controller();monkeypatch.setattr(module,'manager',lambda:m)
    s=opening()
    with pytest.raises(PrivacyError):s.send('Email alice@example.com',ChatClient())
    assert b.starts==0


def test_status_and_capabilities_never_start_model(make_api,monkeypatch):
    import iam_sra.model_lifecycle as module
    m,b,now=controller();monkeypatch.setattr(module,'manager',lambda:m)
    app,service=make_api();client=app.test_client()
    for _ in range(3):
        assert client.get('/v1/capabilities').json['inference']['state']=='idle'
        assert client.get('/v1/inference-status').json['inference']['state']=='idle'
    assert b.starts==0


from test_api_integration import make_api


def test_successful_start_carries_unique_lease_into_verified_project_record(monkeypatch,tmp_path):
    b,row,signals,module=project(monkeypatch,tmp_path);b.marker.unlink()
    calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        row['environment']['IAM_SRA_MODEL_LEASE_ID']=kwargs['env']['IAM_SRA_MODEL_LEASE_ID']
        b.record.write_text(json.dumps(row))
    monkeypatch.setattr(module.subprocess,'run',run)
    b.start(time.monotonic()+100)
    assert b.owns_running_model()
    assert calls[0][2:4]==['start','liono-a2']
    assert calls[0][calls[0].index('--port')+1]=='18003'
    assert calls[0][calls[0].index('--gpu-uuid')+1]=='GPU-A2'
    assert b.stop() and signals==[(123,signal.SIGTERM)]


def test_ops_preserves_lease_marker_without_changing_regular_model_launch(monkeypatch,tmp_path):
    spec=importlib.util.spec_from_file_location('lease_ops',Path(__file__).parents[1]/'scripts/ops.py')
    ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)
    root=tmp_path/'project';root.mkdir();runtime=root/'.runtime'
    monkeypatch.setattr(ops,'ROOT',root);monkeypatch.setattr(ops,'RUNTIME',runtime)
    monkeypatch.setattr(ops,'PROFILE','liono-a2');monkeypatch.setattr(ops,'BASE_URL','http://127.0.0.1:18003')
    monkeypatch.setattr(ops,'recover_record',lambda _:False)
    monkeypatch.setattr(ops,'preflight',lambda **kwargs:['0'])
    monkeypatch.setattr(ops,'vllm_command',lambda row:['synthetic model launch'])
    monkeypatch.setattr(ops,'identity',lambda pid:'verified-start')
    class Process:pid=123
    monkeypatch.setattr(ops.subprocess,'Popen',lambda *args,**kwargs:Process())
    monkeypatch.setenv('IAM_SRA_MODEL_LEASE_ID','review-only-lease')
    ops.start('vllm')
    row=json.loads((runtime/'vllm.pid.json').read_text())
    assert row['environment']['IAM_SRA_MODEL_LEASE_ID']=='review-only-lease'
    (runtime/'vllm.pid.json').unlink();monkeypatch.delenv('IAM_SRA_MODEL_LEASE_ID')
    ops.start('vllm')
    row=json.loads((runtime/'vllm.pid.json').read_text())
    assert 'IAM_SRA_MODEL_LEASE_ID' not in row['environment']


def test_status_is_nonblocking_while_a_cold_start_is_waiting():
    m,b,now=controller();entered=threading.Event();release=threading.Event()
    def start(deadline):
        entered.set();release.wait(timeout=3);b.running=True
    b.start=start
    def inference():
        with m.lease(1000):pass
    worker=threading.Thread(target=inference);worker.start();assert entered.wait(timeout=3)
    assert m.status()['state']=='loading'
    release.set();worker.join(timeout=3);assert not worker.is_alive();m.close()


def test_small_foreign_compute_job_blocks_review_start(monkeypatch,tmp_path):
    import iam_sra.model_lifecycle as module
    root=tmp_path/'project';(root/'scripts').mkdir(parents=True)
    (root/'scripts/ops.py').write_text("def gpu():\n assert PROFILE == 'liono-a2'\n return ['0','GPU-A2','NVIDIA A2','8.6','16384','500']\n")
    b=ProjectA2(18003,root=root)
    monkeypatch.setattr(module.subprocess,'check_output',lambda *a,**kw:'GPU-A2, 456\n')
    with pytest.raises(AssessmentError):b.start(time.monotonic()+100)
    assert not b.marker.exists()


def test_idle_a2_selection_ignores_processes_on_other_cards(monkeypatch,tmp_path):
    import iam_sra.model_lifecycle as module
    root=tmp_path/'project';(root/'scripts').mkdir(parents=True)
    (root/'scripts/ops.py').write_text("def gpu():\n return ['0','GPU-A2','NVIDIA A2','8.6','16384','0']\n")
    b=ProjectA2(18003,root=root)
    monkeypatch.setattr(module.subprocess,'check_output',lambda *a,**kw:'GPU-OTHER, 456\n')
    assert b._idle_gpu_uuid()=='GPU-A2'


def test_unexpected_release_error_is_visible_and_watchdog_can_retry():
    m,b,now=controller()
    with m.lease(1000):pass
    def broken():raise PermissionError('Synthetic release failure')
    original=b.stop;b.stop=broken;now[0]+=61;m.release_if_idle()
    assert m.state=='unavailable' and m.running
    b.stop=original;now[0]+=16;m.release_if_idle()
    assert m.state=='idle' and not m.running


@pytest.mark.presidio_live
def test_real_privacy_accepts_gpu_unavailability_and_retry_export(monkeypatch):
    import iam_sra.model_lifecycle as module
    from iam_sra.chat_client import ChatClient
    from iam_sra.privacy import require_safe_data
    from test_fn_interpretation import opening,DEFINITION
    m,b,now=controller();b.busy=True
    monkeypatch.setattr(module,'manager',lambda:m)
    monkeypatch.setenv('IAM_BASE_URL','http://127.0.0.1:18003')
    s=opening();s.send(DEFINITION,ChatClient(base_url='http://127.0.0.1:18003'))
    assert s.failed_turn_id and s.objective=='drone_description'
    require_safe_data(s.export())
    assert not s.suggestion and not b.running


def test_force_shutdown_never_signals_a_reused_pid(monkeypatch,tmp_path):
    from types import SimpleNamespace
    b,row,signals,module=project(monkeypatch,tmp_path)
    now=[0]
    def clock():now[0]+=10;return now[0]
    monkeypatch.setattr(module,'time',SimpleNamespace(monotonic=clock,sleep=lambda _:None))
    def kill(pid,sig):
        if sig==0:return
        signals.append((pid,sig))
        fields=['0']*20;fields[19]='replacement-start'
        (tmp_path/'proc/123/stat').write_text('123 (python) '+' '.join(fields))
    monkeypatch.setattr(module.os,'killpg',kill)
    assert not b.stop()
    assert signals==[(123,signal.SIGTERM)]
    assert b.marker.exists()
