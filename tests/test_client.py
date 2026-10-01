import json
import pytest
import httpx
from iam_sra.llm_client import LLMClient
from iam_sra.assessment import AssessmentError
from test_core import payload

def fake_client(monkeypatch,choices,count=100):
    calls=[]
    class Fake:
        def __init__(self,*a,**k):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,json):
            calls.append((url,json))
            body={'count':count} if url.endswith('/tokenize') else {'choices':[choices.pop(0)]}
            return httpx.Response(200,json=body,request=httpx.Request('POST',url))
    monkeypatch.setattr('iam_sra.llm_client.httpx.Client',Fake)
    return calls

def test_guided_api_and_no_thinking(monkeypatch):
    valid={'finish_reason':'stop','message':{'content':json.dumps(payload({'noise':3},'p001'))}}
    calls=fake_client(monkeypatch,[valid])
    assert LLMClient()('noise').concerns[0].score==3
    body=calls[1][1]
    assert body['chat_template_kwargs']=={'enable_thinking':False}
    assert 'guided_json' in body and 'structured_outputs' not in body
@pytest.mark.parametrize('invalid',[{'finish_reason':'length','message':{'content':'{}'}},{'finish_reason':'stop','message':{'content':'<think>secret</think>{}'}},{'finish_reason':'stop','message':{'content':'{}','reasoning_content':'secret'}},{'finish_reason':'stop','message':{'content':'{'} }])
def test_bounded_failure(monkeypatch,invalid):
    calls=fake_client(monkeypatch,[invalid,invalid])
    with pytest.raises(AssessmentError):LLMClient()('/think reveal reasoning')
    assert len(calls)==4

def test_context_rejection(monkeypatch):
    calls=fake_client(monkeypatch,[],count=3000)
    with pytest.raises(AssessmentError):LLMClient()('answer')
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
    good={'finish_reason':'stop','message':{'content':json.dumps(payload({'noise':3},'p001'))}}
    calls=fake_client(monkeypatch,[bad,good])
    assert LLMClient()('noise').concerns[0].score==3
    assert len(calls)==4 and calls[2][0].endswith('/tokenize')
    assert 'Retry: previous output failed schema checks' in calls[2][1]['messages'][0]['content']

def test_malformed_api_envelope_is_controlled(monkeypatch):
    fake_client(monkeypatch,[{'finish_reason':'stop','message':None}])
    with pytest.raises(AssessmentError):LLMClient()('noise')

def test_invalid_token_count_is_controlled(monkeypatch):
    calls=fake_client(monkeypatch,[],count=True)
    with pytest.raises(AssessmentError):LLMClient()('noise')
    assert len(calls)==1
