"""Offline sharing checks; no public URL, GPU workload or real tunnel is created."""
from hashlib import sha256
import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from werkzeug.middleware.dispatcher import DispatcherMiddleware


def launcher():
    spec=importlib.util.spec_from_file_location('fn_review_link',Path(__file__).parents[1]/'scripts/share-fn-review.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_dry_run_has_private_a2_api_ui_and_never_starts_or_downloads(monkeypatch,capsys):
    m=launcher()
    monkeypatch.setattr(m,'free_ports',lambda _:pytest.fail('Opened socket'))
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('Started model'))
    monkeypatch.setattr(m,'cloudflared',lambda _:pytest.fail('Downloaded tunnel'))
    assert m.main(['--dry-run'])==0
    plan=json.loads(capsys.readouterr().out)
    assert plan['profile']=='liono-a2' and plan['cookie_secure']
    assert all(plan[k].startswith('http://127.0.0.1:') for k in ['model','api','frontend'])
    assert not plan['changes_firewall'] and not plan['stops_existing_services']


def test_davinci_v100_dry_run_selects_fp16_non_thinking_and_never_starts(monkeypatch,capsys):
    m=launcher()
    monkeypatch.setattr(m,'free_ports',lambda _:pytest.fail('Opened socket'))
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('Started model'))
    monkeypatch.setattr(m,'cloudflared',lambda _:pytest.fail('Downloaded tunnel'))
    assert m.main(['--gpu-profile','davinci-v100','--model-port','18020','--dry-run'])==0
    plan=json.loads(capsys.readouterr().out)
    assert plan['profile']=='davinci-v100' and plan['model_variant']=='fp16'
    assert plan['thinking_enabled'] is False and plan['cpu_offload_gb']==0
    assert plan['model_lifecycle']=='on_demand' and not plan['stops_existing_services']
    assert plan['model']=='http://127.0.0.1:18020'


def test_davinci_v100_dry_run_can_match_a30_thinking_context(monkeypatch,capsys):
    m=launcher()
    monkeypatch.setattr(m,'free_ports',lambda _:pytest.fail('Opened socket'))
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('Started model'))
    monkeypatch.setattr(m,'cloudflared',lambda _:pytest.fail('Downloaded tunnel'))
    assert m.main(['--gpu-profile','davinci-v100','--model-port','18021','--thinking','--dry-run'])==0
    plan=json.loads(capsys.readouterr().out)
    assert plan['profile']=='davinci-v100' and plan['model_variant']=='fp16'
    assert plan['thinking_enabled'] is True and plan['cpu_offload_gb']==0


def test_v100_generation_probe_requests_thinking_for_thinking_backend(monkeypatch):
    m=launcher();calls=[]
    class Response:
        is_error=False
        def json(self):return {'choices':[{'message':{'content':'READY'}}]}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,json):calls.append((url,json));return Response()
    class Backend:
        port=18021;thinking=True
        def start(self,deadline):pass
        def stop(self):return True
    monkeypatch.setattr(m.httpx,'Client',Client)
    m.verify_v100_model(Backend())
    assert calls[0][1]['chat_template_kwargs']['enable_thinking'] is True


def test_prepare_v100_passes_thinking_flag_only_when_requested(monkeypatch,tmp_path):
    m=launcher();monkeypatch.setattr(m,'ROOT',tmp_path)
    calls=[];monkeypatch.setattr(m.subprocess,'run',lambda command,**kwargs:calls.append(command))
    m.prepare_v100('iam-sra-preview',18021,thinking=True)
    assert '--thinking' in calls[0]
    m.prepare_v100('iam-sra-preview',18021)
    assert '--thinking' not in calls[1]


def test_validation_only_needs_no_frontend_build_or_review_ports(monkeypatch,tmp_path):
    from iam_sra import model_lifecycle
    m=launcher();state=tmp_path/'state'
    monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m,'STATE',state)
    monkeypatch.setattr(m.socket,'gethostname',lambda:'liono')
    for name in ('review_ports','free_ports','cloudflared','verify_public'):
        monkeypatch.setattr(m,name,lambda *a,**k:pytest.fail('Validation-only touched public resources'))
    for key in ('IAM_MODEL_VARIANT','IAM_MODEL_THINKING'):
        monkeypatch.setenv(key,os.getenv(key,'0' if key=='IAM_MODEL_THINKING' else 'fp16'))
    stopped=[];validated=[]
    class Backend:
        marker=state/'absent-owner.json'
        def __init__(self,*a,**k):pass
        def stop(self):stopped.append(True);return True
    monkeypatch.setattr(model_lifecycle,'ProjectA2',Backend)
    monkeypatch.setattr(m,'owned_a2',lambda port:False)
    monkeypatch.setattr(m,'prepare_review_model',lambda variant:{'model':'Synthetic checkpoint fixture','revision':'fixture'})
    monkeypatch.setattr(m,'verify_live_interviews',lambda *a:validated.append(True))
    assert m.main(['--validation-only','--thinking'])==0
    assert validated==[True] and stopped==[True]
    assert not (tmp_path/'app/dist/index.html').exists()


