#!/usr/bin/env python3
"""Select Liono/Davinci inference; keep the API, sources and Vue app in this checkout."""
import argparse
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import socket
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PROFILES = json.loads((ROOT / 'configs/gpu-profiles.json').read_text())['profiles']
# Explicit allowlist: never copy sources, transcripts, credentials or environments.
INFERENCE_FILES = (
    'configs/model.json', 'configs/gpu-profiles.json',
    'requirements-vllm.txt', 'requirements-lock.txt',
    'scripts/ops.py', 'scripts/supervise.py', 'scripts/download-model.py',
    'scripts/setup-inference.sh', 'scripts/wait-model.py',
    'scripts/start-vllm.sh', 'scripts/stop-vllm.sh', 'scripts/diagnose-model.py',
)


def archive():
    content = io.BytesIO()
    with tarfile.open(fileobj=content, mode='w') as bundle:
        for name in INFERENCE_FILES:
            path = ROOT / name
            info = tarfile.TarInfo(name)
            data = path.read_bytes()
            info.size = len(data)
            info.mode = 0o600
            bundle.addfile(info, io.BytesIO(data))
    return content.getvalue()


def remote_root(directory):
    path = PurePosixPath(directory)
    if not directory or path.is_absolute() or '..' in path.parts or str(path) == '.':
        raise ValueError('--remote-dir must be a directory relative to the remote home, without ..')
    return '"$HOME"/' + shlex.quote(str(path))


def upload_script(directory, host):
    return f'''set -eu
test "$(hostname -s)" = {shlex.quote(host)} || {{ echo 'Unexpected remote host; nothing uploaded.' >&2; exit 1; }}
root={remote_root(directory)}
if [ -e "$root" ] && [ ! -f "$root/.iam-sra-inference" ]; then
  echo 'Refusing to overwrite an unmarked directory. Choose another --remote-dir.' >&2
  exit 1
fi
umask 077
mkdir -p "$root"
: > "$root/.iam-sra-inference"
tar -xf - -C "$root"
'''


def ssh_command(target):
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@:-]*', target):
        raise ValueError('Use an SSH host alias or user@hostname for --ssh')
    return ['ssh', '-T', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3', target]


def settings(args):
    values = {'IAM_GPU_PROFILE': args.profile, 'IAM_VLLM_PORT': str(args.port),
              'IAM_BASE_URL': f'http://127.0.0.1:{args.port}',
              # Ignore stale device/precision choices from previous launches.
              'IAM_GPU_UUID': args.gpu_uuid or '',
              'IAM_CPU_OFFLOAD_GB': args.cpu_offload_gb if args.cpu_offload_gb is not None else '',
              'IAM_GPU_MEMORY_UTILIZATION': args.gpu_memory_utilization}
    if args.python:
        values['IAM_PYTHON'] = args.python
    return values


def run_host(args, command, *, remote, target=None):
    values = settings(args)
    # An empty offload variable means automatic selection, so remove it.
    automatic = values.pop('IAM_CPU_OFFLOAD_GB') == ''
    if not automatic:
        values['IAM_CPU_OFFLOAD_GB'] = args.cpu_offload_gb
    if remote:
        unset = 'unset IAM_CPU_OFFLOAD_GB; ' if automatic else ''
        script = ('set -eu; cd ' + remote_root(args.remote_dir) + '; ' + unset
                  + 'exec env ' + shlex.join([f'{key}={value}' for key, value in values.items()])
                  + ' ' + shlex.join(command))
        call = ssh_command(target) + [script]
        kwargs = {}
    else:
        environment = os.environ.copy()
        if automatic:
            environment.pop('IAM_CPU_OFFLOAD_GB', None)
        environment.update(values)
        call = command
        kwargs = {'cwd': ROOT, 'env': environment}
    if args.dry_run:
        if not remote:
            print(shlex.join(['env', '-u', 'IAM_CPU_OFFLOAD_GB'] +
                             [f'{key}={value}' for key, value in values.items()] + call), flush=True)
        else:
            print(shlex.join(call), flush=True)
        return
    subprocess.run(call, check=True, **kwargs)


def port_free(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))


