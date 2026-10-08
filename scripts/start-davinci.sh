#!/usr/bin/env bash
set -euo pipefail
IAM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$IAM_ROOT"
export IAM_GPU_UUID=GPU-ac0112df-7098-6c59-5c4f-a57fa666f808
export IAM_MOCK=0
export PYTHONPATH="$IAM_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

nvidia-smi --query-gpu=index,name,uuid,memory.used,memory.total --format=csv,noheader
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --only-binary=:all: -r requirements-app.txt -r requirements-vllm.txt
.venv/bin/python scripts/download-model.py

# Reuse a healthy model server, or start this project's pinned model.
if ! .venv/bin/python - <<'PY'
import httpx
from iam_sra.settings import MODEL
import os
base = 'http://127.0.0.1:' + os.getenv('IAM_VLLM_PORT', '8000')
try:
    with httpx.Client(timeout=5, trust_env=False) as client:
        client.get(base + '/health').raise_for_status()
        models = client.get(base + '/v1/models')
        models.raise_for_status()
        assert MODEL in [m['id'] for m in models.json()['data']]
except Exception:
    raise SystemExit(1)
PY
then
    scripts/preflight.sh
    scripts/start-vllm.sh
fi

.venv/bin/python - <<'PY'
import os
import time
import httpx
url = 'http://127.0.0.1:' + os.getenv('IAM_VLLM_PORT', '8000') + '/health'
print('Waiting up to 10 minutes for the model server...', flush=True)
with httpx.Client(timeout=5, trust_env=False) as client:
    for _ in range(120):
        try:
            client.get(url).raise_for_status()
            break
        except httpx.HTTPError:
            time.sleep(5)
    else:
        raise SystemExit('Model server did not become healthy. Check .runtime/vllm.log.')
PY

scripts/start-ui.sh
scripts/health-check.sh
echo "Open http://localhost:${IAM_UI_PORT:-8501} — real model mode."
