# iam-sra-demo

The default citizen demo separates **views of the proposal** from **readiness evidence**: understanding of possible impacts, information needs, participation, reported influence and opportunities or barriers to agency. Opposition can contain strong evidence; support alone does not establish readiness.

The five-question draft interview adapts to confirmed evidence already supplied, permits skipping and finishing, and asks about influence only after actual participation is reported. Confirming an interpretation does not verify events or approve the methodology. Initial confirmed evidence is preserved when later answers or corrections refine the assessment.

**No numerical CRL or SRL is assigned in the default mode.** Numerical criteria and aggregation await methodological approval. The 15 areas remain topics; historical phase assignments are not CRL stages. The workbook is a partner-review draft.

The older arithmetic remains available explicitly as **Historical experimental acceptance index**, a legacy application policy, not an approved FN formula. Existing acceptance calibration scripts now explicitly select historical sessions; their outputs must not be treated as CRL evidence.

Read [the evidence-mode implementation and validation notes](docs/readiness-evidence-mode.md) and [curated source references](references/source-register.json). Partner source documents remain local and Git-ignored under `references/private/`.

Default demo (with the existing vLLM service running):

```bash
scripts/start-ui.sh
```

Historical demo (restart the UI when changing mode):

```bash
scripts/stop-ui.sh
IAM_ASSESSMENT_MODE=legacy_fn_acceptance_demo scripts/start-ui.sh
```

`IAM_DEVELOPER=1` also enables a mode selector before session creation. The chosen mode remains fixed for that session. Start over to create a session in another mode. `IAM_MOCK=1` in evidence mode is an explicitly empty UI fixture, not a model evaluation.

## Run the application

The local checkout has an isolated `.venv` and revision-pinned model weights under the ignored `.runtime/` directory. From this repository:

```bash
scripts/health-check.sh
# If this project's services are not already running:
scripts/preflight.sh
scripts/start-vllm.sh
# Wait for the model server to become healthy:
scripts/health-check.sh
scripts/start-ui.sh
scripts/health-check.sh
```

Default ports are 8000 for vLLM and 8501 for Streamlit, bound to localhost. Set `IAM_GPU_UUID` to the intended GPU on the current host before launch; `.env.example` documents environment settings, but `.env` is not automatically sourced. The launch scripts preserve the pinned V100-compatible configuration and check process identity before stopping services.

For a remote host, forward the ports from your laptop:

```bash
ssh -N -L 8501:127.0.0.1:8501 -L 8000:127.0.0.1:8000 USER@HOST
```

Open `http://localhost:8501`. Stop only this project's services with:

```bash
scripts/stop-ui.sh
scripts/stop-vllm.sh
```

For direct local UI development with an existing model endpoint:

```bash
.venv/bin/python -m streamlit run app.py
```

Explicit GPU-free UI plumbing mode:

```bash
IAM_MOCK=1 .venv/bin/python -m streamlit run app.py
```

Mock mode is visibly labelled and does not evaluate citizen views. Live errors never switch to mock mode. `IAM_DEVELOPER=1` exposes additional diagnostics and the preserved FN reference-question mode; the default end-to-end tests use reference mode off.

## Installation

Use Python 3.10–3.12. For GPU-free development in a new checkout:

```bash
python3.10 -m venv .venv
.venv/bin/pip install -r requirements-app.txt
```

For the full pinned Linux GPU stack, `scripts/install.sh` creates a new environment, installs `requirements-lock.txt` and downloads the pinned model. It refuses to overwrite an existing `.venv`; set `IAM_PYTHON` if needed. `requirements-vllm.txt` records the principal server pins. See [deployment](docs/deployment.md) for GPU and runtime requirements.

## Automated checks

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python eval/run.py --mock --repeats 1
```

`eval/run.py` now uses the same interpretation → confirmation → initial scoring path as the application. Its scripted confirmations and synthetic examples do not establish citizen agreement or semantic accuracy. Without `--mock`, it requires a live model server:

```bash
PYTHONPATH=src .venv/bin/python eval/run.py --repeats 2 --output .runtime/evaluation-live.json
PYTHONPATH=src .venv/bin/python eval/run.py --held-out --repeats 2 --output .runtime/heldout-live.json
```

Focused diagnostic runners remain available: `scripts/replay-attribution.py`, `scripts/replay-ordinal.py`, `scripts/replay-fn-evidence.py`, and `scripts/smoke-discovery.py`. They retain failures and distinguish execution completion from semantic correctness. The ordinal runner's filename is retained; its current scorer uses LLM-assigned numbers. Live runners are not part of offline CI.

## End-to-end manual tests

Start with [the manual walkthrough](manual-tests/end-to-end-manual-tests.md). [The T01–T32 case guide](manual-tests/followup-assessment-manual-tests.md) provides **155 scripted baseline runs** with expected questions, exact choices, concern gains and final mean/cap/rounding calculations. Nine extension experiments cover policy invariance, reservations, new clarifications, early finish, combined assessment and editing. Record actual outcomes in [the blank results sheet](manual-tests/end-to-end-results-template.csv).

T01–T24 are development cases; T25–T32 retain the fresh-validation split. Fixed final-score targets assume the initial assessment matches the authored baseline. Otherwise record the initial mismatch and independently check follow-up arithmetic from the actual validated-original scores. Authored expectations are not live results or scientifically validated ground truth.

For live initial-stage comparisons:

```bash
.venv/bin/python scripts/run-initial-manual-tests.py --mapping-only
.venv/bin/python scripts/run-initial-manual-tests.py
.venv/bin/python scripts/run-initial-manual-tests.py --split fresh_validation
```

The defaults select the 24 development cases; `--ids` and `--split` control selection. This runner stops after the initial assessment. For the full UI flow use the end-to-end walkthrough. Regenerate the follow-up guide without inference or rewriting its fixtures:

```bash
.venv/bin/python scripts/build-followup-manual-guide.py
```

## Repository layout

| Location | Purpose |
|---|---|
| `app.py` | Current Streamlit interface |
| `src/iam_sra/` | Evidence interpretation, session flow, scoring, updates and reporting |
| `configs/` | Versioned scenario, concern registry, model and experimental policies |
| `prompts/` | Prompts used by current interpretation and confirmed scoring |
| `manual-tests/` | Authored stage-1 and end-to-end experiments, guides and blank results sheet |
| `tests/` | Offline contract, arithmetic and UI regression checks |
| `eval/` | Synthetic fixtures and current-path initial evaluation runner |
| `scripts/` | Service operations, current diagnostics and manual-test tooling |
| `docs/` | Current methodology, update policy, deployment and verification |
| `.runtime/` | Ignored model cache, service state, logs and newly generated reports |

The old pre-confirmation session, one-shot scorer, obsolete smoke scripts and historical reports have been removed from the active repository. Recoverable historical material is in an external archive; see [cleanup notes](docs/repository-cleanup.md). Current export/audit compatibility remains where the application and diagnostic tools use it.

Current readiness interview (1.2.2): [understanding, optional learning and evidence review](docs/readiness-v120-fn-review.md). The historical acceptance index remains separate. See the [UI guide checklist, source pages and verification limits](docs/readiness-ui-guidelines-review.md) for the current interface and missing partner-kit assets.
