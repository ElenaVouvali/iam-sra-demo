#!/usr/bin/env bash
# Model dependencies only. Keep API/privacy environments on the application host.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$task_root"
if [[ ! -e .venv ]]; then
  task_python=${IAM_PYTHON:-}
  if [[ -z "$task_python" ]]; then
    for candidate in python3.10 python3.11 python3.12 python3; do
      if command -v "$candidate" >/dev/null && "$candidate" -c 'import sys; assert (3,10)<=sys.version_info[:2]<(3,13)' 2>/dev/null; then
        task_python=$candidate
        break
      fi
    done
  fi
  if [[ -z "$task_python" ]]; then
    echo 'Python 3.10–3.12 with venv is required. Set IAM_PYTHON to its executable.' >&2
    exit 1
  fi
  "$task_python" -c 'import os,sys; assert (3,10)<=sys.version_info[:2]<(3,13), "Use Python 3.10–3.12"; s=os.statvfs("."); assert s.f_bavail*s.f_frsize>60*1024**3, "Need 60 GiB disk headroom for dependencies and weights"'
  mkdir -p .runtime/tmp .runtime/pip
  export TMPDIR="$task_root/.runtime/tmp" PIP_CACHE_DIR="$task_root/.runtime/pip"
  touch .runtime/inference-install.pending
  "$task_python" -m venv .venv
fi
if [[ -f .runtime/inference-install.pending ]]; then
  mkdir -p .runtime/tmp .runtime/pip
  export TMPDIR="$task_root/.runtime/tmp" PIP_CACHE_DIR="$task_root/.runtime/pip"
  .venv/bin/python -m pip install --only-binary=:all: -r requirements-vllm.txt -c requirements-lock.txt
  rm .runtime/inference-install.pending
fi
# Existing environments are checked, never upgraded/recreated automatically.
.venv/bin/python - <<'PY'
import importlib.metadata
from pathlib import Path
import sys
assert (3,10)<=sys.version_info[:2]<(3,13), 'Model environment needs Python 3.10–3.12'
for line in Path('requirements-vllm.txt').read_text().splitlines():
    if not line.strip() or line.startswith('#'):
        continue
    package, expected = line.split('==')
    actual = importlib.metadata.version(package).split('+')[0]
    if actual != expected:
        raise SystemExit(f'{package}: installed {actual}, expected {expected}. Existing .venv retained; use a separate inference directory.')
PY
.venv/bin/python -m pip check
.venv/bin/python scripts/download-model.py
echo 'Inference environment and pinned Qwen snapshot are ready. No model service was started.'
