#!/usr/bin/env bash
set -euo pipefail
IAM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$IAM_ROOT"
if [[ -e .venv ]]; then
  echo 'Existing project .venv found; refusing to overwrite it.' >&2
  exit 1
fi
IAM_PYTHON="${IAM_PYTHON:-python3.10}"
"$IAM_PYTHON" -c 'import sys; assert (3,10)<=sys.version_info[:2]<(3,13), "Use Python 3.10–3.12"'
mkdir -p .runtime/tmp .runtime/pip
export TMPDIR="$IAM_ROOT/.runtime/tmp"
export PIP_CACHE_DIR="$IAM_ROOT/.runtime/pip"
"$IAM_PYTHON" -c 'import os; s=os.statvfs("."); assert s.f_bavail*s.f_frsize>60*1024**3, "Need 60 GiB disk headroom"'
"$IAM_PYTHON" -m venv .venv
.venv/bin/pip install --only-binary=:all: -r requirements-lock.txt
.venv/bin/python -m pip check
.venv/bin/python scripts/download-model.py
