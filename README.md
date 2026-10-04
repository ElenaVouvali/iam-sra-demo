# iam-sra-demo
A guided English chatbot for one experimental IAM assessment: **The Urban Medical Transit Corridor**, from Future Needs’ *SRA_LLM concept feasibility.pdf*. Python owns the state machine, question selection, arithmetic and validation. Qwen/Qwen3-8B maps citizen evidence and independently reviews each supported concern through a separate localhost vLLM server. Readiness combines concern-specific boundaries and conditional willingness; original-route stance stays separate. Sessions stay in memory; JSON and JSONL export are explicit. Meaning is confirmed before any numeric review.

**Experimental demo:** scores are provisional conditional-readiness interpretations for this scenario. This is not a psychometrically validated instrument, an official EU citizen-readiness measure, or a calibrated SRL scale. All 15 concerns are registered; this scenario cannot assess them all. Missing evidence stays unassessed/null. Medical-benefit support, awareness, original-route acceptance and hypothetical conditional acceptance are kept separate.

Read [latest universal-updates verification](docs/universal-updates-report.md), [evidence-discovery verification and limits](docs/discovery-report.md), [confirmation/reassessment verification](docs/confirmation-report.md), [implementation contract](docs/implementation-contract.md), [methodology and FN questions](docs/methodology.md), [deployment](docs/deployment.md) and [verification results](docs/verification.md).

## Guided evidence discovery

After **Interpret response**, a few neutral questions can clarify an unspecified stance, reasons, topic/facet, acceptance changes or an independently decisive objection. All questions concern the **unchanged original proposal**. Python selects one at a time from `configs/discovery.json`, at most six, and recomputes after each answer. Registry topics can be positive, negative or uncertain; choosing a topic does not establish its severity. Other issues retain their wording with an unmapped status and no invented topic ID. **Skip** and **Finish these questions** preserve unknowns. Explicit acceptance with no reservations ends unnecessary questioning without assessing silent topics.

Review the consolidated meaning and any acceptance boundaries, correct individual meanings, then tick **This reflects what I meant** and click **Continue**. That action confirms meaning and calculates the initial snapshot internally before follow-ups. Boundary answers are stored separately from numbers; they do not directly alter caps or scores. The existing anchors, assessed-only mean, minimum coverage, bottleneck rules and rounding are unchanged and experimental. Discovery can improve coverage but does not guarantee an aggregate.

FN Q1–Q3 remain hypothetical follow-ups with their original provenance and optional all-reference mode. Their selector includes discovered confirmed topics; some facets have no relevant FN hypothetical test. Updated confirmation, separate original/conditional reassessment, immutable initial scores, all15 assessment records and JSON/JSONL remain available. Exports include discovery questions, selections, free text, skips/finish, stable evidence IDs, selection reasons, blockers, unknowns, policy version and unmapped issues. Model interpretations can be wrong; completion is not semantic accuracy or scientific validation.

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
PYTHONPATH=src .venv/bin/python scripts/smoke-discovery.py --output .runtime/discovery-repeat.json
PYTHONPATH=src .venv/bin/python scripts/smoke-updates.py
PYTHONPATH=src .venv/bin/python -m pytest tests/test_live_ui_flow.py tests/test_ui.py -q
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

The citizen flow hides intermediate numbers and shows one final provisional result, explicitly labelled with its proposal context. The JSON/JSONL records include all15 concerns and initial/final-original/conditional scores, reasons and evidence. Exports contain versioned interpretations, confirmations, corrections, immutable snapshots, questions/answers, contextual evidence IDs, model/rubric settings and arithmetic traces. JSONL is one complete session per line. Coverage differences do not imply personal improvement or decline.

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

No database, RAG, agents, fine-tuning or dashboard. PDF, credentials, weights, environments, logs and exports are excluded from Git. The updated application, including evidence discovery, is published on the single `main` branch. Fully merged implementation branches have been removed. Running services require a project-only UI restart to load changed modules. See [calibration report](docs/calibration-report.md) and [methodology](docs/methodology.md) for before/after results and source limitations.

### Universal follow-up updates (policy 1.0, export 5.0)

Python owns typed facet transitions and a reviewed question bank, with at most six follow-ups. Questions declare proposal context, facets, assumptions, choice meanings and limits. Non-FN topics receive an original-position check or a hypothetical question using only citizen-described changes. Unknowns and skipped questions remain unknown. Q3 records policy priority without changing welfare support or caps.

Modified-context meanings receive a score-free facet review in batches of at most six, within a shared180-second deadline and4096-token full-chat budget. After updated confirmation, applicable facets are scored independently with the unchanged conditional rubric. A concern receives the minimum facet score only when every relevant facet has explicitly applicable, clear modified-context citizen evidence; otherwise it is unavailable. Facets never become extra aggregate items. This conservative rule extends FN and requires calibration.

Completion chooses the conditional aggregate when available, otherwise the final-original aggregate with an explicit original-proposal label. A failed modified aggregate is disclosed. With neither, a qualitative completion explains insufficient evidence. Readable export sections separate the summary, proposals, all15 domains, chronological transitions, blockers, arithmetic and dialogue; detailed traces and a legacy4.1 adapter live in audit. Historical export files remain unchanged. Set `IAM_DEVELOPER=1` only to reveal diagnostic UI. See [verification report](docs/universal-updates-report.md).
