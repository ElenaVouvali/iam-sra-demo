"""Synthetic agent contracts and owned API journeys; never live Qwen validation."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil

import httpx
import pytest

from iam_sra.assessment import AssessmentError
from iam_sra.synthetic_respondent import LLMRespondent

ROOT=Path(__file__).resolve().parents[1]


def runner():
    spec=importlib.util.spec_from_file_location('fn_agent_harness',ROOT/'scripts/smoke-fn-interview.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_four_distinct_personas_have_no_target_levels():
    personas=runner().load_agent_personas(ROOT)
    assert set(personas)=={'citizen_short','citizen_extended','organisational','technical'}
    assert all(p['synthetic'] and not any(k in p for k in ('target_level','expected_level','score')) for p in personas.values())
    assert 'component' in personas['technical']['background'] or 'container' in personas['technical']['background']


def test_respondent_sees_visible_question_and_recent_dialogue_only():
    class Respondent:
        def respond(self,question,history):
            self.question=question;self.history=history
            return {'text':'A','control':'answer'}
    r=Respondent()
    chat={'messages':[{'role':'assistant','text':str(i),'objective_id':'hidden_goal'} for i in range(10)],
          'response_options':[{'value':'A','label':'Continue'}],
          'objective_coverage':['hidden_coverage'],'suggestion':{'level':9},'scope':{'secret':'not visible'}}
    assert runner().agent_reply(r,chat)=='A'
    assert r.question=={'question_text':'9','response_options':chat['response_options']}
    assert len(r.history)==6 and all(set(m)=={'role','text'} for m in r.history)
    assert 'hidden' not in json.dumps([r.question,r.history])


@pytest.mark.parametrize('control,expected',[('skip','skip this question'),('unsure','I do not know.'),('decline','prefer not to answer')])
def test_agent_controls_use_existing_screened_chat_actions(control,expected):
    class Respondent:
        def respond(self,*a):return {'text':'','control':control}
    assert runner().agent_reply(Respondent(),{'messages':[{'role':'assistant','text':'A question?'}]})==expected


def test_qualified_uncertainty_is_preserved_instead_of_replaced():
    text='I have heard about a pilot, but I do not know if it operates routinely.'
    class Respondent:
        def respond(self,*a):return {'text':text,'control':'unsure'}
    assert runner().agent_reply(Respondent(),{'messages':[{'role':'assistant','text':'What do you know?'}]})==text


@pytest.mark.parametrize('control',['answer','unsure','skip','decline'])
def test_simulator_text_is_not_replaced_by_a_contradictory_control_hint(control):
    text='I have no further concerns to add.'
    class Respondent:
        def respond(self,*a):return {'text':text,'control':control}
    assert runner().agent_reply(Respondent(),{'messages':[{'role':'assistant','text':'Anything else?'}]})==text


@pytest.mark.parametrize('answer,valid',[('B',True),('Maybe B',False)])
@pytest.mark.parametrize('soft_no_think',[False,True])
def test_llm_respondent_handles_real_choice_contract_without_hidden_criteria(monkeypatch,answer,valid,soft_no_think):
    persona=runner().load_agent_personas(ROOT)['citizen_short'];requests=[]
    original=httpx.Client
    def endpoint(req):
        if req.url.path=='/tokenize':return httpx.Response(200,json={'count':800})
        payload=json.loads(req.content);requests.append(json.loads(payload['messages'][-1]['content']))
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'text':answer,'control':'answer'})}}],
            'usage':{'completion_tokens':12}})
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(endpoint),**kw))
    respondent=LLMRespondent(persona,soft_no_think=soft_no_think)
    question={'question_text':'Choose a perspective.','response_options':[{'value':'A','label':'Citizen'},{'value':'B','label':'Organisation'}]}
    if valid:
        assert respondent.respond(question)['text']=='B'
        assert respondent.last_metrics['generation_calls']==1
    else:
        with pytest.raises(AssessmentError,match='displayed option'):respondent.respond(question)
        assert not respondent.turns
    profile=requests[0]['synthetic_persona']
    assert profile['city']=='Madrid' and profile['perspective']=='personal'
    assert not {'expected_observations','prohibited_inferences','score','anchors','fn_case'} & profile.keys()
    assert respondent.last_settings['synthetic_respondent_soft_no_think']==soft_no_think


def test_an_active_public_review_is_not_interrupted_or_adopted(monkeypatch,tmp_path):
    monkeypatch.setenv('IAM_SRA_ON_DEMAND_GPU','0')
    lock=tmp_path/'.runtime/fn-review/share.lock';lock.parent.mkdir(parents=True);lock.touch()
    with lock.open('r') as held:
        fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(ValueError,match='Stop the FN sharing launcher'):runner().require_unmanaged_endpoint(tmp_path)
    runner().require_unmanaged_endpoint(tmp_path)


@pytest.mark.parametrize('arguments',[
    ['--respondent','agent','--opening-only'],
    ['--respondent','agent','--backend','cpu'],
    ['--max-agent-calls','0'],['--max-turns','10000'],['--case-timeout-seconds','0'],
])
def test_invalid_or_unbounded_agent_runs_are_rejected(arguments):
    with pytest.raises(SystemExit) as exc:runner().main(['--allow-live','--output','.runtime/unused-agent-test',*arguments])
    assert exc.value.code==2


def prepare_runner(monkeypatch,tmp_path):
    module=runner();(tmp_path/'eval').mkdir()
    for name in ('fn_agent_personas_v1.json','fn_golden_paths.json','fn_interpretation_cases.json'):
        shutil.copyfile(ROOT/'eval'/name,tmp_path/'eval'/name)
    module.__file__=str(tmp_path/'scripts/smoke-fn-interview.py')
    monkeypatch.setenv('IAM_SRA_ON_DEMAND_GPU','0')
    for key,default in [('IAM_MODEL_VARIANT','fp16'),('IAM_BASE_URL','http://127.0.0.1:18000'),('IAM_CHAT_SYNTHETIC_REHEARSAL','0')]:
        monkeypatch.setenv(key,os.getenv(key,default))
    original=httpx.Client
    from iam_sra.settings import MODEL
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(
        lambda req:httpx.Response(200,json={'data':[{'id':MODEL}]})),**kw))
    return module


def fixture_api(monkeypatch):
    import iam_sra.api
    from iam_sra.api.adapter import ControllerAdapter
    from iam_sra.api.service import AssessmentService
    from iam_sra.fn_interview import flow_key
    from test_fn_interview import GoldenInterpreter
    from fn_fixture import ScoreFixture
    from test_indicator_api import factory
    adapter=ControllerAdapter(engine_factory=factory,readiness=lambda:{'privacy':'synthetic','corpus':'synthetic'},
        clients_factory=lambda e:{'chat':GoldenInterpreter(flow_key(e.chat.profile or 'citizen',e.chat.depth)),
                                 'chat_score':ScoreFixture()})
    service=AssessmentService(adapter)
    app=iam_sra.api.create_app({'TESTING':True,'SECRET_KEY':'f'*40},service=service)
    monkeypatch.setattr(iam_sra.api,'create_app',lambda *a,**kw:app)
    return service


class ReferenceRespondentFixture:
    """This double replays golden answers, not the new persona's semantics."""
    backend='controlled_reference_fixture'
    def __init__(self,persona,**kw):
        from test_fn_interview import GOLDEN
        self.rows=GOLDEN[persona['fn_case']];self.last_metrics={};self.used_rows=set()
    def respond(self,question,history):
        match=next(((index,row) for index,row in enumerate(self.rows)
                    if index not in self.used_rows and row['question'] in question['question_text']),None)
        if match is None:raise AssertionError('No unused reference answer matches the visible canonical question.')
        index,row=match;self.used_rows.add(index);text=row['answer']
        self.last_metrics={'generation_calls':1,'generated_tokens':30,'generation_http_seconds':.1}
        return {'text':text,'control':'answer'}


