#!/usr/bin/env bash
set -euo pipefail
export IAM_MOCK="${IAM_MOCK:-0}"
IAM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$IAM_ROOT/.venv/bin/python" "$IAM_ROOT/scripts/ops.py" start ui
