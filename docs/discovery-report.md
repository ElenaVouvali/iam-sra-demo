# Evidence discovery · 2026-10-04

Implemented from clean local main `c53591d`, on isolated `feature/evidence-discovery`. No push, merge, service restart, package/environment change or unrelated workload modification. Existing Qwen3-8B/vLLM/V100, the corridor, all15 IDs/phases, confirmation, immutable initial/final profiles and JSON/JSONL remain. FN source provenance remains as documented in methodology; this neutral adaptive questionnaire is an extension, not wording/formulas supplied by FN.

## Implementation

`configs/discovery.json` and `discovery.py` own a deterministic bank/policy: overall stance → unspecified reasons → topic/facet → missing acceptance changes → independent blocker → unmapped issue. Six supplementary questions maximum, one at a time; Skip and Finish preserve unknowns. Positive topics count as evidence, not necessarily objections. Topic/facet nomination alone never establishes severity or a score. Explicit no reservations ends unnecessary questioning. Unmapped issues retain citizen wording with an issue ID, never a fabricated canonical concern.

`Session` collects original-context question/selection/text/control evidence, versions, skips/finish reasons and targeted corrections. `ConversationClient` performs score-free mapping/scope/factual-evidence and sufficiency metadata reviews. If a sparse answer supplies no topic reason, unsupported initial candidate topics are excluded from adaptive selection; later testimony replaces that unconfirmed candidate without inheriting inferred stance. History remains. Contradictory original statements require clarification. Citizen-confirmed blockers/acceptable changes are separately stored and confirmation-bound; neither is an arithmetic input. Interpretation schema1.2, assessment schema3.6, prompt config4.1 and export schema4.1 record the extension. Historical exports are unchanged.

The UI shows neutral discovery/progress and consolidated meaning before confirmation, offers individual meaning/boundary corrections, retains drafted text across controlled errors, and keeps technical diagnostics in the developer panel. Final comparison/downloads remain; blockers, unmapped issues and unresolved topics are visible. Facet-based coverage identifies recorded/clarified topics without a relevant FN hypothetical test. Existing optional all-reference FN questions, original/hypothetical separation, exact combined proposal and updated confirmation remain.

**Unchanged scoring:** rubric anchors, assessed-only mean, minimum3 for an overall index, phase minimum1, phase1 bottleneck threshold≤3/offset+2, cap that cannot raise a mean, and half-up rounding. These remain experimental. Discovery improves evidence collection, not measurement validity or guaranteed aggregate coverage. The exact FN fixture still reproduces4.25/cap4/adjusted4/final4.

## Offline verification

**286 tests passed**, about6s; compilation and Git whitespace checks passed. New checks cover four bare positions; positive noise/no reservations; all15 topics; nomination without stance/severity; no numeric inference before confirmation; adaptive priority/nonrepetition; explicit conditions/boundaries; blockers without arithmetic changes; six-question limits; unknowns/skips/finish; unmapped wording; original/conditional isolation; correction invalidation; atomic retry/draft retention; unsupported-candidate isolation; stable evidence/control IDs; full exports; and comparison UI. Test doubles/mock completion establish plumbing, not semantic accuracy.

## All live attempts

[Machine results](../eval/results/discovery-workflow.json) retain **16 CLI attempts plus1 renderer**, including two controlled failures. Across changing development prompts, **15/17 bounded checks completed**. Four CLI attempts passed every declared qualitative check; completion and qualitative agreement are separate. CLI checks exercise discovery, initial confirmation/scoring and FN selection; the renderer additionally exercises the final comparison/export path. Synthetic scripted confirmations are not citizen agreement, psychometric validation or population evidence.

| Development iteration | CLI completed | All qualitative checks | Median seconds |
|---|---:|---:|---:|
| Initial extraction |4/4|1/4|19.158|
| Positive evidence/eligibility |4/4|1/4|23.194|
| Factual-awareness/semantic review |3/4|2/4|16.748|
| Explicit-reasons sufficiency |1/2|0/2|40.348|
| Isolated unsupported candidates |2/2|0/2|46.668|

The two mixed-position failures occurred at initial confirmation because conflicting interpretations required clarification. No initial score was saved. They were not discarded or converted to mock output. The final two-case batch completed, but neither passed every qualitative check.

