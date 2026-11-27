"""Transport/controller tests only. These never claim live Qwen quality."""
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from iam_sra.assessment import AssessmentError
from iam_sra.baseline import BaselineExtraction
from iam_sra.chat_client import validate_reply
from iam_sra.conversation_client import ConversationClient
from fn_fixture import reply
from test_fn_interpretation import opening


def module(name):
    spec=importlib.util.spec_from_file_location('thinking_'+name,Path(__file__).parents[1]/'scripts'/name)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def request(monkeypatch, *, thinking=True, content='{"interaction":"substantive","claims":[]}',
            reason='Private generated draft alice@example.com',count=1000):
    monkeypatch.setenv('IAM_MODEL_THINKING','1' if thinking else '0')
    c=ConversationClient();c._start();sent=[]
    def endpoint(req):
        body=json.loads(req.content);sent.append((req.url.path,body))
        if req.url.path=='/tokenize':return httpx.Response(200,json={'count':count})
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop',
            'message':{'content':content,'reasoning_content':reason}}],'usage':{'completion_tokens':75}})
    with httpx.Client(transport=httpx.MockTransport(endpoint)) as http:
        try:
            result=c._request(http,'readiness_evidence','Return a supported object.',{'answer':'Synthetic evidence.'},
                BaselineExtraction.model_json_schema(),BaselineExtraction.model_validate_json)
        except AssessmentError as exc:return c,sent,exc
    return c,sent,result


def test_thinking_uses_separate_channel_budget_and_retains_no_private_draft(monkeypatch):
    c,sent,result=request(monkeypatch)
    assert result.claims==[] and c.last_metrics['reasoning_characters']>0
    assert c.last_settings['context_tokens']==8192 and c.last_settings['enable_thinking']
    payload=sent[-1][1]
    assert payload['max_tokens']==1600+1536 and payload['temperature']==.6 and payload['top_k']==20
    assert payload['chat_template_kwargs']=={'enable_thinking':True} and payload['guided_json']
    assert c.last_trace[-1]['raw_output'] is None and c.last_trace[-1]['reasoning_enabled']
    retained=json.dumps([c.last_settings,c.last_metrics,c.last_trace,c.last_diagnostics,c._accepted_wire])
    assert 'alice@example.com' not in retained and 'Private generated draft' not in retained


@pytest.mark.parametrize('enabled',[False,True])
def test_final_think_tags_cannot_be_treated_as_json(monkeypatch,enabled):
    c,_,error=request(monkeypatch,thinking=enabled,reason='A generated draft.',
        content='<think>draft</think>{"interaction":"substantive","claims":[]}')
    assert isinstance(error,AssessmentError) and error.code=='thinking'
    assert c.last_metrics['generation_calls']==2 and c._accepted_wire is None


def test_unexpected_reasoning_is_rejected_when_mode_disabled(monkeypatch):
    c,_,error=request(monkeypatch,thinking=False,reason='A generated draft.')
    assert error.code=='thinking' and c.last_metrics['generation_calls']==2


def test_final_private_content_is_still_blocked_with_thinking_enabled(monkeypatch):
    c,_,error=request(monkeypatch,content='{"interaction":"substantive","claims":[],"note":"alice@example.com"}')
    assert error.code=='privacy' and c._accepted_wire is None
    assert 'alice@example.com' not in json.dumps([c.last_trace,c.last_diagnostics])


def test_model_output_screening_keeps_only_bounded_source_span_metadata(monkeypatch):
    from iam_sra import llm_client, privacy
    screened=[]
    monkeypatch.setattr(privacy,'require_safe_data',lambda value:screened.append(value))
    answer='I do not know who makes that decision in my city. Could you explain?'
    content={'message':'What would you want to know?','interpretation':{
        'information_request':'clarify_current_question',
        'information_request_span':[57,74],'justification':'A short safe explanation is requested.'}}
    body={'choices':[{'message':{'content':json.dumps(content)}}]}
    original=json.loads(body['choices'][0]['message']['content'])
    llm_client._screen_generation_body(body,{'answer':answer},'chat_turn')
    copy=json.loads(screened[-1]['choices'][0]['message']['content'])
    assert copy['interpretation']['information_request_span']==[57,74]
    assert original['interpretation']['information_request_span']==[57,74]
    assert json.loads(body['choices'][0]['message']['content'])==original
    assert copy['interpretation']['justification']==original['interpretation']['justification']


def test_legacy_model_quote_copy_is_discarded_but_other_model_prose_is_screened(monkeypatch):
    from iam_sra import llm_client, privacy
    screened=[]
    monkeypatch.setattr(privacy,'require_safe_data',lambda value:screened.append(value))
    content={'message':'Could you tell me more?','interpretation':{
        'information_request':'drone_definition','information_request_span':[99,400]}}
    body={'choices':[{'message':{'content':json.dumps(content)}}]}
    llm_client._screen_generation_body(body,{'answer':'No, I do not know.'},'chat_turn')
    copy=json.loads(screened[-1]['choices'][0]['message']['content'])
    assert 'information_request_quote' not in copy['interpretation']
    assert copy['message']=='Could you tell me more?'


