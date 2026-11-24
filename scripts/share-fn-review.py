#!/usr/bin/env python3
"""Temporary FN browser link, using the existing Liono A2/model/API/Vue stack.

Run from Liono's normal terminal, not a network/GPU-restricted execution sandbox.
Only the review API, frontend and tunnel started here are stopped on Ctrl+C.
The project-supervised A2 model remains running. No institutional firewall change.
"""
import argparse
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

import httpx

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.runtime/fn-review'
RELEASE = 'https://api.github.com/repos/cloudflare/cloudflared/releases/latest'
LINK = re.compile(r'https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com(?=[\s/]|$)')


def free_ports(ports):
    if len(set(ports)) != len(ports) or any(not 1024 <= p <= 65535 for p in ports):
        raise ValueError('Use three different ports in 1024–65535.')
    # Check review ports first, before downloading or starting any process.
    for port in ports[:2]:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))


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
    page = client.get(origin + '/chat')
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ui-port', type=int, default=5018)
    parser.add_argument('--api-port', type=int, default=8018)
    parser.add_argument('--model-port', type=int, default=18003)
    parser.add_argument('--gpu-uuid', help='An allocated Liono A2, if multiple matching idle GPUs exist')
    parser.add_argument('--dry-run', action='store_true', help='Show the plan without sockets, installs or service changes')
    args = parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps({'profile': 'liono-a2', 'model': f'http://127.0.0.1:{args.model_port}',
            'api': f'http://127.0.0.1:{args.api_port}', 'frontend': f'http://127.0.0.1:{args.ui_port}',
            'public_link': 'Issued by Cloudflare at runtime; verified before printing',
            'third_party_relay': 'Cloudflare', 'cookie_secure': True,
            'stops_existing_services': False, 'changes_firewall': False}, indent=2))
        return 0
    children = []
    lock = None
    owns_state = False
    try:
        if socket.gethostname().split('.')[0] != 'liono':
            raise ValueError('Run this command on Liono, where the selected A2 is located.')
        if not (ROOT / 'app/dist/index.html').is_file():
            raise ValueError('Build the frontend first: cd app && npm run build')
        free_ports([args.ui_port, args.api_port, args.model_port])
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = (STATE / 'share.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owns_state = True
        def stop(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGHUP, stop)
        for name in ('chat-url.txt',):
            (STATE / name).unlink(missing_ok=True)
        with httpx.Client(trust_env=False, timeout=30, follow_redirects=True) as client:
            binary = cloudflared(client)
        env = os.environ.copy()
        env.update(IAM_BASE_URL=f'http://127.0.0.1:{args.model_port}', IAM_VLLM_PORT=str(args.model_port))
        if owned_a2(args.model_port):
            print('Reusing this checkout’s running Liono A2 model.', flush=True)
            command = [sys.executable, str(ROOT / 'scripts/wait-model.py'), '--timeout', '600']
        else:
            print('Starting Qwen on Liono A2 using existing GPU/workload guards.', flush=True)
            command = [sys.executable, str(ROOT / 'scripts/model-host.py'), 'start', 'liono-a2', '--port', str(args.model_port)]
            if args.gpu_uuid:
                command += ['--gpu-uuid', args.gpu_uuid]
        subprocess.run(command, cwd=ROOT, env=env, check=True)
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
        origin = tunnel_origin(launch(tunnel_command(binary, args.ui_port, configuration), output=True))
        env.update(IAM_SRA_API_HOST='127.0.0.1', IAM_SRA_API_PORT=str(args.api_port),
            IAM_SRA_ALLOWED_ORIGINS=origin, IAM_SRA_COOKIE_SECURE='1',
            IAM_SRA_API_SECRET=os.urandom(32).hex(),
            IAM_MODEL_TIMEOUT_SECONDS='900', IAM_SRA_JOB_TIMEOUT='1800', IAM_CHAT_PROCESSING_SECONDS='3600',
            TLDEXTRACT_CACHE=os.environ.get('TLDEXTRACT_CACHE', str(STATE / 'tldextract')))
        # Fixed Python from this invocation; reuse the existing Gunicorn configuration.
        env['IAM_API_PYTHON'] = sys.executable
        launch(['bash', str(ROOT / 'scripts/start-api.sh')])
        with httpx.Client(trust_env=False, timeout=10) as client:
            wait_health(client, f'http://127.0.0.1:{args.api_port}/v1/health', children)
            wait_health(client, origin + '/api/sra-assessment/v1/health', children)
            verify_public(client, origin)
        url = origin + '/chat'
        (STATE / 'chat-url.txt').write_text(url + '\n')
        print('\nFN test link: ' + url, flush=True)
        print('HTTPS page, API, ownership cookie and CSRF checked. A2 model health checked; no model generation test run.', flush=True)
        print('Anyone with this link can open it; use fictional test answers. Traffic passes through Cloudflare.', flush=True)
        print('Keep this terminal open. Ctrl+C closes the link/API/UI; the A2 model remains supervised.', flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(1)
        raise ValueError('A review service stopped. The published link is no longer confirmed active.')
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError, httpx.HTTPError, subprocess.SubprocessError) as exc:
        if isinstance(exc, (OSError, ValueError)):
            print('Startup check: ' + str(exc), file=sys.stderr)
        print('FN link could not be activated. Run from Liono’s normal terminal with GPU/network access. '
            'Check A2 availability, outbound HTTPS/tunnel access, private sources, and free review ports. '
            'No existing service was stopped.', file=sys.stderr)
        return 1
    finally:
        close_children(children)
        if owns_state:
            (STATE / 'chat-url.txt').unlink(missing_ok=True)
        if lock is not None:
            lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
