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
