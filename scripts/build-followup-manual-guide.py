"""Render frozen stage-2 expectations; does not run inference or rewrite fixtures."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def score_text(scores):
    return ', '.join(f"{cid}={value if value is not None else 'unavailable'}" for cid,value in scores.items()) or 'No assessed concerns'


def result_text(ag):
    if ag['rounded'] is None:return 'Unavailable; coverage '+ag['coverage']
    return f"policy adjustment {ag.get('policy_adjustment',0):+d}; mean {ag['mean_fraction']}; cap {ag['minimum']} + 2 = {ag['cap']}; adjusted {ag['adjusted']:.4g}; rounded **{ag['rounded']}/9**; coverage {ag['coverage']}"


def end_to_end(case):
    lines=['### End-to-end score targets','',
           '**Initial / validated original:** '+score_text(case['initial_score_targets'])+'.','',
           '**Initial arithmetic:** '+result_text(case['initial_aggregation_target'])+'.','',
           'These fixed targets apply only when stage 1 matches the authored baseline. With a different live baseline, log that mismatch and calculate follow-up gains from the actual validated-original scores; do not force the model to match this table. Start a fresh session for each branch, leave optional explanations empty, and confirm the final answer review. Do not request the optional combined check in these runs.','',
           '| Run | Answers | Expected final concern scores | Expected final arithmetic |','|---|---|---|---|']
    for b in case['end_to_end_branches']:
        answers='<br>'.join('`'+a['question_id']+'`: '+('Skip' if a['action']=='skip' else a['choice']) for a in b['answers']) or 'No follow-ups; continue to final review'
        lines.append(f"| **{b['id']}** — {b['title']} | {answers} | {score_text(b['expected_final_scores'])} | {result_text(b['expected_final_aggregation'])} |")
    lines+=['','**Export checks:** the initial snapshot stays unchanged; validated-original scores equal the initial scores in these scripts; exported final concern scores match the branch above. The final screen displays only the updated SRL. Unavailable scores remain unavailable. Inspect reasons, evidence, mean inputs, denominator, bottleneck and half-down rounding. Confirm the reported proposal context and export agree with the screen.','']
    return lines


def render(pack):
    counts={k:sum(c['expected_counts'][k] for c in pack['cases']) for k in ['mitigation','clarification','policy_priority','total']}
    lines=['# Manual test pack: FN-led follow-ups and final review','',
           f"{len(pack['cases'])} experiments extend T01–T32 under policy {pack['policy_version']}. Baseline: {counts['mitigation']} mitigation questions, {counts['clarification']} clarifications and {counts['policy_priority']} macro-policy trade-offs ({counts['total']} questions). Authored expectations are not live LLM results.",'',
           'T01–T24 are development cases. T25–T32 retain the fresh-validation split; their scripted expectations have not been fitted to live model outputs. Keep their results separate from development results.','',
           f"The pack includes **{sum(len(c['end_to_end_branches']) for c in pack['cases'])} scripted end-to-end runs**, including one-concern-only resolution runs. Start with the [end-to-end walkthrough and extension tests](end-to-end-manual-tests.md). Record results in [the blank results sheet](end-to-end-results-template.csv).",'',
           '## Setup and scoring policy','',
           '1. Run a fresh session in default mode, paste the response, and check the initial interpretation and scores before proceeding. Log mapping failures; corrected diagnostic runs must be labelled separately.',
           '2. Baseline expectations assume no new discovery testimony or corrections. Compare targeted aspects, contexts, condition meaning and question IDs; live rationale wording and evidence boundaries can vary.',
           '3. Answer the independent concern questions, then the macro-policy question where relevant. The policy question records priorities without changing concern scores or medical-purpose support.',
           '4. Submit the last multiple-choice answer to reach the updated SRL directly. The standard fixed-choice path has no separate outcome-review screen or model inference. Historical scores, evidence, adjustments and arithmetic remain in exports. Added explanations/corrections can still require interpretation and review.',
           '5. Explicit combined-proposal assessment is a separate extension path; it is not presented in the standard fixed-choice flow. Default progression does not claim combined acceptance.','',
           'The progression policy grants at most +2 once per already assessed concern only when every originally objected-to or conditioned aspect is fully resolved under the independent hypotheses. Partial resolution adds +1 once per assessed concern; rejection subtracts 2, bounded at 1. Unsure, skipped and untested aspects give no adjustment. The final policy answer applies +2/−2/0 once to the rounded overall score, within 1–9 and the bottleneck ceiling. Missing scores remain unavailable. Original-proposal corrections can independently change that score. This is a candidate progression index, not the original acceptance rubric or a validated SRL.','',
           '## Scripted branches','',
           '| Branch | Mitigation answers | Macro-policy answer | Expected final behavior |','|---|---|---|---|',
           '| A | Fully addresses this concern | Any offered priority | Eligible assessed concerns gain at most 2 once; the final priority adds +2, −2 or 0 to the rounded overall score, within bounds and the bottleneck ceiling. Original baseline is preserved. |',
           '| B | Partly addresses this concern | Any | Add +1 once per assessed concern, bounded at 9. |',
           '| C | Does not address this concern | Any | Subtract 2 once per assessed concern, bounded at 1. |',
           '| D | Unsure | Unsure | Retain baseline with unresolved outcome. Missing evidence does not become acceptance. |',
           '| E | Skip or finish early | Skip | No gain for unanswered gates. Only shown questions may enter an optional combined proposal. |','',
           'Only concerns with an initial numeric score and confirmed objections or conditions generate follow-ups. Uncertain and unassessed aspects remain recorded without a stage-two question or policy topic. Scripted branches are not predictions of citizen answers.','',
           '## Case index','',
           '| Case | Mitigations | Clarifications | Policy trade-offs | Total | Combined check |','|---|---:|---:|---:|---:|---|']
    for c in pack['cases']:
        n=c['expected_counts'];lines.append(f"| [{c['id']}](#{c['id'].lower()}) | {n['mitigation']} | {n['clarification']} | {n['policy_priority']} | {n['total']} | {'Optional' if c['combined_question_available'] else 'Not applicable'} |")
    for c in pack['cases']:
        lines+=['',f"<a id=\"{c['id'].lower()}\"></a>",f"## {c['id']} — {c['title']}",'','**Original response:**','','```text',c['response'],'```','', '**Review note:** '+c['review_notes'],'']
        lines+=end_to_end(c)
        if not c['expected_questions']:
            lines+=['**Expected follow-ups: none.** Retain missing evidence and show the final-original assessment; no progression gain is established.'];continue
        for i,q in enumerate(c['expected_questions'],1):
            spec=q['contract'];targets=', '.join(t['concern_id']+':'+t['facet'] for t in spec['targets']) or 'No numerical scoring targets; policy preference only'
            lines += [f"### Question {i}: `{q['id']}`",'',f"Context: **{spec['context']}**. Targeted aspects: {targets}.",'','**Illustrative wording for the authored interpretation:**','']
            lines += ['> '+line if line else '>' for line in q['text'].splitlines()]
            lines += ['','**Choices:**','']+['- '+label for label in q['choices']]
            if q['apply_to_joint']:lines+=['','**Mitigation source:** '+('Reviewed hypothetical mitigation bank; citizen-stated conditions remain in the evidence record and are not assumed satisfied.' if q['condition_evidence_ids'] else 'Reviewed hypothetical mitigation bank; feasibility and effectiveness require verification.')]
            lines+=['']
        lines+=['**Default finish:** confirm the independent answers and inspect the final assessment screen. A combined acceptance question is not mandatory.']
        if c['combined_question_available']:
            lines+=['','**Combined-assessment extension:** explicitly request this separate path if interactions need examination; it is not offered in the standard fixed-choice flow. Acceptance and remaining objections are recorded explicitly; conditional scoring is a separate assessment, rather than the bounded progression index.']
            if c['expected_unchanged_aspect_keys_after_all_fully_addressed']:
                lines+=['','**Earlier-view confirmations if a combined check is requested after branch A:**','']+['- `'+key+'`' for key in c['expected_unchanged_aspect_keys_after_all_fully_addressed']]
    lines+=['','## Limits and FN explanation','',
            '- Numerical +2 is an explicit candidate policy requiring FN/ISCTE and Living Lab calibration. Consistent arithmetic does not establish scientific validity.',
            '- A rejected mitigation normally confirms the barrier rather than lowering the score. Q3 preferences do not imply weaker medical-purpose support.',
            '- T10 still illustrates a relevance issue: the generic visual bank can repeat a remedy explicitly rejected by the citizen. Record this for mitigation-bank refinement.',
            '- T18/T24 retain unknown emissions without generating a follow-up for that aspect.',
            '- Ongoing conditions can receive confirmation questions; distinguish accepted ongoing requirements from withheld acceptance.',
            '- Original/final coverage changes make numerical deltas incomparable. The final screen discloses them.',
            '- Raw conditional acceptance of a combined proposal and bounded progression have different constructs; the screen labels each explicitly.','',
            'Fixtures: [followup-assessment-cases.json](followup-assessment-cases.json). Original test pack: [initial-assessment-manual-tests.md](initial-assessment-manual-tests.md).','']
    return '\n'.join(lines)

if __name__=='__main__':
    (ROOT/'manual-tests/followup-assessment-manual-tests.md').write_text(render(json.loads((ROOT/'manual-tests/followup-assessment-cases.json').read_text())))
