import importlib.util
from pathlib import Path

import pytest


def load_ops():
    spec = importlib.util.spec_from_file_location('launch_selection', Path(__file__).parents[1] / 'scripts/ops.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(monkeypatch, ops, used0=22227, used1=22333):
    monkeypatch.setattr(ops.subprocess, 'check_output', lambda *a, **kw:
        f'0, GPU-a, NVIDIA A30, 8.0, 24576, {used0}, 550\n'
        f'1, GPU-b, Tesla V100, 7.0, 32768, {used1}, 550\n')


def test_busy_gpus_are_never_selected(monkeypatch):
    ops = load_ops()
    monkeypatch.setattr(ops, 'UUID', '')
    inventory(monkeypatch, ops)
    with pytest.raises(RuntimeError, match='No unique idle'):
        ops.gpu()


def test_unique_idle_gpu_selected_by_inventory(monkeypatch):
    ops = load_ops()
    monkeypatch.setattr(ops, 'UUID', '')
    inventory(monkeypatch, ops, used1=0)
    assert ops.gpu()[1] == 'GPU-b'


def test_ambiguous_idle_gpus_require_explicit_choice(monkeypatch):
    ops = load_ops()
    monkeypatch.setattr(ops, 'UUID', '')
    inventory(monkeypatch, ops, used0=0, used1=0)
    with pytest.raises(RuntimeError, match='No unique idle'):
        ops.gpu()
    monkeypatch.setattr(ops, 'UUID', 'GPU-a')
    assert ops.gpu()[1] == 'GPU-a'


def test_unknown_uuid_is_not_substituted(monkeypatch):
    ops = load_ops()
    monkeypatch.setattr(ops, 'UUID', 'GPU-other-host')
    inventory(monkeypatch, ops, used1=0)
    with pytest.raises(RuntimeError, match='absent from this host'):
        ops.gpu()


def test_custom_model_address_preserved(monkeypatch):
    monkeypatch.setenv('IAM_BASE_URL', 'http://127.0.0.1:8010/')
    assert load_ops().BASE_URL == 'http://127.0.0.1:8010'


@pytest.mark.parametrize('profile,host,name,cap,total,offload', [
    ('liono-v100s', 'liono', 'Tesla V100S-PCIE-32GB', '7.0', 32768, 0),
    ('liono-a2', 'liono', 'NVIDIA A2', '8.6', 15360, 8),
    ('davinci-v100', 'davinci', 'Tesla V100-PCIE-16GB', '7.0', 16384, 8),
    ('davinci-v100', 'davinci', 'Tesla V100-PCIE-32GB', '7.0', 32768, 0),
    ('davinci-a30', 'davinci', 'NVIDIA A30', '8.0', 24576, 0),
])
def test_named_profiles_select_correct_gpu_and_memory_plan(monkeypatch, profile, host, name, cap, total, offload):
    ops = load_ops()
    monkeypatch.setattr(ops, 'PROFILE', profile)
    monkeypatch.setattr(ops, 'UUID', '')
    monkeypatch.setattr(ops.socket, 'gethostname', lambda: host + '.microlab.ntua.gr')
    monkeypatch.delenv('IAM_CPU_OFFLOAD_GB', raising=False)
    # The first GPU is idle but unrelated. It must never substitute for this profile.
    monkeypatch.setattr(ops.subprocess, 'check_output', lambda *a, **kw:
        f'0, GPU-other, NVIDIA A100, 8.0, 40960, 0, 550\n'
        f'2, GPU-selected, {name}, {cap}, {total}, 0, 550\n')
    row = ops.gpu()
    assert row[0] == '2' and row[1] == 'GPU-selected'
    assert ops.cpu_offload(row) == offload


def test_profile_on_wrong_host_refused_before_gpu_query(monkeypatch):
    ops = load_ops()
    monkeypatch.setattr(ops, 'PROFILE', 'davinci-v100')
    monkeypatch.setattr(ops.socket, 'gethostname', lambda: 'liono')
    monkeypatch.setattr(ops.subprocess, 'check_output', lambda *a, **kw: pytest.fail('GPU queried on wrong host'))
    with pytest.raises(RuntimeError, match='must run on davinci'):
        ops.gpu()


def test_busy_selected_profile_never_falls_back_to_other_idle_card(monkeypatch):
    ops = load_ops()
    monkeypatch.setattr(ops, 'PROFILE', 'liono-v100s')
    monkeypatch.setattr(ops, 'UUID', '')
    monkeypatch.setattr(ops.socket, 'gethostname', lambda: 'liono')
    monkeypatch.setattr(ops.subprocess, 'check_output', lambda *a, **kw:
        '0, GPU-busy, Tesla V100S-PCIE-32GB, 7.0, 32768, 20000, 550\n'
        '1, GPU-idle, NVIDIA A2, 8.6, 15360, 0, 550\n')
    with pytest.raises(RuntimeError, match='No unique idle'):
        ops.gpu()


def test_uuid_must_match_profile(monkeypatch):
    ops = load_ops()
    monkeypatch.setattr(ops, 'PROFILE', 'davinci-v100')
    monkeypatch.setattr(ops, 'UUID', 'GPU-a')
    monkeypatch.setattr(ops.socket, 'gethostname', lambda: 'davinci')
    inventory(monkeypatch, ops, used0=0, used1=0)
    with pytest.raises(RuntimeError, match='does not match'):
        ops.gpu()


def test_explicit_uuid_cannot_override_busy_check(monkeypatch):
    ops = load_ops()
    monkeypatch.setattr(ops, 'PROFILE', '')
    monkeypatch.setattr(ops, 'UUID', 'GPU-a')
    inventory(monkeypatch, ops)
    with pytest.raises(RuntimeError, match='existing workload'):
        ops.gpu()


@pytest.mark.parametrize('name,cap', [('NVIDIA A2000', '8.6'), ('NVIDIA A3000', '8.0'),
                                     ('NVIDIA A2', '8.0'), ('Tesla V100', '8.0')])
def test_name_and_compute_capability_must_both_match(name, cap):
    assert load_ops().gpu_class(['0', 'GPU-test', name, cap]) is None


@pytest.mark.parametrize('value', ['-1', '17', 'nan', 'inf'])
def test_invalid_offload_cannot_launch(monkeypatch, value):
    ops = load_ops()
    monkeypatch.setenv('IAM_CPU_OFFLOAD_GB', value)
    with pytest.raises(RuntimeError, match='between 0 and 16'):
        ops.cpu_offload(['0', 'GPU-a', 'NVIDIA A2', '8.6', '15360'])


def test_offload_requires_available_host_memory(monkeypatch, tmp_path):
    ops = load_ops()
    meminfo = tmp_path / 'meminfo'
    meminfo.write_text('MemAvailable: 1048576 kB\n')
    monkeypatch.setattr(ops, 'Path', lambda _: meminfo)
    monkeypatch.delenv('IAM_CPU_OFFLOAD_GB', raising=False)
    with pytest.raises(RuntimeError, match='12 GiB available'):
        ops.check_offload_memory(['0', 'GPU-a', 'NVIDIA A2', '8.6', '15360'])


def test_a2_launch_keeps_pinned_model_and_inference_contract(monkeypatch, tmp_path):
    import json
    ops = load_ops()
    (tmp_path / 'configs').mkdir()
    pinned = (ops.ROOT / 'configs/model.json').read_text()
    (tmp_path / 'configs/model.json').write_text(pinned)
    snapshot = tmp_path / '.runtime/huggingface/hub/models--Qwen--Qwen3-8B/snapshots' / json.loads(pinned)['revision']
    snapshot.mkdir(parents=True)
    (snapshot / 'model.safetensors').touch()
    monkeypatch.setattr(ops, 'ROOT', tmp_path)
    monkeypatch.setattr(ops, 'RUNTIME', tmp_path / '.runtime')
    monkeypatch.delenv('IAM_CPU_OFFLOAD_GB', raising=False)
    command = ops.vllm_command(['1', 'GPU-a', 'NVIDIA A2', '8.6', '15360'])
    for option, value in [('--model', str(snapshot)), ('--dtype', 'half'),
                          ('--max-model-len', '4096'), ('--max-num-seqs', '1'),
                          ('--cpu-offload-gb', '8.0'), ('--host', '127.0.0.1'),
                          ('--guided-decoding-backend', 'xgrammar')]:
        assert command[command.index(option) + 1] == value
    assert '--quantization' not in command
