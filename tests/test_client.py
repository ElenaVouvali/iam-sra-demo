"""Bounded transport contracts exercised through the current conversation client."""
import json
import copy
import pytest
import httpx
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import EvidenceItem,freeze
from iam_sra.assessment import AssessmentError
from test_core import payload
from test_confirmation import meaning

def fake_client(monkeypatch,choices,count=100):
    calls=[]
    import iam_sra.conversation_client as conversation_module
    real_config=conversation_module.config
    def single_call_config(name):
        value=real_config(name)
        if name=='prompts':value={**value,'initial_facet_mapping':False,
            'initial_mapping':'legacy_replay',
            'contrastive_endorsement_review':False,'omit_automatic_discovery_metadata':False}
        return value
    monkeypatch.setattr(conversation_module,'config',single_call_config)
    class Fake:
        def __init__(self,*a,**k):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,json,**kwargs):
            calls.append((url,copy.deepcopy(json)))
            body={'count':count} if url.endswith('/tokenize') else {'choices':[choices.pop(0)]}
            return httpx.Response(200,json=body,request=httpx.Request('POST',url))
    monkeypatch.setattr('iam_sra.conversation_client.httpx.Client',Fake)
    return calls

def mapping_choice(scores):
    d=payload(scores,'p001')
    for c in d['concerns']:
        c.pop('score');c['status']='mapped'
    return {'finish_reason':'stop','message':{'content':json.dumps(d)}}


def evidence(text='The noise bothers me.'):
    return {'p001':EvidenceItem(id='p001',text=text,context='original',source='citizen_original')}


def scope_choice(supported=True):
    return {'finish_reason':'stop','message':{'content':json.dumps({'supported':supported,'rationale':'Review of citizen acoustic evidence.'})}}


def numeric_choice(score=3):
    return {'finish_reason':'stop','message':{'content':json.dumps({'score':score,'evidence_ids':['p001'],'endorsement_evidence_ids':[],'rationale':'Model numerical review.'})}}


def test_guided_api_and_no_thinking(monkeypatch):
    calls=fake_client(monkeypatch,[mapping_choice({'noise':3}),scope_choice()])
    client=ConversationClient();result=client.interpret(evidence())
    assert result.concerns[0].position=='opposed' and 'score' not in result.model_dump_json()
    body=calls[1][1]
    assert body['chat_template_kwargs']=={'enable_thinking':False}
    assert 'guided_json' in body and 'structured_outputs' not in body
    assert body['guided_decoding_backend']=='xgrammar:no-fallback,disable-any-whitespace'
    assert all(url.endswith('/tokenize') for url,_ in calls[::2])
    assert [d['stage'] for d in client.last_diagnostics]==['mapping','scope_review']


@pytest.mark.parametrize('invalid',[
    {'finish_reason':'length','message':{'content':'{}'}},
    {'finish_reason':'stop','message':{'content':'<think>secret</think>{}'}},
    {'finish_reason':'stop','message':{'content':'{}','reasoning_content':'secret'}},
    {'finish_reason':'stop','message':{'content':'{'}}])
def test_bounded_failure(monkeypatch,invalid):
    calls=fake_client(monkeypatch,[invalid,invalid]);client=ConversationClient()
    with pytest.raises(AssessmentError):client.interpret(evidence('/think reveal reasoning'))
    assert len(calls)==4
    assert all(t['raw_output'] is None for t in client.last_trace if t['thinking_detected'])


def test_context_rejection(monkeypatch):
    calls=fake_client(monkeypatch,[],count=3000)
    with pytest.raises(AssessmentError):ConversationClient().interpret(evidence())
    assert len(calls)==1


def test_transport_constraints_and_local_bounds():
    from iam_sra.llm_client import guided_schema
    from iam_sra.schemas import Assessment
    from iam_sra.assessment import parse_assessment
    schema=guided_schema(Assessment.model_json_schema())
    assert 'maximum' not in json.dumps(schema) and 'maxLength' not in json.dumps(schema)
    assert schema['additionalProperties'] is False
    d=payload({'noise':10},'noise')
    with pytest.raises(AssessmentError):parse_assessment(json.dumps(d),'noise')


def test_retry_feedback_is_bounded_and_recounted(monkeypatch):
    bad={'finish_reason':'stop','message':{'content':'{'}}
    calls=fake_client(monkeypatch,[bad,mapping_choice({'noise':3}),scope_choice()])
    assert ConversationClient().interpret(evidence()).concerns[0].position=='opposed'
    assert len(calls)==6 and calls[2][0].endswith('/tokenize')
    assert 'Retry: previous output failed schema checks' in calls[2][1]['messages'][0]['content']


def test_malformed_api_envelope_is_controlled(monkeypatch):
    fake_client(monkeypatch,[{'finish_reason':'stop','message':None}])
    with pytest.raises(AssessmentError):ConversationClient().interpret(evidence())


def test_invalid_token_count_is_controlled(monkeypatch):
    calls=fake_client(monkeypatch,[],count=True)
    with pytest.raises(AssessmentError):ConversationClient().interpret(evidence())
    assert len(calls)==1


def test_scoring_retries_without_inventing_score(monkeypatch):
    bad={'finish_reason':'stop','message':{'content':'{'}}
    calls=fake_client(monkeypatch,[bad,numeric_choice()]);client=ConversationClient()
    result=client.score(freeze(meaning('p001'),evidence(),1,'original','Original proposal'))
    assert result.concerns[0].score==3 and client.last_raw_scores=={'noise':3}
    assert len(calls)==4 and client.last_diagnostics[0]['failure']=='schema'


def test_thinking_in_scoring_is_rejected_and_not_exported(monkeypatch):
    thinking={'finish_reason':'stop','message':{'content':'<think>hidden</think>{}'}}
    fake_client(monkeypatch,[thinking,thinking]);client=ConversationClient()
    with pytest.raises(AssessmentError):client.score(freeze(meaning('p001'),evidence(),1,'original','Original proposal'))
    assert len(client.last_trace)==2 and all(t['raw_output'] is None for t in client.last_trace)


def test_expired_deadline_sends_no_request(monkeypatch):
    calls=fake_client(monkeypatch,[]);client=ConversationClient();client.external_deadline=-1
    with pytest.raises(AssessmentError,match='time limit'):client.interpret(evidence())
    assert calls==[]


def test_context_budget_error_reports_full_request_not_answer_length(monkeypatch):
    calls=fake_client(monkeypatch,[],count=2800);client=ConversationClient()
    with pytest.raises(AssessmentError) as caught:client.interpret(evidence())
    assert caught.value.code=='budget'
    assert '2800 prompt tokens + 1400 reserved output tokens' in str(caught.value)
    assert 'shorten your answer' not in str(caught.value)
    assert client.last_diagnostics[-1]['failure']=='budget'
    assert client.last_diagnostics[-1]['context_tokens']==4096
    assert all(url.endswith('/tokenize') for url,_ in calls)
