#!/usr/bin/env python3
"""Temporary FN browser link using the existing Vue/API stack and a selected GPU.

Run from Liono's normal terminal, not a network/GPU-restricted execution sandbox.
Only the review API, frontend and tunnel started here are stopped on Ctrl+C.
The selected model starts on demand and is released after inactivity or review shutdown.
"""
import argparse
import errno
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
from queue import Empty, Queue
import re
import shutil
import signal
import socket
import subprocess
import sys
from threading import Thread
import time
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.runtime/fn-review'
REVIEW_PATH = '/iam-sra-fn-review'
RELEASE = 'https://api.github.com/repos/cloudflare/cloudflared/releases/latest'
LINK = re.compile(r'https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com(?=[\s/]|$)')


def free_ports(ports):
    if len(set(ports)) != len(ports) or any(not 1024 <= p <= 65535 for p in ports):
        raise ValueError('Use three different ports in 1024–65535.')
    # Check review ports first, before downloading or starting any process.
    for port in ports[:2]:
        if not port_available(port):
            raise ValueError(f'Review port {port} is occupied. Omit explicit review ports for automatic selection.')


def port_available(port):
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', port))
        except OSError as exc:
            if exc.errno == errno.EADDRINUSE:
                return False
            raise  # Permission/network restrictions are not port conflicts.
    return True


def review_ports(ui, api, model):
    """Skip busy defaults; explicit ports must be honoured or clearly rejected."""
    explicit = [p for p in (ui, api, model) if p is not None]
    if len(set(explicit)) != len(explicit) or any(not 1024 <= p <= 65535 for p in explicit):
        raise ValueError('Use three different ports in 1024–65535.')
    excluded = set(explicit)
    selected = []
    for name, requested, preferred in [('frontend', ui, 5018), ('API', api, 8018)]:
        if requested is not None:
            if not port_available(requested):
                raise ValueError(f'The requested {name} port {requested} is occupied. '
                    f'Omit --{"ui" if name == "frontend" else "api"}-port to choose automatically.')
            selected.append(requested)
        else:
            port = next((p for p in range(preferred, preferred + 100)
                         if p not in excluded and port_available(p)), None)
            if port is None:
                raise ValueError(f'No free {name} port found in {preferred}–{preferred + 99}; select an explicit port.')
            selected.append(port)
            excluded.add(port)
    return tuple(selected)


def owned_a2(port):
    """Reuse only this checkout's live, recorded A2 supervisor on this port."""
    try:
        row = json.loads((ROOT / '.runtime/vllm.pid.json').read_text())
        proc = Path('/proc') / str(int(row['pid']))
        started = (proc / 'stat').read_text().split(') ', 1)[1].split()[19]
        command = (proc / 'cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
        env = row['environment']
        return (proc.stat().st_uid == os.getuid() and row['root'] == str(ROOT)
            and started == row['start_time'] and command == row['command']
            and command[1:3] == [str(ROOT / 'scripts/supervise.py'), 'vllm']
            and env.get('IAM_GPU_PROFILE') == 'liono-a2'
            and env.get('IAM_BASE_URL') == f'http://127.0.0.1:{port}')
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return False


def prepare_review_model(variant):
    """CPU/network-only preparation; pinned model cache is additive."""
    sys.path.insert(0, str(ROOT / 'src'))
    from iam_sra.model_spec import load_model, snapshot_path, validate_awq_snapshot
    spec = load_model(ROOT, variant)
    cached = snapshot_path(ROOT, spec)
    if variant == 'awq':
        try:
            validate_awq_snapshot(cached)
            return spec
        except (OSError, ValueError, KeyError):
            pass
    elif list(cached.glob('*.safetensors')):
        return spec
    print('Preparing '+spec['model']+' in the existing cache (first AWQ download is about 6.1 GB; no GPU is used).', flush=True)
    environment = os.environ.copy()
    environment['IAM_MODEL_VARIANT'] = variant
    subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'scripts/download-model.py')],
                   cwd=ROOT, env=environment, check=True)
    if variant == 'awq': validate_awq_snapshot(cached)
    return spec


