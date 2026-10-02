# Experimental FN-aligned scenario readiness · revision 3

This demo implements a provisional interpretation of Future Needs’ *SRA_LLM concept feasibility.pdf*. Scores are source-inspired ordinal judgments, not calibrated probabilities, psychometric measurements, an official EU instrument or population readiness. The arithmetic mean is an illustrative index. Confirmation checks interpretation, not measurement validity.

## Source contract and provenance

Physical PDF pp.1–2 list the 15 topics and four/four/seven phase memberships. Those canonical IDs and phase mappings are unchanged. Stored phase SRL ranges are source taxonomy, not restrictions on individual scores (FN itself assigns phase-2 noise3). pp.3–4 propose structured LLM interpretation and warn about inflation from conversational language. p.5 contains the corridor and citizen sample; pp.6–7 propose welfare/equity=8, noise=3, visual pollution=4, perceived safety/privacy=2, mean4.25 and cap4. pp.8–9 give three validation gates and an illustrative combined-outcome table. p.10 is blank. The PDF stays outside Git.

The separately requested GA Living Lab table and latest exported session were not found in the accessible project/home source locations at inspection; their paths have been requested. No content is invented for them. Registry provenance currently supports the FN PDF mapping only. The user-reported export (privacy1/noise1/infrastructure1, Q1 accepts shielding, Q2 retains residential routing, Q3 unsure) is a reported observation, not a directly inspected file. Fresh baseline inference independently reproduces its three score-1 mappings. Review of the two missing files remains required when supplied.

The reviewed baseline is `edbcb22fbc3cd014bfbe6b2293587ad30b166e66`. Local main matched that commit with a clean working tree. Work is isolated on `recalibrate/fn-scenario-readiness`; no push or changes to historical exports/evaluation artifacts.

## Construct and evidence mapping

The current construct is **Provisional FN-aligned scenario readiness**: concern-specific position, expressed conditions and willingness under those conditions. Original-route stance remains separate, globally and per concern. Acceptance of medical/public benefits, awareness, original-route acceptance, conditions and hypothetical modifications are different records. A concerned citizen willing to accept a changed route is not automatically a categorical refuser, nor automatically highly ready. A low privacy/noise score can coexist with high medical-public-benefit support.

Every registry entry includes scope, inclusion/exclusion criteria, facets and illustrative anchors in `configs/concerns.json`. The general 1–9 anchors in `configs/scoring.json` distinguish refusal even under modifications (1), strong boundaries (2), strong disruption with conditional openness (3), conditional local intrusion (4), mixed readiness (5), tentative acceptance (6), qualified acceptance (7), clear support (8) and unqualified concern-specific endorsement (9). The single FN example cannot calibrate all nine levels or all 15 topics. These distinctions are engineering choices requiring FN review.

For FN alignment, lifesaving hospital/public-service support maps to the **medical_public_benefit** facet within welfare_equity. Distributive equity is a distinct facet: no equitable access, fair distribution or equity knowledge is inferred from medical support. `medical_public_benefit_support` is also displayed as an interpretation, but it is never another numeric item in the aggregate. Each canonical concern counts once even with two facets.

Personal surveillance discomfort maps to perceived_safety_privacy; system failure mechanisms, hacking, data retention or access governance require separate technical evidence. Seeing cameras watch property does not alone establish visual pollution. The FN attribution of low altitude/rerouting to visual pollution is ambiguous. We permit a broader **visible_physical_intrusion** facet only if the answer separately expresses an objection to visible aircraft; a mapping note and supporting passage are required. Low altitude alone, privacy camera visibility or a rerouting condition alone is insufficient. Strict mapping therefore may omit FN’s visual score4 rather than invent sky-clutter statements.

Residential rerouting is an acceptance condition unless physical facility siting, construction, zoning or allocation of land is separately expressed. It is not automatically infrastructure/land use, SUMP integration, accessibility or airspace capacity. Shared passages may support independent acoustic/privacy meanings, with an explicit `distinct_shared_evidence` decision and rationale; one objection must not be multiplied across concerns. Additional genuinely supported topics are permitted and are visible in mean inputs, so their effect is reviewable.

Missing/ambiguous evidence is unassessed/null, never zero or a neutral5. Ambiguous mappings require clarification and retain their reasons. There is no inference from verbosity, civic-minded language, opposition, psychological motives or hidden technical mistrust. No NIMBY/personality, irrationality or cognitive-dissonance labels are implemented.

## Model interpretation and bounded execution

The mapping call gives Qwen all15 scopes/exclusions; each independent review receives the selected concern guidance and general anchors. The separate reviewer checks explicit semantic scope before anchoring and receives only the requested canonical concern ID and the full citizen text, without first-pass stance, facets or condition annotations. Qwen interprets semantic evidence, conditional willingness and provisional scores. Mapping eligibility uses mapped/needs_clarification, distinct from the final assessed/unassessed readiness status. An explicit medical-support dimension can nominate a missing medical_public_benefit welfare facet for independent review; this general FN mapping rule never assigns a score or implies distributive equity. The nomination and its exact evidence IDs are exported separately. Hard English lexical vetoes and substring support detection are removed: “uncomfortable” is not “comfortable” support and “dislike” is not “like” support. Keyword overlap does not establish a concern or stance. This removes false negatives without guaranteeing the model’s semantic correctness.