def test_reference_respondent_fixture_consumes_repeated_canonical_questions_in_order():
    respondent=ReferenceRespondentFixture({'fn_case':'citizen_short'})
    first=respondent.respond({'question_text':'Why?'},[])
    second=respondent.respond({'question_text':'Why?'},[])
    assert first['text'].startswith('Because the extra travel time')
    assert second['text'].startswith('I understand why they might be useful')


@pytest.mark.presidio_live
def test_controlled_citizen_short_agent_api_reaches_result_review(monkeypatch,tmp_path):
    module=prepare_runner(monkeypatch,tmp_path);service=fixture_api(monkeypatch)
    monkeypatch.setattr('iam_sra.synthetic_respondent.LLMRespondent',ReferenceRespondentFixture)
    output=tmp_path/'.runtime/agent'
    try:code=module.main(['--allow-live','--respondent','agent','--case','citizen_short','--output',str(output)])
    finally:service.close()
    report=json.loads((output/'metrics.json').read_text());row=report['cases'][0]
    assert code==0 and row['stage']=='ended' and row['protocol_passed']
    assert row['score_status'] in {'suggested','abstained'} and row['validation'] in {'agrees','uncertain'}
    assert row['json_export_succeeded'] and row['jsonl_export_succeeded'] and row['markdown_export_succeeded']


