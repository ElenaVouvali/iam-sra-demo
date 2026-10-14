"""Synthetic regressions; mocked extraction is not a live semantic assessment."""
import json

import httpx
import pytest

from iam_sra.baseline import (BaselineExtraction, BaselineClaim, CanonicalReview,
    canonical_claim, reviewed_canonical)
from iam_sra.conversation_client import ConversationClient
from iam_sra.assessment import AssessmentError
from iam_sra.privacy import PrivacyError, require_clean
from test_baseline import Extractor, claim, answer, familiarity
from test_baseline_adaptive import new, until
from test_baseline_ui import start, click


@pytest.mark.parametrize('text',[
    'I like the idea of deliveries by drone, but I cannot explain what difference they would make.',
    'I oppose deliveries by drone, but I do not know what effect they would have.',
    'I am not sure whether anything would change.',
])
def test_opinion_or_unknown_effect_never_justifies_a_reasoning_probe(text):
    s=new();familiarity(s);until(s,'understanding')
    # Even if extraction mislabels this, the absent named effect cannot justify
    # asking why "that effect" happens. It also cannot satisfy reasoning.
    answer(s,text,[claim(kind='claim_without_detail',span_quote=text,effect_quote='',topic_ids=[])])
    assert s.current_question['id']=='experience'
    assert s.current_profile['requirements']['understanding']['status']=='missing'
    assert any(r['rule_id']=='no_named_unexplained_effect' for r in s.skipped_by_design)


def test_named_effect_probe_shows_the_actual_effect_and_checks_its_quote():
    s=new();familiarity(s);until(s,'understanding')
    text='Deliveries could be quicker, but I cannot explain why.'
    answer(s,text,[claim(kind='claim_without_detail',span_quote=text,effect_quote='Deliveries could be quicker')])
    assert s.current_question['id']=='reasoning'
    assert 'Deliveries could be quicker' in s.current_question['question_text']
    with pytest.raises(AssessmentError):
        canonical_claim({'evidence_id':'p1','claim_type':'understanding_claim_without_detail',
            'span_quote':text,'effect_quote':'Less traffic','interpretation':'You expect less traffic.',
            'subject':'respondent','domain':'IAM'}, {'p1':text})


def test_independent_review_can_preserve_uncertainty_instead_of_an_effect():
    text='I have no idea what would change.'
    source=BaselineExtraction(interaction='substantive',claims=[BaselineClaim.model_validate(
        claim(kind='claim_without_detail',evidence_id='p1',span_quote=text))])
    review=CanonicalReview(decisions=[{'candidate':0,'supported':True,
        'claim_type':'understanding_unknown','effect_quote':'',
        'interpretation':'You are unsure what difference deliveries would make.'}])
    result=reviewed_canonical(source,review,{'p1':text})
    assert result.claims[0].kind=='unknown' and not result.claims[0].effect_quote


def test_output_privacy_retry_stays_inside_the_two_attempt_budget():
    client=ConversationClient();client._start();calls=[]
    secret='My PIN is 1846.'
    def handler(req):
        if req.url.path=='/tokenize':return httpx.Response(200,json={'count':10})
        calls.append(1)
        content={'interaction':'substantive','claims':[]} if len(calls)>1 else {'answer':secret}
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(content)}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        result=client._request(http,'readiness_evidence','Return only supported evidence.',
            {'answer':'I do not know.'},BaselineExtraction.model_json_schema(),BaselineExtraction.model_validate_json)
    assert len(calls)==2 and result.claims==[]
    assert secret not in repr(vars(client))
    assert any(d.get('privacy_boundary')=='model_output' for d in client.last_diagnostics)
    assert len(client.last_trace)==1  # Only the screened response enters the trace.


