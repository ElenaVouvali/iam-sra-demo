import json
import copy
import pytest
import httpx
from iam_sra.llm_client import LLMClient
from iam_sra.assessment import AssessmentError
from test_core import payload
from iam_sra.settings import CONCERNS

def fake_client(monkeypatch,choices,count=100):
    calls=[]
    class Fake:
        def __init__(self,*a,**k):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,json,**kwargs):
            calls.append((url,copy.deepcopy(json)))
            body={'count':count} if url.endswith('/tokenize') else {'choices':[choices.pop(0)]}
            return httpx.Response(200,json=body,request=httpx.Request('POST',url))
    monkeypatch.setattr('iam_sra.llm_client.httpx.Client',Fake)
    return calls

def mapping_choice(scores):
    d=payload(scores,'p001')
    for c in d['concerns']:
        c.pop('score');c['status']='mapped'
    return {'finish_reason':'stop','message':{'content':json.dumps(d)}}

def score_choice(scores):
    d={'concern_scores':[{'concern_id':cid,'scope_supported':score is not None,'position':'opposed' if score is not None else 'unassessed','facets':[CONCERNS[cid]['facets'][0]] if score is not None else [],'excerpts':['p001'] if score is not None else [],'status':'assessed' if score is not None else 'unassessed','decision':'retained' if score is not None else 'excluded','score':score,'rationale':'Provisional evidence anchor.'} for cid,score in scores.items()]}
    return {'finish_reason':'stop','message':{'content':json.dumps(d)}}

def test_guided_api_and_no_thinking(monkeypatch):
    calls=fake_client(monkeypatch,[mapping_choice({'noise':3}),score_choice({'noise':3})])
    assert LLMClient()('noise').concerns[0].score==3
    body=calls[1][1]
    assert body['chat_template_kwargs']=={'enable_thinking':False}
    assert 'guided_json' in body and 'structured_outputs' not in body
    retained,excluded=calls[3][1]['guided_json']['$defs']['ScoreDecision']['oneOf']
    review=retained['properties']['excerpts']
    assert review=={'type':'array','enum':[['p001']]}
    assert retained['properties']['scope_supported']['const'] is True
    assert retained['properties']['score']['enum']==list(range(1,10))
    assert excluded['properties']['score']['const'] is None
    facets=retained['properties']['facets']['enum']
    assert all(len(fs)==len(set(fs)) and len(fs)<=2 for fs in facets)
    assert [CONCERNS['noise']['facets'][0]] in facets
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
    calls=fake_client(monkeypatch,[bad,mapping_choice({'noise':3}),score_choice({'noise':3})])
    assert LLMClient()('noise').concerns[0].score==3
    assert len(calls)==6 and calls[2][0].endswith('/tokenize')
    assert 'Retry: previous output failed schema checks' in calls[2][1]['messages'][0]['content']

def test_malformed_api_envelope_is_controlled(monkeypatch):
    fake_client(monkeypatch,[{'finish_reason':'stop','message':None}])
    with pytest.raises(AssessmentError):LLMClient()('noise')

def test_invalid_token_count_is_controlled(monkeypatch):
    calls=fake_client(monkeypatch,[],count=True)
    with pytest.raises(AssessmentError):LLMClient()('noise')
    assert len(calls)==1


def test_scoring_can_exclude_unsupported_mapping_without_score_substitution(monkeypatch):
    fake_client(monkeypatch,[mapping_choice({'visual_pollution':4}),score_choice({'visual_pollution':None})])
    client=LLMClient();result=client('Low altitude alone.')
    concern=result.concerns[0]
    assert concern.status=='unassessed' and concern.score is None
    assert client.last_raw_scores=={'visual_pollution':None}
    assert len(client.last_trace)==2

def test_scoring_requires_every_candidate_once(monkeypatch):
    fake_client(monkeypatch,[mapping_choice({'noise':3}),score_choice({}),score_choice({})])
    with pytest.raises(AssessmentError):LLMClient()('noise')

def test_score_review_retries_without_inventing_score(monkeypatch):
    invalid={'finish_reason':'stop','message':{'content':'{'}}
    calls=fake_client(monkeypatch,[mapping_choice({'noise':3}),invalid,score_choice({'noise':3})])
    client=LLMClient();assert client('noise').concerns[0].score==3
    assert len(calls)==6 and client.last_diagnostics[1]['stage']=='scoring'
    assert client.last_diagnostics[1]['failure']=='schema'