@pytest.mark.presidio_live
def test_all_four_agent_api_journeys_review_exports_and_report_are_honest(monkeypatch,tmp_path):
    module=prepare_runner(monkeypatch,tmp_path);service=fixture_api(monkeypatch)
    monkeypatch.setattr('iam_sra.synthetic_respondent.LLMRespondent',ReferenceRespondentFixture)
    output=tmp_path/'.runtime/agent'
    try:code=module.main(['--allow-live','--respondent','agent','--output',str(output)])
    finally:service.close()
    assert code==0
    report=json.loads((output/'metrics.json').read_text())
    assert report['semantic_accuracy'] is None and not report['fn_example_replay']
    assert report['review_readiness']=='manual_review_required' and not report['independent_validation']
    assert len(report['cases'])==4
    for row in report['cases']:
        assert row['stage']=='ended' and row['protocol_passed']
        assert row['controlled_api_fixture'] and row['respondent_backend']=='controlled_reference_fixture'
        assert row['validation']=='uncertain' and row['model_suggestion_unchanged_after_review']
        assert row['interpretation_checks_passed'] is None and row['agent_generation_calls']>0
        for suffix in ('json','jsonl','md'):assert (output/(row['case']+'.'+suffix)).is_file()
    assert (output/'summary.md').is_file()


@pytest.mark.parametrize('arguments,failure',[
    (['--max-turns','10'],'turn_limit'),(['--max-agent-calls','4'],'agent_call_limit'),
])
def test_agent_limits_leave_original_partial_records(monkeypatch,tmp_path,arguments,failure):
    module=prepare_runner(monkeypatch,tmp_path);service=fixture_api(monkeypatch)
    monkeypatch.setattr('iam_sra.synthetic_respondent.LLMRespondent',ReferenceRespondentFixture)
    output=tmp_path/'.runtime/agent'
    try:code=module.main(['--allow-live','--respondent','agent','--case','citizen_short','--output',str(output),*arguments])
    finally:service.close()
    assert code==1
    row=json.loads((output/'metrics.json').read_text())['cases'][0]
    assert row['failure']==failure and not row['protocol_passed'] and row['stage']=='conversation'
    assert row['level'] is None and (output/'citizen_short.json').is_file()


def test_unavailable_endpoint_writes_no_fictitious_live_results(monkeypatch,tmp_path):
    module=prepare_runner(monkeypatch,tmp_path)
    # prepare_runner already installed a mock factory; replace it with a failing
    # context manager without reaching any network or application service.
    class Unavailable:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,*a):raise httpx.ConnectError('Synthetic unavailable endpoint')
    monkeypatch.setattr(httpx,'Client',lambda **kw:Unavailable())
    output=tmp_path/'.runtime/agent'
    assert module.main(['--allow-live','--respondent','agent','--output',str(output)])==2
    data=json.loads((output/'metrics.json').read_text())
    assert data['cases_executed']==0 and data['live_inference']=='unavailable' and not data['services_changed']
    assert (output/'summary.md').is_file()


