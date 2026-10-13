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

print('GPU inventory (no processes will be stopped):')
try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=index,uuid,name,memory.total,memory.used',
                             '--format=csv'], capture_output=True, text=True, timeout=10)
    print(result.stdout if result.returncode == 0 else 'GPU inventory unavailable in this environment.')
except (OSError, subprocess.TimeoutExpired):
    print('GPU inventory unavailable in this environment.')

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
