"""Actual client/HTTP/validation/controller path with labelled synthetic outputs.

These tests establish integration behaviour, not real Qwen semantic accuracy.
The smoke runner separately exercises pinned Qwen inference and real privacy.
"""
import json

import httpx
import pytest

from iam_sra.assessment import AssessmentError
from iam_sra.chat_client import ChatClient, FNReply
from iam_sra.chat_session import ChatSession
from indicator_fixtures import bank
from fn_fixture import reply, SyntheticInterpreter


DEFINITION='An aircraft that can fly without a pilot sitting inside it.'
USES='Photography, deliveries and maybe emergency services.'


def opening():
    session=ChatSession(bank(),synthetic=True)
    for text in ('A','Madrid','yes'):session.send(text,SyntheticInterpreter())
    assert session.objective=='drone_description'
    return session


def install_http(monkeypatch, response):
    original=httpx.Client
    calls=[]
    def endpoint(request):
        body=json.loads(request.content)
        calls.append((request.url.path,body))
        if request.url.path=='/tokenize':return httpx.Response(200,json={'count':1200})
        payload=json.loads(body['messages'][-1]['content'])
        generated=response(payload,len([path for path,_ in calls if path=='/v1/chat/completions']))
        content=generated if isinstance(generated,str) else json.dumps(generated)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':content}}]})
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(endpoint),**kw))
    return calls


@pytest.mark.parametrize('wording', ['Thank you.', 'In your own words, what is a drone?',
    'How do you feel about your privacy?', '', None, 'Unneeded text. '*70])
def test_clear_fn_answers_advance_once_despite_unused_wording(monkeypatch,wording):
    def output(payload,_):
        value=reply(payload)
        value['message']=wording
        return value
    calls=install_http(monkeypatch,output)
    s=opening();client=ChatClient()
    for text,goal,next_goal in ((DEFINITION,'drone_description','drone_uses'),
                                (USES,'drone_uses','healthcare_awareness')):
        s.send(text,client)
        assert s.fn.coverage[goal]['status']=='explored'
        assert s.fn.coverage[goal]['evidence_ids']==[s.active_evidence()[-1]['id']]
        assert s.objective==next_goal and not s.failed_turn_id and not s.failures
        assert s.messages[-1]['act']=='question'
    assert len([path for path,_ in calls if path=='/v1/chat/completions'])==2
    assert all(metric['generation_calls']==1 for metric in s.metrics)
    assert s.view()['answer_processing']['status']=='ready'


def test_compact_fn_schema_keeps_grounding_and_omits_legacy_annotation_work():
    properties=FNReply.model_json_schema()['properties']
    assert set(properties)=={'interpretation','message','context_facts','source_ids'}
    assert FNReply.model_json_schema()['required']==['interpretation']


@pytest.mark.parametrize('comparison',[False,True])
def test_empty_answer_wording_tasks_do_not_require_invented_interpretation(monkeypatch,comparison):
    def output(payload,_):
        result={'message':'Can you explain what the word drone means to you?'}
        if comparison:
            result.update(proposed_action='offer_comparison',variants=[
                'Can you describe a drone in everyday language?',
                'What does the word drone mean to you?'])
        return result
    install_http(monkeypatch,output)
    s=opening();request=s._request('',comparison=comparison)
    result=ChatClient().turn(request)
    assert result['interpretation'] is None and not result['_quality_issues']
    if comparison:assert len(result['variants'])==2


def test_omitted_optional_wording_is_accepted_without_a_second_generation(monkeypatch):
    def output(payload,_):
        result=reply(payload);result.pop('message')
        return result
    calls=install_http(monkeypatch,output)
    s=opening();s.send(DEFINITION,ChatClient())
    assert s.objective=='drone_uses' and not s.failures
    assert len([path for path,_ in calls if path=='/v1/chat/completions'])==1


