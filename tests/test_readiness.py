"""Readiness construct, source arithmetic and export regression tests."""
import json
import pytest
from test_core import payload, assessment
from iam_sra.assessment import parse_assessment, AssessmentError, check_eligibility
from iam_sra.settings import CONCERNS, QUESTIONS, POLICY
from iam_sra.scoring import aggregate
from iam_sra.validation import outcome, conclusions
from iam_sra.validation import select_questions
from iam_sra.legacy_session import Session
from iam_sra.schemas import SCHEMA_VERSION

@pytest.mark.parametrize('score',[2,3,4,6,7,8])
def test_opposition_does_not_determine_readiness_integer(score):
    text='I oppose this noisy route but would accept inaudible flights.'
    p=payload({'noise':score},text)
    p['concerns'][0].update(position='opposed',conditional_willingness='willing',conditions=[text])
    assert parse_assessment(json.dumps(p),text).concerns[0].score==score

@pytest.mark.parametrize('score',[3,4,5,6,7])
def test_mixed_readiness_is_not_fixed_at_five(score):
    text='I am partly supportive of the sound level and partly opposed.'
    p=payload({'noise':score},text);p['concerns'][0]['position']='mixed'
    assert parse_assessment(json.dumps(p),text).concerns[0].score==score

@pytest.mark.parametrize('cid',list(CONCERNS))
def test_all_fifteen_have_scopes_facets_and_anchors(cid):
    definition=CONCERNS[cid]
    assert all(definition[k] for k in ['scope','inclusion','exclusion','facets','illustrative_anchors'])
    a=assessment({cid:7},'Evidence about this topic.')
    assert a.concerns[0].facets==[definition['facets'][0]]
    assert sum(c.status=='assessed' for c in a.concerns)==1

@pytest.mark.parametrize('text',['uncomfortable','dislike','The hum spoils quiet rest.','Life-saving hospital service matters.'])
def test_no_substring_stance_or_keyword_veto(text):
    # This checks removal of lexical gates, not the semantic accuracy of fixtures.
    a=assessment({'welfare_equity' if 'service' in text else 'noise':3},text)
    assert check_eligibility(a) is a

def test_invalid_cross_topic_facet_rejected():
    p=payload({'noise':3});p['concerns'][0]['facets']=['personal_privacy']
    with pytest.raises(AssessmentError):parse_assessment(json.dumps(p),'noise privacy visual welfare')

def test_condition_must_be_actual_citizen_text():
    p=payload({'noise':3});p['concerns'][0].update(conditional_willingness='willing',conditions=['invented condition'])
    with pytest.raises(AssessmentError):parse_assessment(json.dumps(p),'noise privacy visual welfare')

def test_benefit_dimension_is_not_counted_twice():
    a=assessment({'welfare_equity':8,'noise':3,'perceived_safety_privacy':2})
    r=aggregate(a)
    assert r['trace']['denominator']==3 and r['mean']==13/3
    assert r['trace']['mean_inputs']==[{'concern_id':'welfare_equity','score':8},{'concern_id':'noise','score':3},{'concern_id':'perceived_safety_privacy','score':2}]

def test_exact_fn_fixture_and_trace():
    r=aggregate(assessment({'welfare_equity':8,'noise':3,'visual_pollution':4,'perceived_safety_privacy':2}))
    assert (r['mean'],r['cap'],r['adjusted'],r['rounded'])==(4.25,4,4,4)
    assert r['trace']['eligible_blockers']==[{'concern_id':'perceived_safety_privacy','score':2,'phase':1}]
    assert r['trace']['selected_minimum']==2 and r['trace']['offset']==2

def test_exported_session_validation_pattern():
    a=assessment({'welfare_equity':8,'noise':3,'perceived_safety_privacy':2})
    responses=[outcome(q,q['choices'][i]) for q,i in zip(QUESTIONS,[0,2,2])]
    c=conclusions(responses,a);statuses={r['concern_id']:r['status'] for r in c['concern_validation']}
    assert statuses=={'welfare_equity':'unresolved','noise':'partially_tested','perceived_safety_privacy':'resolved_under_assumptions'}
    assert c['residential_routing']['status']=='remaining'
    assert 'Routing over a residential area' in c['remaining_concerns']
    assert a.concerns[0].score==8 and c['numerical_update'] is None

