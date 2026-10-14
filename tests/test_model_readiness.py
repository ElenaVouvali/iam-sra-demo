"""Synthetic HTTP/clock checks; these do not establish host/GPU availability."""
import importlib.util
from pathlib import Path

import httpx
import pytest


spec = importlib.util.spec_from_file_location('wait_model', Path(__file__).parents[1] / 'scripts/wait-model.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize('base', ['http://127.0.0.1:8000', 'http://localhost:8000/'])
def test_only_project_local_endpoint_can_be_recovered(base):
    assert module.project_local_endpoint(base, 8000)


@pytest.mark.parametrize('base', ['http://remote.example:8000', 'http://localhost:8001',
    'http://localhost:8000/v1', 'http://person:synthetic-secret@localhost:8000',
    'http://localhost:8000/?redirect=elsewhere', 'https://localhost:8000',
    'http://localhost:invalid'])
def test_other_endpoints_cannot_trigger_local_restart(base):
    assert not module.project_local_endpoint(base, 8000)


class Clock:
    def __init__(self): self.now = 0
    def clock(self): return self.now
    def sleep(self, seconds): self.now += seconds


def test_loading_waits_for_health_and_expected_alias(capsys):
    calls = []
    def endpoint(request):
        calls.append(request.url.path)
        if len(calls) == 1:
            return httpx.Response(503)
        if request.url.path == '/v1/models':
            return httpx.Response(200, json={'data': [{'id': 'Qwen/Qwen3-8B'}]})
        return httpx.Response(200)
    clock = Clock()
    with httpx.Client(transport=httpx.MockTransport(endpoint)) as client:
        assert module.wait(client, 'http://127.0.0.1:8000', 10, clock=clock.clock, sleep=clock.sleep)
    assert calls == ['/health', '/health', '/v1/models']
    assert clock.now == 2
    assert 'is ready' in capsys.readouterr().out


@pytest.mark.parametrize('models', [{'data': [{'id': 'other-model'}]}, {'data': None}, []])
def test_healthy_port_with_wrong_or_invalid_models_is_not_ready(models, capsys):
    def endpoint(request):
        return httpx.Response(200, json=models if request.url.path == '/v1/models' else {})
    clock = Clock()
    with httpx.Client(transport=httpx.MockTransport(endpoint)) as client:
        assert not module.wait(client, 'http://127.0.0.1:8000', 3, clock=clock.clock, sleep=clock.sleep)
    assert clock.now == 3
    assert 'timed out' in capsys.readouterr().out


def test_unavailable_service_has_bounded_wait_and_no_body_or_credentials_echo(capsys):
    def endpoint(request):
        return httpx.Response(500, text='Synthetic unsafe diagnostic content must not be printed')
    clock = Clock()
    with httpx.Client(transport=httpx.MockTransport(endpoint)) as client:
        assert not module.wait(client, 'http://person:synthetic-secret@localhost:8000', 5,
                               clock=clock.clock, sleep=clock.sleep)
    output = capsys.readouterr().out
    assert 'synthetic-secret' not in output and 'unsafe diagnostic' not in output
    assert clock.now == 5
