"""Readiness construct, source arithmetic and export regression tests."""
import json
import pytest
from test_core import payload, assessment
from iam_sra.assessment import parse_assessment, AssessmentError, check_eligibility
from iam_sra.settings import CONCERNS, QUESTIONS, POLICY
from iam_sra.scoring import aggregate
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
    assert {b['concern_id'] for b in r['trace']['eligible_blockers']}=={'welfare_equity','noise','visual_pollution','perceived_safety_privacy'}
    assert r['trace']['scope']=='all_assessed_concerns'
    assert r['trace']['selected_minimum']==2 and r['trace']['offset']==2










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
