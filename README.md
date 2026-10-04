# iam-sra-demo
A guided English chatbot for one experimental IAM assessment: **The Urban Medical Transit Corridor**, from Future Needs’ *SRA_LLM concept feasibility.pdf*. Python owns the state machine, question selection, arithmetic and validation. Qwen/Qwen3-8B maps citizen evidence and independently reviews each supported concern through a separate localhost vLLM server. Readiness combines concern-specific boundaries and conditional willingness; original-route stance stays separate. Sessions stay in memory; JSON and JSONL export are explicit. Meaning is confirmed before any numeric review.

**Experimental demo:** scores are provisional conditional-readiness interpretations for this scenario. This is not a psychometrically validated instrument, an official EU citizen-readiness measure, or a calibrated SRL scale. All 15 concerns are registered; this scenario cannot assess them all. Missing evidence stays unassessed/null. Medical-benefit support, awareness, original-route acceptance and hypothetical conditional acceptance are kept separate.

Read [current verification and limits](docs/confirmation-report.md), [implementation contract](docs/implementation-contract.md), [methodology and FN questions](docs/methodology.md), [deployment](docs/deployment.md) and [verification results](docs/verification.md).

## Run on liono
This checkout already has an isolated `.venv` and a downloaded, revision-pinned model in `.runtime/` (both Git-ignored). Use a normal shell on liono; no sudo or driver changes.

```bash
cd ~/IAM_CC/iam-sra-demo
scripts/preflight.sh
scripts/start-vllm.sh
# Initial loading takes approximately one minute; check until healthy.
scripts/health-check.sh
scripts/start-ui.sh
scripts/health-check.sh
```

If a project server is already running, use health-check instead of starting another. Preflight before both services start checks available ports, V100 UUID, disk headroom and workloads. The vLLM launcher verifies UUID, then uses physical index 1 because vLLM 0.8.5's NVML implementation rejects UUID strings. The selected GPU becomes logical 0. No A2 or tensor parallelism.

On your laptop:

```bash
ssh -N -L 8501:127.0.0.1:8501 -L 8000:127.0.0.1:8000 elvouvali@liono.microlab.ntua.gr
```

Open `http://localhost:8501`. DNS/VPN access to the lab must work from the laptop. Streamlit and vLLM bind only to 127.0.0.1. Ports are configurable through exported `IAM_UI_PORT` and `IAM_VLLM_PORT`; update both forwarding ports accordingly. `.env.example` documents settings; `.env` is not automatically loaded.

Stop only this project's processes:

```bash
scripts/stop-ui.sh
scripts/stop-vllm.sh
```

## Fresh installation
Use Python 3.10–3.12. On this liono installation, the following existing Python interpreter can create a separate environment without changing its packages:

```bash
cd ~/IAM_CC/iam-sra-demo
/home/elvouvali/miniforge3/envs/mailohls-llm-v2/bin/python -m venv .venv
mkdir -p .runtime/tmp .runtime/pip
export TMPDIR="$PWD/.runtime/tmp"
export PIP_CACHE_DIR="$PWD/.runtime/pip"
# Full observed package lock, including vLLM/PyTorch CUDA 12.4 binaries.
.venv/bin/pip install --only-binary=:all: -r requirements-lock.txt
.venv/bin/python scripts/download-model.py
scripts/preflight.sh
```

`requirements-app.txt` is sufficient for GPU-free development; `requirements-vllm.txt` contains principal server pins. The full lock is for the verified Linux x86-64/Python 3.10 stack; do not reuse an existing research environment. Reserve at least 60 GiB /home headroom before a fresh install/download. Installation caches, temporary files and weights remain under `.runtime/` on /home; no source build is required.

