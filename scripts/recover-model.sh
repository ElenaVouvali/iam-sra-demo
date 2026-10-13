#!/usr/bin/env bash
# Run on the GPU/model host, using the existing project's process identity checks.
set -euo pipefail
IAM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if "$IAM_ROOT/.venv/bin/python" - <<'PY'
import os,httpx
port=os.getenv('IAM_VLLM_PORT','8000')
base=os.getenv('IAM_BASE_URL',f'http://127.0.0.1:{port}').rstrip('/')
try:
    with httpx.Client(timeout=5,trust_env=False) as client:
        client.get(f'{base}/health').raise_for_status()
        models=client.get(f'{base}/v1/models');models.raise_for_status()
        assert any(m['id']=='Qwen/Qwen3-8B' for m in models.json()['data'])
except Exception:raise SystemExit(1)
PY
then
    echo 'The configured model service is healthy; no restart needed.'
    exit 0
fi
if [[ -n "${IAM_BASE_URL:-}" ]]; then
    echo "The configured IAM_BASE_URL is unavailable or does not serve Qwen/Qwen3-8B. No process was stopped. Run scripts/diagnose-model.py." >&2
    exit 1
fi
cd "$IAM_ROOT"
# Check GPU availability before stopping any project process.
"$IAM_ROOT/.venv/bin/python" - <<'PY'
import runpy
ops = runpy.run_path('scripts/ops.py')
try:
    row = ops['gpu']()
except (RuntimeError, OSError) as exc:
    raise SystemExit(str(exc)) from None
if float(row[5]) > 2048:
    raise SystemExit('Selected GPU is occupied. Existing workloads are retained. Run scripts/diagnose-model.py.')
PY
"$IAM_ROOT/scripts/stop-vllm.sh"
"$IAM_ROOT/scripts/start-vllm.sh"
echo 'Model startup requested. Run scripts/health-check.sh when loading has finished.'
