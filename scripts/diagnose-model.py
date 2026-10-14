#!/usr/bin/env python3
"""Read-only host diagnostics. Never print process arguments or credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import httpx

def process_args(directory):
    return [part.decode(errors='replace') for part in (directory / 'cmdline').read_bytes().split(b'\0') if part]


def recorded_supervisor(proc, project):
    """Only a still-visible, exact recorded supervisor establishes ancestry."""
    try:
        record = json.loads((project / '.runtime/vllm.pid.json').read_text())
        directory = proc / str(int(record['pid']))
        actual = process_args(directory)
        start = (directory / 'stat').read_text().split(') ', 1)[1].split()[19]
        if (directory.stat().st_uid == os.getuid() and record['root'] == str(project)
                and record['start_time'] == start and actual == record['command']
                and len(actual) == 4 and actual[1:3] == [str(project / 'scripts/supervise.py'), 'vllm']):
            return int(record['pid'])
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        pass
    return None


def describe_process(pid, *, proc=Path('/proc'), project=ROOT):
    """Ownership hints only, never permission to kill; no arguments are returned."""
    result = {'pid': pid, 'owner_uid': None, 'same_user': None,
              'parent_pid': None, 'kind': 'unknown', 'project_relation': 'not_visible'}
    directory = proc / str(pid)
    try:
        uid = directory.stat().st_uid
        result.update(owner_uid=uid, same_user=uid == os.getuid())
        args = process_args(directory)
        if 'vllm.entrypoints.openai.api_server' in args:
            result['kind'] = 'vllm_api'
        elif args and args[0].startswith('VLLM::'):
            result['kind'] = 'vllm_worker'
        elif args and Path(args[0]).name.startswith('python'):
            result['kind'] = 'python_process'
        else:
            result['kind'] = 'other_process'
        parent = int(next(line.split()[1] for line in (directory / 'status').read_text().splitlines() if line.startswith('PPid:')))
        result['parent_pid'] = parent
        result['project_relation'] = 'same_user_other_or_unknown_context' if result['same_user'] else 'other_user'
        try:
            if result['same_user'] and (directory / 'cwd').resolve(strict=True) == project:
                result['project_relation'] = 'project_directory_only_unverified'
        except OSError:
            pass
        supervisor = recorded_supervisor(proc, project)
        current = pid
        seen = set()
        for _ in range(12):
            if current in seen or current <= 1:
                break
            if result['same_user'] and supervisor is not None and current == supervisor:
                result['project_relation'] = 'verified_recorded_model_tree'
                break
            seen.add(current)
            current = int(next(line.split()[1] for line in (proc / str(current) / 'status').read_text().splitlines() if line.startswith('PPid:')))
    except (OSError, ValueError, StopIteration):
        pass
    return result


def gpu_process_rows(output, *, proc=Path('/proc'), project=ROOT):
    import re
    rows = []
    for line in output.splitlines():
        fields = [field.strip() for field in line.split(',')]
        if len(fields) != 3 or not re.fullmatch(r'GPU-[a-fA-F0-9-]+', fields[0]) or not fields[1].isdigit():
            continue
        rows.append({**describe_process(int(fields[1]), proc=proc, project=project),
                     'gpu_uuid': fields[0], 'memory_mib': int(fields[2]) if fields[2].isdigit() else None})
    return rows


def gpu_process_inventory():
    print('GPU process ownership (read-only; no command arguments shown):')
    try:
        result = subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_gpu_memory',
                                 '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print('GPU process inventory unavailable in this environment.')
            return
        rows = gpu_process_rows(result.stdout)
        for row in rows:
            print(json.dumps(row, sort_keys=True))
        if not rows:
            print('No compute-process rows reported; GPU memory may still be reserved or not visible.')
        print('Project directory alone is not verified ownership. Do not stop unrelated or unidentified workloads.')
    except (OSError, subprocess.TimeoutExpired):
        print('GPU process inventory unavailable in this environment.')


def main():
    print('GPU inventory (no processes will be stopped):')
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=index,uuid,name,memory.total,memory.used',
                                 '--format=csv'], capture_output=True, text=True, timeout=10)
        print(result.stdout if result.returncode == 0 else 'GPU inventory unavailable in this environment.')
    except (OSError, subprocess.TimeoutExpired):
        print('GPU inventory unavailable in this environment.')

    gpu_process_inventory()

    # Read listener ports only; avoid command lines, which may contain API keys.
    ports = {int(os.getenv('IAM_VLLM_PORT', '8000'))}
    for table in ('/proc/net/tcp', '/proc/net/tcp6'):
        try:
            for line in Path(table).read_text().splitlines()[1:]:
                fields = line.split()
                if fields[3] == '0A':
                    ports.add(int(fields[1].split(':')[1], 16))
        except (OSError, ValueError, IndexError):
            pass
    addresses = {f'http://127.0.0.1:{port}' for port in ports}
    if os.getenv('IAM_BASE_URL'):
        addresses.add(os.environ['IAM_BASE_URL'].rstrip('/'))
    found = False
    with httpx.Client(timeout=1, trust_env=False, follow_redirects=False) as client:
        for base in sorted(addresses):
            try:
                response = client.get(base + '/v1/models')
                if response.status_code != 200:
                    continue
                models = response.json().get('data', [])
                if not isinstance(models, list):
                    continue
                compatible_name = any(isinstance(m, dict) and m.get('id') == 'Qwen/Qwen3-8B' for m in models)
                # Do not echo arbitrary server output or credential-bearing addresses.
                from urllib.parse import urlsplit
                parsed = urlsplit(base)
                display = f'{parsed.scheme}://{parsed.hostname}:{parsed.port or 80}'
                print('Model endpoint:', display, '| expected Qwen/Qwen3-8B alias:', compatible_name,
                      '| health:', client.get(base + '/health').status_code)
                found = True
            except (httpx.HTTPError, ValueError, TypeError, AttributeError):
                continue
    print('Alias/health checks do not verify model revision, tokenization or guided JSON compatibility.')
    if not found:
        print('No reachable OpenAI model-list endpoint found on local listening ports.')

    print('Project record visibility:')
    for kind in ('vllm', 'ui'):
        try:
            record = json.loads((ROOT / '.runtime' / (kind + '.pid.json')).read_text())
            print(kind, 'record PID', int(record['pid']), '| visible:', Path(f"/proc/{int(record['pid'])}").exists())
        except (OSError, ValueError, KeyError, TypeError):
            print(kind, 'record unavailable')


if __name__ == '__main__':
    main()
