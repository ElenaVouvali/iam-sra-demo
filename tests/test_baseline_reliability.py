import json

import pytest

from iam_sra.assessment import AssessmentError
from iam_sra.baseline import (
    BaselineClaim, BaselineExtraction, CanonicalClaim, CanonicalDecision,
    CanonicalExtraction, CanonicalReview, canonical_claim,
    reviewed_canonical,
)
from iam_sra.baseline_client import BaselineClient
from iam_sra.baseline_session import BaselineSession
from iam_sra.evidence import passages
from iam_sra.llm_client import LLMTransport
from iam_sra.privacy import PrivacyError, require_safe_data
from iam_sra.settings import config


def test_canonical_claim_contract_removes_redundant_temporary_labels():
    props=CanonicalExtraction.model_json_schema()['$defs']['CanonicalClaim']['properties']
    assert 'claim_type' in props
    assert not {'dimension','kind','temporality'} & set(props)
    assert CanonicalClaim.model_fields['span_quote'].is_required()


def test_exact_answer_span_is_required_and_checked():
    passage={'B1_2.p001':'I attended the meeting and only listened.'}
    with pytest.raises(AssessmentError,match='exact span'):
        canonical_claim({'evidence_id':'B1_2.p001','claim_type':'exposure_learning',
            'span_quote':'I proposed a change.','interpretation':'The respondent contributed.',
            'topic_ids':[],'subject':'respondent','domain':'IAM'},passage)


def test_listening_and_no_contribution_remain_distinct_claims():
    text='I attended the seminar and only listened. I did not contribute comments.'
    evidence={f'B1_2.{k}':v for k,v in passages(text).items()}
    eid=next(iter(evidence))
    source=BaselineExtraction(interaction='substantive',claims=[])
    review=CanonicalReview(decisions=[],additional_claims=[
        {'evidence_id':eid,'claim_type':'exposure_learning','span_quote':'I attended the seminar and only listened.',
         'interpretation':'The respondent reports attending and listening.','topic_ids':[],'subject':'respondent','domain':'transferable',
         'activity_quote':'the seminar'},
        {'evidence_id':'B1_2.p002','claim_type':'participation_absence','span_quote':'I did not contribute comments.',
         'interpretation':'The respondent says they did not contribute.','topic_ids':[],'subject':'respondent','domain':'transferable',
         'activity_quote':''},
    ])
    result=reviewed_canonical(source,review,evidence)
    assert {(c.dimension,c.kind,c.temporality) for c in result.claims}=={
        ('exposure','learning_exposure','actual'),('participation','absence','not_applicable')}
    assert len({c.span_quote for c in result.claims})==2


def test_intention_cannot_be_relabelled_actual_without_distinct_answer_span():
    text='I would attend a consultation.'
    eid=next(iter(passages(text)))
    evidence={eid:text}
    source=BaselineExtraction(interaction='substantive',claims=[BaselineClaim(
        evidence_id=eid,dimension='participation',kind='intention',temporality='intention',
        interpretation='The respondent would attend.',span_quote=text,topic_ids=[],subject='respondent',domain='IAM')])
    review=CanonicalReview(decisions=[CanonicalDecision(candidate=0,supported=True,
        claim_type='participation_contribution',reason='Reclassification.',interpretation='The respondent attended.')])
    with pytest.raises(AssessmentError,match='distinct supporting answer span'):
        reviewed_canonical(source,review,evidence)


def test_grounding_review_runs_even_if_extraction_is_empty(monkeypatch):
    calls=[];schemas=[]
    text='Deliveries might arrive sooner in urgent situations.'
    def fake_request(self,http,stage,system,user,schema,validator):
        calls.append(stage);schemas.append(schema)
        if stage=='readiness_evidence':
            wire={'interaction':'substantive','claims':[]}
        else:
            eid=next(iter(user['passages']))
            wire={'decisions':[],'additional_claims':[{'evidence_id':eid,
                'claim_type':'understanding_claim_without_detail','span_quote':text,
                'interpretation':'The respondent says deliveries might arrive sooner.','topic_ids':[],
                'subject':'respondent','domain':'IAM','activity_quote':'','time_quote':'',
                'ambiguities':[],'outcome_relation':'unknown'}]}
        return validator(json.dumps(wire))
    monkeypatch.setattr(LLMTransport,'_request',fake_request)
    session=BaselineSession();session.set_context('personal','citizen','madrid');session.answer('little',None)
    session.answer(text,BaselineClient())
    assert calls==['readiness_evidence','readiness_grounding']
    for schema in schemas:
        assert 'claim_type' in schema['$defs']['CanonicalClaim']['properties']
        assert 'dimension' not in schema['$defs']['CanonicalClaim']['properties']
        assert 'kind' not in schema['$defs']['CanonicalClaim']['properties']
        assert 'temporality' not in schema['$defs']['CanonicalClaim']['properties']
        assert len(schema['$defs']['CanonicalClaim']['properties']['claim_type']['enum'])>10
    assert session.pending['claims'][0]['kind']=='claim_without_detail'
    assert session.pending['claims'][0]['span_quote']==text