def execute(args):
    profile = PROFILES[args.profile]
    remote = socket.gethostname().split('.')[0].lower() != profile['host']
    target = args.ssh or os.getenv('IAM_' + profile['host'].upper() + '_SSH') or profile.get('ssh')
    if remote and not target:
        raise ValueError(f"Run this profile on {profile['host']}, or provide --ssh user@hostname")
    if remote:
        ssh_command(target)  # Validate before any side effect.
        remote_root(args.remote_dir)
    print(f"{args.profile}: {profile['host']} / {profile['gpu'].upper()}; "
          f"app endpoint http://127.0.0.1:{args.port}", flush=True)

    if args.action == 'prepare':
        if remote:
            upload = ssh_command(target) + [upload_script(args.remote_dir, profile['host'])]
            if args.dry_run:
                print('Upload only: ' + ', '.join(INFERENCE_FILES), flush=True)
                print(shlex.join(upload), flush=True)
            else:
                subprocess.run(upload, input=archive(), check=True)
        run_host(args, ['bash', 'scripts/setup-inference.sh'], remote=remote, target=target)
        return
    if args.action == 'check':
        run_host(args, ['.venv/bin/python', 'scripts/ops.py', 'preflight', 'vllm'],
                 remote=remote, target=target)
        return
    if args.action == 'tunnel' and not remote:
        raise ValueError('This profile is local; no model SSH tunnel is required')
    # Do not start a remote model if the application-side forward is occupied.
    if remote and not args.dry_run:
        port_free(args.port)
    if args.action == 'start':
        run_host(args, ['.venv/bin/python', 'scripts/ops.py', 'start', 'vllm'],
                 remote=remote, target=target)
    run_host(args, ['.venv/bin/python', 'scripts/wait-model.py', '--timeout', str(args.timeout)],
             remote=remote, target=target)
    if remote:
        command = ssh_command(target)
        # SSH options precede the destination; both ends bind exclusively to loopback.
        command[-1:-1] = ['-N', '-o', 'ExitOnForwardFailure=yes', '-L',
                         f'127.0.0.1:{args.port}:127.0.0.1:{args.port}']
        print('Keep this terminal open for the model tunnel. Ctrl+C closes the tunnel; '
              'the remote model stays running.', flush=True)
        if args.dry_run:
            print(shlex.join(command), flush=True)
        else:
            subprocess.run(command, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list', 'prepare', 'check', 'start', 'tunnel'])
    parser.add_argument('profile', nargs='?', choices=PROFILES)
    parser.add_argument('--port', type=int, default=18000, help='Model and local forward port (default: 18000)')
    parser.add_argument('--remote-dir', default='iam-sra-inference', help='Separate directory relative to remote home')
    parser.add_argument('--ssh', help='Override SSH destination; existing SSH config/ProxyJump is honoured')
    parser.add_argument('--gpu-uuid', help='Select one matching GPU if multiple idle cards match')
    parser.add_argument('--cpu-offload-gb', help='Override automatic 8 GiB weight offload on <=18 GiB GPUs')
    parser.add_argument('--gpu-memory-utilization', default='0.80')
    parser.add_argument('--python', help='Python 3.10–3.12 executable for a NEW model environment')
    parser.add_argument('--timeout', type=int, default=600, help='Model readiness timeout, 1–600 seconds')
    parser.add_argument('--dry-run', action='store_true', help='Print commands; do not connect, install or start')
    args = parser.parse_args(argv)
    if args.action == 'list':
        for name, profile in PROFILES.items():
            print(f"{name:16} {profile['host']:8} {profile['gpu'].upper()}")
        return 0
    if not args.profile:
        parser.error('a profile is required')
    if not 1024 <= args.port <= 65535 or not 1 <= args.timeout <= 600:
        parser.error('use a port between 1024 and 65535 and a timeout between 1 and 600')
    try:
        memory = float(args.gpu_memory_utilization)
        offload = float(args.cpu_offload_gb) if args.cpu_offload_gb is not None else 0
        if not 0.1 <= memory <= 0.85 or not math.isfinite(offload) or not 0 <= offload <= 16:
            raise ValueError
    except ValueError:
        parser.error('memory utilization must be 0.1–0.85 and CPU offload must be 0–16 GiB')
    try:
        execute(args)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            print(f'Command failed (exit {exc.returncode}). No existing service was stopped. '
                  'For model loading failures, inspect .runtime/vllm.log on the model host.', file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