def prepare_v100(remote_dir, port, *, thinking=False):
    """Prepare an isolated Davinci inference checkout without starting a model."""
    command=[sys.executable,str(ROOT/'scripts/model-host.py'),'prepare','davinci-v100',
        '--variant','fp16','--port',str(port),'--remote-dir',remote_dir]
    if thinking:command.append('--thinking')
    subprocess.run(command,cwd=ROOT,check=True)


def verify_v100_model(backend):
    """Verify one real completion in the selected V100 mode, then release its lease."""
    backend.start(time.monotonic()+610)
    probe_error=None
    try:
        with httpx.Client(timeout=180,trust_env=False) as client:
            response=client.post(f'http://127.0.0.1:{backend.port}/v1/chat/completions',json={
                'model':'Qwen/Qwen3-8B','messages':[{'role':'user','content':'Return only the word READY.'}],
                'temperature':0,'max_tokens':512,
                'chat_template_kwargs':{'enable_thinking':bool(backend.thinking)}})
            if response.is_error:
                probe_error=f'HTTP {response.status_code}'
                raise ValueError('V100 inference probe failed: '+probe_error)
            content=response.json()['choices'][0]['message'].get('content','')
            if not isinstance(content,str) or not content.strip():
                probe_error='empty completion'
                raise ValueError('V100 inference probe failed: '+probe_error)
    except httpx.TimeoutException:
        probe_error='request timeout'
        raise ValueError('V100 inference probe failed: '+probe_error) from None
    except httpx.HTTPError as exc:
        probe_error=type(exc).__name__
        raise ValueError('V100 inference probe failed: '+probe_error) from None
    except (KeyError,ValueError) as exc:
        if probe_error is None:probe_error='invalid response ('+type(exc).__name__+')'
        raise
    finally:
        if not backend.stop():
            raise ValueError('The V100 probe model could not be safely released.')


def cloudflared(client):
    installed = shutil.which('cloudflared')
    if installed:
        return installed
    arch = {'x86_64': 'amd64', 'aarch64': 'arm64'}.get(platform.machine())
    if platform.system() != 'Linux' or not arch:
        raise ValueError('Install cloudflared for this platform first.')
    print('Downloading the official cloudflared binary into .runtime/tools (no sudo).', flush=True)
    release = client.get(RELEASE)
    release.raise_for_status()
    asset = next((a for a in release.json()['assets'] if a['name'] == f'cloudflared-linux-{arch}'), None)
    if not asset or not re.fullmatch(r'sha256:[0-9a-f]{64}', asset.get('digest') or ''):
        raise ValueError('Official release has no SHA-256 digest. Install cloudflared manually; nothing executed.')
    url = asset['browser_download_url']
    if not url.startswith('https://github.com/cloudflare/cloudflared/releases/download/'):
        raise ValueError('Unexpected cloudflared download origin.')
    expected = asset['digest'].split(':')[1]
    tools = ROOT / '.runtime/tools'
    tools.mkdir(parents=True, exist_ok=True)
    destination = tools / ('cloudflared-' + expected[:16])
    if destination.exists() and sha256(destination.read_bytes()).hexdigest() == expected:
        return str(destination)
    temporary = destination.with_suffix('.download')
    try:
        digest = sha256()
        size = 0
        with client.stream('GET', url) as response:
            response.raise_for_status()
            with temporary.open('wb') as output:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 128 * 1024 * 1024:
                        raise ValueError('Unexpected cloudflared download size.')
                    output.write(chunk)
                    digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError('Cloudflared checksum mismatch; nothing executed.')
        temporary.chmod(0o700)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return str(destination)


def tunnel_command(binary, port, configuration):
    return [binary, 'tunnel', '--config', str(configuration), '--no-autoupdate',
        '--url', f'http://127.0.0.1:{port}', '--protocol', 'http2',
        '--metrics', '127.0.0.1:0', '--loglevel', 'info']


def tunnel_origin(process, timeout=90):
    origins = Queue(maxsize=1)
    def drain():
        for line in process.stdout:
            match = LINK.search(line)
            if match and match.group() not in {'https://api.trycloudflare.com', 'https://www.trycloudflare.com'} and origins.empty():
                origins.put_nowait(match.group())
            # Do not retain tunnel logs, which could include request details.
    Thread(target=drain, daemon=True).start()
    deadline = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < deadline:
        try:
            return origins.get(timeout=.5)
        except Empty:
            pass
    raise ValueError('Cloudflare did not issue a test URL. Check outbound Internet access on Liono.')


