"""Offline orchestration tests; no SSH connection or GPU workload is started."""
import importlib.util
import io
from pathlib import Path
import shlex
import subprocess
import tarfile

import pytest


def runner(monkeypatch, host='liono'):
    spec = importlib.util.spec_from_file_location('model_host', Path(__file__).parents[1] / 'scripts/model-host.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.socket, 'gethostname', lambda: host)
    monkeypatch.delenv('IAM_DAVINCI_SSH', raising=False)
    monkeypatch.delenv('IAM_LIONO_SSH', raising=False)
    return module


@pytest.mark.parametrize('profile', ['liono-v100s', 'liono-a2', 'davinci-v100', 'davinci-a30'])
def test_dry_run_never_connects_installs_or_opens_socket(monkeypatch, capsys, profile):
    module = runner(monkeypatch)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: pytest.fail('Executed dry-run command'))
    monkeypatch.setattr(module, 'port_free', lambda _: pytest.fail('Opened a socket'))
    for action in ('prepare', 'check', 'start'):
        assert module.main([action, profile, '--dry-run']) == 0
    output = capsys.readouterr().out
    assert profile in output
    if profile.startswith('davinci'):
        assert '127.0.0.1:18000:127.0.0.1:18000' in output
        assert 'evouvali@davinci.microlab.ntua.gr' in output
        assert 'ExitOnForwardFailure=yes' in output
    else:
        assert 'ssh ' not in output


def test_a30_fp16_thinking_dry_run_uses_same_pinned_remote_stack(monkeypatch,capsys):
    module=runner(monkeypatch)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('Dry run executed'))
    assert module.main(['start','davinci-a30','--thinking','--variant','fp16','--dry-run'])==0
    assert 'IAM_MODEL_THINKING=1' in capsys.readouterr().out


def test_v100_fp16_thinking_dry_run_uses_8192_token_configuration(monkeypatch,capsys):
    module=runner(monkeypatch)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('Dry run executed'))
    assert module.main(['start','davinci-v100','--thinking','--variant','fp16','--dry-run'])==0
    output=capsys.readouterr().out
    assert 'IAM_MODEL_THINKING=1' in output
    assert 'IAM_GPU_PROFILE=davinci-v100' in output


def test_remote_start_checks_local_port_then_starts_waits_and_forwards(monkeypatch):
    module = runner(monkeypatch)
    calls = []
    monkeypatch.setattr(module, 'port_free', lambda port: calls.append(('port', port)))
    monkeypatch.setattr(module.subprocess, 'run', lambda command, **kw: calls.append(command))
    assert module.main(['start', 'davinci-v100', '--port', '18002']) == 0
    assert calls[0] == ('port', 18002)
    assert len(calls) == 4
    assert 'scripts/ops.py start vllm' in calls[1][-1]
    assert 'IAM_GPU_PROFILE=davinci-v100' in calls[1][-1]
    assert 'scripts/wait-model.py --timeout 600' in calls[2][-1]
    assert calls[3][calls[3].index('-L') + 1] == '127.0.0.1:18002:127.0.0.1:18002'
    assert calls[3][-1] == 'evouvali@davinci.microlab.ntua.gr'
    assert 'stop' not in ' '.join(str(call) for call in calls)


def test_remote_start_refuses_busy_local_endpoint_before_any_ssh(monkeypatch, capsys):
    module = runner(monkeypatch)
    def occupied(_):
        raise OSError('Address already in use')
    monkeypatch.setattr(module, 'port_free', occupied)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: pytest.fail('Remote mutated with occupied local port'))
    assert module.main(['start', 'davinci-v100']) == 1
    assert 'Address already in use' in capsys.readouterr().err


def test_remote_tunnel_reconnect_does_not_restart_model(monkeypatch):
    module = runner(monkeypatch)
    calls = []
    monkeypatch.setattr(module, 'port_free', lambda _: None)
    monkeypatch.setattr(module.subprocess, 'run', lambda command, **kw: calls.append(command))
    assert module.main(['tunnel', 'davinci-a30']) == 0
    assert len(calls) == 2 and 'wait-model.py' in calls[0][-1]
    assert '-N' in calls[1]
    assert not any('ops.py start' in argument for call in calls for argument in call)


def test_failed_remote_start_does_not_open_tunnel(monkeypatch):
    module = runner(monkeypatch)
    calls = []
    monkeypatch.setattr(module, 'port_free', lambda _: None)
    def failure(command, **kwargs):
        calls.append(command)
        raise module.subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(module.subprocess, 'run', failure)
    assert module.main(['start', 'davinci-v100']) == 1
    assert len(calls) == 1


