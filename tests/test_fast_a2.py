"""Fast A2 configuration/provenance tests; no GPU or real model download."""
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

import httpx
import pytest
from iam_sra.model_spec import load_model,snapshot_path,validate_awq_snapshot
from iam_sra.model_lifecycle import ProjectA2
from test_model_launch_selection import load_ops
from test_fn_review_link import launcher
from test_model_lifecycle import project

ROOT=Path(__file__).resolve().parents[1]


def fixture_root(tmp_path):
    (tmp_path/'configs').mkdir()
    for name in ('model.json','model-awq.json'):
        (tmp_path/'configs'/name).write_bytes((ROOT/'configs'/name).read_bytes())
    path=snapshot_path(tmp_path,load_model(tmp_path,'awq'));path.mkdir(parents=True)
    (path/'config.json').write_text(json.dumps({'model_type':'qwen3','quantization_config':{'bits':4,'quant_method':'awq'}}))
    (path/'model.safetensors.index.json').write_text(json.dumps({'weight_map':{'synthetic.weight':'model-00001.safetensors'}}))
    for name in ['model-00001.safetensors','tokenizer.json','tokenizer_config.json']:(path/name).write_bytes(b'Synthetic fixture, not real model data.')
    return path


def test_separate_pins_and_default_full_precision_are_preserved(monkeypatch):
    monkeypatch.delenv('IAM_MODEL_VARIANT',raising=False)
    original=json.loads((ROOT/'configs/model.json').read_text())
    assert load_model(ROOT)==original and original['revision']=='b968826d9c46dd6066d109eabc6255188de91218'
    awq=load_model(ROOT,'awq')
    assert awq['model']=='Qwen/Qwen3-8B-AWQ' and awq['revision']=='4da05a8edb55c6046cce958586c33b61da07bb79'
    assert awq['weight_bits']==4 and awq['quantization']=='awq_marlin'
    assert snapshot_path(ROOT,awq)!=snapshot_path(ROOT,original)


def test_awq_uses_marlin_and_zero_offload_with_the_existing_safety_contract(monkeypatch,tmp_path):
    path=fixture_root(tmp_path);ops=load_ops()
    monkeypatch.setattr(ops,'ROOT',tmp_path);monkeypatch.setenv('IAM_MODEL_VARIANT','awq')
    monkeypatch.delenv('IAM_CPU_OFFLOAD_GB',raising=False)
    command=ops.vllm_command(['0','GPU-A2','NVIDIA A2','8.6','15360'])
    for flag,value in [('--model',str(path)),('--served-model-name','Qwen/Qwen3-8B-AWQ'),
        ('--cpu-offload-gb','0.0'),('--quantization','awq_marlin'),('--dtype','half'),('--host','127.0.0.1'),
        ('--max-model-len','4096'),('--max-num-seqs','1'),('--guided-decoding-backend','xgrammar')]:
        assert command[command.index(flag)+1]==value
    assert '--disable-log-requests' in command and '--enforce-eager' in command


def test_awq_cannot_silently_reenable_cpu_offload_or_run_on_v100(monkeypatch,tmp_path):
    fixture_root(tmp_path);ops=load_ops();monkeypatch.setattr(ops,'ROOT',tmp_path)
    monkeypatch.setenv('IAM_MODEL_VARIANT','awq');monkeypatch.setenv('IAM_CPU_OFFLOAD_GB','8')
    with pytest.raises(RuntimeError,match='zero CPU offload'):ops.cpu_offload(['0','','','','16384'])
    monkeypatch.delenv('IAM_CPU_OFFLOAD_GB')
    with pytest.raises(RuntimeError,match='Ampere'):ops.vllm_command(['0','GPU-X','V100','7.0','32768'])