@pytest.mark.parametrize('boundary',['model_output','assessment_record'])
def test_output_rejection_keeps_safe_answer_for_retry_without_consuming_question(monkeypatch,caplog,boundary):
    class UnsafeOnce(Extractor):
        def __init__(self):
            super().__init__();self.last_trace=[];self.last_diagnostics=[]
        def extract_baseline(self,*args,**kwargs):
            if not getattr(self,'failed',False):
                self.failed=True
                if boundary=='model_output':
                    self.rows=[claim('concept','unknown',topic_ids=[],interpretation='Alice Example does not know.')]
                else:
                    self.last_settings={'note':'My PIN is 1846.'}
                return super().extract_baseline(*args,**kwargs)
            self.rows=[claim('concept','unknown',topic_ids=[],interpretation='You do not know what a drone is.')]
            return super().extract_baseline(*args,**kwargs)
    app=start(monkeypatch,UnsafeOnce());click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    text='I have heard the word, but I do not know what a drone is.'
    app.text_area(key='baseline_answer_text').set_value(text);click(app,'Continue')
    assert app.session_state.session.state=='interview' and len(app.session_state.session.events)==1
    assert app.text_area(key='baseline_answer_text').value==text
    assert any(b.label=='Retry this answer' for b in app.button)
    assert not any('new session' in w.value for w in app.warning)
    assert 'Alice Example' not in caplog.text and '1846' not in caplog.text
    assert 'privacy_findings' in caplog.text
    click(app,'Retry this answer');click(app,'Confirm and continue')
    assert len(app.session_state.session.events)==2
    assert app.session_state.session.events[-1]['text']==text


@pytest.mark.parametrize('interaction,text,message',[
    ('unsure','I am unsure.','You are unsure about this question.'),
    ('declined','I would prefer not to answer.','You prefer not to answer this question.'),
])
def test_written_uncertainty_or_refusal_has_a_clear_confirmable_summary(monkeypatch,interaction,text,message):
    app=start(monkeypatch,Extractor(interaction=interaction));click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value(text);click(app,'Continue')
    assert any(e.value==message for e in app.markdown)
    assert not any('could not summarize' in e.value for e in app.markdown)
    click(app,'Confirm and continue')
    assert app.session_state.session.events[-1]['interaction']==interaction
    assert app.session_state.session.current_question['id']=='delivery'


@pytest.mark.presidio_live
def test_installed_detector_accepts_benign_unknown_effect_and_blocks_private_controls():
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    for text in [
        'I like the idea of deliveries by drone, but I cannot explain what difference they would make.',
        'I would prefer not to answer.',
        'I cannot yet explain the effects on local services.',
    ]:assert require_clean(text)==text
    for text in ['My PIN is 1846.','My home address is Amfitritis 12.']:
        with pytest.raises(PrivacyError):require_clean(text)


@pytest.mark.presidio_live
def test_real_detector_uncertainty_round_trip_with_mocked_model_and_export(monkeypatch):
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    from iam_sra.baseline_client import BaselineClient
    s=new();familiarity(s);until(s,'understanding')
    text='I like the idea of deliveries by drone, but I cannot explain what difference they would make.'
    calls=[];real=httpx.Client
    def handler(req):
        calls.append(req.url.path)
        if req.url.path=='/tokenize':return httpx.Response(200,json={'count':100})
        payload=json.loads(req.content)
        supplied=json.loads(payload['messages'][1]['content'])
        eid=next(iter(supplied['passages']))
        claim_data={'evidence_id':eid,'claim_type':'understanding_unknown','span_quote':text,
            'effect_quote':'','interpretation':'You are unsure what difference drone deliveries could make.',
            'topic_ids':[],'subject':'respondent','domain':'IAM'}
        result=({'decisions':[{'candidate':0,'supported':True,'claim_type':'understanding_unknown','effect_quote':''}],
                 'additional_claims':[]} if 'candidates' in supplied else
                {'interaction':'substantive','claims':[claim_data]})
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(result)}}]})
    monkeypatch.setattr('iam_sra.baseline_client.httpx.Client',lambda **kw:real(transport=httpx.MockTransport(handler)))
    s.answer(text,BaselineClient());s.confirm(True,actor='automation')
    assert s.current_question['id']=='experience'
    assert s.current_profile['coverage']['understanding']['status']=='unknown'
    s.finish();s.complete(actor='automation')
    data=s.export()
    assert data['schema_version']=='iam-baseline-2.3.1'
    assert data['events'][-1]['text']==text and data['numerical_crl'] is None
    assert calls==['/tokenize','/v1/chat/completions']*2