def test_empty_mapping_does_not_call_scorer(monkeypatch):
    calls=fake_client(monkeypatch,[mapping_choice({})]);client=LLMClient()
    assert all(c.score is None for c in client('I am unsure.').concerns)
    assert len(calls)==2 and client.last_raw_scores=={}

def test_thinking_in_second_stage_is_rejected_and_not_exported(monkeypatch):
    thinking={'finish_reason':'stop','message':{'content':'<think>hidden</think>{}'}}
    fake_client(monkeypatch,[mapping_choice({'noise':3}),thinking,thinking]);client=LLMClient()
    with pytest.raises(AssessmentError):client('noise')
    assert all(t['raw_output'] is None for t in client.last_trace if t['stage']=='scoring')


def test_scope_support_is_required_before_numeric_anchor(monkeypatch):
    invalid=score_choice({'noise':3})
    data=json.loads(invalid['message']['content']);data['concern_scores'][0]['scope_supported']=False
    invalid['message']['content']=json.dumps(data)
    fake_client(monkeypatch,[mapping_choice({'noise':3}),invalid,invalid]);client=LLMClient()
    with pytest.raises(AssessmentError):client('noise')
    assert client.last_raw_scores=={}

def test_separate_review_for_each_assessed_concern(monkeypatch):
    calls=fake_client(monkeypatch,[mapping_choice({'noise':3,'perceived_safety_privacy':2}),score_choice({'noise':3}),score_choice({'perceived_safety_privacy':2})])
    client=LLMClient();a=client('Noise and cameras worry me.')
    assert len(calls)==6 and client.last_raw_scores=={'noise':3,'perceived_safety_privacy':2}
    assert [c.score for c in a.concerns if c.status=='assessed']==[3,2]

def test_expired_assessment_deadline_sends_no_request(monkeypatch):
    times=iter([0,181]);monkeypatch.setattr('iam_sra.llm_client.time.monotonic',lambda:next(times))
    calls=fake_client(monkeypatch,[])
    with pytest.raises(AssessmentError,match='time limit'):LLMClient()('Noise bothers me.')
    assert calls==[]


def test_medical_facet_nomination_is_general_and_never_canned_score(monkeypatch):
    mapped=mapping_choice({'noise':3});data=json.loads(mapped['message']['content'])
    data['medical_public_benefit_support']['interpretation']='supported'
    mapped['message']['content']=json.dumps(data)
    calls=fake_client(monkeypatch,[mapped,score_choice({'noise':3}),score_choice({'welfare_equity':5})]);client=LLMClient()
    a=client('I support hospital public services but object to buzzing.')
    assert client.last_raw_scores=={'noise':3,'welfare_equity':5}
    assert next(c for c in a.concerns if c.concern_id=='welfare_equity').score==5
    assert client.last_candidate_projections[0]['score_assigned'] is False
    assert len(calls)==6


def test_explicit_conditions_are_reviewed_even_if_mapper_unclear(monkeypatch):
    mapped=mapping_choice({'noise':3});data=json.loads(mapped['message']['content'])
    data['concerns'][0].update(status='needs_clarification',position='uncertain',excerpts=[],conditions=['p001'],conditional_willingness='willing')
    mapped['message']['content']=json.dumps(data)
    score=score_choice({'noise':4})
    row=json.loads(score['message']['content']);row['concern_scores'][0].update(position='uncertain',conditions=['p001'],conditional_willingness='willing')
    score['message']['content']=json.dumps(row)
    fake_client(monkeypatch,[mapped,score]);result=LLMClient()('I would accept quieter flights.')
    assert result.concerns[0].score==4 and result.concerns[0].position=='uncertain'

def test_independent_review_does_not_inherit_mapping_annotations(monkeypatch):
    mapped=mapping_choice({'noise':3});data=json.loads(mapped['message']['content'])
    data['concerns'][0].update(position='supported',conditional_willingness='willing',conditions=['p001'])
    mapped['message']['content']=json.dumps(data)
    calls=fake_client(monkeypatch,[mapped,score_choice({'noise':3})])
    LLMClient()('The hum is intolerable.')
    review=json.loads(calls[3][1]['messages'][1]['content'])
    assert review['citizen_passages']==[{'id':'p001','text':'The hum is intolerable.'}]
    assert review['requested_concern_id']=='noise'
    assert set(review)=={'citizen_passages','requested_concern_id'}