@pytest.mark.parametrize('runtime_error',[False,True])
def test_agent_failure_remains_partial_and_is_not_reported_as_success(monkeypatch,tmp_path,runtime_error):
    module=prepare_runner(monkeypatch,tmp_path);service=fixture_api(monkeypatch)
    class Broken(ReferenceRespondentFixture):
        def respond(self,*a):
            if runtime_error:raise RuntimeError('Synthetic private error: alice@example.com')
            raise AssessmentError('A synthetic timeout.',code='timeout')
    monkeypatch.setattr('iam_sra.synthetic_respondent.LLMRespondent',Broken)
    output=tmp_path/'.runtime/agent'
    try:code=module.main(['--allow-live','--respondent','agent','--case','citizen_short','--output',str(output)])
    finally:service.close()
    assert code==1
    row=json.loads((output/'metrics.json').read_text())['cases'][0]
    assert row['failure']==('unexpected_runtime_failure' if runtime_error else 'agent_or_privacy_failure') and not row['protocol_passed']
    assert row['stage']=='conversation' and row['level'] is None
    assert row['run_incomplete']
    assert 'alice@example.com' not in (output/'metrics.json').read_text()
    assert (output/'citizen_short.json').is_file()


def test_original_reference_cli_still_checks_source_answers_and_agreement(monkeypatch,tmp_path):
    module=prepare_runner(monkeypatch,tmp_path);service=fixture_api(monkeypatch)
    output=tmp_path/'.runtime/reference'
    try:code=module.main(['--allow-live','--respondent','reference','--case','citizen_short','--save-traces','--output',str(output)])
    finally:service.close()
    report=json.loads((output/'metrics.json').read_text());row=report['cases'][0]
    assert code==0 and report['fn_example_replay']
    assert report['live_inference']=='controlled_fixture' and not report['live_scoring_gate']['passed']
    assert row['developer_trace_saved'] and (output/'citizen_short-trace.json').is_file()
    assert row['interpretation_checks_passed'] and row['validation']=='agrees'
    assert row['agent_generation_calls']==0 and row['stage']=='ended'


@pytest.mark.presidio_live
def test_real_privacy_accepts_all_agent_persona_content_and_a_report(tmp_path):
    from iam_sra.privacy import require_safe_data
    module=runner();module.load_agent_personas(ROOT)
    require_safe_data({'respondent_backend':LLMRespondent.backend})
    module.write_summary(tmp_path,{'live_inference':'unavailable'})
    assert 'No live interviews ran' in (tmp_path/'summary.md').read_text()


def test_fn_scale_ids_are_metadata_only_in_exact_reference_fields(monkeypatch):
    from iam_sra import privacy
    original=privacy.detector()
    class MisreadReference:
        def analyze(self,*,text,**kwargs):
            found=list(original.analyze(text=text,**kwargs))
            if text.startswith(('organisational-','technical-')):
                found.append(privacy.Finding('PERSON',0,len(text)))
            return found
    monkeypatch.setattr(privacy,'detector',lambda:MisreadReference())
    value='organisational-4'
    for record in (
        {'chat':{'messages':[{'scale':{'anchors':[{'id':value}]}}]}},
        {'conversation':{'suggestion':{'anchor':{'id':value},'anchor_id':value}}},
        {'user':{'anchors':[{'id':value}]}},
        {'choices':[{'message':{'content':json.dumps({'selected_anchor_id':value})}}]},
    ):privacy.require_safe_data(record)
    for record in ({'answer':value},{'quote':value},{'text':value},{'id':value},
                   {'user':{'answer':json.dumps({'anchors':[{'id':value}]})}},
                   {'chat':{'scale':{'anchors':[{'id':'organisational-10'}]}}},
                   {'chat':{'scale':{'anchors':[{'id':'Alice Example'}]}}}):
        with pytest.raises(privacy.PrivacyError):privacy.require_safe_data(record)