def test_privacy_failure_metadata_has_path_but_never_echoes_value(monkeypatch):
    import iam_sra.privacy as privacy
    class Result:
        entity_type='EMAIL_ADDRESS';start=0;end=19;score=.93
        recognition_metadata={'recognizer_name':'SyntheticEmailRecognizer'}
    class FakeDetector:
        def analyze(self,**kwargs):return [Result()] if '@' in kwargs['text'] else []
    monkeypatch.setattr(privacy,'detector',lambda:FakeDetector())
    with pytest.raises(PrivacyError) as error:
        require_safe_data({'answer':'person@example.test'})
    rendered=json.dumps({'findings':error.value.findings,'message':str(error.value)})
    assert error.value.findings[0]['field_path']=='root.answer'
    assert error.value.findings[0]['recognizer']=='SyntheticEmailRecognizer'
    assert error.value.findings[0]['confidence']==.93
    assert 'person@example.test' not in rendered


def test_unrelated_explained_effect_does_not_close_another_effect_gap():
    from test_baseline_adaptive import new, familiarity, answer, knowledge, claim
    s=new();familiarity(s)
    answer(s,'Aircraft can carry parcels. Deliveries might arrive sooner. Road traffic could ease if van trips are replaced.',
        knowledge()+[
            claim('understanding','claim_without_detail',evidence_id='B3_2.p002',span_quote='Deliveries might arrive sooner.',effect_quote='arrive sooner'),
            claim('understanding','explained_impact',evidence_id='B3_2.p003',span_quote='Road traffic could ease if van trips are replaced.'),
        ])
    assert s.current_question['id']=='reasoning'


def test_activity_outcome_matching_requires_explicit_same_activity():
    from iam_sra.baseline_routing import compatible_context
    contribution={'subject':'respondent','domain':'transferable','time_quote':'last year',
                  'activity_quote':'the bus-route consultation'}
    same={'subject':'respondent','domain':'transferable','time_quote':'last year',
          'activity_quote':'the bus-route consultation'}
    different={'subject':'respondent','domain':'transferable','time_quote':'last year',
               'activity_quote':'the drone consultation'}
    unstated={'subject':'respondent','domain':'transferable','time_quote':'', 'activity_quote':''}
    assert compatible_context(contribution,same)
    assert not compatible_context(contribution,different)
    assert not compatible_context(contribution,unstated)


def test_benchmark_preview_requires_exact_fixture_expectation_and_logs_clean_text(monkeypatch):
    import iam_sra.baseline_benchmark as benchmark
    raw='My home address is 77 Example Street'
    cleaned='My [private detail removed]'
    def fake_screen(text):
        if text==raw:raise PrivacyError('Private details detected.',preview=cleaned,entity_types=['PRIVATE_ADDRESS'])
        return text
    monkeypatch.setattr(benchmark,'require_clean',fake_screen)
    answer,confirmed=benchmark.checked_fixture_answer(
        {'privacy_preview_confirmations':{'synthetic_address':cleaned}},'synthetic_address',{'text':raw,'control':'answer'})
    assert confirmed and answer['text']==cleaned and raw not in json.dumps(answer)
    with pytest.raises(PrivacyError):benchmark.checked_fixture_answer({},'synthetic_address',{'text':raw,'control':'answer'})
    with pytest.raises(PrivacyError):benchmark.checked_fixture_answer(
        {'privacy_preview_confirmations':{'synthetic_address':'wrong preview'}},'synthetic_address',{'text':raw,'control':'answer'})
