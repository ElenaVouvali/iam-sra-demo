# FN-led follow-up update policy and final assessment review

Policy: updates 3.0.0-experimental; bounded progression 1.0.0-pilot. This is a candidate implementation for methodological review, not a scientifically calibrated citizen or ecosystem SRL.

## What the final screen explains

The screen shows three clearly named values: the immutable initial assessment; the validated-original assessment after genuine original-proposal corrections; and the final assessment after follow-ups. Its table reports all 15 concerns, original and final scores, numerical differences, and reasons. Expanders show citizen evidence and exact mean/cap/rounding calculations. Missing scores remain visibly unavailable. JSON/JSONL export schema 5.4 contains identical `final_assessment_review` data, the policy version, per-concern gate states and evidence references.

The default final number is a baseline-dependent progression index. If a combined-proposal check was explicitly requested, its conditional acceptance rating is identified separately and the independent progression index is also disclosed. Neither number replaces the historical baseline. If coverage changes, the screen warns that the numerical difference is not a like-for-like improvement measure. An existing direct overall-acceptance rule can produce a headline without any concern aggregate; that is explicitly labelled and its arithmetic is not invented.

## Default sequence and interpretation

1. Independent questions test expressed objections or stated conditions. Each targets the actual objected-to/conditioned aspects, without including independently accepted companion aspects merely because they share a concern ID.
2. Uncertain aspects receive original-context clarification first. T18/T24 now clarify unknown emissions separately from accepted energy demand.
3. Hypotheses use citizen-described changes where available; otherwise reviewed mitigations are proposed with feasibility/effectiveness assumptions. They do not assert verified engineering outcomes.
4. When relevant, a neutral FN-Q3-style question asks about delivery benefits versus resolving the expressed concerns, under an explicitly hypothetical timing/cost trade-off. It permits conditional and unsure answers, without an invented 12-minute delay. It follows pending concern questions even if an original clarification queues a new test.
5. The citizen reviews the independent answers and confirms meaning before final calculation. A combined-proposal check is available for interactions or explicit assessment of one revised proposal; it is not compulsory in the independent progression path.

Q3 has no numerical targets, no bonus/penalty and no effect on medical-purpose support. Its selected answer and explanation are retained in the report. Genuine changes to the original medical-benefit position must be made as an explicit original-context correction rather than inferred from a policy preference.

## Exact numerical rule

First independently reassess any original-proposal concerns whose confirmed meanings changed. This gives the validated-original profile; unchanged original scores carry forward.

For each concern with an existing validated-original score b:

- Identify every aspect with an original opposed/mixed position or a recorded condition.
- Grant one gain g = min(2, 9 − b) only if every such aspect has an explicit fully resolved hypothetical gate and no unresolved conflict or qualifying clarification retaining a reservation/condition.
- Otherwise g = 0. Partial resolution does not establish which subset is resolved. Rejection confirms the barrier rather than automatically intensifying it. Unknowns and skips cannot establish resolution.
- Progression score = b + g. Multiple answers/facets never earn multiple concern bonuses. A missing b stays missing; a gate does not invent a score for missing baseline evidence.

Aggregate each assessed concern once. Calculate the equally weighted mean, cap it at minimum assessed concern + 2 across all phases, and round halves down. The cap never increases the mean. Original arithmetic and numerical anchors are unchanged. Progression values do not inherit the original anchor meanings: progression 9 does not establish authored unreserved endorsement, and progression 4 does not necessarily mean a further change is required.

For a privacy/noise/medical-benefit baseline of 2/3/8, mean 13/3 and cap 4 give initial 4. With all privacy and noise barriers fully addressed, progression values become 4/5/8: mean 17/3, cap 6, rounded 6. Rejection or uncertainty retains 2/3/8 and final 4. Resolving noise alone gives 2/5/8, mean 5, cap 4, final 4; resolving privacy alone gives 4/3/8, final 5. Any Q3 priority leaves these calculations unchanged. The privacy bottleneck explains the asymmetry.

## What is inherited from FN and what is an application choice

FN supplies targeted hypothetical barrier tests and a macro-policy trade-off (SRA_LLM_FN_concept.pdf pp.8–9). Its illustrative score bands motivate testing bounded progression, but do not establish a universal two-point transition algorithm. The +2 limit is an explicit pilot hypothesis, not a numerical requirement from FN.

The implementation does not automatically penalise rejection of an ineffective mitigation, diagnose mistrust from it, or equate prioritising privacy with rejection of medical welfare. Independent gates establish separate outcomes; joint acceptance is only established by an explicit combined answer. These distinctions make the evidence and proposal context traceable.

GA.pdf Task 3.2 requires measurable reflective indicators with methodological and Living Lab review. Part B pp.5/16 describe citizen empowerment/agency, separate readiness dimensions and individual versus ecosystem reports. An individual scenario-based progression index must therefore not be represented as the complete ecosystem SRL or as evidence that hypothetical safeguards have improved real-world readiness.

## Calibration and verification

Compare this candidate against independent FN/ISCTE judgements, alternative +1/+2 increments, evidence-based conditional reassessment, missing-data behavior and sensitivity to initial-score errors and bottlenecks. Use unseen cases and Living Lab feedback. The OECD/JRC Handbook on Constructing Composite Indicators supports a theoretical framework, explicit aggregation choices and sensitivity analysis; it does not validate this particular formula: https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf

Automated checks verify policy/state/arithmetic/evidence/UI contracts. They use explicit test doubles, not live citizen or model accuracy measurements. The updated 32-case manual pack includes 54 mitigation questions, 6 clarifications and 19 policy trade-offs, with 155 scripted baseline runs and nine extension experiments. T01–T24 are development cases; T25–T32 retain the fresh-validation split. It documents current behavior and remaining mitigation-bank limitations such as T10's rejected visual remedy. Re-run with the pinned live model before claiming semantic accuracy or presenting a live-result dataset to FN.