Qwen selects numbered passage IDs; Python retrieves exact untouched citizen wording for excerpts and conditions. Rationale is interpretation, not a fabricated quotation. Pydantic enforces canonical IDs, one item per concern, facet membership, integer1–9, assessed score/evidence, unassessed null and exact evidence matching. Stance no longer fixes score bands or mixed=5. Schema3.5 also permits assessed conditional readiness when original-route stance is unknown; unassessed readiness does not erase an explicitly stated original stance. Schema3.2 onward additionally constrains global dimension citation shapes: unassessed requires[], otherwise one selected passage. Concern evidence can still include up to three passages and all citizen passages remain available; this limits citation count, not the input or assessed evidence. The small mapping decision vocabulary avoids unconstrained explanation loops; distinct interpretations are explained in concise rationales.

A semantic mapping call is followed by independent review/scoring of each evidenced topic candidate (at most15); one retry per call, maximum32 calls, with an overall180-second assessment deadline and at most120 seconds per HTTP request. Candidates with neither evidence nor conditions skip numeric review. Mapping reserves1400 output tokens; each independent review reserves300. All attempts count the complete chat via vLLM `/tokenize` and enforce4096 total; excessive text is rejected, not truncated. No source-score recognition, canned inference, offset or individual-score substitution occurs. Python performs aggregation only. Invalid/truncated/unsupported outputs are controlled failures, not invented profiles. Rejected visible thinking content is not exported. Existing Qwen revision, V100-only FP16/V0/XFORMERS deployment is retained; no reasoning parser or mock fallback.

## Deterministic aggregation

Assessed scores only enter the unweighted mean. At least three assessed concerns are required for an overall illustrative index; phases need one assessed concern for their mean. Coverage and all missing topics are displayed; these thresholds are experimental choices, not FN coverage rules. A single corridor does not assess all15.

The FN fixture deterministically produces mean4.25, selected privacy minimum2, offset2, cap4, adjusted4 and half-up final4. Live inference never uses this fixture to replace scores.

The generalized bottleneck remains experimental: assessed phase-1 scores<=3 are eligible, select the minimum, add2 and cap the mean. FN p.7 illustrates privacy2+2 but does not establish a universal phase-1 threshold or offset. `aggregate.trace` exports every mean input, denominator, eligible blocker/score/phase, selected minimum, offset, threshold, enabled flag, cap application and rounding. `min(mean,cap)` ensures a cap cannot increase a result. No aggregate is returned below the coverage requirement.

## Validation and preservation

Original questions/choices are preserved from pp.8–9 with their hypothetical assumptions; unsure/none and optional clarification are documented extensions. Default selection follows assessed concerns. Because the original Q1 presupposes route opposition, it is selected automatically only for an evidenced opposed/mixed route stance and assessed privacy/data-security objection. Positive or unknown route stance is not labelled an opposition blocker. Citizens can explicitly consider all three questions without thereby assessing extra topics.

All applicable p.9 combination rules are retained: Q1 AND Q2 acceptance, rejection of Q1 OR Q2, and local-rights priority in Q3. Overlapping rules are not given invented precedence. The proposed6–7,2–3 and cap4 outcomes are reference metadata only: FN provides no numerical update formula. Original scores never change after validation. Corrections to the original interpretation create a separate version with citizen restatement and reason.

Actual question/answer gates are recorded per concern/facet as resolved_under_assumptions, remaining, partially_tested, untested or unresolved. There is no static tested-set deletion. Q1 acceptance resolves personal viewing privacy under shielding only; it does not establish technical safety or full-route acceptance. Q2 bundles altitude, sound, curfew and visibility: rejection because routing remains residential does not resolve noise. Visual-clutter rejection preserves that objection without independently resolving sound. Q3 is a policy preference; unsure leaves its trade-off unresolved. Other facets and unasked topics remain untested. Multiple concerns remain simultaneously.

For the reported export pattern Q1accept/Q2residential objection/Q3unsure, privacy is resolved under assumptions, noise is only partially tested, residential routing remains and the policy trade-off is unresolved. No numeric update or full-route acceptance is inferred. Camera shielding, sound at120m and the extra12-minute delivery time are hypothetical, not engineering/clinical facts. Leading wording and bundled interventions prevent causal or clinical conclusions.

## Questions for FN / deviations requiring review

- p.7 mean4.25 versus p.9 mean6.0: which calculation was intended?
- What evidence anchors distinguish all nine integers and generalize beyond one sample?
- Does “lowest phase score” mean an individual concern or a phase mean? When is a bottleneck eligible, and why+2?
- Is ordinal averaging defensible for the intended use, and what minimum coverage is required?
- How should medical public benefit and distributive equity be represented without conflating knowledge or distribution?
- Is visible physical intrusion an intended visual-pollution facet, and when is the FN example sufficient evidence?
- Which separate meanings justify scoring overlapping concerns rather than recording one routing condition?
- What numerical validation-update formula is intended, and how should overlapping outcomes interact?
- How should leading privacy/clinical wording be revised and Q2 changes unbundled?
- Which additional scenarios cover the other15 concerns, and how does the separate GA Living Lab table constrain scope?

Synthetic cases and repeated model runs check engineering behavior, not scientific validation. Remaining model discrepancies and failed attempts are reported in `docs/calibration-report.md`; no agreement claim is conditioned only on accepted samples.
