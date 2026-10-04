# Attribution and applicability verification

Baseline: `2b1923ce094f09e1e7bfb4d8a3bbccf2560ceef1`, clean local `main`. No applicable AGENTS.md found. FN PDF at `/home/elvouvali/SRA_LLM concept feasibility.pdf`, physical pp.5–9 reviewed; `iam-assessment.jsonl` and the separate GA were not found locally. The small synthetic `eval/attribution_cases.json` and existing FN reference replace no real citizen export; no full session or PDF is committed.

## Implemented behaviour

- Common score-free semantic attribution now separates altitude/frequency from airspace crowding, separation and coordination. Independent contrastive checks also prevent height-only privacy/risk and coordination-only system-reliability inference. Supported traffic and facility/land-planning claims remain eligible, including paraphrases. Unsupported nominations remain diagnostic; all mapping contexts use the same review path.
- Discovery boundary metadata previously bypassed scoped interpretation. Each nomination now needs facet attribution and a separate explicit independent-decisiveness check, followed by reconciliation with the original facet ledger. Missing meanings are clarified before any actionable boundary. Unknown decisiveness never creates a score. Raw nominations/rejections, evidence, reasons and edits stay in audit.
- Existing joint-proposal applicability now asks explicit, unselected Yes / My view has changed / Unsure / Skip questions, retains original evidence links and mixed positions/conditions, and re-reviews affirmed meaning under the conditional rubric. Changed answers require words; unknowns stay unavailable. Jointly accepted tested privacy/noise evidence remains usable. Targeted clarification and answer editing invalidate dependent confirmations/results while preserving the initial snapshot and revision history.
- Schema5.2 adds boundary/applicability provenance to the existing record layout. The legacy list of affirmative applicability keys remains accepted; new responses are richer records. Historical exports are unchanged. Registry2.2, discovery1.1 and prompt policy5.2 version these changes.
- Generation constraints mirror existing mapped-position invariants and constrain outside-registry wording to verbatim citizen passages. Neither app-owned validation flags nor question assumptions establish citizen evidence.

Changed areas: `app.py`; `conversation_client.py`, `session.py`, `discovery.py`, `reporting.py`; registry/discovery/prompt configs; scope/discovery prompts; focused regressions, synthetic contrasts and live replay scripts; README/methodology. Scoring/reassessment anchors, minimum3, mean, bottleneck/rounding, scenario, IDs/phases, environments and deployment scripts are unchanged.

## Offline verification

380 tests passed in13.45s; the final attribution/client/evidence regression subset was rechecked after making the topic-only review flag application-owned. Compile checks and `git diff --check` passed. Tests include unsupported altitude/routing nominations, legitimate capacity/facility contrasts, separate topic/independent-decisiveness checks, metadata bypass rejection, neutral unknown answers, usable gate/joint evidence, explicit medical applicability versus Skip/Unsure, mixed conditions, direct clarification UI, stale-result invalidation, immutable originals, versioned exports and precise fallback reporting. Deterministic model doubles verify logic, not Qwen semantic accuracy.

The numeric regression verifies the inputs themselves: medical8, noise3, privacy2; exactly3 inputs and denominator3, mean13/3, eligible privacy minimum2, offset2, cap4, adjusted4 and half-up final4. No false airspace/infrastructure item enters the denominator. FN's separate illustrative four-item4.25 fixture also still passes.

## Every live attempt

The pre-existing localhost Qwen3-8B endpoint was healthy at the start. Checks were serial, non-thinking, FP16/V0/XFORMERS as configured, context4096, max concurrency1, temperature0.2/top_p0.8, existing pinned model revision. Stages retain180-second deadlines/two attempts per request; contrast runs have a240-second total bound/45-second case deadline. No model downloads, GPU changes, environment updates or service restarts/stops were performed. All inputs were synthetic; scripted user confirmation is an engineering check, not a citizen study.

