# Methodology and FN feedback
This is an experimental scenario-based assessment, not a psychometrically validated instrument, official EU citizen-readiness measure, or scientifically calibrated numeric scale. Citizen confirmation checks interpretation only. No population inference is supported.

## Page-level implementation map
PDF pages are physical pages, including the blank p.10. pp.1–2 register 15 concerns in three phases; phase membership is application controlled, not a model judgment. Phase bands are source taxonomy, not constraints on concern scores. pp.3–4 motivate JSON interpretation and score-inflation checks; strict Pydantic schemas, exact excerpt checks and bounded retries replace source free-form summarized evidence. p.5 supplies the original corridor and response; scenario wording is preserved, with all details labeled hypothetical. pp.6–7 supply the reference scores (8,3,4,2), mean 4.25, and illustrative cap 4. pp.8–9 supply Q1–Q3 and original choices; stored verbatim after PDF line-wrap normalization. We add unsure/none and optional clarification. p.10 has no substantive text.

## Deviations required for defensible interpretation
No NIMBY archetype, cognitive dissonance, ignorance, irrationality, anti-technology bias or inferred technical mistrust. Opposition is a stated preference, possibly informed. Medical public-benefit support is separate from awareness, understanding, equity knowledge and route acceptance. FN's welfare/equity=8 reference maps public-service support to equity without evidence about distribution or vulnerable groups; live assessment does not make that inference. The reference visual=4 also overlaps altitude and privacy; live interpretation requires explicit visual concern. Verbosity/civic-minded phrasing is not readiness evidence.

All 15 concerns are registered; one scenario cannot assess them all. Missing or ambiguous concerns remain unassessed/null. The four intended targets do not imply welfare/equity is always assessed. Coverage is shown out of 15 and by phase; no global readiness conclusion follows. Awareness uses demonstrated/uncertain/unassessed, never opposed; a demonstrated interpretation requires an explicit correct scenario fact. This is an interpretation, not a knowledge test. Concise rationales are evidence-based explanations, not hidden reasoning. Excerpt matching establishes textual fidelity, not truth of semantic interpretation.

## Provisional arithmetic and anchors
configs/scoring.json explicitly versions nine acceptance anchors. The single FN example cannot calibrate nine levels; knowledge is reported separately without numeric score. Scores describe concern-specific original-scenario acceptance, an explicit deviation from a developmental SRL maturity scale. Aggregate only assessed scores, require at least three, and phase means require one. These thresholds are implementation choices, not FN requirements. Generalized eligible bottleneck: assessed phase-1 score ≤3; cap=min eligible+2. Adjusted=min(mean,cap), never an increase. Half-up rounding follows capping. A partial phase mean is not comprehensive phase readiness. No aggregate when fewer than three concerns are evidenced. Original and corrected snapshots retain separate arithmetic.

## Validation semantics
Q1 acceptance resolves only the stated privacy concern under shielding; does not imply entire route acceptance or technical safety. Q2 bundles altitude, sound, curfew and implied visibility: acceptance applies to the bundle, not a causal estimate for noise alone. Q3 records a policy preference under a hypothetical delay, never a diagnosis. Unsure is unresolved. Separate outcomes and clarifications are retained, including simultaneously remaining concerns and apparently conflicting preferences under different hypotheticals. Questions selected by explicit assessed concern IDs, without telling citizens they have blockers. Corrections use a complete restatement of original position plus reason and create a separate snapshot. Optional validation clarification is recorded verbatim, not automatically rescored.

Camera shielding feasibility, sound at 120 m, and 12-minute delivery impact are scenario assumptions, not established engineering/clinical facts. Original question wording is retained for traceability despite leading/bundled wording; neutral wrapper and uncertainty option are additions. No automatic increases to 6–7 or decreases to 2–3; numerical update remains null.

## Questions for Future Needs
- p.7 mean is 4.25; p.9 calls the same unweighted mean 6.0. Which arithmetic is intended?
- What observable score anchors and evidence requirements justify all nine levels? Are these acceptance or maturity scores?
- Does 'Lowest Phase Score' mean minimum concern or phase mean? Which phases/thresholds trigger a bottleneck, and is +2 universal?
- What numerical validation-update formula, if any, can be justified?
- How resolve overlapping outcomes: accepts Q1/Q2 while favoring privacy in Q3, or multiple remaining concerns?
- How revise leading wording, especially clinical urgency and guaranteed shrouding, and unbundle Q2 for interpretable effects?
- What further scenarios assess the other concerns and equity knowledge? What minimum coverage permits a summary?
- Can the combined perceived safety/privacy concern distinguish its two constructs? Does the reference privacy evidence justify any safety inference?

Synthetic evaluation checks software/model behavior only; it is not scientific validation. Future empirical calibration needs independent FN review and a suitably designed study.

## Experimental evidence eligibility and consistency gates
`configs/evidence_eligibility.json` versions a conservative English topic-presence screen over assessed verbatim excerpts. It rejects topic mappings without a listed lexical cue (for example, a camera alone does not establish technical security), and supported positions require an acceptance cue. Concern-specific position must also agree with provisional score bands: opposed 1–4, explicitly mixed 5, supported 6–9. Explicit uncertainty/ambiguity remains unassessed/null and may retain exact excerpts; it is not a neutral 5. These are rejection checks, not replacement scores or a semantic measurement model. Unsupported output is retried once with non-citizen error feedback, then rejected. The FN fixture is only an arithmetic fixture and does not go through live eligibility checks.

These additional choices arose from observed over-assessment and instruction-induced score changes during engineering evaluation. Topic terms are incomplete, substring-based and English-only; they can cause false negatives, miss negation/context, and do not prove semantic correctness. A user may clarify/restated their response after a controlled error. Their performance needs FN review; they are neither calibrated anchors nor a claim of prompt-injection immunity. Each model result remains provisional and citizen-correctable.