def wait_health(client, url, processes, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(p.poll() is not None for p in processes):
            raise ValueError('A review service exited during startup; no link was published.')
        try:
            response = client.get(url)
            if response.status_code == 200 and response.json().get('status') == 'ready':
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(1)
    raise ValueError('Review API is not ready. Check private source/corpus and privacy dependencies.')


def verify_public(client, origin):
    """Test the HTTPS page, proxy, Secure ownership cookie and CSRF, then clear."""
    page = client.get(origin + REVIEW_PATH)
    page.raise_for_status()
    if '<html' not in page.text.lower():
        raise ValueError('Public URL did not return the app.')
    prefix = origin + '/api/sra-assessment/v1'
    boot = client.get(prefix + '/capabilities')
    boot.raise_for_status()
    headers = {'X-CSRF-Token': boot.json()['csrf_token'], 'Origin': origin}
    created = client.post(prefix + '/sessions', json={'mode': 'chat'}, headers=headers)
    created.raise_for_status()
    session = created.json()['session']
    try:
        messages = session['chat']['messages']
        if session['chat']['stage'] != 'conversation' or not any(m.get('act') == 'introduction' for m in messages):
            raise ValueError('Public onboarding check failed.')
    finally:
        cleared = client.delete(prefix + '/sessions/' + session['id'],
            headers={**headers, 'X-Session-Version': str(session['version'])})
        cleared.raise_for_status()


def close_children(processes):
    for process in reversed(processes):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                continue
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)


def public_origin(value):
    """An administrator-configured HTTPS proxy; this does not create DNS."""
    origin=urlsplit(value)
    if (origin.scheme!='https' or not origin.hostname or origin.username or origin.password
            or origin.path not in {'','/'} or origin.query or origin.fragment
            or origin.port not in {None,443}):
        raise argparse.ArgumentTypeError('Use an approved HTTPS origin, for example https://iam-sra.example.org.')
    return value.rstrip('/')


def verify_live_interviews(backend, args, children):
    """Hold the exact model lease before starting any public API or tunnel."""
    backend.start(time.monotonic()+610)
    marker=backend._marker() or {}
    if not backend.owns_running_model() or not marker.get('lease_id'):
        raise ValueError('Live validation model ownership could not be verified.')
    output=STATE/('live-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:8])
    env=os.environ.copy()
    env.update(IAM_BASE_URL=f'http://127.0.0.1:{args.model_port}',IAM_MODEL_VARIANT=args.model_variant,
        IAM_MODEL_THINKING='1' if args.thinking else '0',IAM_SRA_ON_DEMAND_GPU='0',
        IAM_SRA_VALIDATION_LEASE=marker['lease_id'],IAM_MODEL_TIMEOUT_SECONDS='1800',
        IAM_SRA_JOB_TIMEOUT='1800',IAM_CHAT_PROCESSING_SECONDS='3600',
        TLDEXTRACT_CACHE=os.environ.get('TLDEXTRACT_CACHE',str(STATE/'tldextract')))
    command=[sys.executable,str(ROOT/'scripts/smoke-fn-interview.py'),'--allow-live',
        '--respondent','agent','--model-variant',args.model_variant,'--case','all',
        '--base-url',env['IAM_BASE_URL'],'--require-scoring','--case-timeout-seconds','7200',
        '--output',str(output)]
    if args.thinking:command.append('--thinking')
    print('Validating four complete live interviews and scoring before publication. This occupies the A2 while tests run.',flush=True)
    # The child prints only screened metrics/transcripts, never raw model output.
    log=STATE/('validation-'+uuid4().hex+'.log')
    with log.open('x') as stdout:
        log.chmod(0o600)
        process=subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True,stdout=stdout)
        children.append(process)
        try:code=process.wait(timeout=4*7200+300)
        finally:
            if process.poll() is None:close_children([process])
    if not backend.stop():
        raise ValueError('The validation model could not be safely released; no public link was opened.')
    if code!=0:
        raise ValueError(f'Live interviews did not pass scoring/review. Inspect {output}/metrics.json and {log}. No FN link was opened.')
    report=json.loads((output/'metrics.json').read_text())
    # Re-evaluate the report rather than trusting only the process exit status.
    import importlib.util
    spec=importlib.util.spec_from_file_location('fn_live_gate',ROOT/'scripts/smoke-fn-interview.py')
    harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(harness)
    if harness.live_scoring_failures(report,thinking=args.thinking):
        raise ValueError(f'Live scoring report failed publication checks: {output}.')
    print('Live completion/scoring checks passed. Human semantic review is still required. Report: '+str(output),flush=True)
    return output