def test_thinking_context_overflow_keeps_originals_and_does_not_generate(monkeypatch):
    c,sent,error=request(monkeypatch,count=7000)
    assert error.code=='budget' and [p for p,_ in sent]==['/tokenize']
    assert c.last_diagnostics[-1]['context_tokens']==8192


def test_long_exact_quotes_and_bad_optional_topics_do_not_reject_clear_answer():
    s=opening()
    answer=('My role is to assess the thermal performance and mounting interface of a reusable '
        'temperature-controlled sample container intended for integration with a healthcare drone. '
        'I focus on component-level testing, not the aircraft or complete delivery system.')
    req=s._request(answer);req['current_answer_id']='m99'
    out=reply(req);out['interpretation']['answer_quote']=answer
    out['interpretation']['coverage'][0]['quote']=answer
    out['interpretation']['topics']=[{'topic':'unsupported optional label','quote':42}]
    out['decision_summary']='The response describes component work and its limits.'
    result=validate_reply(out,req)
    assert result['interpretation']['answer_quote']==answer and len(answer)>240
    assert result['interpretation']['topics']==[] and not result['_quality_issues']
    assert result['justification']==out['decision_summary']
    assert 'interpretation.topics.0' in result['_annotation_warnings']


def test_core_schema_errors_have_safe_precise_locations():
    s=opening();req=s._request('A simple description.');req['current_answer_id']='m99'
    out=reply(req);out['interpretation']['action']={'alice@example.com':'invalid'}
    with pytest.raises(AssessmentError) as exc:validate_reply(out,req)
    assert exc.value.field=='interpretation.action'
    assert exc.value.validation_fields[0]['location']==['interpretation','action']
    assert 'alice@example.com' not in str(exc.value.validation_fields)


@pytest.mark.presidio_live
def test_extended_agent_answer_with_real_corpus_privacy_reaches_next_question(monkeypatch):
    from iam_sra.chat_session import ChatSession
    from iam_sra.chat_client import ChatClient
    from iam_sra.conversation_corpus import load_corpus
    from indicator_fixtures import bank
    from test_fn_interpretation import install_http
    install_http(monkeypatch,lambda payload,_:reply(payload,
        kind='yes' if payload['fn']['evidence_goal']=='drone_recognition' else 'substantive'))
    s=ChatSession(bank(),synthetic=True,corpus=load_corpus());client=ChatClient()
    for answer in ('A','Coimbra','B',
        'Yes. A drone is an aircraft without an onboard pilot. I have seen photography and delivery uses.',
        "A drone is an aircraft without an onboard pilot. I've seen them used for photography and deliveries, including healthcare services."):
        s.send(answer,client)
    assert s.objective=='drone_uses' and not s.failed_turn_id and not s.failures
    assert s.context['city']=='Coimbra' and s.metrics[-1]['generation_calls']==1


@pytest.mark.parametrize('variant,product,cap,memory',[
    ('awq','NVIDIA A2','8.6','15360'),('fp16','NVIDIA A30','8.0','24576')])
def test_thinking_launch_uses_existing_v0_reasoner_and_no_offload(monkeypatch,tmp_path,variant,product,cap,memory):
    ops=module('ops.py');model=ops.load_model(ops.ROOT,variant)
    filename='model-awq.json' if variant=='awq' else 'model.json'
    (tmp_path/'configs').mkdir();(tmp_path/'configs'/filename).write_text(json.dumps(model))
    snapshot=ops.snapshot_path(tmp_path,model);snapshot.mkdir(parents=True)
    (snapshot/'model.safetensors').touch()
    monkeypatch.setattr(ops,'ROOT',tmp_path)
    monkeypatch.setattr(ops,'validate_awq_snapshot',lambda p:p)
    monkeypatch.setenv('IAM_MODEL_VARIANT',variant);monkeypatch.setenv('IAM_MODEL_THINKING','1')
    monkeypatch.delenv('IAM_CPU_OFFLOAD_GB',raising=False)
    cmd=ops.vllm_command(['0','GPU-fixture',product,cap,memory])
    assert cmd[cmd.index('--max-model-len')+1]=='8192'
    assert '--enable-reasoning' in cmd and cmd[cmd.index('--reasoning-parser')+1]=='deepseek_r1'
    assert float(cmd[cmd.index('--cpu-offload-gb')+1])==0


