# Current assessment methodology

This is an experimental interpretation of the FN medical-drone scenario, not a calibrated SRL instrument. FN supplies the scenario, concern taxonomy, illustrative scores, targeted hypothetical barrier tests and a macro-policy trade-off. The exact numerical progression policy is an application proposal requiring FN/ISCTE and Living Lab review. [The follow-up policy](fn-followup-update-policy.md) explains that distinction and the GA relationship.

## Original-proposal interpretation and scoring

The initial mapper classifies explicitly expressed issues in citizen passage batches, then reviews the evidence for nominated facets. It checks subject relevance, exact citizen quotations, requirements, qualifications, balanced positions and uncertainty. It does not nominate every facet merely because it appears in the registry or scenario. The independent facet ledger preserves accepted companion aspects and unknown aspects separately from the parent concern summary.

The citizen reviews and confirms the meaning before numerical scoring. The model assigns each assessable facet a 1–9 value under `configs/ordinal.json` and `prompts/confirmed-scoring.txt`. A score-free strength review checks endorsement evidence. Inconsistent numbers or unsupported highest scores receive bounded numerical reassessment; persistent inconsistency makes the facet unavailable without substituting a Python score. Original-route acceptance and medical-purpose support remain separate dimensions.

Python validates scope, evidence IDs, context, canonical facets and numeric bounds. It combines assessable facet values using their minimum, once per concern. Explicitly unknown evidence is not a neutral 5. The confirmed initial snapshot remains immutable; corrections are separate evidence and assessments.

## Aggregation

For each profile, average only assessed concern scores. One assessed concern is sufficient. Cap the mean at the lowest assessed concern across all phases plus 2, using `min(mean, cap)` so the cap cannot raise the result. Round to the nearest integer with exact halves rounded down. All 15 concerns are reported, with unavailable values and coverage disclosed. Phase summaries do not constrain individual concern scores to phase-specific ranges.

A no-reservations confirmation with no scored concerns can invoke the separate direct overall-acceptance rule in `configs/discovery.json`. It is not a fabricated concern mean. Discovery of new original evidence can change coverage; an initial/final delta with changed coverage is not a like-for-like improvement measure.

## Follow-ups and final result

The default sequence tests expressed objections or conditions independently, clarifies unknown aspects, then asks a relevant neutral policy trade-off. Mitigations come from citizen conditions or a reviewed hypothetical bank; feasibility and effectiveness are assumptions, not verified outcomes.

The bounded progression index starts from validated-original concern scores and grants at most +2 once per assessed concern only after every originally opposed/mixed or conditioned facet is fully resolved. Partial, rejected, uncertain, skipped and untested gates do not automatically change numbers. Macro-policy choices do not change scores or reduce medical-purpose support. This progression index has different semantics from the initial acceptance-score anchors.

An explicitly requested combined-proposal check assesses acceptance of one revised proposal and interactions between changes. Its conditional rating remains separate from progression. Separate mitigation acceptance does not establish joint acceptance. The final screen identifies the selected context and shows the initial, validated-original and final scores, concern changes, evidence and arithmetic.

## Verification and scientific limits

Offline checks establish state, schema, evidence, arithmetic and UI contracts using authored inputs and test doubles. They do not establish live-model accuracy, psychological validity or population readiness. The manual pack preserves development and fresh-validation splits; targets must not be changed merely to match model outputs. Current stage-1 mapping and mitigation relevance still require live review. Past reports have been archived outside the active repository and are not current performance claims.

Use [the manual walkthrough](../manual-tests/end-to-end-manual-tests.md), [verification status](verification.md), and [data handling](privacy.md) when presenting or evaluating the application.