def verify_model_led_interviews(backend,args,children):
    """Run complete model-led interviews on the selected profile before opening a URL."""
    gpu_profile=getattr(args,'gpu_profile','davinci-v100')
    variant=getattr(args,'model_variant','awq' if gpu_profile=='liono-a2' else 'fp16')
    backend.start(time.monotonic()+610)
    marker=backend._marker() or {}
    if not backend.owns_running_model() or not marker.get('lease_id'):
        raise ValueError(f'{gpu_profile} model-led validation could not verify its model lease.')
    env=os.environ.copy()
    env.update(IAM_BASE_URL=f'http://127.0.0.1:{args.model_port}',IAM_MODEL_VARIANT=variant,
        IAM_MODEL_THINKING='1' if args.thinking else '0',IAM_SRA_ON_DEMAND_GPU='0',
        IAM_SRA_VALIDATION_LEASE=marker['lease_id'],IAM_MODEL_TIMEOUT_SECONDS='900',
        IAM_SRA_JOB_TIMEOUT='1800',IAM_CHAT_PROCESSING_SECONDS='3600',
        IAM_SRA_GPU_PROFILE=gpu_profile,
        IAM_CHAT_INTERVIEW_STRATEGY='model_led_fn',
        TLDEXTRACT_CACHE=os.environ.get('TLDEXTRACT_CACHE',str(STATE/'tldextract')))
    if gpu_profile=='davinci-v100':env['IAM_SRA_REMOTE_DIR']=args.remote_dir
    scenarios=[('citizen_short','fn_unfamiliar_citizen'),
               ('organisational','fn_planning_unit'),
               ('technical','fn_container_component')]
    outputs=[]
    try:
        for case,persona in scenarios:
            output=STATE/(gpu_profile+'-model-led-'+case+'-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:8])
            outputs.append(output)
            command=[sys.executable,str(ROOT/'scripts/smoke-fn-interview.py'),'--allow-live',
                '--respondent','agent','--persona-id',persona,'--model-variant',variant,
                '--case',case,'--base-url',env['IAM_BASE_URL'],'--max-turns','120',
                '--max-agent-calls','100','--case-timeout-seconds','1800','--save-traces','--output',str(output)]
            if args.thinking:command.append('--thinking')
            if args.thinking:command.append('--respondent-no-think')
            print(f'Running complete {gpu_profile} model-led {case} interview, score, review and export.',flush=True)
            log=STATE/(gpu_profile+'-model-led-validation-'+case+'-'+uuid4().hex+'.log')
            with log.open('x') as stdout:
                log.chmod(0o600)
                process=subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True,stdout=stdout)
                children.append(process)
                try:code=process.wait(timeout=1950)
                finally:
                    if process.poll() is None:close_children([process])
                children.remove(process)
            if code!=0:
                raise ValueError(f'{gpu_profile} model-led {case} interview failed; inspect {output}/metrics.json and {log}. No link was opened.')
            report=json.loads((output/'metrics.json').read_text())
            row=next((item for item in report.get('cases',[]) if item.get('case')==case),None)
            if not row or not row.get('protocol_passed') or row.get('run_incomplete'):
                raise ValueError(f'{gpu_profile} model-led {case} interview did not satisfy completion/review/export checks: {output}. No link was opened.')
            if row.get('scoring_generation_calls',0)<1 or row.get('score_status') not in {'suggested','abstained'}:
                raise ValueError(f'{gpu_profile} model-led {case} scoring was not completed: {output}. No link was opened.')
            if row.get('score_status')=='suggested' and (not 1<=int(row.get('level') or 0)<=9
                    or not row.get('score_citation_count') or not row.get('score_boundary_present')):
                raise ValueError(f'{gpu_profile} model-led {case} score lacked a validated citation/boundary: {output}. No link was opened.')
            print(f'{gpu_profile} model-led {case} completion, scoring/review and export checks passed: {output}',flush=True)
        return outputs
    finally:
        if not backend.stop():
            raise ValueError('The V100 model-led validation model could not be safely released.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ui-port', type=int, help='Explicit frontend port; otherwise try 5018–5117')
    parser.add_argument('--api-port', type=int, help='Explicit API port; otherwise try 8018–8117')
    parser.add_argument('--gpu-profile',choices=['liono-a2','liono-v100s','davinci-v100'],default='liono-a2')
    parser.add_argument('--remote-dir',default='iam-sra-v100-review',help='Separate Davinci inference directory')
    parser.add_argument('--model-variant', choices=['awq','fp16'], default=None, help='Defaults to AWQ for A2 and FP16 for V100')
    parser.add_argument('--model-port', type=int, default=None)
    parser.add_argument('--thinking',action='store_true',help='Experimental thinking with an 8192-token context; requires live validation on the selected profile.')
    parser.add_argument('--interview-strategy',choices=['controller_fn','model_led_fn'],
        default=os.getenv('IAM_CHAT_INTERVIEW_STRATEGY','controller_fn'),
        help='Use the isolated model-led FN interviewer only when explicitly selected.')
    parser.add_argument('--validation-only',action='store_true',help='Run live model validation and exit without publishing.')
    parser.add_argument('--public-origin',type=public_origin,help='Existing approved HTTPS reverse proxy pointing at --ui-port; no Cloudflare Quick Tunnel is started.')
    parser.add_argument('--gpu-uuid', help='An allocated Liono A2, if multiple matching idle GPUs exist')
    parser.add_argument('--idle-seconds', type=int, default=60, help='Release the review model after this many idle seconds (10–3600)')
    parser.add_argument('--release-existing-a2', action='store_true', help='Explicitly release the old always-on review A2 model at --model-port')
    parser.add_argument('--dry-run', action='store_true', help='Show the plan without sockets, installs or service changes')
    args = parser.parse_args(argv)
    args.model_variant=args.model_variant or ('awq' if args.gpu_profile=='liono-a2' else 'fp16')
    args.model_port=args.model_port or {'liono-a2':18003,'liono-v100s':18022,'davinci-v100':18010}[args.gpu_profile]
    if args.gpu_profile=='davinci-v100' and args.model_variant!='fp16':
        parser.error('Davinci V100 preview requires FP16.')
    if args.gpu_profile=='davinci-v100' and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',args.remote_dir):
        parser.error('--remote-dir must be a simple isolated directory name.')
    if not 1024<=args.model_port<=65535:parser.error('--model-port must be in 1024–65535.')
    if args.thinking and (args.gpu_profile,args.model_variant) not in {('liono-a2','awq'),('liono-v100s','fp16'),('davinci-v100','fp16')}:
        parser.error('--thinking requires Liono A2/AWQ or a validated FP16 profile.')
    if not 10 <= args.idle_seconds <= 3600:
        parser.error('--idle-seconds must be in 10–3600')
    if args.dry_run:
        print(json.dumps({'profile': args.gpu_profile, 'model': f'http://127.0.0.1:{args.model_port}',
            'api': f'http://127.0.0.1:{args.api_port or 8018}', 'frontend': f'http://127.0.0.1:{args.ui_port or 5018}',
            'automatic_review_ports': args.ui_port is None or args.api_port is None,
            'public_link': args.public_origin or 'Issued by Cloudflare at runtime; verified before printing',
            'third_party_relay': None if args.public_origin else 'Cloudflare', 'cookie_secure': True,
            'model_lifecycle': 'on_demand', 'idle_seconds': args.idle_seconds,
            'model_variant': args.model_variant, 'cpu_offload_gb': 0 if args.gpu_profile in {'davinci-v100','liono-v100s'} or args.model_variant == 'awq' else 8,
            'thinking_enabled':args.thinking,'live_scoring_required':True,'validation_only':args.validation_only,
            'interview_strategy':args.interview_strategy,
            'full_model_led_validation':args.interview_strategy=='model_led_fn',
            'approved_public_origin':args.public_origin,
            'release_previous_review_model': args.release_existing_a2,
            'stops_existing_services': args.release_existing_a2, 'changes_firewall': False}, indent=2))
        return 0
    children = []
    lock = None
    owns_state = False
    backend = None
    try:
        if socket.gethostname().split('.')[0] != 'liono':
            raise ValueError('Run this command on Liono; Vue/API stay here while inference is forwarded from Davinci.')
        if not args.validation_only:
            if not (ROOT / 'app/dist/index.html').is_file():
                raise ValueError('Build the frontend first: cd app && npm run build')
            args.ui_port, args.api_port = review_ports(args.ui_port, args.api_port, args.model_port)
            free_ports([args.ui_port, args.api_port, args.model_port])
            print(f'Review ports: frontend {args.ui_port}, API {args.api_port}, model {args.model_port}.', flush=True)
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = (STATE / 'share.lock').open('a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('The FN sharing launcher is already running. Save current interview downloads, '
                'press Ctrl+C in its terminal/tmux, then rerun this command. '
                'Its GPU idle watcher must be stopped before isolated validation.') from None
        owns_state = True
        def stop(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGHUP, stop)
        sys.path.insert(0, str(ROOT / 'src'))
        os.environ['IAM_MODEL_THINKING']='1' if args.thinking else '0'
        os.environ['IAM_MODEL_VARIANT']=args.model_variant
        from iam_sra.model_lifecycle import ProjectA2, ProjectDavinciV100, ProjectLionoV100S
        if args.gpu_profile=='liono-a2':
            backend = ProjectA2(args.model_port, root=ROOT, gpu_uuid=args.gpu_uuid, variant=args.model_variant)
        elif args.gpu_profile=='liono-v100s':
            backend = ProjectLionoV100S(args.model_port,root=ROOT,gpu_uuid=args.gpu_uuid,variant='fp16')
        else:
            backend = ProjectDavinciV100(args.model_port,root=ROOT,remote_dir=args.remote_dir,variant='fp16')
        if backend.marker.exists() and not backend.stop():
            raise ValueError('Cannot verify/release the previous review model; inspect its owner record in a normal terminal.')
        if args.gpu_profile=='liono-a2' and owned_a2(args.model_port):
            if not args.release_existing_a2:
                raise ValueError('An always-on A2 model already occupies the review endpoint. '
                    'To release that old review model, rerun with --release-existing-a2.')
            if not backend.release_existing():
                raise ValueError('The old review model could not be safely released.')
        for name in ('chat-url.txt',):
            (STATE / name).unlink(missing_ok=True)
        if args.gpu_profile=='davinci-v100':
            print(f'Preparing isolated Davinci directory {args.remote_dir}; this does not modify the A30 service.',flush=True)
            prepare_v100(args.remote_dir,args.model_port,thinking=args.thinking)
            verify_v100_model(backend)
            print('V100 generation probe passed.',flush=True)
            if args.interview_strategy=='model_led_fn':
                verify_model_led_interviews(backend,args,children)
            else:
                print('Full-interview prepublication validation is available when --interview-strategy model_led_fn is selected.',flush=True)
        elif args.gpu_profile=='liono-v100s':
            spec=prepare_review_model('fp16')
            print('Review checkpoint: '+spec['model']+' / '+spec['revision'],flush=True)
            verify_v100_model(backend)
            print('Liono V100S generation probe passed.',flush=True)
            if args.interview_strategy=='model_led_fn':
                verify_model_led_interviews(backend,args,children)
            else:
                raise ValueError('V100S review requires --interview-strategy model_led_fn for complete prepublication validation.')
        else:
            spec = prepare_review_model(args.model_variant)
            print('Review checkpoint: '+spec['model']+' / '+spec['revision'], flush=True)
            if args.interview_strategy=='model_led_fn':
                verify_model_led_interviews(backend,args,children)
            else:
                verify_live_interviews(backend,args,children)
        if args.validation_only:return 0
        children.clear()  # The finished validation child cannot trip service health checks.
        if not args.public_origin:
            with httpx.Client(trust_env=False, timeout=30, follow_redirects=True) as client:
                binary = cloudflared(client)
        env = os.environ.copy()
        env.update(IAM_BASE_URL=f'http://127.0.0.1:{args.model_port}', IAM_VLLM_PORT=str(args.model_port), IAM_MODEL_VARIANT=args.model_variant,
            IAM_MODEL_THINKING='1' if args.thinking else '0')
        env['IAM_CHAT_INTERVIEW_STRATEGY']=args.interview_strategy
        env.pop('IAM_SRA_VALIDATION_LEASE',None)
        env.update(IAM_SRA_ON_DEMAND_GPU='1', IAM_SRA_GPU_IDLE_SECONDS=str(args.idle_seconds),
            IAM_SRA_REVIEW_GPU_UUID=args.gpu_uuid or '')
        env['IAM_SRA_GPU_PROFILE']=args.gpu_profile
        if args.gpu_profile=='davinci-v100':env['IAM_SRA_REMOTE_DIR']=args.remote_dir
        def launch(command, *, output=False, cwd=ROOT):
            process = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True,
                stdout=subprocess.PIPE if output else subprocess.DEVNULL,
                stderr=subprocess.STDOUT if output else subprocess.DEVNULL, text=True)
            children.append(process)
            return process
        env.update(HOST='127.0.0.1', IAM_SRA_UI_PORT=str(args.ui_port),
            IAM_SRA_API_TARGET=f'http://127.0.0.1:{args.api_port}')
        launch([sys.executable, 'serve_app.py'], cwd=ROOT / 'app')
        configuration = STATE / 'empty-config.yml'
        configuration.write_text('{}\n')  # Do not read/change existing Cloudflare account configuration.
        origin = args.public_origin or tunnel_origin(launch(tunnel_command(binary, args.ui_port, configuration), output=True))
        env.update(IAM_SRA_API_HOST='127.0.0.1', IAM_SRA_API_PORT=str(args.api_port),
            IAM_SRA_ALLOWED_ORIGINS=origin, IAM_SRA_COOKIE_SECURE='1',
            IAM_SRA_API_SECRET=os.urandom(32).hex(),
            IAM_MODEL_TIMEOUT_SECONDS='1800', IAM_SRA_JOB_TIMEOUT='1800', IAM_CHAT_PROCESSING_SECONDS='3600',
            TLDEXTRACT_CACHE=os.environ.get('TLDEXTRACT_CACHE', str(STATE / 'tldextract')))
        # Fixed Python from this invocation; reuse the existing Gunicorn configuration.
        env['IAM_API_PYTHON'] = sys.executable
        launch(['bash', str(ROOT / 'scripts/start-api.sh')])
        with httpx.Client(trust_env=False, timeout=10) as client:
            wait_health(client, f'http://127.0.0.1:{args.api_port}/v1/health', children)
            wait_health(client, origin + '/api/sra-assessment/v1/health', children)
            verify_public(client, origin)
        url = origin + REVIEW_PATH
        (STATE / 'chat-url.txt').write_text(url + '\n')
        print('\nFN test link: ' + url, flush=True)
        print(f'HTTPS page, API, ownership cookie and CSRF checked. The model starts on demand on {args.gpu_profile}.', flush=True)
        print('Anyone with this link can open it; use fictional test answers.'+
            ('' if args.public_origin else ' Traffic passes through Cloudflare.'), flush=True)
        print(f'The review model is released after {args.idle_seconds} idle seconds. Keep this terminal open; Ctrl+C closes the link and releases its model.', flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(1)
        raise ValueError('A review service stopped. The published link is no longer confirmed active.')
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError, httpx.HTTPError, subprocess.SubprocessError) as exc:
        if isinstance(exc, (OSError, ValueError)):
            print('Startup check: ' + str(exc), file=sys.stderr)
        task='Live FN validation could not complete.' if args.validation_only else 'FN link could not be activated.'
        print(task+' Run from Liono’s normal terminal with GPU/network access. '
            'Check selected GPU availability, outbound HTTPS/tunnel access, private sources, and free review ports. '
            'No unrelated service was stopped.', file=sys.stderr)
        return 1
    finally:
        close_children(children)
        if backend is not None and not backend.stop():
            print('Review model release could not be verified. Inspect .runtime/fn-review/model-owner.json in the normal Liono terminal.', file=sys.stderr)
        if owns_state:
            (STATE / 'chat-url.txt').unlink(missing_ok=True)
        if lock is not None:
            lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
