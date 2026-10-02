# Verification results
For the latest schema3.5/prompt3.3 implementation, see the [2026-10-02 recalibration report](calibration-report.md). The sections below are preserved historical observations, not current performance estimates.

Observed on liono, 2026-10-01. These are engineering checks on synthetic/source-example text, **not scientific validation**.

## Executed checks
- 93 offline tests passed (approximately 1.7 seconds), covering arithmetic/caps/half-up rounding, nulls and coverage, evidence matching, invalid/truncated output, input/context limits, state transitions, isolation, original/corrected snapshots, all 48 Q1/Q2/Q3 choice combinations, three-question UI flow, explicit mock UI mode, schema/API compatibility, retry bounds, injection score-position consistency and conservative eligibility checks.
- Python compilation, shell syntax checks and `pip check` passed.
- CUDA import and execution passed: torch2.6.0+cu124, vLLM0.8.5, XFormers0.0.29.post2; one visible GPU, logical0 Tesla V100S CC7.0; FP16 CUDA tensor sum returned16.0.
- vLLM startup passed with V0, XFormers, FP16, context4096, max-num-seqs1, tensor-parallel-size1, memory-utilization0.80, localhost8000. Streamlit bound localhost8501. Both health endpoints passed.
- Final prompt1.3.0/rubric1.1.0: a live FN response session completed Q1,Q2,Q3, preserved original scores and returned qualitative outcomes without a numerical update. A real Streamlit AppTest run (no mock/test double) also completed the session and rendered the download/export control. The renderer test is not a laptop browser/SSH forwarding test.
- Normal and `/think` raw requests passed non-thinking checks; no reasoning_content or visible think tags. This is sample-based behavior, not an injection-immunity guarantee.
- The 1.3.0 injection assessment runs both retained opposed privacy with score1; injected commands did not create all-9 scores. No numerical score was substituted by the application.

## Final repeated synthetic evaluation
Eight cases, two runs each: strong support, conditional acceptance, rejection, general uncertainty, mixed concerns, verbose opposition, prompt injection and FN reference text. Final recorded data: [live-v100.json](../eval/results/live-v100.json).

| Check | Observed result |
|---|---|
| Full Pydantic schema/coherence on final attempts | 12/16 |
| Exact evidence/conditions among schema-passing final attempts | 11/12 |
| Fully accepted assessments (including eligibility) | 10/16 |
| Citizen-facing controlled errors | 6/16; no assessment saved |
| Original-route stance agreement on accepted runs | 10/10; only opposition cases accepted in this run |
| Expected concern precision/recall on accepted runs | 1.0/1.0, using provisional developer expectations |
| End-to-end request latency | min6.948s, median11.7875s, mean13.4039s, max27.492s, including retries |
| Score variation across two accepted repeats | no integer variation observed for accepted concerns; not evidence of calibration |

Accepted: conditional, rejection, verbose, injection and FN reference, both repeats. Strong support failed once on technical-topic eligibility and once on exact evidence. General uncertainty and mixed concern cases failed schema/coherence in both repeats. These failures are **material model limitations**, not successful interpretation checks. The conservative gates can reject valid alternative wording and produce false negatives. General uncertainty/ambiguity must not be converted into an invented score; the app correctly fails closed when Qwen cannot produce a coherent result.

All final accepted case stances were opposition; the run therefore does not demonstrate reliable support/uncertainty interpretation. Agreement on accepted samples excludes rejected samples and must not be reported as overall success. Developer expectations are engineering fixtures, not calibrated labels. Two repeats are a tiny sample; sampling temperature0.2, no fixed seed.

The FN live response assessed noise1 and perceived safety/privacy1, leaving the other13 unassessed. It returned no aggregate because fewer than three concerns were assessed. Compared with historical FN noise3/privacy2, differences were -2/-1. Welfare/equity and visual pollution were not forced into live output. The separate historical fixture (8,3,4,2) deterministically gives mean4.25 and illustrative final4; neither fixture integers nor text matching controls live inference.