| Attempt | Seconds | Actual outcome |
| --- | ---: | --- |
| FN 1 | 28.686 | Unmapped issue must preserve citizen wording. |
| FN 2 | 30.456 | Unmapped issue must preserve citizen wording. |
| FN 3 | 74.052 | Complete: original 8/3/2, mean13/3, cap4; modified9/8/9, mean26/3, final9. |
| A: altitude_only | 10.461 | No airspace, but overbroad personal-privacy nomination remained; later guarded independently. |
| A: frequency_noise | 10.701 | Expected tested mappings/exclusions passed: noise |
| A: traffic_separation | 16.687 | Airspace retained, but extra system-reliability nomination remained; latest independent guard not live-completed. |
| A: capacity_paraphrase | 34.298 | Expected tested mappings/exclusions passed: airspace_capacity |
| A: rerouting_only | 27.685 | Model schema failure at concerns.1:value_error, concerns.2:value_error; Mapped concern requires an explicit position or conditional willingness; otherwise needs_clarification; Mapped concern requires an explicit position or conditional willingness; otherwise needs_clarification; no assessment saved. |
| A: landing_pad | 35.971 | Model schema failure at concerns.5:value_error; Mapped concern requires an explicit position or conditional willingness; otherwise needs_clarification; no assessment saved. |
| A: independent_noise | 19.889 | Expected tested mappings/exclusions passed: noise |
| B: rerouting_only | 31.534 | Expected tested mappings/exclusions passed: perceived_safety_privacy |
| B: landing_pad | 25.724 | Expected tested mappings/exclusions passed: infrastructure_land_use |
| C: altitude_only | 10.835 | No airspace, but overbroad personal-privacy nomination remained; later guarded independently. |
| C: traffic_separation | 16.491 | Airspace retained, but extra system-reliability nomination remained; latest independent guard not live-completed. |
| D: altitude_only | 13.861 | Expected tested mappings/exclusions passed:  |
| D: traffic_separation | 17.795 | Live interpretation unavailable; no mock fallback. |

FN3 completed in74.052s. Exactly medical benefit/noise/personal privacy remained; airspace was excluded before scoring. Discovery's unsupported airspace/technical-safety nominations and an unproven independent noise claim were audit-only, not actionable blockers. No infrastructure/visual topic entered its aggregate or modified requirements. Original8/3/2 gave mean13/3, cap4, final4. After Q1/Q2 acceptance, Q3 neighborhood priority, explicit combined acceptance and affirmative medical applicability, the observed modified scores were privacy9/noise8/medical9, mean26/3, final9. These values are not forced and do not validate the rubric. Medical support was not treated as equity knowledge.

Two initial FN attempts failed the existing evidence guard because metadata put passage IDs in `unmapped_issues` instead of quotations. The schema fix preceded FN3. BatchA's rerouting/facility attempts failed existing mapped-position validation; BatchB succeeded after mirroring that invariant in generation. BatchA's permissive contract only checked the primary exclusion, so its height/privacy and coordination/reliability extras were inspected and explicitly counted as semantic failures in this report. BatchC made the exclusions explicit and failed both. BatchD corrected the height-only privacy nomination; its traffic request then returned HTTP500 and the endpoint shut down. Final read-only health check found **both vLLM and Streamlit unavailable**. Shutdown cause is not established; no service was restarted. Thus the latest reliability exclusion and a full FN replay after the final additional facet guards remain live-unverified. Their deterministic tests pass. Do not treat successful output among accepted cases as overall semantic accuracy.

Detailed synthetic traces remain Git-ignored in `.runtime/`, not published session data. Each attempted case, failure stage, latency, schema/evidence checks and settings is recorded. There were3 FN session attempts and13 contrastive attempts; no failures are omitted.

## FN alignment and remaining limits

The medical/noise/privacy separation follows FN pp.5–7, with visual attribution intentionally conservative. Independent scope/boundary review, explicit applicability, conservative facet completeness and answer revision handling are application extensions. FN pp.8–9 suggest gates and illustrative outcomes but provide no numerical update formula. The3-concern minimum, ordinal averaging, phase-1 threshold/offset and conditional anchors remain experimental and require FN calibration. No psychometric or population validity is claimed. Semantic classifiers can still err; direct user clarification and audit remain necessary. Coverage can remain insufficient after a completed dialogue.

Work remains on local `main`; this task does not push changes.

Schema5.2 is additive to5.1's organization; version-aware consumers should tolerate new fields. The4.1 audit adapter remains. Existing in-memory sessions and historical files are not retroactively relabelled as validated; use a new session when loading the changed code.

## Commands

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_attribution_confirmation.py
# Run only if an existing endpoint is healthy:
scripts/health-check.sh
PYTHONPATH=src .venv/bin/python scripts/replay-fn-evidence.py
PYTHONPATH=src .venv/bin/python scripts/replay-attribution.py
```

No service restart was executed. When you choose to load the code, the existing project-owned UI commands are `scripts/stop-ui.sh` and `scripts/start-ui.sh`; they do not restart vLLM. The model endpoint is currently unavailable, so a UI-only restart will not restore inference. This task deliberately leaves that service state unchanged.