@pytest.mark.parametrize('fault',['missing_shard','empty_shard','wrong_bits','wrong_method','unsafe_index'])
def test_cache_validation_rejects_incomplete_or_wrong_artifact(tmp_path,fault):
    path=fixture_root(tmp_path)
    if fault=='missing_shard':(path/'model-00001.safetensors').unlink()
    if fault=='empty_shard':(path/'model-00001.safetensors').write_bytes(b'')
    if fault in {'wrong_bits','wrong_method'}:
        value=json.loads((path/'config.json').read_text())
        value['quantization_config']['bits' if fault=='wrong_bits' else 'quant_method']=8 if fault=='wrong_bits' else 'another-method'
        (path/'config.json').write_text(json.dumps(value))
    if fault=='unsafe_index':(path/'model.safetensors.index.json').write_text(json.dumps({'weight_map':{'weight':'../foreign.safetensors'}}))
    with pytest.raises(ValueError):validate_awq_snapshot(path)


def test_prepared_cache_needs_no_network_gpu_or_reinstall(monkeypatch,tmp_path):
    fixture_root(tmp_path);module=launcher();monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:pytest.fail('Already cached: do not download or start'))
    assert module.prepare_review_model('awq')['model']=='Qwen/Qwen3-8B-AWQ'


def test_review_default_is_fast_awq_but_original_is_explicitly_available(capsys):
    module=launcher();assert module.main(['--dry-run'])==0
    plan=json.loads(capsys.readouterr().out)
    assert plan['model_variant']=='awq' and plan['cpu_offload_gb']==0 and plan['idle_seconds']==60
    assert module.main(['--model-variant','fp16','--dry-run'])==0
    plan=json.loads(capsys.readouterr().out);assert plan['model_variant']=='fp16' and plan['cpu_offload_gb']==8


