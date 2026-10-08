# Root correction of stage-1 mapping — 7 October 2026

## Current status: one direct interpretation request (7.3.0)

Version 7.3.0 calibrates the interpretation instructions against T01–T24 development targets and historical failure categories, preserving T25–T32 as separate validation cases. See [manual-case calibration](manual-case-calibration.md) for the exact scope, live runner and limitations. Numerical policies are unchanged. This is a prompt candidate, not a live-validated accuracy claim.

Version 7.2.0 adds contrastive prompt guidance for medical-purpose support versus awareness/trust, viewing privacy versus cybersecurity, and low altitude/surveillance visibility versus visual pollution. These are general attribution distinctions, not Python keyword overrides. The citizen-reported extra facets and missing medical support motivated this development calibration. Evaluation must include other responses and untouched validation cases; scripted tests do not establish model accuracy. No extra initial model calls are added. The post-confirmation endorsement reviewer now constrains its quotation field to supplied unchanged passages, retaining ID-to-source validation rather than asking for free transcription. The reported post-confirmation error has no saved technical trace establishing which evidence check failed. This change addresses one identified failure mechanism, not a verified diagnosis of that particular attempt. Local live preflight remains blocked by `Operation not permitted`.

The active wire format remains the compact array introduced in 7.1.0. Following a reported output-limit failure, direct interpretation uses a compact array of expressed facets, without free-text rationales or a registry-sized optional output object. The model still supplies all semantic positions, willingness and citations in one call. Neutral application audit labels replace generated rationales; original passages remain available for review. No live success is claimed until the compact-format report has been inspected.

At the user's request, initial interpretation now uses `direct_interpretation.py`: one model request reads the complete citizen answer and returns the whole-route stance and independent facet meanings with supporting and condition passage IDs. Python validates structure and provenance, assembles the existing ledger, and waits for citizen confirmation. It makes no semantic review, omission-recovery or scope-veto calls at this stage. The previous pipelines are inactive by default. Existing scoring and follow-up policies are unchanged.

The earlier live FN baseline completed in 27.99 seconds with 23 generation calls but had an extra equity facet and a missing noise condition. The direct path makes one generation call on valid output, with one retry allowed for invalid structure or references. This is a request-count reduction, not yet a measured speed or accuracy claim. Use the live privacy pack, full development pack and untouched fresh-validation pack to evaluate it. The sections below are historical experiment records.

## Status: replacement withdrawn from the guided application

Configuration 6.0.1 restores `expressed_issue_then_facet` as the production initial mapper. The reported live FN response under 6.0.0 omitted medical support, noise and privacy, and instead displayed unsupported cost/business uncertainty. The engineering tests below used synthetic model responses and did not establish live semantic accuracy. The direct-role mapper remains available for controlled experiments, not as the default application path. The earlier quotation-based mapper now tolerates whitespace-only PDF formatting differences while preserving original source spans. Incomplete model reviews stay on the saved-answer retry screen and cannot become confirmable interpretations. This rollback changes neither numerical scoring nor follow-up policy. A live rerun is still required to assess model accuracy; rollback itself does not establish scientific validation.

The remainder records the rationale and limitations of the withdrawn 6.0.0 experiment.

Configuration 6.0.2 further removes generated quotation strings and subject substrings from the restored issue-first pipeline. Evidence extraction now returns three arrays of existing passage IDs; the application retrieves the original text. Subject admission returns only an existing quotation key or an empty string. This addresses the continuing baseline evidence-verification failure without relaxing provenance checks or reintroducing the all-facets mapper. It does not establish semantic correctness: relevance and role selection still need live evaluation. The T01 live runner was attempted again but blocked at preflight with `Operation not permitted`.

## Evidence from the complete development run

`mapping-development-20261007-085814.json` completed 20/24 cases; only 10/24 matched coverage, positions and conditions. Four cases aborted on generated subject-quotation validation. The six diagnostic successes did not generalize.

The traces show structural failures, beyond isolated prompt wording:

- T02's concrete imperative remedies became acceptance labels, losing conditions.
- T07 and T11 had only rejection labels, but a later balance reviewer nevertheless manufactured a balanced position.
- T17 admitted an allocation requirement into medical-purpose support.
- T06 lost a known uncertain energy facet before later reviews could see it.
- Generated quotations and subject substrings introduced avoidable validation failures. Exact-source checks correctly rejected fabricated text; making the citizen retry did not solve the generation problem.

Repeated LLM checks were neither independent raters nor guaranteed validators. They sometimes undid a correct earlier decision, and short-lived six-case success encouraged adding more recovery branches. The full suite is the development criterion.

## Replacement implementation

Prompt configuration 6.0.0 uses `passage_mapping.py` through the existing guided application's initial mapper. The previous pipeline remains accessible only as a historical replay path for its engineering tests; it is not the default initial mapping engine.

Each of the 26 registered facets receives one independent request containing its scope, exclusions, original proposal and unchanged citizen passages. The output is a fixed object whose existing passage IDs map to semantic role enums. There are no generated quotations, new evidence identifiers, rationales, subject substrings, candidate-only gates or recovery/balance-promotion stages. All facets are reviewed so a missed nomination cannot irreversibly hide a topic. Unmentioned topics should receive only `unrelated_or_factual` labels.

The roles distinguish current acceptance, current opposition, refusal despite changes, a prerequisite, accepted ongoing obligations, explicit balance, caution, uncertainty and unrelated/factual text. Python builds a coherent semantic ledger from those descriptions; it does not supply a numerical concern score. A prerequisite is not an acceptance vote. Refusal is not turned into balance because an alternative is mentioned. Opposite unqualified labels alone are treated as unresolved conflict rather than automatically manufacturing balanced willingness. Explicit balanced evaluation remains a legitimate mixed position. Unknown is not replaced with a neutral score.

The existing evidence ledger can hold at most three passages per facet. Excess required evidence is explicitly unresolved, rather than silently truncated. A bounded semantic/schema failure in one facet preserves other successful reviews and is exposed in the runner and UI. Overall scoring is blocked while any such reviews remain unresolved, preventing partial success from silently inflating the aggregate. Transport, context-budget and deadline failures still stop processing; they cannot produce a valid assessment. Draft evidence remains saved for retry.

No numerical targets, rubric, score aggregation, bottleneck, phase definitions or fresh-validation cases were changed. Production code has no test IDs or expected-answer branches. Source roles remain fully auditable in `passage_role_annotations`, with failures in `unresolved_facet_reviews`.

## Tradeoff and verification

The initial stage normally makes 26 facet requests plus one separate whole-route request, with at most one retry per request and the same shared 180-second budget. This is more work than the previous pipeline for a very short answer, but avoids its large number of corrective calls on complex testimony. Actual live latency and accuracy must be measured; neither is guaranteed by the redesign.

The complete engineering suite passed 942 tests before the final additional blocking regression; the subsequent targeted mapping/semantic/runner selection passed 113 tests, including that regression. These are explicit contract tests, not live-model accuracy claims. A live preflight again failed with `[Errno 1] Operation not permitted`; no new model results were obtained in this environment.

First compare the replacement on T01,T02,T05,T06,T07,T08,T09,T10,T11,T14,T15,T16,T17,T18,T19,T20,T21,T23,T24. If the diagnostic is satisfactory, run all 24 development cases, then numerical scoring. Preserve T25–T32 for fresh validation. If direct annotation still makes clear semantic mistakes, compare model capability on the unchanged evidence and labels rather than indefinitely adding more LLM self-review layers. Passing a development pack is not population or cross-scenario validity.
