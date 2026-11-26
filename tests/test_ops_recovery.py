import importlib.util
import json
from pathlib import Path
import pytest


def ops_module():
    spec=importlib.util.spec_from_file_location('project_ops',Path(__file__).parents[1]/'scripts/ops.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def setup_proc(monkeypatch,tmp_path,commands):
    ops=ops_module()
    root=tmp_path/'project';root.mkdir();runtime=root/'.runtime'
    proc=tmp_path/'proc';proc.mkdir()
    for index,args in enumerate(commands(ops,root),start=100):
        entry=proc/str(index);entry.mkdir();(entry/'cmdline').write_bytes(b'\0'.join(a.encode() for a in args)+b'\0')
    monkeypatch.setattr(ops,'ROOT',root);monkeypatch.setattr(ops,'RUNTIME',runtime)
    monkeypatch.setattr(ops,'Path',lambda value:proc if value=='/proc' else Path(value))
    monkeypatch.setattr(ops.os,'getpgid',lambda pid:pid)
    monkeypatch.setattr(ops,'identity',lambda pid:'verified-start')
    return ops,runtime


def command(ops,root,app=None):
    return [ops.sys.executable,str(root/'scripts/supervise.py'),'ui',json.dumps([ops.sys.executable,'-m','streamlit','run',str(app or root/'app.py')])]


def test_recovers_exact_project_supervisor(monkeypatch,tmp_path):
    ops,runtime=setup_proc(monkeypatch,tmp_path,lambda ops,root:[command(ops,root)])
    assert ops.recover_record('ui')
    record=json.loads((runtime/'ui.pid.json').read_text())
    assert record['pid']==100 and record['start_time']=='verified-start'


def test_does_not_adopt_another_app(monkeypatch,tmp_path):
    ops,runtime=setup_proc(monkeypatch,tmp_path,lambda ops,root:[command(ops,root,root/'other.py')])
    assert not ops.recover_record('ui') and not (runtime/'ui.pid.json').exists()


def test_refuses_multiple_supervisors(monkeypatch,tmp_path):
    ops,runtime=setup_proc(monkeypatch,tmp_path,lambda ops,root:[command(ops,root),command(ops,root)])
    with pytest.raises(RuntimeError,match='Multiple'):ops.recover_record('ui')
    assert not (runtime/'ui.pid.json').exists()


def test_v100_thinking_launch_uses_fp16_8192_and_reasoning_parser(monkeypatch,tmp_path):
    ops=ops_module();snapshot=tmp_path/'snapshot';snapshot.mkdir()
    (snapshot/'model.safetensors').write_bytes(b'fixture')
    monkeypatch.setenv('IAM_MODEL_VARIANT','fp16')
    monkeypatch.setenv('IAM_MODEL_THINKING','1')
    monkeypatch.setenv('IAM_GPU_MEMORY_UTILIZATION','0.80')
    monkeypatch.setenv('IAM_CPU_OFFLOAD_GB','0')
    monkeypatch.setattr(ops,'load_model',lambda root:{'model':'Qwen/Qwen3-8B'})
    monkeypatch.setattr(ops,'snapshot_path',lambda root,model:snapshot)
    row=['1','GPU-V100','Tesla V100-PCIE-32GB','7.0','32768','0','driver']
    command=ops.vllm_command(row)
    assert command[command.index('--dtype')+1]=='half'
    assert command[command.index('--max-model-len')+1]=='8192'
    assert '--enable-reasoning' in command
    assert command[command.index('--reasoning-parser')+1]=='deepseek_r1'
    assert command[command.index('--cpu-offload-gb')+1]=='0.0'