def test_new_process_model_name_and_provenance_select_actual_quantized_artifact():
    result=subprocess.run([sys.executable,'-c',"import json; from iam_sra.settings import MODEL,config; print(json.dumps({'model':MODEL,'spec':config('model')}))"],
        cwd=ROOT,env={**os.environ,'IAM_MODEL_VARIANT':'awq','PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,check=True)
    value=json.loads(result.stdout)
    assert value['model']==value['spec']['model']=='Qwen/Qwen3-8B-AWQ'
    assert value['spec']['quantization']=='awq_marlin'


def test_readiness_requires_the_selected_model_alias(monkeypatch):
    spec=importlib.util.spec_from_file_location('fast_model_ready',ROOT/'scripts/wait-model.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setenv('IAM_MODEL_VARIANT','awq')
    def endpoint(req):return httpx.Response(200,json={'data':[{'id':'Qwen/Qwen3-8B'}]})
    with httpx.Client(transport=httpx.MockTransport(endpoint)) as client:
        assert not module.ready(client,'http://127.0.0.1:18003',time.monotonic()+10)
    def endpoint(req):return httpx.Response(200,json={'data':[{'id':'Qwen/Qwen3-8B-AWQ'}]})
    with httpx.Client(transport=httpx.MockTransport(endpoint)) as client:
        assert module.ready(client,'http://127.0.0.1:18003',time.monotonic()+10)


def test_owner_cannot_reuse_a_different_precision_and_cleans_its_wrong_start(monkeypatch,tmp_path):
    backend,row,signals,module=project(monkeypatch,tmp_path);backend.variant='awq'
    assert not backend.owns_running_model()  # Old fp16 is never presented as AWQ.
    backend.marker.unlink()
    def run(cmd,**kwargs):
        row['environment']['IAM_SRA_MODEL_LEASE_ID']=kwargs['env']['IAM_SRA_MODEL_LEASE_ID']
        backend.record.write_text(json.dumps(row))  # Simulate a bad launcher ignoring the requested variant.
    monkeypatch.setattr(module.subprocess,'run',run)
    from iam_sra.assessment import AssessmentError
    with pytest.raises(AssessmentError):backend.start(time.monotonic()+100)
    assert len(signals)==1 and not backend.marker.exists()


def test_remote_upload_remains_inference_only_and_helper_is_shared(monkeypatch,tmp_path):
    from test_model_host import runner
    module=runner(monkeypatch)
    archive=module.archive()
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        assert not any(name.startswith(('src/','app/','references/')) for name in files.getnames())
        assert files.extractfile('scripts/model_spec.py').read()==(ROOT/'src/iam_sra/model_spec.py').read_bytes()
        files.extractall(tmp_path,filter='data')
    result=subprocess.run([sys.executable,str(tmp_path/'scripts/wait-model.py'),'--check-local-only'],cwd=tmp_path,
        env={**os.environ,'PYTHONPATH':'','IAM_BASE_URL':'http://127.0.0.1:18003','IAM_VLLM_PORT':'18003','IAM_MODEL_VARIANT':'fp16'},capture_output=True,text=True)
    assert result.returncode==0,result.stderr


@pytest.mark.presidio_live
def test_awq_provenance_is_honest_and_passes_existing_real_privacy(monkeypatch):
    from iam_sra.chat_session import ChatSession
    from iam_sra.privacy import require_safe_data
    from indicator_fixtures import bank
    monkeypatch.setenv('IAM_MODEL_VARIANT','awq')
    session=ChatSession(bank(),synthetic=True)
    result=session.export()
    assert result['model_provenance']==load_model(ROOT,'awq')
    require_safe_data(result)


@pytest.mark.parametrize('key',['citizen_short','citizen_extended','organisational','technical'])
def test_quantized_provenance_keeps_all_fn_reference_paths_separate(monkeypatch,key):
    from test_fn_interview import replay
    monkeypatch.setenv('IAM_MODEL_VARIANT','awq')
    s,client,scorer,questions=replay(key)
    assert s.stage=='review'
    assert s.export()['model_provenance']==load_model(ROOT,'awq')
    assert len(s.view()['scale']['anchors'])==9
    before=deepcopy(s.suggestion);s.send('A',client)
    assert s.stage=='ended' and s.suggestion==before


def test_generation_measurements_distinguish_model_wait_from_actual_http_time(monkeypatch):
    from test_fn_interpretation import opening,DEFINITION
    from fn_fixture import reply
    from iam_sra.chat_client import ChatClient
    original=httpx.Client
    def endpoint(request):
        if request.url.path=='/tokenize':return httpx.Response(200,json={'count':1200})
        payload=json.loads(json.loads(request.content)['messages'][-1]['content'])
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(reply(payload))}}],
            'usage':{'completion_tokens':150}})
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(endpoint),**kw))
    s=opening();s.send(DEFINITION,ChatClient())
    metric=s.metrics[-1]
    assert metric['generated_tokens']==150 and metric['generation_http_seconds']>=0
    assert metric['model_wait_seconds']>=0 and metric['generation_calls']==1
    assert s.objective=='drone_uses'


def test_fast_profile_rejects_remote_or_other_gpu_variants_without_actions(monkeypatch):
    from test_model_host import runner
    module=runner(monkeypatch)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:pytest.fail('Unsupported profile must not run'))
    assert module.main(['start','davinci-v100','--variant','awq'])==1
    assert module.main(['start','liono-v100s','--variant','awq'])==1


def test_awq_owned_start_passes_variant_and_preserves_safe_release(monkeypatch,tmp_path):
    backend,row,signals,module=project(monkeypatch,tmp_path)
    backend.variant='awq';backend.marker.unlink();calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        row['environment']['IAM_SRA_MODEL_LEASE_ID']=kwargs['env']['IAM_SRA_MODEL_LEASE_ID']
        row['environment']['IAM_MODEL_VARIANT']=kwargs['env']['IAM_MODEL_VARIANT']
        backend.record.write_text(json.dumps(row))
    monkeypatch.setattr(module.subprocess,'run',run)
    backend.start(time.monotonic()+100)
    assert backend.owns_running_model()
    assert calls[0][calls[0].index('--variant')+1]=='awq'
    assert backend.stop() and len(signals)==1