## Tests and synthetic evaluation

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python eval/run.py --mock --repeats 1
# Requires running Qwen server; no implicit mock fallback.
PYTHONPATH=src .venv/bin/python eval/run.py --repeats 2 --output .runtime/evaluation-live.json
PYTHONPATH=src .venv/bin/python eval/run.py --held-out --repeats 2 --output .runtime/heldout-live.json
PYTHONPATH=src .venv/bin/python scripts/smoke-confirmed.py
PYTHONPATH=src .venv/bin/python scripts/smoke-ui.py
```

Explicit GPU-free UI mode:

```bash
IAM_MOCK=1 scripts/start-ui.sh
```

Mock mode is visibly labeled and produces a fixed uncertain, unassessed fixture. It checks UI plumbing, not interpretation. Restart the UI with `IAM_MOCK=0` for live mode. Synthetic evaluation checks schema/evidence compliance, qualitative agreement, repeated score variation and latency; it does not establish scientific validity.

## Session flow and limits
Answer → score-free interpretation → explicit confirmation → initial scoring → follow-ups → updated interpretation and explicit confirmation → final scoring → comparison/export.

Correct individual meanings or add omitted concerns in your own words; a complete restatement is not required. The UI shows model wording separately from citizen evidence. Edits invalidate confirmation and dependent final scores. Initial scores are saved once as an immutable snapshot. Confirmation establishes agreement about meaning, not scientific validity. Ambiguous meanings stay unassessed and conflicting answers require a targeted clarification.

Follow-up choices and optional text have stable evidence IDs and an explicit original/hypothetical context. Q1 addresses viewing privacy, Q2 bundles altitude/sound/curfew, and Q3 records policy preference. Relevant questions follow the confirmed facets, with an explicit all-reference option. Before conditional scoring, respond to the exact combined proposal; accepting separate Q1/Q2 changes is insufficient. Include any remaining concerns and confirm the resulting modified-context meaning.

Final original-proposal scoring uses the initial rubric and reviews only concerns with relevant confirmed original-context evidence changes; other scores carry forward with a reason. Conditional scoring uses a separate experimental acceptance-after-mitigation rubric. Untested original facets remain unavailable unless explicitly addressed. Each profile recomputes its own mean/cap/coverage/phase summaries in Python. No fixed bonus, inferred cap removal or automatic FN6–7/2–3 outcome is used. No new relevant original evidence means unchanged original scores. See [the reassessment policy](configs/reassessment.json) and [methodology](docs/methodology.md).

The final table includes all15 concerns and initial/final-original/conditional scores, reasons and evidence. Exports contain versioned interpretations, confirmations, corrections, immutable snapshots, questions/answers, contextual evidence IDs, model/rubric settings and arithmetic traces. JSONL is one complete session per line. Coverage differences do not imply personal improvement or decline.

Maximum input is 4000 UTF-8 bytes, plus actual per-call full-chat token budgets of4096. Excessive input is rejected, never truncated. The model selects numbered citizen passages; Python retrieves their original wording, while Qwen interprets their meaning in rationales. Each explicit action has an overall180-second deadline. Submission performs semantic mapping and numeric-free scope review of up to15 candidates, with at most one retry per call; no numeric stage runs before confirmation. After confirmation, independent numeric-only review runs per evidenced concern (up to15), with at most one retry per call. Final original and conditional reviews are separate bounded stages. Empty mappings skip scoring. Mapping reserves1400 output tokens, each semantic or numeric review300; every full-chat prompt plus reserved output must fit4096. Schema/evidence failures are controlled; transport failures are controlled errors with no invented result. Requests are serialized in the app and server concurrency is one. Timeout is 120 seconds per HTTP request; retries are recounted against the full context limit. Eligibility is interpreted semantically under the15 versioned scopes; Python validates facet membership, IDs, null/range and exact passages. There are no lexical vetoes or stance-to-score bands. Semantic correctness is still provisional. Logs rotate at 2 MiB with two backups per service; routine logs omit raw citizen text. Exports include citizen text and should be saved deliberately.

## Repository
- `src/iam_sra/`: UI-independent schemas, assessment, session, scoring, validation and HTTP client.
- `configs/`, `prompts/`: versioned registry, scenario, questions, provisional anchors/policy and model revision.
- `eval/fn_reference.json`: historical fixture (8,3,4,2; mean 4.25; illustrative final 4), never substituted into inference.
- `tests/`, `eval/`, `scripts/`, `docs/`: checks, synthetic cases, operations and traceability.

For a project-only UI restart after deploying this branch (not performed during implementation):

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
scripts/stop-ui.sh
scripts/start-ui.sh
sleep 5
scripts/health-check.sh
```

The existing vLLM server does not need a restart. If laptop8501 is occupied, use `ssh -N -L 8502:127.0.0.1:8501 elvouvali@liono.microlab.ntua.gr` and open `http://localhost:8502`.

No database, RAG, agents, fine-tuning or dashboard. PDF, credentials, weights, environments, logs and exports are excluded from Git. The recalibration baseline is published; new work is isolated on `feature/confirmed-reassessment` and is not pushed. See [calibration report](docs/calibration-report.md) and [methodology](docs/methodology.md) for before/after results and source limitations.
