# IAM-SRA2 citizen interviews

Main contains the updated citizen app: a scenario-free baseline interview, an
optional medical-drone scenario interview, source-grounded information, privacy
screening and a provisional workbook-based CRL score screen after the scenario
interview. Baseline answers remain separate from scenario scoring. SRL also
requires technical and organisational evidence and is not inferred from one
citizen interview.

The new selectable **Conversational interview and illustrative case** joins the
general interview, a confirmed profile, source-selected medical-corridor example,
contextual questions, optional sourced explanation and final screened export.
See the [meeting guide and three copy-paste scripts](docs/conversational-meeting-demo.md).
The current 1.1 update adds GA route examples, reviewed adaptive question wording
and an evidence assessment against each workbook CRL anchor. See the
[update and verification guide](docs/conversation-update-1.1.md).
It remains a draft readiness instrument.

The feature branch `feature/adaptive-conversation-v1.2` adds objective-level
planning, grounded topic memory, and a synthetic respondent evaluation runner.
Its source review status and operational limits are documented in
[`Adaptive conversational assessment v1.2`](docs/adaptive-conversation-v1.2.md).

```bash
cd ~/iam-sra-demo
.venv-privacy/bin/python scripts/build-conversation-corpus.py
scripts/stop-ui.sh
IAM_MOCK=0 IAM_BASE_URL=http://127.0.0.1:18000 IAM_ASSESSMENT_MODE=retrieval_grounded_conversation scripts/start-ui.sh
```

The current davinci model endpoint uses port 18000; set `IAM_BASE_URL` to your
service address (port 8000 for the original direct-host setup). Open
http://localhost:8501. Restart the UI
after code changes; browser refresh alone does not reload modules with file
watching disabled. Sources and the generated corpus remain Git-ignored.

The original IAM-SRA acceptance demo is preserved on
[`legacy`](https://github.com/ElenaVouvali/iam-sra-demo/tree/legacy),
commit `708024817f31b48c7a9009a8ba5103cbf10b93f8`. Its numerical acceptance
policies, calibration runners and manual packs belong to that branch.

## Run

Use Python 3.10–3.12. Keep existing environments and downloaded weights.
For a fresh GPU-free installation:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-app.txt
scripts/setup-privacy.sh
```

With the existing local model service running:

```bash
scripts/start-ui.sh
scripts/health-check.sh
```

Open **http://localhost:8501**. New sessions start with the role-aware, scenario-free [baseline 2.1 interview](docs/baseline-adaptive-interview.md). Its summary
can open the illustrative scenario. To start directly with the scenario:

```bash
IAM_ASSESSMENT_MODE=acceptance_and_readiness_evidence scripts/start-ui.sh
```

Restart a running UI before changing its environment. `IAM_DEVELOPER=1` enables
mode selection and diagnostics. `IAM_MOCK=1` uses empty UI fixtures rather than
live assessment. Services bind to localhost; set `IAM_GPU_UUID` for this host
before starting the model. See [deployment](docs/deployment.md).

## Privacy

Local screening runs before model calls and session retention, screens responses
and downloads, and requires confirmation of cleaned text. Missing detector
resources block processing. Run the real detector preflight:

```bash
.venv-privacy/bin/python scripts/check-privacy.py
```

Detection can miss private information. Use synthetic examples; see
[privacy and retention](docs/privacy.md). Private source documents, environments,
model weights, logs and exports stay outside Git.

## Verification

```bash
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-baseline.py --help
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-readiness-evidence.py --help
```

Live smoke runners require the model host. Offline tests validate flow and
boundaries, not model accuracy. [Baseline design](docs/phase1-baseline.md),
[adaptive benchmark and exact run commands](docs/baseline-adaptive-benchmark.md),
[CPU-only automatic benchmark](docs/cpu-benchmark.md),
[historical benchmark seed](docs/baseline-benchmark-seed.md),
[scenario and score design](docs/readiness-evidence-mode.md) and
[cleanup details](docs/repository-cleanup.md) describe the retained components.

## Run both versions

The existing local legacy checkout is `~/iam-sra-demo-2026-10-08`:

```bash
cd ~/iam-sra-demo-2026-10-08
IAM_UI_PORT=8502 scripts/start-ui.sh
```

Open **http://localhost:8502** alongside the updated app on 8501. Both can share
the model server on 8000, with separate UI sessions and logs. Forward both UI
ports if connecting remotely. The legacy app does not have the newer privacy
controls.

Current interface and saved-session review: [dynamic interview improvements](docs/dynamic-interview-review.md). The proposed adaptive conversational mode v1.2 is documented in [adaptive conversation v1.2](docs/adaptive-conversation-v1.2.md); it remains pending partner review and is available on branch `feature/adaptive-conversation-v1.2`. The synthetic interviewer evaluation is separate from real stakeholder data.
