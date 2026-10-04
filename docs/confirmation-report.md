# Confirmation and reassessment · 2026-10-04

Implemented on local `feature/confirmed-reassessment`, from clean `recalibrate/fn-scenario-readiness` commit418f79c. No push, merge, service restart, environment change or unrelated workload modification. PDF re-read in full at `/home/elvouvali/SRA_LLM concept feasibility.pdf`; GA not found. Canonical15 concerns, phase mappings, fixed corridor, original rubric/arithmetic and pinned Qwen3-8B/V100 deployment are preserved.

## Before / after

| Before418f79c | Current guided application |
|---|---|
| Submission mapped and immediately scored | Submission maps and checks scope with **no numeric calls** |
| Confirmation followed already-created scores | Explicit confirmation freezes a versioned meaning before numeric review |
| Complete restatement for correction | Targeted citizen-authored correction or omitted concern; provenance/history retained |
| Scorer could change mapped stance/facets | Numeric-only score/rationale output; frozen meanings cannot be remapped |
| Follow-up text stored but not interpreted | Choice and optional text interpreted with stable IDs and original/hypothetical contexts |
| Separate Q1/Q2 outcomes | Exact combined proposal, explicit joint choice/remaining concerns and updated confirmation |
| Qualitative-only final validation | Unchanged original rubric for relevant original clarifications; distinct experimental modified-context rubric |
| Original/corrected display, JSON | All15 initial/final-original/conditional comparison, traces, phases, JSON and JSONL |

Policy1.0-experimental is in [reassessment.json](../configs/reassessment.json). No fixed bonuses, automatic cap removal, source6–7/2–3 forcing, source-text recognition or mock fallback. Missing/ambiguous evidence stays null. Conditional coverage is independent; new coverage/different proposals do not measure personal improvement. Untested original facets are excluded explicitly, not silently resolved. More detail and source-page questions are in [methodology](methodology.md).

## Offline verification

**239 tests passed** (approximately5s). Includes original fixture mean4.25/cap4/adjusted4/final4, nulls and coverage, generation bounds/retries, state isolation, no numeric calls before confirmation, tamper detection, edits invalidating confirmation, corrections reaching scoring, follow-up text/context, targeted contradictions, joint acceptance/choice-text conflict, unique joint evidence IDs/history, selective re-review, untested facets, cap recomputation, atomic final failure, immutable initial snapshot, all15 comparison and complete single-line JSONL. Existing historical contract checks use explicitly named `legacy_session` and never the guided UI. New mock mode remains visibly labelled. Python compilation and Git whitespace checks passed.

## Every attempted live session

[Machine results](../eval/results/confirmation-workflow.json) include all attempts and per-stage diagnostics/settings; the four development iterations are distinct, not one frozen scientific evaluation. Scripted synthetic confirmations are not citizen study data. Completion is not semantic agreement. No scoring stage ran before initial or updated confirmation. A separate isolated concern review additionally passed with full original testimony plus a user-authored correction; this is recorded separately from the23 full-session attempts.

| Batch | Completed / attempted | Median end-to-end seconds |
|---|---:|---:|
| Initial development flow |1/4|14.593|
| Revised numeric instruction |2/5|16.753|
| Added score-free scope review |2/5|19.706|
| Final mapping transport and conditional instruction |4/5|58.775|
| Explicit original-noise correction |1/1|103.113|
| Live Streamlit renderer |1/1|72.552|
| Whole-history renderer repeat |0/1|29.433|
| Concern-specific history renderer repeat |0/1|2.584|
| All attempted sessions |**11/23**|Not pooled across changing prompts|

Twelve incomplete sessions returned controlled schema/clarification failures. Early failures involved unsupported awareness/trust mappings, refusal to score clear benefit/conditional evidence, and a malformed follow-up mapping missing facets/evidence. The final5-case batch completed support, uncertainty, mixed and FN; opposition returned to clarification at welfare review despite explicit medical support. All attempted failures remain visible. The final transport prevents empty mapped citations/facets; scope review is still fallible.

| Final5-case batch | Initial → final original | Conditional | Seconds |
|---|---|---|---:|
| Support |trust9/privacy9/noise9/welfare8 → unchanged|noise8/welfare9;2/15, no overall index|64.642|
| Opposition |No complete initial snapshot|Unavailable: welfare review declined|23.089|
| Uncertainty |All null → unchanged|Unavailable, unsure joint answer|46.101|
| Mixed |privacy2/noise3/welfare8 → unchanged|privacy8/welfare9;2/15, no overall index|58.775|
| FN reference |privacy2/noise3/welfare8 → unchanged; initial/final4|privacy9/noise8/welfare9; mean8.6667, no eligible cap, rounded9|80.204|