def test_active_launcher_has_actionable_error_and_keeps_existing_link(monkeypatch,tmp_path,capsys):
    import fcntl
    m=launcher();state=tmp_path/'state';state.mkdir()
    link=state/'chat-url.txt';link.write_text('existing operator link')
    monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m,'STATE',state)
    monkeypatch.setattr(m.socket,'gethostname',lambda:'liono')
    with (state/'share.lock').open('a') as held:
        fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert m.main(['--validation-only'])==1
    assert 'sharing launcher is already running' in capsys.readouterr().err
    assert link.read_text()=='existing operator link'


@pytest.mark.parametrize('ports',[[5018,5018,18003],[0,8018,18003],[5018,8018,65536]])
def test_bad_port_plan_is_rejected_before_side_effects(ports):
    with pytest.raises(ValueError):launcher().free_ports(ports)


def test_blocked_start_cannot_delete_an_existing_link(monkeypatch,tmp_path):
    m=launcher();state=tmp_path/'state';state.mkdir();link=state/'chat-url.txt';link.write_text('existing operator link')
    monkeypatch.setattr(m,'STATE',state)
    monkeypatch.setattr(m,'ROOT',tmp_path)
    monkeypatch.setattr(m.socket,'gethostname',lambda:'wrong-host')
    assert m.main([])==1
    assert link.read_text()=='existing operator link'


@pytest.mark.parametrize('fault',[None,'digest','origin'])
def test_official_cloudflared_download_integrity(monkeypatch,tmp_path,fault):
    m=launcher();monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m.shutil,'which',lambda _:None)
    monkeypatch.setattr(m.platform,'system',lambda:'Linux');monkeypatch.setattr(m.platform,'machine',lambda:'x86_64')
    binary=b'Synthetic binary fixture: never executed.'
    digest=sha256(binary).hexdigest()
    asset={'name':'cloudflared-linux-amd64','digest':'sha256:'+('0'*64 if fault=='digest' else digest),
        'browser_download_url':('https://untrusted.invalid/file' if fault=='origin' else
            'https://github.com/cloudflare/cloudflared/releases/download/fixture/cloudflared-linux-amd64')}
    def response(req):
        return httpx.Response(200,json={'assets':[asset]}) if str(req.url)==m.RELEASE else httpx.Response(200,content=binary)
    with httpx.Client(transport=httpx.MockTransport(response),follow_redirects=True) as client:
        if fault:
            with pytest.raises(ValueError):m.cloudflared(client)
            assert not list(tmp_path.rglob('*.download'))
        else:
            path=Path(m.cloudflared(client));assert path.read_bytes()==binary and path.stat().st_mode&0o100
            assert m.cloudflared(client)==str(path)


def test_missing_official_digest_fails_without_executing(monkeypatch,tmp_path):
    m=launcher();monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m.shutil,'which',lambda _:None)
    monkeypatch.setattr(m.platform,'system',lambda:'Linux');monkeypatch.setattr(m.platform,'machine',lambda:'x86_64')
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'assets':[]}))) as client:
        with pytest.raises(ValueError,match='SHA-256'):m.cloudflared(client)


def test_tunnel_uses_loopback_http2_and_isolated_configuration():
    m=launcher();command=m.tunnel_command('cloudflared',5018,Path('/tmp/empty.yml'))
    assert command[command.index('--url')+1]=='http://127.0.0.1:5018'
    assert command[command.index('--protocol')+1]=='http2'
    assert command[command.index('--config')+1]=='/tmp/empty.yml'
    process=SimpleNamespace(stdout=io.StringIO('ignore log\nhttps://api.trycloudflare.com/tunnel\nhttps://synthetic-review.trycloudflare.com\n'),poll=lambda:None)
    assert m.tunnel_origin(process,timeout=1)=='https://synthetic-review.trycloudflare.com'
    assert not m.LINK.search('https://synthetic-review.trycloudflare.com.evil.invalid')


