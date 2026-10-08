# End-to-end manual application tests

This walkthrough tests the Streamlit application from the original response to the final screen and downloaded report. Use it with the [32 case scripts and expected questions](followup-assessment-manual-tests.md), [machine-readable expectations](followup-assessment-cases.json), and [blank results sheet](end-to-end-results-template.csv).

Policy: `3.0.0-experimental`; bounded progression: `1.0.0-pilot`; export: `5.4.0`. These are authored development experiments, not recorded live-model results or scientifically validated SRL targets. The 24 development responses are reused. T25–T32 retain the fresh-validation split; keep their results separate and do not tune expectations to match live outputs.

## Start the app

Use the project's configured inference server and run the app from the repository root:

```bash
.venv/bin/python -m streamlit run app.py
```

Use default mode. Keep FN reference mode off. Record model, prompt, scoring, registry and update-policy versions from the exported metadata. Do not change settings between paired runs. An unavailable inference server is a blocked run, not a failed score assertion.

## One complete run

1. Start a fresh session and read the original urban medical corridor proposal. Paste the exact case response.
2. Inspect the interpretation: concern IDs, independent facets, positions and citizen conditions. Use the original case's [stage-1 expectations](initial-assessment-manual-tests.md). If discovery questions appear, finish those questions without adding testimony for these baseline scripts. Do not claim “no reservations” unless the experiment explicitly requires it. Confirm the interpretation and obtain the initial assessment.
3. Record every initial concern score and the initial mean, cap, rounding and coverage. Compare them with the case's end-to-end baseline. Log a mismatch before continuing. Do not silently edit the live interpretation to match the fixture. A separate corrected diagnostic run must be labelled as such.
4. Select **Continue to follow-up questions**. For the selected branch, check each question's meaning, targets, context and mitigation source against the case guide. Citizen-stated conditions should retain their meaning. Questions are deterministic given the interpreted meaning; live evidence passages and wording may differ. The same response can produce a different queue if the LLM's mapping differs: record both the mapping mismatch and its downstream effect.
5. Select the exact branch answer for each question, leaving **Explain your answer, if you wish** empty. For branch E select **Skip** at each question. Answer original-context clarifications with **I am unsure**; do not choose a correction option with empty text. Use the specified neutral/unsure policy answer. The policy trade-off should follow the independent questions; it has no numerical scoring targets.
6. On the updated review screen, check the recorded answers. Leave **Assess the combined proposal** unused in the baseline runs. Confirm the answer review and continue to the final assessment.
7. Record the three metrics: **Initial assessment**, **Validated original proposal**, and **Final assessment after follow-ups**. Check the table of all 15 concerns, numerical changes, reasons and unavailable values. Open **Aggregation and bottleneck calculations** and the evidence section. Compare the final values with the branch table.
8. Download the JSON report and the JSONL dialogue. Confirm the displayed values agree with `final_assessment_review`, `final_summary` and `aggregation`. The original snapshot must remain unchanged. Baseline runs have no combined proposal or conditional assessment. Keep the exports with the results sheet; never replace authored fixtures with live outputs.

For baseline scripts, validated-original scores must equal initial scores. If live stage 1 differs from the target, independently recompute the expected progression from the actual baseline and gate results. Log the fixed-target mismatch and this conditional arithmetic check separately. If a model or UI failure prevents completion, record the stage and error rather than reporting a successful final-score comparison.

## Score oracle for baseline runs

A fully resolved gate earns at most `+2` **once per assessed concern**, only when all that concern's originally opposed/mixed or conditioned facets are fully resolved. Clamp at 9. An accepted companion facet alone does not earn a bonus. A partial, rejected, unsure, skipped or unanswered gate earns zero; a missing original score stays missing. Macro-policy answers earn zero and never automatically lower medical-purpose support.

For the scored concerns, calculate:

```text
mean = sum(final concern scores) / number of assessed concerns
cap = minimum(final concern scores) + 2
adjusted = min(mean, cap)
final = nearest integer to adjusted, with exact halves rounded down
```

No assessed concerns means an unavailable concern aggregate. Unmentioned concerns are excluded, not filled with zeros. This bounded progression index does not establish acceptance of a combined proposal and does not reuse the meaning of the initial acceptance-score anchors.

## Recommended execution order

Start with these runs, then complete the remaining case/branch rows in the results sheet:

| Runs | Main check |
|---|---|
| T01-A, T01-C, T01-ONLY_noise, T01-ONLY_perceived_safety_privacy | Initial 4; final respectively 6, 4, 4, 5. Resolving noise alone leaves privacy as the bottleneck. |
| T03-BASE, T04-BASE, T06-BASE | No invented mitigation question or score; unresolved evidence remains unresolved. |
| T10-A and T10-C | A hypothetical full-resolution answer tests arithmetic; C tests rejection. Also log that the visual remedy can repeat a remedy the original response already rejected. |
| T14-A and T14-B | Multiple concerns: full vs partial resolution, half-down rounding, no per-question multiplication of gains. |
| T18-BASE and T24-A | Clarify unknown emissions independently from accepted energy demand; no numerical score invented for missing emissions evidence. |
| T20-A and T20-E | All 15 concerns, clamping, all-phase bottleneck and skipped-answer handling. |
| T01-A repeated with all four policy choices | The score and medical-benefit support remain identical across the four runs. |