def test_local_start_clears_stale_gpu_choices_and_needs_no_ssh(monkeypatch):
    module = runner(monkeypatch)
    monkeypatch.setenv('IAM_GPU_UUID', 'GPU-stale')
    monkeypatch.setenv('IAM_CPU_OFFLOAD_GB', '15')
    monkeypatch.setenv('IAM_GPU_PROFILE', 'davinci-a30')
    calls = []
    monkeypatch.setattr(module.subprocess, 'run', lambda command, **kw: calls.append((command, kw)))
    assert module.main(['start', 'liono-a2', '--gpu-uuid', 'GPU-a2']) == 0
    assert len(calls) == 2
    environment = calls[0][1]['env']
    assert environment['IAM_GPU_PROFILE'] == 'liono-a2'
    assert environment['IAM_GPU_UUID'] == 'GPU-a2'
    assert 'IAM_CPU_OFFLOAD_GB' not in environment
    assert all(call[0][0] == '.venv/bin/python' for call in calls)


def test_remote_prepare_copies_only_inference_files_and_preserves_app(monkeypatch):
    module = runner(monkeypatch)
    calls = []
    monkeypatch.setattr(module.subprocess, 'run', lambda command, **kw: calls.append((command, kw)))
    assert module.main(['prepare', 'davinci-v100', '--python', '/opt/python3.11']) == 0
    assert len(calls) == 2
    assert '.iam-sra-inference' in calls[0][0][-1]
    assert 'Unexpected remote host' in calls[0][0][-1]
    assert 'IAM_PYTHON=/opt/python3.11' in calls[1][0][-1]
    with tarfile.open(fileobj=io.BytesIO(calls[0][1]['input'])) as bundle:
        assert set(bundle.getnames()) == set(module.INFERENCE_FILES)
        assert all(member.isfile() for member in bundle.getmembers())
        assert not any(name.startswith(('references/', 'src/', 'app/', '.venv', '.runtime')) for name in bundle.getnames())


def test_upload_refuses_existing_unmarked_directory(monkeypatch, tmp_path):
    module = runner(monkeypatch)
    destination = tmp_path / 'existing'
    destination.mkdir()
    important = destination / 'existing-work.txt'
    important.write_text('preserve this')
    host = subprocess.check_output(['hostname', '-s'], text=True).strip()
    script = module.upload_script('iam-sra-inference', host).replace(
        'root=' + module.remote_root('iam-sra-inference'), 'root=' + shlex.quote(str(destination)))
    result = subprocess.run(['bash', '-c', script], input=module.archive(), capture_output=True)
    assert result.returncode == 1 and b'Refusing to overwrite' in result.stderr
    assert important.read_text() == 'preserve this'
    assert not (destination / 'scripts').exists()


def test_upload_updates_managed_files_but_preserves_environment_and_cache(monkeypatch, tmp_path):
    module = runner(monkeypatch)
    destination = tmp_path / 'inference'
    destination.mkdir()
    (destination / '.iam-sra-inference').touch()
    for name in ('.venv/existing-python', '.runtime/model-cache', '.runtime/vllm.pid.json'):
        path = destination / name
        path.parent.mkdir(exist_ok=True)
        path.write_text('existing state')
    host = subprocess.check_output(['hostname', '-s'], text=True).strip()
    script = module.upload_script('iam-sra-inference', host).replace(
        'root=' + module.remote_root('iam-sra-inference'), 'root=' + shlex.quote(str(destination)))
    result = subprocess.run(['bash', '-c', script], input=module.archive(), capture_output=True)
    assert result.returncode == 0, result.stderr
    assert (destination / 'scripts/ops.py').read_bytes() == (module.ROOT / 'scripts/ops.py').read_bytes()
    for name in ('.venv/existing-python', '.runtime/model-cache', '.runtime/vllm.pid.json'):
        assert (destination / name).read_text() == 'existing state'


@pytest.mark.parametrize('directory', ['/tmp/app', '../existing', '.', 'nested/../app', ''])
def test_remote_prepare_rejects_nonisolated_directory_before_connection(monkeypatch, directory):
    module = runner(monkeypatch)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: pytest.fail('Connected with invalid directory'))
    assert module.main(['prepare', 'davinci-v100', '--remote-dir', directory]) == 1


def test_ssh_options_cannot_be_injected(monkeypatch):
    module = runner(monkeypatch)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: pytest.fail('Invalid SSH argument executed'))
    assert module.main(['start', 'davinci-v100', '--ssh=-oProxyCommand=unexpected']) == 1


def test_missing_liono_destination_is_actionable_on_davinci(monkeypatch, capsys):
    module = runner(monkeypatch, host='davinci')
    assert module.main(['start', 'liono-a2', '--dry-run']) == 1
    assert '--ssh user@hostname' in capsys.readouterr().err


@pytest.mark.parametrize('arguments', [
    ['--port', '80'], ['--timeout', '601'], ['--cpu-offload-gb', 'nan'],
    ['--cpu-offload-gb', '-1'], ['--gpu-memory-utilization', '1.0'],
])
def test_invalid_operational_limits_fail_before_side_effects(monkeypatch, arguments):
    module = runner(monkeypatch)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: pytest.fail('Invalid limits executed'))
    with pytest.raises(SystemExit) as exc:
        module.main(['start', 'davinci-v100', *arguments])
    assert exc.value.code == 2
