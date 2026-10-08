"""Authored stage-2 fixtures verify selector/session contracts, not live semantics."""
import json
import csv
from copy import deepcopy
from pathlib import Path
import runpy
import pytest
from iam_sra.schemas import MappingAssessment
from iam_sra.interpretation import EvidenceItem, check_meaning
from iam_sra.updates import FacetMeaning, select_followups, contract
from iam_sra.settings import config, CONCERNS
from iam_sra.session import Session, State
from test_confirmation import Fake
from iam_sra.scoring import aggregate
from iam_sra.schemas import Assessment
from iam_sra.assessment_review import final_review

ROOT=Path(__file__).resolve().parents[1]
PACK=json.loads((ROOT/'manual-tests/followup-assessment-cases.json').read_text())
CASES=PACK['cases']
INITIAL={c['id']:c for c in json.loads((ROOT/'manual-tests/initial-assessment-cases.json').read_text())['cases']}


def authored(case):
    return MappingAssessment.model_validate(case['authored_mapping']),{k:EvidenceItem.model_validate(v) for k,v in case['authored_evidence'].items()}


def session(case):
    meaning,evidence=authored(case);client=Fake(meaning);s=Session();s.begin();s.submit(case['response'],client)
    # Explicit engineering substitution, never presented as live interpretation.
    s.draft=meaning;s.evidence.update(evidence)
    s.original_facets={f['concern_id']+':'+f['facet']:FacetMeaning.model_validate(f) for f in case['authored_facets']}
    s.finish_discovery();s.confirm(True);s.score_initial(client)
    for row in s._initial['assessment']['concerns']:
        row['score']=case['initial_score_targets'].get(row['concern_id'])
        row['status']='assessed' if row['score'] is not None else 'unassessed'
    s._initial['aggregate']=aggregate(Assessment.model_validate(s._initial['assessment']))
    return s,client


def test_pack_coverage_policy_and_guide_are_current():
    assert {c['id'] for c in CASES}==set(INITIAL) and len(CASES)==32
    assert all(c['evaluation_split']==INITIAL[c['id']].get('evaluation_split','development') for c in CASES)
    assert PACK['policy_version']==config('updates')['version']
    assert sum(c['expected_counts']['total'] for c in CASES)==sum(len(c['expected_questions']) for c in CASES)
    render=runpy.run_path(str(ROOT/'scripts/build-followup-manual-guide.py'))['render']
    assert (ROOT/'manual-tests/followup-assessment-manual-tests.md').read_text()==render(PACK)