| Case | Repeated observation and remaining limitation |
|---|---|
| Bare acceptance → acoustic comfort |Initially mapped positive noise as unassessed; later noise9 in two runs. Final awareness review rejected the earlier invented factual understanding. Coverage1/15, no aggregate.|
| Bare rejection → privacy condition |Early unsupported awareness/trust was once scored1. The final sufficiency/isolation path asks reasons → privacy → blocker in3 questions instead of spending6 on phantom topics. Final **privacy score2, coverage1/15**, no aggregate. Conditional willingness was still misread as not_willing despite explicit acceptance under shielding; user correction is necessary.|
| Bare uncertainty → financing information need |Mapped uncertain financing and left its score null. No aggregate; the uncertainty check passed in each iteration where attempted.|
| Mixed → medical benefit plus equity uncertainty |Still mapped overall mixed stance as uncertain. Both welfare facets appeared in the final run, but the parent position was uncertain and no numeric score resulted. Medical support and unresolved equity require careful citizen review.|

Privacy2 is a live model output, not a point bonus or blocker-driven cap. Repeated privacy scores/mappings varied (null,1, an unsupported trust1,1,2); acoustic results varied (null,9,9). These observations are not a stable calibration estimate. All CLI cases had insufficient scored coverage for an overall index. No attempt substituted a fixture. Unsupported/ambiguous candidate mappings remain visible as needing clarification; citizen confirmation must not be treated as proof that a model mapping is correct.

The live Streamlit renderer completed explicit no-reservations acceptance, both confirmations, unchanged final-original carry-forward,15 comparison rows and2 downloads with JSON/JSONL equivalence (64.199s). It preserved initial records and returned insufficient evidence rather than an invented aggregate. This is an isolated renderer, not a laptop browser/SSH check or restart of the running UI.

The final normalization of excluded candidates clears their unestablished stance/facets/conditions while retaining raw interpretation history. This normalization, exclusion of topic-free original history from concern-specific numeric review, and control-evidence refinements passed offline regressions; the live checks above exercised their preceding selector/isolation behavior, not a new full rerun of every final normalization detail.

## Resources and limits

Existing pinned Qwen revision `b968826d9c46dd6066d109eabc6255188de91218`, vLLM0.8.5, FP16/V0/XFORMERS,4096 context, max concurrency1 and V100 selection are unchanged. Largest recorded CLI prompt plus reserved output:2709 tokens. Mapping/semantic reviews allow up to34 attempts within180s; initial metadata reserves500 tokens, two attempts within a separate180s. Each supplementary semantic answer is independently bounded; nomination-only/blocker-only choices make no inference call. Six questions bound the dialogue. No silent evidence truncation, visible thinking, OOM or package install observed.

V100 after-action samples were26898–26900MiB (~26.27GiB), not peak measurements. The A2 had an existing busy unrelated workload; it was only observed, never used or altered. Final health check: vLLM and Streamlit healthy. Running services were not restarted and the running UI may retain the previous modules until a project-only UI restart.

Limits: semantic metadata/scope review are fallible; repeated runs differ; facets under one numeric parent can remain ambiguous; six questions may leave issues unresolved; questions can affect later testimony; confirmed blockers are acceptance boundaries, not calibrated bottlenecks. Source questions are bundled/leading; FN lacks complete score anchors and a numerical update formula, and source mean4.25 versus6.0 remains inconsistent. GA provenance remains pending. No scientific validity, official EU readiness or established engineering/clinical effects are claimed.

## Commands

On liono, when ready to load this local branch (not executed by the agent):

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
git switch feature/evidence-discovery
PYTHONPATH=src .venv/bin/python -m pytest -q
scripts/stop-ui.sh
scripts/start-ui.sh
scripts/health-check.sh
```

No vLLM restart is needed. Bounded live repeat (writes a new ignored artifact):

```bash
PYTHONPATH=src .venv/bin/python scripts/smoke-discovery.py --output .runtime/discovery-repeat.json
PYTHONPATH=src .venv/bin/python scripts/smoke-discovery-ui.py
```

Laptop: `ssh -N -L 8502:127.0.0.1:8501 elvouvali@liono.microlab.ntua.gr`, then open `http://localhost:8502`.
