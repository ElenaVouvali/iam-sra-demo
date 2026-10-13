import json
import httpx
import pytest
from iam_sra.conversation_client import ConversationClient
from iam_sra.assessment import AssessmentError
from iam_sra.baseline import BaselineExtraction


def invoke(handler):
    c=ConversationClient();c._start()
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        result=c._request(http,'readiness_evidence','Return a supported object.',{'answer':'A synthetic answer.'},
            BaselineExtraction.model_json_schema(),lambda raw:BaselineExtraction.model_validate_json(raw))
    return c,result


def completion():return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"interaction":"substantive","claims":[]}'}}]})


def test_one_transient_connection_failure_is_retried_without_user_intervention():
    calls=[]
    def handler(req):
        calls.append(req.url.path)
        if len(calls)==1:raise httpx.ConnectError('Sensitive upstream detail',request=req)
        return httpx.Response(200,json={'count':10}) if req.url.path=='/tokenize' else completion()
    c,result=invoke(handler)
    assert calls==['/tokenize','/tokenize','/v1/chat/completions']
    assert 'Sensitive upstream detail' not in repr(c.last_diagnostics)


@pytest.mark.parametrize('status,code,attempts',[(400,'service_request',1),(429,'service_busy',1),(503,'transport',2)])
def test_http_rejections_are_classified_and_never_echo_response_bodies(status,code,attempts):
    calls=[]
    def handler(req):calls.append(req.url.path);return httpx.Response(status,json={'error':'My PIN is 1846'})
    with pytest.raises(AssessmentError) as error:invoke(handler)
    assert error.value.code==code and '1846' not in str(error.value)
    assert len(calls)==attempts


def test_timeout_is_distinct_from_connection_failure():
    def handler(req):raise httpx.ReadTimeout('Private response',request=req)
    with pytest.raises(AssessmentError) as error:invoke(handler)
    assert error.value.code=='timeout'


def test_malformed_completion_envelope_retries_instead_of_crashing_ui():
    generations=[]
    def handler(req):
        if req.url.path=='/tokenize':return httpx.Response(200,json={'count':10})
        generations.append(1)
        return httpx.Response(200,json={'choices':[]}) if len(generations)==1 else completion()
    c,result=invoke(handler)
    assert len(generations)==2 and result.claims==[]


def test_schema_errors_have_safe_field_diagnostics_and_bounded_retry():
    def handler(req):
        if req.url.path=='/tokenize':return httpx.Response(200,json={'count':10})
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"claims":[]}'}}]})
    c=ConversationClient();c._start()
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(AssessmentError):c._request(http,'readiness_evidence','Return JSON.',{'answer':'Synthetic.'},{},BaselineExtraction.model_validate_json)
    fields=[d['validation_fields'] for d in c.last_diagnostics if 'validation_fields' in d]
    assert fields[0][0]=={'location':['interaction'],'type':'missing'}
    assert c.last_metrics['generation_calls']==2
