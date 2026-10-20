#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$task_root"
task_privacy_python=${IAM_PRIVACY_PYTHON:-$task_root/.venv-privacy/bin/python}
task_api_env=${IAM_API_ENV:-$task_root/.venv-api}
if [[ ! -x "$task_privacy_python" ]]; then
    printf 'Prepare the pinned CPU privacy environment first with scripts/setup-privacy.sh.\n' >&2
    exit 1
fi
if [[ ! -x "$task_api_env/bin/python" ]]; then
    "$task_privacy_python" -m venv "$task_api_env"
fi
task_privacy_packages=$("$task_privacy_python" -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
"$task_api_env/bin/python" - "$task_privacy_packages" <<'PY'
from pathlib import Path
import sys
import sysconfig
# Reuse the existing CPU-only privacy resources read-only. No dependency is
# installed into or removed from that environment or the GPU environment.
Path(sysconfig.get_path('purelib'), 'iam_sra_privacy_resources.pth').write_text(sys.argv[1] + '\n')
PY
"$task_api_env/bin/python" -m pip install -r requirements-api.txt
PYTHONPATH=src "$task_api_env/bin/python" scripts/check-privacy.py
printf 'API dependencies are installed separately; existing model resources were preserved.\n'