## Observed resources
Initial GPUs: A2 1MiB; V100S 1MiB. Server warmed at25928MiB; subsequent inference reached27540MiB (about26.9GiB), with sampled GPU utilization82%. A2 remained1MiB/0%. GPU-memory-utilization0.80 is a vLLM budgeting target, not an absolute total-process memory cap; runtime/cache allocations increased the measured total. No OOM was observed. Server logs showed roughly32–39 generated tokens/s during these runs, not a controlled performance benchmark.

Before install: root27GiB and /home142GiB available. After isolated environment, binary-package cache and model download, approximately114GiB remained on /home during the run; the final post-stop preflight observed122.7GiB available. Environments, installation cache, model snapshot, temporary files and rotating logs stayed under this project's /home directory. Existing research environments/caches/workloads and drivers were not upgraded or terminated.

## Blocked/unexecuted boundaries
No remaining GPU or inference blocker for the demonstrated FN session. Laptop SSH forwarding and real laptop-browser interaction were not executed here; exact commands are in README. CI workflow was added and its commands were run locally, but no remote GitHub Actions run or publication occurred. No psychometric validity, clinical/engineering feasibility of hypothetical changes, population-level readiness claim, or numerical validation-update calibration was attempted.

Earlier engineering runs exposed UUID incompatibility, slow Outlines schema compilation, extra topic mappings and instruction-influenced scores. Final configuration uses UUID-verified numeric GPU selection, XGrammar-compatible transport schema plus strict local bounds/coherence, conservative evidence eligibility and bounded corrective retry. Earlier successful runs are not counted as final results.

Services were stopped after the original verification; they have since been started for the user’s session. Source PDF SHA256: `c3f780e368193f45e83827e27fc7438bedc9e38d1a68f31f60835dbf1525866a`, located outside the repository. Questions requiring FN feedback are recorded in methodology.md.


## Revision 2.0.0 · 2026-10-01

Re-read the source validation table on physical p.9 and implemented all three combination gates, preserving overlapping outcomes. Offline suite: **152 passed**, including all 48 choice combinations, evidence passage retrieval, unknown-reference rejection, preservation of originals and optional complete-question selection. Compilation and Git whitespace checks passed.

Real Qwen3-8B/V100 inference through the live Streamlit renderer completed Q1, Q2 and Q3, preserved the original assessment and rendered JSON export. The selected choices were Q1 acceptance, Q2 visual-clutter objection and Q3 privacy priority; expected combined outcomes are remaining objection plus local-rights priority, with numerical update null. The complete-reference-question option was used. This checks application behavior, not scientific validity.

Three earlier live passage-selection checks accepted the original FN text twice and a line-wrapped variant once. Retrieved evidence matched the citizen text in every accepted result; one variant required the bounded retry. Outputs identified only privacy or only noise, so inference remains incomplete. An initial UI smoke assuming three automatically selected questions failed when fewer concerns were identified; the revised explicit all-three option completes that session without inventing concern scores. Earlier aggregate evaluation results above belong to prompt 1.3 and are historical, not current-prompt performance estimates. No new repeatability benchmark was performed for prompt 2.0.


## Recalibration · 2026-10-02 · schema3.5 / prompt3.3

212 offline tests passed. The exact four-label FN arithmetic fixture remains mean4.25/cap4/adjusted4/final4. Final live benchmarks attempted38 assessments:34 accepted,4 controlled schema errors;18 passed every declared per-case check. Results include all attempted cases and retrospective grading notes. A real Streamlit renderer session completed the three reference questions and JSON export with original scores preserved. Normal and /think raw requests passed non-thinking checks; two separate CLI session attempts failed safely. Services are healthy after restarting only the project UI.

The repeated FN benchmark accepted two of three attempts, each welfare8/noise3/privacy2, mean4.3333/final4, with visual pollution unassessed. Welfare condition annotations remain incorrect, so full-profile agreement is not claimed. Broad held-out agreement is2/8; all15-topic agreement6/15. These are material model limitations, not scientific validation. See [calibration report](calibration-report.md) and [machine summary](../eval/results/recalibration-summary.json) for raw-score comparisons, settings, latency, sampled memory, extra failed smoke attempts and pending GA/export source review. Historical results above were not overwritten.