def test_unasked_noise_and_unrelated_facility_are_untested():
    a=assessment({'noise':3,'infrastructure_land_use':4,'perceived_safety_privacy':2})
    c=conclusions([outcome(QUESTIONS[0],QUESTIONS[0]['choices'][0])],a)
    assert set(c['untested_original_concerns'])=={'noise','infrastructure_land_use'}

def test_privacy_gate_does_not_resolve_other_perceived_safety_facet():
    p=payload({'perceived_safety_privacy':2});p['concerns'][0]['facets']=['personal_privacy','perceived_safety']
    a=parse_assessment(json.dumps(p),'noise privacy visual welfare')
    r=conclusions([outcome(QUESTIONS[0],QUESTIONS[0]['choices'][0])],a)['concern_validation'][0]
    assert r['status']=='partially_tested' and r['untested_facets']==['perceived_safety']

def test_export_separates_raw_scores_aggregate_and_corrections():
    class Fake:
        last_raw_scores={'noise':3};last_diagnostics=[];last_trace=[];last_settings={'enable_thinking':False}
        def __call__(self,text):return assessment({'noise':3},text)
    s=Session();s.begin();s.submit('The buzz bothers me.',Fake())
    original=s.original.model_dump();s.correct('I accept quieter flights.','Earlier willingness was missed.',Fake())
    s.validate(True,include_reference_questions=True)
    for q in s.questions:s.respond(q['choices'][-1])
    r=s.export()
    assert r['versions']['schema']==SCHEMA_VERSION
    assert r['original_inference']['raw_model_scores']=={'noise':3}
    assert r['original_inference']['application_derived_concern_scores']=={}
    assert r['original']==original and len(r['corrections'])==1
    assert [v['presented_question']['id'] for v in r['validation']]==['q1','q2','q3']
    assert r['original_profile']['mapping_decisions'][0]['score_anchor']==POLICY['anchors']['3']


def test_policy_tradeoff_does_not_test_distributive_equity():
    p=payload({'welfare_equity':4});p['concerns'][0]['facets']=['distributive_equity']
    a=parse_assessment(json.dumps(p),'noise privacy visual welfare')
    review=conclusions([outcome(QUESTIONS[2],QUESTIONS[2]['choices'][0])],a)['concern_validation'][0]
    assert review['status']=='untested' and review['untested_facets']==['distributive_equity']


def test_export_cannot_mutate_session_or_registry():
    s=Session();s.begin();s.submit('Noise bothers me.',lambda text:assessment({'noise':3},text));s.validate(True,include_reference_questions=True)
    for q in s.questions:s.respond(q['choices'][-1])
    exported=s.export();exported['validation'][0]['code']='privacy_resolved'
    exported['original_profile']['concern_definitions'][0]['phase']=99
    assert s.responses[0]['code']=='unresolved'
    assert CONCERNS['public_awareness_trust']['phase']==1


def test_known_conditional_willingness_can_be_scored_with_unknown_original_stance():
    text='I would accept only after independent tests establish fault tolerance and cyber protection.'
    p=payload({'technical_safety_security_privacy':5},text)
    p['concerns'][0].update(position='uncertain',conditional_willingness='willing',conditions=[text])
    a=parse_assessment(json.dumps(p),text)
    assert a.concerns[0].score==5 and a.concerns[0].position=='uncertain'

def test_unassessed_readiness_does_not_erase_known_original_stance():
    text='I oppose the noise but cannot judge what changes would help.'
    p=payload({'noise':3},text);p['concerns'][0].update(status='unassessed',score=None,position='opposed',conditional_willingness='uncertain')
    assert parse_assessment(json.dumps(p),text).concerns[0].position=='opposed'

@pytest.mark.parametrize('stance',['supported','uncertain','unassessed'])
def test_opposition_question_is_not_assumed_for_a_nonopposing_route(stance):
    from iam_sra.schemas import Dimension
    a=assessment({'perceived_safety_privacy':2})
    a.current_route_stance=Dimension(interpretation=stance,excerpts=[] if stance=='unassessed' else ['noise privacy visual welfare'],rationale='Original stance stays separate.')
    assert 'q1' not in [q['id'] for q in select_questions(a)]

def test_positive_privacy_is_not_called_an_opposition_blocker():
    a=assessment({'perceived_safety_privacy':8})
    a.concerns[0].position='supported'
    assert 'q1' not in [q['id'] for q in select_questions(a)]
