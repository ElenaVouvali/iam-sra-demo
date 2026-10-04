# Universal follow-up updates and simplified citizen flow

2026-10-04. Baseline `main` aa11d98; local implementation branch `feature/universal-updates-simple-ui`. No push, merge, service restart, environment installation or model-deployment change was performed. The working tree was clean at the start; no applicable AGENTS.md was found. Sources: accessible FN PDF, physical pp.5–9, and existing registry/methodology. GA document unavailable; existing canonical registry/phase mappings retained without inventing source instructions.

## Implemented

- `updates.py` and `configs/updates.json`: typed question contracts and seven facet transitions, six-question budget, reviewed non-FN templates, exact citizen-described hypothetical changes, contextual blockers and chronological updates. Q1 cannot resolve security/safety; Q2 routing/visual responses cannot independently resolve noise; Q3 cannot alter welfare scores or caps. Security still receives its own clarification even when Q1 is selected.
- Existing `Session` pipeline extended, rather than replaced: both confirmation gates, immutable initial snapshot, selective original review, explicit joint proposal and independent conditional review. No relevant new original evidence means scores carry. Unknowns remain null. Retry preserves confirmations/drafts and caches successful original review while conditional calculation is pending.
- Score-free modified facet interpretation in batches of at most six, bounded by180s and full4096-token budgets. Each applicable confirmed facet receives independent conditional-rubric review; the parent concern uses the minimum only if all required facets are assessed. No original score inheritance, fixed bonuses, duplicate facet denominator or “yes means7”. Medical support does not establish equity, shielding does not establish security, rerouting does not establish infrastructure/visual objection.
- One question/short confirmation at a time, Continue as primary action, no intermediate numbers/tables/JSON. One labelled final result with deterministic conditional→final-original→unavailable fallback and meaningful qualitative completion. Diagnostics require `IAM_DEVELOPER=1`.
- Schema5.0 JSON/JSONL separates summary, proposals, all15 domain records, transitions, contextual boundaries, aggregation, dialogue/confirmation and audit. Citizen quotations and model explanations are distinct; nulls have reasons. A legacy4.1 adapter remains in audit. Historical exports were not rewritten.

Scoring anchors, conditional anchors, aggregation, minimum coverage, bottleneck/rounding, fixed scenario, registry, dependencies, launch scripts and model pins remain unchanged. Original and modified results use independent arithmetic traces and disclose denominator changes.

## Offline verification

**323 passed** with `PYTHONPATH=src .venv/bin/python -m pytest -q`. Compile checks and `git diff --check` passed. Tests cover no scoring before confirmation, retry/draft preservation, edits/corrections, original/modified isolation, selective carry, mixed facets, skipped/unknown evidence, typed transitions, medical-edit invalidation, security clarification, Q3 independence, contextual blockers, joint acceptance, caps/fixture arithmetic, all15 exports, headline fallback and simplified Streamlit flow. UI tests use explicitly labelled test doubles; they do not establish model semantic accuracy.

## Every live attempt

Existing Qwen3-8B/vLLM/V100 only, FP16/V0/XFORMERS,4096 context, concurrency1, non-thinking. Temperature0.2/top_p0.8; maximum two attempts per call. Scripted confirmations exercise plumbing and are not real citizen agreement or measurement validation.

| Attempt | Result | Seconds | Observation |
|---|---|---:|---|
| Sandbox support | Transport blocked before inference |0.040| No result substituted |
| Sandbox opposition | Transport blocked before inference |0.019| No result substituted |
| Sandbox uncertainty | Transport blocked before inference |0.020| No result substituted |
| Sandbox mixed | Transport blocked before inference |0.021| No result substituted |
| Live support | Completed |27.736| Original coverage0/15; qualitative completion, no aggregate |
| Live opposition | Controlled failure |51.452| Q1 schema: mapped concern lacked explicit position/willingness |
| Live uncertainty | Completed |15.611| Original coverage0/15; qualitative completion, no aggregate |
| Live mixed | Controlled failure |48.407| Same Q1 schema failure |
| Targeted-schema opposition repeat | Completed |106.674| Original2/15, no aggregate; modified3/15, mean8.333…, rounded8 |
| Targeted-schema mixed repeat | Completed |99.903| Original2/15, no aggregate; modified3/15, mean8.333…, rounded8 |

The two failure cases motivated restricting follow-up semantic schemas to declared target concerns. The repeat used explicit combined acceptance plus specific privacy/noise and medical-benefit testimony. Modified noise8/privacy8/medical9 were model reviews, not fixed assignments; security remained unavailable when not established. The original cap4 remained recorded independently. All successful sessions preserved the initial snapshot. Support/uncertainty completion with0/15 shows that an engineering success is not sufficient evidence of semantic adequacy: original model mapping/scope review can still under-assess explicit positions. No claim of calibrated labels, population readiness or score improvement follows from these runs. This report does not claim real-browser verification; Streamlit renderer was verified offline.

Detailed attempted-session diagnostics/settings remain in ignored `.runtime/updates-smoke.json`, `updates-smoke-live.json`, and `updates-smoke-repeat.json`; these synthetic records are not routinely logged citizen testimony. Final read-only health: vLLM and Streamlit healthy. V100 resident allocation26994MiB; sampled utilization0–67%. A2's unrelated14763MiB allocation was observed only and untouched. GPU samples are point measurements, not peak memory/latency benchmarks.

## Remaining methodological limits

FN supplies examples, not numerical transition calibration. The minimum-facet rule, applicability requirements, template bank and headline policy are application-designed conservative choices requiring FN review. Existing missing anchors/calibration, ordinal averaging, minimum coverage, generalized bottleneck, overlapping/leading/bundled validation choices and4.25-versus6.0 inconsistency remain. Unknown facets can reduce coverage even when a citizen accepts a combined proposal. User confirmation checks meaning, not validity. The separate physical assumptions remain hypothetical, not engineering/clinical guarantees.

## Project-only commands

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src .venv/bin/python -m pytest -q
# Optional bounded live checks; records every success/failure, no fallback:
PYTHONPATH=src .venv/bin/python scripts/smoke-updates.py
PYTHONPATH=src .venv/bin/python scripts/smoke-updates.py --ids opposition,mixed --joint accept --output .runtime/updates-repeat.json
# When ready to load the updated UI; project-owned UI only, keep vLLM running:
scripts/stop-ui.sh
scripts/start-ui.sh
scripts/health-check.sh
```

From the laptop, use an available local port:

```bash
ssh -N -L 8502:127.0.0.1:8501 elvouvali@liono.microlab.ntua.gr
```

Open http://localhost:8502. Restart commands are provided, not executed.