def good_report(thinking=False):
    row={'backend':'vllm','controlled_api_fixture':False,'respondent_backend':'existing_qwen_synthetic-1.2.0',
        'scope':'full_interview','protocol_passed':True,'generation_calls':5,'agent_generation_calls':3,
        'scoring_generation_calls':1,'score_status':'suggested','level':4,'score_citation_count':1,
        'score_boundary_present':True,'model_suggestion_unchanged_after_review':True,
        'json_export_succeeded':True,'jsonl_export_succeeded':True,'markdown_export_succeeded':True,
        'thinking_enabled':thinking,'reasoning_characters':30 if thinking else 0}
    return {'live_inference':'executed','respondent':'agent','cases':[
        dict(row,case=k) for k in ('citizen_short','citizen_extended','organisational','technical')]}


@pytest.mark.parametrize('fault',[None,'fixture','no_score_calls','unavailable','no_reasoning','missing_role','changed_score'])
def test_publication_gate_requires_real_calls_scoring_and_review(fault):
    m=module('smoke-fn-interview.py');r=good_report(True)
    if fault=='fixture':r['cases'][0]['controlled_api_fixture']=True
    if fault=='no_score_calls':r['cases'][0]['scoring_generation_calls']=0
    if fault=='unavailable':r['cases'][0]['level']=None;r['cases'][0]['score_status']='unavailable'
    if fault=='no_reasoning':r['cases'][0]['reasoning_characters']=0
    if fault=='missing_role':r['cases'].pop()
    if fault=='changed_score':r['cases'][0]['model_suggestion_unchanged_after_review']=False
    assert bool(m.live_scoring_failures(r,thinking=True))==(fault is not None)


def test_honest_model_abstention_is_allowed_only_after_actual_scoring_call():
    m=module('smoke-fn-interview.py');r=good_report()
    r['cases'][0].update(level=None,score_status='abstained',score_citation_count=0,score_boundary_present=False)
    assert not m.live_scoring_failures(r)
    r['cases'][0]['scoring_generation_calls']=0
    assert m.live_scoring_failures(r)


def test_larger_scoring_budget_supplies_every_original_instead_of_char_count_abstention(monkeypatch):
    from test_fn_interview import replay
    monkeypatch.setenv('IAM_MODEL_THINKING','1')
    s,_,scorer,_=replay('citizen_extended')
    # Additional screened synthetic evidence makes the old character guard
    # observable. The fixture scorer proves payload preservation, not a level.
    for _ in range(2):
        s._user('I can compare delivery alternatives and ask for evidence about their effects. '*15)
    scorer.calls.clear();s._report(score_client=scorer)
    assert len(scorer.calls)==1
    originals=scorer.calls[0]['originals']
    assert sum(len(m['text']) for m in originals)>5000
    assert [m['id'] for m in originals]==[m['id'] for m in s.active_evidence()]


@pytest.mark.parametrize('valid',[False,True])
def test_sharing_launcher_checks_live_report_before_public_services(monkeypatch,tmp_path,valid):
    from types import SimpleNamespace
    m=module('share-fn-review.py');monkeypatch.setattr(m,'STATE',tmp_path)
    class Backend:
        stopped=False
        def start(self,deadline):pass
        def _marker(self):return {'lease_id':'private-test-lease'}
        def owns_running_model(self):return True
        def stop(self):self.stopped=True;return True
    backend=Backend();calls=[]
    def popen(command,**kw):
        calls.append((command,kw['env']))
        assert '--require-scoring' in command and '--thinking' in command
        output=Path(command[command.index('--output')+1]);output.mkdir()
        report=good_report(True)
        if not valid:report['cases'][0]['controlled_api_fixture']=True
        (output/'metrics.json').write_text(json.dumps(report))
        return SimpleNamespace(wait=lambda **k:0,poll=lambda:0)
    monkeypatch.setattr(m.subprocess,'Popen',popen)
    args=SimpleNamespace(model_port=18003,model_variant='awq',thinking=True)
    if valid:assert m.verify_live_interviews(backend,args,[]).is_dir()
    else:
        with pytest.raises(ValueError,match='failed publication checks'):m.verify_live_interviews(backend,args,[])
    assert backend.stopped and len(calls)==1
    assert calls[0][1]['IAM_SRA_ON_DEMAND_GPU']=='0'
    assert calls[0][1]['IAM_SRA_VALIDATION_LEASE']=='private-test-lease'


@pytest.mark.parametrize('origin,valid',[
    ('https://iam-sra.example.org',True),('http://iam-sra.example.org',False),
    ('https://name:password@example.org',False),('https://example.org/path',False),
])
def test_administrator_proxy_origin_is_explicit(origin,valid):
    import argparse
    m=module('share-fn-review.py')
    if valid:assert m.public_origin(origin)==origin
    else:
        with pytest.raises(argparse.ArgumentTypeError):m.public_origin(origin)