@pytest.mark.parametrize('fault',['quote','evidence_id','goal','missing_interpretation'])
def test_bad_grounding_is_retried_and_cannot_become_coverage(monkeypatch,fault):
    def output(payload,attempt):
        result=reply(payload)
        if attempt==1:
            if fault=='quote':result['interpretation']['answer_quote']='An invented quotation.'
            if fault=='evidence_id':result['interpretation']['coverage'][0]['evidence_id']='m9999'
            if fault=='goal':result['interpretation']['coverage'][0]['goal']='qualification_evidence'
            if fault=='missing_interpretation':result.pop('interpretation')
        return result
    calls=install_http(monkeypatch,output)
    s=opening();s.send(DEFINITION,ChatClient())
    assert s.objective=='drone_uses' and not s.failures
    assert len([path for path,_ in calls if path=='/v1/chat/completions'])==2
    assert s.fn.coverage['drone_description']['evidence_ids']==[s.active_evidence()[-1]['id']]
    assert 'm9999' not in s.fn.coverage['drone_description']['evidence_ids']


def test_real_semantic_ambiguity_still_receives_one_relevant_followup(monkeypatch):
    def output(payload,_):
        result=reply(payload,coverage=[],action='clarify')
        result['message']='What do you mean by machine here?'
        return result
    install_http(monkeypatch,output)
    s=opening();s.send('It is a machine, but I am unsure which kind.',ChatClient())
    assert s.objective=='drone_description' and not s.failed_turn_id
    assert s.messages[-1]['text']=='What do you mean by machine here?'
    assert 'drone_description' not in s.fn.coverage


@pytest.mark.parametrize('kind,status',[('uncertain','unknown'),('declined','declined')])
def test_explicit_uncertainty_or_refusal_cannot_be_overridden_by_explored_annotation(monkeypatch,kind,status):
    def output(payload,_):
        result=reply(payload,kind=kind,status='explored')
        result['interpretation']['coverage'][0]['answer_kind']='substantive'
        return result
    install_http(monkeypatch,output)
    s=opening();s.send('I do not know how to describe it.',ChatClient())
    assert s.fn.coverage['drone_description']['status']==status
    assert s.fn.facts['drone_description']==kind
    assert s.objective=='drone_uses'
    assert s.annotations[-1]['answer_kind']==kind
    assert s.suggestion is None


def test_negative_examples_answer_records_no_knowledge_claim_or_numeric_readiness(monkeypatch):
    install_http(monkeypatch,lambda payload,_:reply(payload,
        kind='uncertain' if payload['fn']['evidence_goal']=='drone_description' else 'no',
        status='unknown' if payload['fn']['evidence_goal']=='drone_description' else 'explored'))
    s=opening();s.send('I do not know how to describe it.',ChatClient())
    s.send("I can't think of any examples.",ChatClient())
    assert s.fn.coverage['drone_uses']['status']=='explored' and s.fn.facts['drone_uses']=='no'
    assert s.annotations[-1]['goal_evidence'][0]['answer_kind']=='no'
    assert s.objective=='healthcare_awareness' and not s.concerns and s.suggestion is None


def test_model_goal_identifiers_do_not_become_participant_topics_and_wildlife_is_retained(monkeypatch):
    install_http(monkeypatch,lambda payload,_:reply(payload,kind='uncertain',status='unknown',
        topics=['drone_recognition','wildlife']))
    s=opening();s.send('I cannot define it, but I worry about wildlife.',ChatClient())
    assert [row['topic'] for row in s.concerns]==['wildlife']
    assert not s.priorities and not s.failures


def test_timeout_retry_keeps_original_answer_and_original_question(monkeypatch):
    s=opening()
    class Down:
        def turn(self,request):raise AssessmentError('Synthetic request timeout',code='timeout')
    s.send(DEFINITION,Down())
    original=s.failed_turn_id
    for text in ('retry',DEFINITION):
        s.send(text,Down())
        assert s.failed_turn_id==original and s.objective=='drone_description'
        assert 'drone_description' not in s.fn.coverage and not s.fn.unresolved_gaps
        assert 'reword' in s.messages[-1]['text'] and 'clarify' not in s.messages[-1]['text']
    requests=[]
    def output(payload,_):
        requests.append(payload)
        return reply(payload)
    install_http(monkeypatch,output)
    s.send('retry',ChatClient())
    assert s.objective=='drone_uses' and not s.failed_turn_id
    assert requests[0]['answer']==DEFINITION and requests[0]['current_answer_id']==original
    assert requests[0]['last_question']=='In your own words, what is a drone?'
    assert len([row for row in s.active_evidence() if row['text']==DEFINITION])==1


