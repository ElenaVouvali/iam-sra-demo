"""Synthetic process tables; diagnostics neither signal nor print arguments."""
import importlib.util
import json
import os
from pathlib import Path


spec = importlib.util.spec_from_file_location('model_diagnostics', Path(__file__).parents[1] / 'scripts/diagnose-model.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def process(proc, project, pid, parent, args, start='recorded_start'):
    entry = proc / str(pid)
    entry.mkdir()
    (entry / 'cmdline').write_bytes(b'\0'.join(a.encode() for a in args) + b'\0')
    (entry / 'status').write_text(f'Name:\tpython\nPPid:\t{parent}\n')
    (entry / 'stat').write_text(f'{pid} (python) ' + ' '.join(['S', str(parent)] + ['0'] * 17 + [start]))
    (entry / 'cwd').symlink_to(project, target_is_directory=True)


def fixture(tmp_path):
    proc = tmp_path / 'proc'; proc.mkdir()
    project = tmp_path / 'project'; project.mkdir(); (project / '.runtime').mkdir()
    args = ['/python', str(project / 'scripts/supervise.py'), 'vllm', '[]']
    process(proc, project, 100, 1, args)
    (project / '.runtime/vllm.pid.json').write_text(json.dumps({'pid': 100, 'start_time': 'recorded_start',
        'root': str(project), 'command': args}))
    return proc, project


def test_verified_ancestry_identifies_model_tree_without_arguments(tmp_path):
    proc, project = fixture(tmp_path)
    process(proc, project, 200, 100, ['/python', '-m', 'vllm.entrypoints.openai.api_server', '--api-key', 'synthetic-secret'])
    row = module.describe_process(200, proc=proc, project=project)
    assert row['project_relation'] == 'verified_recorded_model_tree'
    assert row['same_user'] and row['parent_pid'] == 100 and row['kind'] == 'vllm_api'
    assert 'synthetic-secret' not in json.dumps(row) and 'api-key' not in json.dumps(row)


def test_orphan_same_directory_is_unverified_not_adopted(tmp_path):
    proc, project = fixture(tmp_path)
    process(proc, project, 201, 1, ['/python', 'unrelated.py'])
    row = module.describe_process(201, proc=proc, project=project)
    assert row['project_relation'] == 'project_directory_only_unverified'


def test_reused_supervisor_pid_is_not_verified(tmp_path):
    proc, project = fixture(tmp_path)
    (proc / '100/stat').write_text('100 (python) ' + ' '.join(['S', '1'] + ['0'] * 17 + ['new_start']))
    process(proc, project, 202, 100, ['/python', '-m', 'vllm.entrypoints.openai.api_server'])
    assert module.describe_process(202, proc=proc, project=project)['project_relation'] == 'project_directory_only_unverified'


def test_other_user_is_never_marked_project_owned(monkeypatch, tmp_path):
    proc, project = fixture(tmp_path)
    process(proc, project, 203, 100, ['/python'])
    current_uid = os.getuid()
    monkeypatch.setattr(module.os, 'getuid', lambda: current_uid + 1)
    row = module.describe_process(203, proc=proc, project=project)
    assert row['project_relation'] == 'other_user' and row['same_user'] is False


def test_missing_process_and_malformed_gpu_rows_are_safe(tmp_path):
    proc, project = fixture(tmp_path)
    assert module.describe_process(404, proc=proc, project=project)['project_relation'] == 'not_visible'
    rows = module.gpu_process_rows('GPU-abcd, 404, 17007\nunsafe payload\nGPU-abcd, NaN, 200\n', proc=proc, project=project)
    assert len(rows) == 1 and rows[0]['pid'] == 404 and rows[0]['memory_mib'] == 17007
