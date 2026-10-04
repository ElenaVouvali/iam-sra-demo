# Evidence preservation and citizen review

2026-10-04; reviewed baseline3b7487c, clean local main, no applicable AGENTS.md. Existing FN PDF physical pp.5–9 reviewed. No unrelated files/workloads, deployment, model snapshots, GPU allocations or environments changed. No service restart, push or merge performed.

## Focused changes

- Session/interpretation preserve separate original aspect meanings and provenance. Clear medical benefit survives equity uncertainty; one-aspect corrections preserve other valid aspects. Global discovery sufficiency cannot clear validated evidence. Scope-rejected mappings cannot become modified requirements or be re-nominated through medical metadata.
- Per-aspect scope review plus independent registry-owned semantic attribution distinguish routing from actual facilities/land planning, and viewing privacy from aesthetics. Raw wrong nominations remain in audit. No brittle keyword rules or special treatment of the sample text.
- Purposeful contracts replace routine confirmation questions: ask only about unclear meanings, missing acceptable changes, genuine objections or applicability to the changed proposal. Choices have declared meanings; correction without explanation is rejected. FN source wording stays in exports/developer reference mode. Q2 explicitly keeps flights over the neighbourhood up to15/day.
- Tested choices plus explicit joint acceptance establish those tested aspects without repeated testimony. A concise explicit affirmation supports an unchanged aspect in the displayed combined context. Original scores are not inherited into that context; each meaning is re-reviewed with the existing conditional anchors. Generic approval cannot establish equity, safety or security. Q3 never becomes a physical change or numeric cap command.
- One structured citizen summary, plain optional explanations, targeted missing-meaning actions and one labelled final result. Original objections are not remaining modified objections. “Remaining objection” does not imply independent decisiveness.
- Back and answer-specific edits restore the same question/context/draft, invalidate dependent results, keep the initial snapshot immutable and preserve chronological superseded records with distinct evidence IDs. JSONL/JSON schema5.1 adds these revisions and original facet meanings; legacy sections/adapter remain, historical files unchanged.

Numeric anchors, assessed-only aggregation, minimum3 concerns, bottleneck eligibility/offset, phase mappings and rounding are unchanged. Fixed scenario, all15 IDs and Qwen3-8B/vLLM/V100 deployment preserved.

## Verification

Offline tests cover the above paths, source-fixture arithmetic, negation/unknowns, context isolation, contradictory choices, restored drafts and completed-session edits. Test doubles exercise software contracts, not model semantics. **349 tests passed**, including Streamlit renderer and evidence-editing regressions. Compile and whitespace checks passed.

The configured endpoint was already healthy. Three live FN replays ran with temperature0.2/top_p0.8, pinnedQwen3-8B, FP16/V0/XFORMERS,4096 full-chat context, concurrency1, no thinking, bounded calls/retries. Confirmations and choices were scripted engineering inputs, not real citizen agreement. No mock substitution. The sandbox health check could not reach localhost; read-only unsandboxed health succeeded, without a service change.

| Live replay | Mapping and exclusions | Original/final-original | Modified | Latency |
|---|---|---|---|---:|
| First | medical benefit, noise, personal privacy; **incorrect facility-siting nomination survived generic scope review** |8/3/2 plus infrastructure2; mean3.75, cap4, result4;4/15 |medical9/noise8/privacy9; infrastructure unavailable; mean8.667, result9;3/15 |64.114s |
| Independent-attribution repeat | medical benefit, noise, personal privacy; infrastructure excluded as `flight_routing_only`; visual unassessed |8/3/2 unchanged; mean4.333, cap4, result4;3/15 |medical9/noise8/privacy9; mean8.667, result9;3/15 |65.145s |
| Final-prompt replay | Same three intended aspects; infrastructure excluded, visual unassessed; no visible thinking in all recorded calls |8/3/2 unchanged; mean4.333, cap4, result4;3/15 |medical9/noise8/privacy9; mean8.667, result9;3/15 |61.939s |

All three completed; none had a transport/schema failure. The first nevertheless failed the intended mapping criterion, and is retained rather than counted as semantic success. Both subsequent replays excluded that observed error. Only Q1/Q2/Q3 were presented; no routine welfare reconfirmation. The combined response accepted the exact changes; medical support was explicitly affirmed as still applicable. The accepted privacy/noise choices remained supporting evidence with their original question links. No original score changed.

This is not broad semantic validation or numerical calibration. The modified9 is the observed output of the existing rubric/model, not a forced FN6–7 outcome. Strict visual attribution differs from FN's illustrative four-dimension fixture: camera viewing and altitude alone do not independently establish aesthetics. The deterministic fixture still retains8/3/4/2, mean4.25, cap4, result4. Further held-out and repeated semantic studies remain needed; residual false scope decisions are possible.

Ignored detailed records: `.runtime/fn-evidence-replay.json`, `.runtime/fn-evidence-replay-attribution.json` and `.runtime/fn-evidence-replay-final.json`, with all mappings, exclusions, scores, confirmations, settings and diagnostics. Original/modified arithmetic is independently traced. Deployment hardware and resident allocations were not altered or reconfigured.

## FN alignment and extensions

FN pp.5–9 motivate the medical scenario, concern interpretation and targeted privacy/noise/policy questions. Semantic attribution checks, aspect ledgers, unchanged-meaning applicability confirmation, combined acceptance, selective reassessment, editing checkpoints and headline/export policy are application-designed extensions. They require FN review, especially ordinal anchors/averaging, aspect combination and conditional calibration. The9-level scale, bottleneck generalization, p.9 arithmetic inconsistency, overlap/leading wording and limited15-topic coverage remain unresolved. No psychometric, engineering, clinical or population validity is claimed.

## Commands

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m pytest tests/test_evidence_repair.py -q
# Optional bounded live replay; endpoint must already be running:
PYTHONPATH=src .venv/bin/python scripts/replay-fn-evidence.py --output .runtime/fn-replay-repeat.json
```

The running services were not restarted. If needed after reviewing the change, the owner can reload only the project UI with `scripts/stop-ui.sh` followed by `scripts/start-ui.sh`; keep vLLM unchanged. Tests render the updated app directly, independently of the running UI.