def test_changed_answer_after_failure_is_interpreted_against_actual_question(monkeypatch):
    s=opening()
    class Down:
        def turn(self,request):raise AssessmentError('Synthetic connection failure',code='transport')
    s.send(DEFINITION,Down())
    requests=[]
    def output(payload,_):requests.append(payload);return reply(payload)
    install_http(monkeypatch,output)
    s.send('It flies with no pilot on board.',ChatClient())
    assert requests[0]['last_question']=='In your own words, what is a drone?'
    assert s.objective=='drone_uses' and not s.failed_turn_id


@pytest.mark.parametrize('body',['not json',{'message':'What else?'}])
def test_repeated_malformed_output_never_advances_or_labels_respondent_uncertain(monkeypatch,body):
    calls=install_http(monkeypatch,lambda *_:body)
    s=opening();s.send(DEFINITION,ChatClient())
    assert s.objective=='drone_description' and s.failed_turn_id
    assert 'drone_description' not in s.fn.coverage and not s.fn.unresolved_gaps
    assert s.messages[-1]['act']=='failure' and s.failures[-1]['code'] in {'schema','evidence'}
    assert len([path for path,_ in calls if path=='/v1/chat/completions'])==2
    assert s.metrics[-1]['diagnostics'] and 'not json' not in json.dumps(s.metrics)


def test_unused_private_model_wording_is_still_screened(monkeypatch):
    def output(payload,_):
        result=reply(payload);result['message']='Alice Example attended a meeting.'
        return result
    install_http(monkeypatch,output)
    s=opening();s.send(DEFINITION,ChatClient())
    assert s.objective=='drone_description' and s.failed_turn_id
    assert 'Alice Example' not in json.dumps(s.export())
    assert 'drone_description' not in s.fn.coverage


def test_skip_after_technical_failure_cannot_retry_previous_goal(monkeypatch):
    install_http(monkeypatch,lambda *_:'not json')
    s=opening();s.send(DEFINITION,ChatClient());s.send('skip',ChatClient())
    assert s.objective=='drone_uses' and not s.failed_turn_id
    s.send('retry',ChatClient())
    assert s.objective=='drone_uses' and s.messages[-1]['act']=='recovery'


@pytest.mark.presidio_live
def test_real_privacy_allows_complete_fn_client_pipeline_for_clear_citizen_answers(monkeypatch):
    from iam_sra.privacy import detector
    detector()
    install_http(monkeypatch,lambda payload,_:reply(payload))
    s=opening();client=ChatClient()
    for answer in (DEFINITION,USES):s.send(answer,client)
    assert s.objective=='healthcare_awareness' and not s.failures
    assert all(metric['generation_calls']==1 for metric in s.metrics)


@pytest.mark.parametrize('container',[
    lambda value:{'user':{'current_answer_id':value}},
    lambda value:{'user':{'original_context':[{'id':value}]}},
    lambda value:{'interpretation':{'coverage':[{'evidence_id':value}]}},
    lambda value:{'coverage':[{'evidence_id':value}]},
    lambda value:{'choices':[{'message':{'content':json.dumps({'interpretation':{'coverage':[{'evidence_id':value}]}})}}]},
])
def test_generated_fn_ids_are_metadata_but_names_and_answer_text_remain_screened(monkeypatch,container):
    from iam_sra import privacy
    class FlagNames:
        def analyze(self,*,text,**kwargs):
            return [privacy.Finding('PERSON',0,len(text))] if text in {'m16','Alice Example'} else []
    monkeypatch.setattr(privacy,'detector',lambda:FlagNames())
    privacy.require_safe_data(container('m16'))
    with pytest.raises(privacy.PrivacyError):privacy.require_safe_data(container('Alice Example'))
    for value in ({'answer':'m16'},{'user':{'answer':'m16'}},{'quote':'m16'}):
        with pytest.raises(privacy.PrivacyError):privacy.require_safe_data(value)