The FN conditional integers describe an explicitly accepted combined proposal plus new synthetic clarification. They do not overwrite original boundaries and are not FN-calibrated labels. FN's ambiguous visual4 stays unassessed; the original mean is4.3333 rather than fixture4.25, cap4/final4. Support incorrectly includes public-awareness/trust based on route/camera testimony even after semantic review: **a completed workflow is not a correct mapping**. Conditional scores/mappings vary, and welfare8→9 under a changed context is not evidence of better readiness. These remaining semantic errors require user review and FN calibration feedback.

A separate live synthetic citizen explicitly corrected only the **original** acoustic position to accept the60m hum/all original hours, retaining camera objection. Initial privacy2/noise3/welfare8 was preserved. Final-original privacy2/noise9/welfare8 gives mean6.3333, cap4, final4. Only noise was re-reviewed; privacy/welfare were carried. An additional isolated live numeric review explicitly included the entire original testimony as historical context plus the corrected confirmed noise meaning and again returned9 (13.669s). It did not remap the correction or score another concern. This demonstrates refinement, selective evidence use and cap recomputation, not scientific calibration.

The real Streamlit renderer used Q1accept/Q2residential rejection/Q3unsure and a joint-unsure response. It completed both confirmations and final scoring, displayed15 comparison rows and2 downloads, preserved initial/final-original mean4.3333/cap4/final4, and withheld a conditional profile. Renderer checks are not laptop browser/SSH tests.

A later renderer repeat failed at welfare scoring (29.433s): giving that reviewer the entire original answer caused it to conflate medical support with route opposition. Interpretation schema1.1 now supplies concern-specific supporting original passages, including superseded evidence after corrections, alongside current confirmed testimony. The complete original answer remains in the export; unrelated testimony is not silently remapped. The subsequent renderer attempt failed before interpretation (2.584s) because live vLLM was unavailable. Thus the final concern-history refinement is offline verified, but its live end-to-end check is blocked. No mock fallback or restart was used.

## Resources and remaining limits

Pinned model revision `b968826d9c46dd6066d109eabc6255188de91218`, vLLM0.8.5, FP16, V0/XFORMERS,4096 context, concurrency1 on the V100 are unchanged. Thinking is disabled and visible thinking/truncation is still rejected. The largest recorded CLI full-chat prompt plus reserved output was**3316 tokens**. Each interpretation action permits one mapping plus up to15 numeric-free scope reviews (max32 calls),180s overall; each numeric profile up to15 reviews/max30 calls,180s. Final original and conditional are separate stages; a final click can take up to360s. No silent truncation. More calls add latency.

V100 after-action samples ranged26880–27144MiB (up to26.51GiB), not peaks. A2 read-only samples were4MiB; no A2 model process was launched. No OOM observed, no packages installed and no process stopped/restarted. The final read-only health check found Streamlit healthy and vLLM unavailable (ConnectError); no service was restarted. The existing localhost deployment is unchanged; the running UI needs a project-only restart to load the new Python modules.

Remaining FN questions: source mean4.25 versus6.0; nine anchors and ordinal averaging; bottleneck definition/threshold/offset; minimum coverage; numerical update formula; combined versus separate intervention evidence; leading/bundled questions and overlapping outcomes; medical benefit versus equity; visual/infrastructure mapping; coverage beyond one scenario and the missing GA. This demo has no psychometric/population validity or established engineering/clinical assumptions. Historical exports/results were not overwritten.

## Commands

On liono, **when ready to load the new UI**:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src .venv/bin/python -m pytest -q
scripts/stop-ui.sh
scripts/start-ui.sh
sleep 5
scripts/health-check.sh
```

No vLLM restart is needed. Laptop tunnel:

```bash
ssh -N -L 8502:127.0.0.1:8501 elvouvali@liono.microlab.ntua.gr
```

Open `http://localhost:8502`. Bounded live checks (no mock fallback):

```bash
PYTHONPATH=src .venv/bin/python scripts/smoke-confirmed.py
PYTHONPATH=src .venv/bin/python scripts/smoke-confirmed.py --ids fn_reference --original-correction --output .runtime/original-correction-repeat.json
PYTHONPATH=src .venv/bin/python scripts/smoke-ui.py
```

GPU-free UI: `IAM_MOCK=1 scripts/start-ui.sh` when the project UI is stopped. Mock is a fixed uncertain plumbing fixture, never a live-error fallback.