def test_blank_results_sheet_covers_every_baseline_run_and_extensions():
    with (ROOT/'manual-tests/end-to-end-results-template.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    baseline=[r for r in rows if r['case_id'].startswith('T')]
    assert {(r['case_id'],r['branch_id']) for r in baseline}=={(c['id'],b['id']) for c in CASES for b in c['end_to_end_branches']}
    assert len(baseline)==155
    assert {r['case_id'] for r in rows if r['case_id'].startswith('X')}=={f'X{i:02}' for i in range(1,10)}
    assert all(r['status']=='NOT_RUN' and not r['actual_final'] for r in rows)
    for c in CASES:
        assert c['initial_score_targets']==INITIAL[c['id']]['expected_scores']
        for b in c['end_to_end_branches']:
            assert b['expected_final_aggregation']['coverage']==c['initial_aggregation_target']['coverage']


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_expected_questions_match_authored_semantics_and_have_real_citizen_condition_quotes(case):
    meaning,evidence=authored(case)
    assert case['response']==INITIAL[case['id']]['response']
    check_meaning(meaning,evidence,'original')
    for e in evidence.values():assert e.text in case['response']
    facets={(c.concern_id,f) for c in meaning.concerns for f in c.facets}
    assert facets=={(cid,f) for cid,fs in INITIAL[case['id']]['expected_facets'].items() for f in fs}
    questions=select_followups(meaning,evidence,facet_meanings=[FacetMeaning.model_validate(f) for f in case['authored_facets']],assessed_scores=case['initial_score_targets'])
    assert questions==case['expected_questions']
    assert [q['id'] for q in questions]==case['expected_question_ids']
    for q in questions:
        spec=contract(q)
        assert {(t.concern_id,t.facet) for t in spec.targets}<=facets
        if q['condition_evidence_ids']:
            assert all(r in evidence for r in q['condition_evidence_ids'])
            assert 'You previously asked for:' not in q['text']
        if q['apply_to_joint']:
            assert spec.modification==' '.join(config('updates')['mitigations'][t.facet] for t in spec.targets)
    assert bool([q for q in questions if q['apply_to_joint']])==case['combined_question_available']


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
@pytest.mark.parametrize('branch',['full','partial','remaining','unsure','skip'])
def test_scripted_branches_keep_initial_snapshot_and_require_explicit_joint_answer(case,branch):
    s,c=session(case);initial=deepcopy(s.initial);s.begin_followups()
    assert [q['id'] for q in s.questions]==case['expected_question_ids']
    index={'full':0,'partial':1,'remaining':2,'unsure':3}
    while s.state==State.FOLLOWUPS:
        q=s.current_question
        if branch=='skip':s.skip_followup();continue
        choice=q['choices'][index[branch]] if q['apply_to_joint'] else q['choices'][-1]
        s.respond(choice,'',c)
    assert s.initial==initial and s.conditional is None
    assert s.joint_required==case['combined_question_available']
    assert not s.joint_confirmation_required
    if s.joint_required:
        if branch=='full':
            assert set(s.unchanged_aspects())==set(case['expected_unchanged_aspect_keys_after_all_fully_addressed'])
        # An unsure combined answer is an independent scripted branch closure.
        s.record_joint('unsure',[],'',c)
    s.continue_final(True,c)
    assert s.initial==initial and s.final['assessment']==initial['assessment'] and s.conditional is None


@pytest.mark.parametrize('case',[c for c in CASES if c['combined_question_available']],ids=lambda c:c['id'])
@pytest.mark.parametrize('joint_choice',['accept','reject'])
def test_joint_acceptance_and_rejection_are_explicit_independent_choices(case,joint_choice):
    s,c=session(case);initial=deepcopy(s.initial);s.begin_followups()
    gate_index=0 if joint_choice=='accept' else 2
    while s.state==State.FOLLOWUPS:
        q=s.current_question;s.respond(q['choices'][gate_index] if q['apply_to_joint'] else q['choices'][-1],'',c)
    unchanged={key:{'response':'yes','clarification':''} for key in s.unchanged_aspects()}
    remaining=[] if joint_choice=='accept' else list(dict.fromkeys(q['relevant_concerns'][0] for q in s.presented_followups if q['apply_to_joint']))
    s.record_joint(joint_choice,remaining,'',c,unchanged)
    assert s.joint['choice']==joint_choice and s.joint['remaining_concern_ids']==remaining
    assert s.conditional_draft.current_route_stance.interpretation==('supported' if joint_choice=='accept' else 'opposed')
    assert s.initial==initial and s.conditional is None
    s.continue_final(True,c)
    assert s.initial==initial and s.final['assessment']==initial['assessment']
    assert s.export()['dialogue_and_confirmations']['presented_followups']


@pytest.mark.parametrize('case,branch',[(c,b) for c in CASES for b in c['end_to_end_branches']],
                         ids=[c['id']+'-'+b['id'] for c in CASES for b in c['end_to_end_branches']])
def test_end_to_end_manual_targets_match_confirmed_default_progression(case,branch):
    s,c=session(case)
    # Substitute the explicitly authored baseline to isolate follow-up arithmetic.
    # This is an engineering check, never a measurement of live scoring accuracy.
    for row in s._initial['assessment']['concerns']:
        row['score']=case['initial_score_targets'].get(row['concern_id'])
        row['status']='assessed' if row['score'] is not None else 'unassessed'
    s._initial['aggregate']=aggregate(Assessment.model_validate(s._initial['assessment']))
    initial=deepcopy(s.initial);s.begin_followups()
    for answer in branch['answers']:
        assert s.current_question['id']==answer['question_id']
        if answer['action']=='skip':s.skip_followup()
        else:s.respond(answer['choice'],answer['clarification'],c,answer['context'])
    assert s.state==State.UPDATED and not s.joint_confirmation_required
    s.continue_final(True,c);review=final_review(s)
    assert s.initial==initial and s.joint is None and s.conditional is None
    assert review['final_profile']==branch['expected_final_profile']
    assert review['same_coverage']==branch['expected_same_coverage']
    for row in review['concerns']:
        cid=row['concern_id']
        assert row['validated_original_score']==branch['expected_validated_original_scores'].get(cid)
        assert row['final_score']==branch['expected_final_scores'].get(cid)
    for row in review['progression']['decisions']:
        assert row['gain']==branch['expected_gains'].get(row['concern_id'],0)
    expected=branch['expected_final_aggregation'];actual=review['final_aggregate']
    for field in ['mean','cap','adjusted','rounded','coverage']:
        assert actual[field]==expected[field]
    assert actual['trace']['selected_minimum']==expected['minimum']
    assert actual['trace']['cap_applied']==expected['cap_applied']
    assert review['final_headline']==expected['rounded']
    assert all(a['numerical_change']==config('updates')['macro_policy']['score_adjustments'].get(a['code'],0) if not a['skipped'] else a['numerical_change']==0 for a in review['policy_priority_answers'])
    assert s.export()['final_assessment_review']==review
