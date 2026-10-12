#!/usr/bin/env bash
set -euo pipefail
IAM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m venv "$IAM_ROOT/.venv-privacy"
"$IAM_ROOT/.venv-privacy/bin/python" -m pip install -r "$IAM_ROOT/requirements-app.txt" -r "$IAM_ROOT/requirements-privacy.txt"
"$IAM_ROOT/.venv-privacy/bin/python" -m pip check
