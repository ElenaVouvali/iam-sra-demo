#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$task_root"
task_python=${IAM_API_PYTHON:-$task_root/.venv-api/bin/python}
if [[ ! -x "$task_python" ]]; then
    printf 'Create the separate API environment as documented in docs/iamcc-integration.md.\n' >&2
    exit 1
fi
if [[ -z "${IAM_BASE_URL:-}" ]]; then
    printf 'Set IAM_BASE_URL to the existing verified local model endpoint before starting the API.\n' >&2
    exit 1
fi
export PYTHONPATH="$task_root/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$task_python" -m gunicorn --config configs/gunicorn_api.py 'iam_sra.api:create_app()'