def test_exposure_ids_and_lossless_score_columns_are_metadata_only(monkeypatch):
    from iam_sra import privacy
    class FlagIds:
        def analyze(self,*,text,**kw):
            return [privacy.Finding('PERSON',0,len(text))] if text in {'x3','m16','Alice Example'} else []
    monkeypatch.setattr(privacy,'detector',lambda:FlagIds())
    columns=['id','text','objective','information_exposure_ids']
    table={'original_columns':columns,'originals':[['m16','A safe description.','recognition',['x3']]]}
    privacy.require_safe_data({'user':table})
    privacy.require_safe_data({'conversation':{'messages':[{'information_exposure_ids':['x3']}],
        'information_exposures':[{'id':'x3'}]}})
    privacy.require_safe_data({'user':{'supplied_information':[{'id':'x3'}]}})
    privacy.require_safe_data({'choices':[{'message':{'content':json.dumps({'citations':[{'evidence_id':'m16','quote':'A safe description.'}]})}}]})
    for record in (
        {'answer':'x3'},{'quote':'x3'},{'text':'m16'},
        {'conversation':{'messages':[{'information_exposure_ids':['Alice Example']}]}},
        {'user':{'original_columns':columns,'originals':[['m16','x3','recognition',['x3']]]}},
        {'user':{'answer':json.dumps(table)}},
    ):
        with pytest.raises(privacy.PrivacyError):privacy.require_safe_data(record)


@pytest.mark.presidio_live
def test_real_detector_preserves_information_exposure_references_in_exports_and_score_table():
    from iam_sra.privacy import require_safe_data
    require_safe_data({'conversation':{'messages':[{'information_exposure_ids':['x1','x2','x3']}],
        'information_exposures':[{'id':'x3','text':'General information about drone services.'}]}})
    require_safe_data({'user':{'original_columns':['id','text','objective','information_exposure_ids'],
        'originals':[['m16','I would compare the evidence.','evaluation_evidence',['x3']]],
        'supplied_information':[{'id':'x3','text':'General information about drone services.'}]}})


@pytest.mark.presidio_live
def test_exact_fn_review_prompts_do_not_allow_personal_data_or_changed_text():
    from iam_sra import privacy
    from iam_sra.fn_interview import specification
    review=specification()['review']['citizen_short']
    text=review['question'].format(level=4)+'\n\n'+'\n'.join(f'{k}. {label}' for k,label in zip('ABCDE',review['choices']))
    privacy.require_safe_data({'text':text})
    privacy.require_safe_data({'chat':{'messages':[{'text':text}]}})
    for record in ({'text':text+' Email alice@example.com'},
                   {'text':text.replace('It describes me well','My name is Alice Example')},
                   {'quote':text},{'answer':text},
                   {'text':json.dumps({'chat':{'messages':[{'text':text}]}})}):
        with pytest.raises(privacy.PrivacyError):privacy.require_safe_data(record)


@pytest.mark.presidio_live
def test_city_acknowledgement_keeps_context_without_a_name_echo():
    from iam_sra.chat_session import ChatSession
    from fn_fixture import SyntheticInterpreter
    from indicator_fixtures import bank
    s=ChatSession(bank(),synthetic=True);c=SyntheticInterpreter()
    s.send('A',c);s.send('Coimbra',c)
    assert s.context['city']=='Coimbra' and s.objective=='citizen_duration'
    acknowledgement=next(m['text'] for m in s.messages if m.get('act')=='city_acknowledgement')
    assert 'Coimbra' not in acknowledgement


@pytest.mark.presidio_live
def test_controlled_quotes_do_not_create_a_partial_surname_from_vans():
    from fn_fixture import reply
    from iam_sra.privacy import require_safe_data
    from test_fn_interview import GOLDEN
    answer=next(r['answer'] for r in GOLDEN['citizen_extended'] if r['id']=='open_priorities')
    result=reply({'answer':answer,'current_answer_id':'m1','fn':{'evidence_goal':'open_priorities'}},topics=['noise'])
    quote=result['interpretation']['topics'][0]['quote']
    assert quote in answer and len(quote)<=160 and not quote.endswith(' van')
    require_safe_data(result)


@pytest.mark.presidio_live
def test_transcript_renderer_checks_structured_content_before_formatting():
    from iam_sra import privacy
    from iam_sra.fn_interview import specification
    review=specification()['review']['citizen_short']
    text=review['question'].format(level=4)+'\n\n'+'\n'.join(f'{k}. {label}' for k,label in zip('ABCDE',review['choices']))
    conversation={'messages':[{'role':'assistant','text':text}]}
    assert text in runner().render_transcript(conversation)
    conversation['messages'].append({'role':'respondent','text':'Email alice@example.com'})
    with pytest.raises(privacy.PrivacyError):runner().render_transcript(conversation)
