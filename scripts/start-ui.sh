#!/usr/bin/env bash
set -euo pipefail
export IAM_MOCK="${IAM_MOCK:-0}"
IAM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IAM_UI_PYTHON="$IAM_ROOT/.venv/bin/python"
if [[ -x "$IAM_ROOT/.venv-privacy/bin/python" ]] && "$IAM_ROOT/.venv-privacy/bin/python" -c "import streamlit, presidio_analyzer, en_core_web_sm" 2>/dev/null; then
  IAM_UI_PYTHON="$IAM_ROOT/.venv-privacy/bin/python"
fi
exec "$IAM_UI_PYTHON" "$IAM_ROOT/scripts/ops.py" start ui