Some cases have no mitigation questions, so only BASE is needed. Their route acceptance and discovery behavior still require review. Confirmed overall acceptance without reservations with **no scored concerns** has a separate direct overall-9 rule; do not confuse it with a concern aggregate. That rule is not invoked by the baseline scripts.

## Extension experiments

These runs intentionally add evidence or request a different proposal context. Their final numbers are not fixed by the baseline branch tables. Check the confirmed semantics first, then the arithmetic.

| ID | Setup and exact action | Expected behavior |
|---|---|---|
| X01 | Repeat T01-A four times, selecting each offered macro-policy choice in turn, with no explanation. | Identical initial/validated/final concern scores and final 6 when the baseline matches. Preserve medical-benefit 8. Store the chosen priority and numerical change 0. |
| X02 | T01: fully resolve privacy. At noise choose **Partly addresses this concern**, and explain: “The proposed change helps, but the remaining buzzing would still disturb my evening rest.” | Noise has no bonus; privacy can gain 2. With the authored baseline, final 5. Record the remaining noise reservation and its evidence. |
| X03 | T01: at noise choose the full-resolution option but explain: “I still oppose the remaining noise. This does not fully address my concern.” | Do not silently treat contradictory testimony as clean full resolution. Review the conflict/reservation and confirm the intended meaning; unresolved contradiction cannot earn a noise gain. Do not continue through an unresolved conflict. |
| X04 | T18: at the original emissions clarification select the correction option and explain: “I oppose the emissions of this original route. I would accept it only after an independent lifecycle comparison shows lower emissions than the current delivery option.” | Clarify and confirm the newly clear original meaning. Queue an emissions mitigation based on that condition, followed by a policy trade-off. Do not retest accepted energy demand. Reassess the original energy/emissions concern from confirmed evidence; any later gain uses that assessed baseline. Initial unknown emissions stay unchanged in the initial snapshot. If coverage increases, flag that the delta is not like-for-like. |
| X05 | T01: answer the first mitigation fully, then select **Finish questions** before the remaining gates. Confirm the review. | Only tested and fully resolved concerns can gain. Untested aspects do not become accepted. With privacy tested first and the authored baseline, final 5; the untouched noise stays 3. No mandatory combined question. |
| X06 | T01-A: before confirmation, open the optional check and select **Assess the combined proposal**. Accept the combined proposal, confirm unchanged applicable views where requested, and explain: “I accept the combined changes; my medical-purpose support remains unchanged.” | Explicit joint acceptance is recorded. Final headline uses an assessable conditional combined-proposal rating, clearly labelled separately from the original assessment and independent progression. If conditional evidence is insufficient, disclose original fallback. Do not expect the baseline final 6 as the joint rating. |
| X07 | T01-A: request the optional combined check, reject it, select noise as remaining, and explain: “Each change separately helps, but together the new route concentrates noise at the time I rest. Privacy is addressed; I still support medical deliveries.” | Explicit interaction/remaining-noise evidence is recorded for the combined proposal. Independent full-resolution gates must not imply joint acceptance. Original snapshot is preserved. Conditional noise is assessed from the new evidence, not by applying an automatic -2. |
| X08 | Complete T01-A, then use the earlier-answer editing controls to change the noise follow-up to rejection. Reconfirm and complete again. | Invalidate affected confirmations/results and recalculate without retaining a stale noise gain. With unchanged authored original scores, the recomputed progression is final 5. Export only the current result as current, retaining any historical audit events separately. |
| X09 | T20-A: inspect concerns with multiple targeted facets and any original score 7–9. Repeat with those multi-facet gates partial/unsure. | At most one concern gain, never +2 per facet. A resolved baseline 7 reaches at most 9; baseline 8 reaches at most 9; baseline 9 stays 9. Partial/uncertain required facets prevent a whole-concern gain. Record which actual gates exercise these limits. |

## Results and pass criteria

The CSV has one blank row per baseline run and extension experiment. Copy it to a dated results file before editing. Fill the live initial, validated-original and final values, coverage, observed questions, semantic mismatch, score mismatch, arithmetic status, UI/export status and export location. For X01 store four exports and all four priorities.

A successful backend calculation alone is insufficient: question relevance, condition fidelity, confirmation, visible score context and downloaded evidence must also pass. Distinguish stage-1 mapping/scoring deviations, follow-up selection deviations, hypothetical interpretation errors, calculation errors and presentation/export errors. An unavailable number is a correct outcome when the evidence is unavailable.

The automated fixture checks exercise all scripted baseline branches using authored mappings and substituted baseline numbers. They verify state transitions, final arithmetic, original preservation and exports. They do not measure the live LLM or replace these UI experiments.