@pytest.mark.parametrize('allowed',[True,False])
def test_public_verifier_checks_real_owner_cookie_csrf_and_clears_blank_session(make_api,allowed):
    # In-process WSGI transport, equivalent routes/headers; not a network test.
    app,manager=make_api();origin='https://synthetic-review.trycloudflare.com'
    app.config.update(SESSION_COOKIE_SECURE=True,ALLOWED_ORIGINS=[origin] if allowed else [])
    def private_api(environ,start_response):
        environ.update(HTTP_HOST='127.0.0.1:8018',**{'wsgi.url_scheme':'http'})
        return app(environ,start_response)
    def frontend(environ,start_response):
        start_response('200 OK',[('Content-Type','text/html')]);return [b'<html>synthetic frontend fixture</html>']
    wsgi=DispatcherMiddleware(frontend,{'/api/sra-assessment':private_api})
    with httpx.Client(transport=httpx.WSGITransport(app=wsgi)) as client:
        if allowed:
            launcher().verify_public(client,origin)
            assert any(cookie.secure for cookie in client.cookies.jar)
            # No participant data or live blank session remains after verification.
            assert not manager.records
        else:
            with pytest.raises(httpx.HTTPStatusError):launcher().verify_public(client,origin)


# Reuse the existing injected synthetic API fixture; no production mock is added.
from test_api_integration import make_api


@pytest.mark.parametrize('fault',[None,'profile','port','stale','command'])
def test_reuses_only_the_live_recorded_a2_supervisor(monkeypatch,tmp_path,fault):
    m=launcher();root=tmp_path/'project';runtime=root/'.runtime';runtime.mkdir(parents=True)
    proc=tmp_path/'proc';pid=proc/'123';pid.mkdir(parents=True)
    command=['/existing/python',str(root/'scripts/supervise.py'),'vllm','synthetic launch fixture']
    row={'pid':123,'root':str(root),'start_time':'start-123','command':command,
        'environment':{'IAM_GPU_PROFILE':'liono-a2','IAM_BASE_URL':'http://127.0.0.1:18003'}}
    fields=['0']*20;fields[19]='start-123'
    (pid/'stat').write_text('123 (python) '+' '.join(fields))
    (pid/'cmdline').write_bytes(b'\0'.join(s.encode() for s in command)+b'\0')
    if fault=='profile':row['environment']['IAM_GPU_PROFILE']='liono-v100s'
    if fault=='port':row['environment']['IAM_BASE_URL']='http://127.0.0.1:18002'
    if fault=='stale':row['start_time']='an earlier process'
    if fault=='command':row['command']=['another service']
    (runtime/'vllm.pid.json').write_text(json.dumps(row))
    monkeypatch.setattr(m,'ROOT',root)
    monkeypatch.setattr(m,'Path',lambda value:proc if value=='/proc' else Path(value))
    assert m.owned_a2(18003)==(fault is None)


def test_occupied_defaults_are_skipped_without_reusing_ports(monkeypatch):
    m=launcher();busy={5018,5019,8018}
    monkeypatch.setattr(m,'port_available',lambda port:port not in busy)
    assert m.review_ports(None,None,18003)==(5020,8019)
    # Reserve the explicit API choice before selecting a frontend automatically.
    assert m.review_ports(None,5020,18003)==(5021,5020)


def test_explicit_busy_port_is_named_and_never_silently_changed(monkeypatch):
    m=launcher();monkeypatch.setattr(m,'port_available',lambda port:port!=8028)
    with pytest.raises(ValueError,match=r'API port 8028.*Omit --api-port'):
        m.review_ports(None,8028,18003)


def test_model_port_is_excluded_from_automatic_review_ports(monkeypatch):
    m=launcher();monkeypatch.setattr(m,'port_available',lambda port:True)
    assert m.review_ports(None,None,5018)==(5019,8018)


def test_all_busy_candidates_produce_bounded_clear_failure(monkeypatch):
    m=launcher();probed=[]
    monkeypatch.setattr(m,'port_available',lambda port:probed.append(port) or False)
    with pytest.raises(ValueError,match='No free frontend port'):
        m.review_ports(None,None,18003)
    assert len(probed)==100


@pytest.mark.parametrize('error,expected',[(98,False),(1,None)])
def test_only_address_in_use_is_treated_as_a_busy_port(monkeypatch,error,expected):
    m=launcher()
    class Probe:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def bind(self,address):raise OSError(error,'Synthetic socket error')
    monkeypatch.setattr(m.socket,'socket',lambda:Probe())
    if expected is None:
        with pytest.raises(OSError) as exc:m.port_available(5018)
        assert exc.value.errno==1
    else:assert m.port_available(5018) is expected


def test_final_port_check_reports_the_conflicting_number(monkeypatch):
    m=launcher();monkeypatch.setattr(m,'port_available',lambda p:p!=8018)
    with pytest.raises(ValueError,match='Review port 8018 is occupied'):
        m.free_ports([5018,8018,18003])
