"""Production proxy transport checks with explicit synthetic controllers and no model calls."""
import importlib.util
import json
from pathlib import Path
import threading
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
from uuid import uuid4
import time
import httpx
import pytest
from test_api_integration import make_api  # Explicit test fixture; never a production fallback.


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


class ThreadedWSGI(ThreadingMixIn, WSGIServer):
    daemon_threads = True


@pytest.fixture
def proxy(make_api, monkeypatch, tmp_path):
    app, manager = make_api()
    backend = make_server('127.0.0.1', 0, app, server_class=ThreadedWSGI, handler_class=QuietHandler)
    spec = importlib.util.spec_from_file_location('sra_frontend_proxy', Path('app/serve_app.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dist = tmp_path / 'dist'
    dist.mkdir(); (dist / 'index.html').write_text('<html>SPA fixture</html>')
    monkeypatch.setattr(module, 'DIST', dist)
    monkeypatch.setenv('IAM_SRA_API_TARGET', 'http://127.0.0.1:' + str(backend.server_port))
    server = module.ThreadingHTTPServer(('127.0.0.1', 0), module.Handler)
    threads = [threading.Thread(target=item.serve_forever, daemon=True) for item in (backend, server)]
    for thread in threads:
        thread.start()
    with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}', trust_env=False) as client:
        yield client, module, manager
    for item in (server, backend):
        item.shutdown(); item.server_close()
    for thread in threads:
        thread.join(timeout=2)


def test_production_proxy_cookie_csrf_status_jobs_and_json_jsonl(proxy):
    client, module, manager = proxy
    prefix = '/api/sra-assessment/v1'
    bootstrap = client.get(prefix + '/capabilities')
    assert bootstrap.status_code == 200
    assert bootstrap.headers['cache-control'] == 'no-store'
    assert 'HttpOnly' in bootstrap.headers['set-cookie'] and 'SameSite=Strict' in bootstrap.headers['set-cookie']
    headers = {'X-CSRF-Token': bootstrap.json()['csrf_token'], 'Origin': 'http://127.0.0.1:5001'}
    assert client.post(prefix + '/sessions', json={}).status_code == 403
    assert client.post(prefix + '/sessions', json={}, headers={**headers, 'Origin': 'https://foreign.invalid'}).status_code == 403
    created = client.post(prefix + '/sessions', json={}, headers=headers)
    assert created.status_code == 201
    view = created.json()['session']
    path = prefix + '/sessions/' + view['id']

    def act(action, data=None):
        nonlocal view
        response = client.post(path + '/actions', headers=headers, json={'action': action, 'data': data or {}, 'expected_version': view['version'], 'request_id': str(uuid4())})
        assert response.status_code == 202, response.text
        job = response.json()['job_id']
        end = time.monotonic() + 5
        while time.monotonic() < end:
            result = client.get(prefix + '/jobs/' + job)
            assert result.status_code == 200
            if result.json()['job']['status'] in {'completed', 'failed'}:
                assert result.json()['job']['status'] == 'completed', result.text
                break
            time.sleep(.005)
        else:
            pytest.fail('Synthetic proxy job timed out')
        view = client.get(path).json()['session']
        return job

    jid = act('set_context', {'perspective': 'personal', 'role': 'citizen', 'city': 'madrid'})
    stale = client.post(path + '/actions', headers=headers, json={'action': 'finish', 'data': {}, 'expected_version': 0, 'request_id': str(uuid4())})
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'stale_action'
    with httpx.Client(base_url=client.base_url, trust_env=False) as foreign:
        foreign.get(prefix + '/capabilities')
        assert foreign.get(path).status_code == 404
        assert foreign.get(prefix + '/jobs/' + jid).status_code == 404
        assert foreign.get(path + '/export').status_code == 404
    act('finish'); act('confirm_general'); act('decline_scenario'); act('confirm_final')
    for format, mime in [('json', 'application/json'), ('jsonl', 'application/x-ndjson')]:
        response = client.get(path + '/export', params={'format': format})
        assert response.status_code == 200 and response.headers['content-type'].startswith(mime)
        assert response.headers['cache-control'] == 'no-store'
        assert response.headers['content-disposition'] == f'attachment; filename="iam-sra2.{format}"'
        assert json.loads(response.content)['export_profile'] == 'browser_evidence'
        if format == 'jsonl':
            assert len(response.text.splitlines()) == 1
    deleted = client.delete(path, headers={**headers, 'X-Session-Version': str(view['version'])})
    assert deleted.status_code == 204
    assert client.get(path).status_code == 410


def test_production_spa_unknown_tools_and_safe_unavailable_errors(proxy, monkeypatch):
    client, module, manager = proxy
    for path in ('/', '/tools/sra-assessment', '/tools/sra-assessment/app', '/privacy'):
        response = client.get(path)
        assert response.status_code == 200 and 'SPA fixture' in response.text
    for path in ('/api', '/api/', '/api/not-a-tool/v1/health', '/api/sra-assessment-other/v1/health', '/assets/missing.js'):
        assert client.get(path).status_code == 404
    assert client.put('/api/sra-assessment/v1/sessions').status_code == 405
    monkeypatch.setenv('IAM_SRA_API_TARGET', 'http://127.0.0.1:1')
    response = client.get('/api/sra-assessment/v1/health')
    assert response.status_code == 502
    assert '127.0.0.1' not in response.text and 'refused' not in response.text
    assert response.headers['cache-control'] == 'no-store'


def test_proxy_cluster_and_host_target_compatibility(proxy, monkeypatch):
    _, module, _ = proxy
    monkeypatch.delenv('IAM_SRA_API_TARGET')
    monkeypatch.setenv('IAMIQ_IN_CLUSTER', '1')
    assert module.target('sra-assessment') == 'http://iam-sra-api:8001'
    monkeypatch.setenv('IAMIQ_IN_CLUSTER', '0'); monkeypatch.setenv('K8S_HOST', 'example.invalid')
    assert module.target('sra-assessment') == 'http://example.invalid:8001'
    monkeypatch.setenv('IAM_SRA_API_TARGET', 'https://approved.invalid:8443')
    assert module.target('sra-assessment') == 'https://approved.invalid:8443'
    monkeypatch.setenv('IAM_SRA_API_TARGET', 'https://credentials:secret@forbidden.invalid')
    with pytest.raises(ValueError):
        module.target('sra-assessment')
