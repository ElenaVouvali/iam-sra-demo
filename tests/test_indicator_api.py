"""Actual API/controller jobs with synthetic definitions, not live-model results."""
import json
import threading
import time
import pytest
pytest.importorskip('flask')
from iam_sra.api import create_app
from iam_sra.api.adapter import ControllerAdapter
from iam_sra.api.service import AssessmentService
from iam_sra.baseline_client import MockBaselineClient
from iam_sra.conversation_session import ConversationSession
from iam_sra.indicator_assessment import IndicatorAssessment
from iam_sra.synthetic_runner import synthetic_collection
from indicator_fixtures import bank, questionnaire, Client
from test_api_integration import Browser, MockScore


def factory():
    s=ConversationSession(synthetic_collection());s.indicators=IndicatorAssessment(bank(),questionnaire());return s


@pytest.fixture
def api_factory():
    managers=[]
    def make(client=None):
        adapter=ControllerAdapter(engine_factory=factory,
            clients_factory=lambda e: {'baseline':MockBaselineClient(),'planner':None,'score':MockScore(),'indicator':client or Client()},
            readiness=lambda:{'privacy':'synthetic','corpus':'synthetic'})
        manager=AssessmentService(adapter);managers.append(manager)
        app=create_app({'TESTING':True,'SECRET_KEY':'indicator-test-only-not-for-deployment'},service=manager)
        browser=Browser(app);browser.new();browser.act('set_context',{'perspective':'personal','role':'citizen','city':'madrid'})
        browser.act('finish');browser.act('confirm_general');browser.act('decline_scenario');browser.act('confirm_final')
        return browser,manager
    yield make
    for m in managers:m.close()


def select(b):
    b.act('select_indicators',{'indicator_ids':['indicator-07'],'context':'general_understanding'})


def suggest(b):
    b.act('indicator_answer',{'text':'I propose protections for rest.'})
    b.act('indicator_confirm');b.act('indicator_finish');b.act('indicator_suggest')


def test_full_controller_job_review_and_both_projected_exports(api_factory):
    b,m=api_factory();select(b);suggest(b)
    result=b.view['indicator_assessment'];r=result['current']
    assert r['participant'] is None and r['tool']['statement']['level']==5
    assert len(r['scale'])==9 and len(result['coverage'])==15
    b.act('indicator_review',{'choice':'select','statement_id':'indicator-07-crl-3','revision':result['revision'],'explanation':'The lower description fits my situation.'})
    b.read();row=b.view['indicator_assessment']['current']
    assert row['participant']['statement']['level']==3 and row['tool']['statement']['level']==5
    assert row['participant']['disagrees_with_tool'] is True
    assert row['tool']['statement']['row_review_status']=='To review'
    for fmt in ('json','jsonl'):
        response=b.client.get('/v1/sessions/'+b.view['id']+'/export?format='+fmt)
        assert response.status_code==200
        data=json.loads(response.data);a=data['indicator_assessment'];saved=a['results'][0]
        assert saved['participant']['statement']['level']==3 and saved['tool']['statement']['level']==5
        assert a['bank']['source']['document']=='synthetic-readiness.xlsx'
        assert saved['events'][0]['reading']['observations'][0]['quote']=='I propose protections for rest.'
        assert data['numerical_crl'] is None and data['numerical_srl'] is None
        text=response.data.decode()
        assert '/home/' not in text and 'base_url' not in text and 'prompts' not in text


def test_model_abstention_and_explicit_participant_level_one(api_factory):
    b,_=api_factory(Client(abstain=True));select(b);suggest(b)
    assert b.view['indicator_assessment']['current']['tool']['status']=='abstained'
    b.act('indicator_review',{'choice':'select','statement_id':'indicator-07-crl-1','revision':b.view['indicator_assessment']['revision']})
    row=b.view['indicator_assessment']['current']
    assert row['participant']['statement']['level']==1 and row['tool']['statement'] is None


def test_correction_fences_out_stale_review_and_preserves_superseded_judgments(api_factory):
    b,_=api_factory();select(b);suggest(b)
    old=b.view['indicator_assessment']['revision']
    b.act('indicator_review',{'choice':'endorse','revision':old})
    row=b.view['indicator_assessment']['current'];event=row['events'][0]
    b.act('indicator_edit',{'event_id':event['id'],'mode':'interpretation'})
    assert b.view['indicator_assessment']['current']['tool'] is None
    assert b.view['indicator_assessment']['current']['participant'] is None
    b.act('indicator_correct',{'text':'Keep my stated safeguards without inventing participation.'})
    b.act('indicator_confirm');b.act('indicator_finish')
    assert b.submit('indicator_review',{'choice':'endorse','revision':old}).status_code==409
    assert b.view['indicator_assessment']['current']['tool'] is None


def test_late_suggestion_cannot_commit_after_reset(api_factory):
    begun=threading.Event();release=threading.Event()
    class Slow(Client):
        def match(self,*args):
            begun.set();release.wait(3);return super().match(*args)
    b,m=api_factory(Slow());select(b)
    b.act('indicator_answer',{'text':'I propose safeguards.'});b.act('indicator_confirm');b.act('indicator_finish')
    response=b.submit('indicator_suggest');assert response.status_code==202
    assert begun.wait(2)
    b.read();b.act('reset');release.set();time.sleep(.1);b.read()
    assert b.view['state']=='general_welcome'
    assert b.view['indicator_assessment']['entry_possible'] is True
    assert b.view['indicator_assessment']['current'] is None
    assert not any(r['tool'] for r in b.view['indicator_assessment']['coverage'])
    assert b.client.get('/v1/jobs/'+response.json['job_id']).status_code==410


@pytest.mark.parametrize('action,data,field',[
    ('select_indicators',{'indicator_ids':['indicator-07'],'context':'general_understanding','use_case':'Near Alice Example.'},'use_case'),
    ('indicator_answer',{'text':'Alice Example suggested safeguards.'},'text'),
    ('indicator_correct',{'text':'Alice Example meant safeguards.'},'text'),
    ('indicator_review',{'choice':'unsure','revision':0,'explanation':'Alice Example disagrees.'},'explanation')])
def test_each_new_text_field_uses_bound_cleaned_preview(api_factory,action,data,field):
    b,_=api_factory()
    if action!='select_indicators':select(b)
    if action=='indicator_correct':b.act('indicator_answer',{'text':'I propose safeguards.'})
    if action=='indicator_review':
        b.act('indicator_finish');data['revision']=b.view['indicator_assessment']['revision']
    response=b.submit(action,data);assert response.status_code==200
    preview=response.json['session']['preview'];assert preview and 'Alice Example' not in json.dumps(preview)
    value=preview['fields']
    for key in field.split('.'):value=value[key]
    assert '[private detail removed]' in value
    b.view=response.json['session'];b.act('confirm_cleaned',{'preview_id':preview['id']})
    assert 'Alice Example' not in json.dumps(b.view)


def test_unknown_or_wrong_profile_requests_are_rejected(api_factory):
    b,_=api_factory()
    assert b.submit('select_indicators',{'indicator_ids':['not-real'],'context':'general_understanding'}).status_code==409
    assert b.submit('select_indicators',{'profile':'unknown_profile','indicator_ids':['indicator-07'],'context':'general_understanding'}).status_code==400
    select(b);suggest(b)
    assert b.submit('indicator_review',{'choice':'select','statement_id':'indicator-08-crl-5','revision':b.view['indicator_assessment']['revision']}).status_code==409

@pytest.mark.parametrize('profile,scale',[('citizen','crl'),('organisational','orl'),('technical','trl')])
def test_direct_profile_journey_continuation_and_projected_exports(api_factory,profile,scale):
    b,_=api_factory();b.act('reset')
    b.act('start_assessment',{'profile':profile,'use_case':'Synthetic proposed service'})
    assert not b.view['answers'] and b.view['indicator_assessment']['selected_indicator_ids']==[f'indicator-{i:02d}' for i in range(1,16)]
    if profile!='citizen':b.act('indicator_scope',{'organisation_or_unit':'Planning unit','responsibilities':'Planning','technical_object':'Test model','object_version':'A','intended_environment':'Laboratory','component_scope':'model'})
    b.act('indicator_answer',{'text':'I propose safeguards because repeated disruption matters.'});b.act('indicator_confirm');b.act('indicator_suggest')
    a=b.view['indicator_assessment'];assert a['current']['tool']['statement']['profile']==profile
    b.act('indicator_review',{'choice':'select','statement_id':f'indicator-01-{scale}-3','revision':a['revision']})
    old=b.view['indicator_assessment']['current']['participant']
    for n in (6,11,1):b.act('indicator_next',{'indicator_id':f'indicator-{n:02d}'})
    assert b.view['indicator_assessment']['current']['participant']==old
    b.act('complete_assessment')
    for fmt in ('json','jsonl'):
        saved=json.loads(b.client.get('/v1/sessions/'+b.view['id']+'/export?format='+fmt).data)
        a=saved['indicator_assessment'];r=a['results'][0]
        assert a['profile']==profile and a['questionnaire']['questionnaire_version']=='2026-10-21-v0.2'
        assert r['participant']['statement']['level']==3 and r['tool']['statement']['level']==5
        assert len(a['coverage'])==15 and saved['numerical_srl'] is None


@pytest.mark.parametrize('action,data,field',[
 ('start_assessment',{'profile':'technical','use_case':'A synthetic service','technical_object':'Alice Example model'},'technical_object'),
 ('indicator_scope',{'technical_object':'Alice Example model','intended_environment':'Laboratory'},'technical_object'),
 ('indicator_add_information',{'text':'Alice Example reported further evidence.'},'text'),
 ('select_indicators',{'profile':'technical','indicator_ids':['indicator-01'],'context':'general_understanding','use_case_fields':{'significant_unknowns':'Alice Example is unsure.'}},'use_case_fields.significant_unknowns')])
def test_v02_new_free_text_uses_existing_privacy_preview(api_factory,action,data,field):
    b,_=api_factory();b.act('reset')
    if action!='start_assessment':
        b.act('start_assessment',{'profile':'technical','use_case':'Synthetic service'})
        if action=='indicator_add_information':
            b.act('indicator_scope',{'technical_object':'Test model'});b.act('indicator_answer',{'text':'The model was tested in a laboratory.'})
    response=b.submit(action,data);assert response.status_code==200
    preview=response.json['session']['preview'];assert preview and 'Alice Example' not in json.dumps(preview)
    value=preview['fields']
    for key in field.split('.'):value=value[key]
    assert '[private detail removed]' in value
    b.view=response.json['session'];b.act('confirm_cleaned',{'preview_id':preview['id']})
    assert 'Alice Example' not in json.dumps(b.view)


def test_scope_edit_is_blocked_during_matching_and_invalidates_completed_judgment(api_factory):
    begun=threading.Event();release=threading.Event()
    class Slow(Client):
        def match(self,*args):begun.set();release.wait(3);return super().match(*args)
    b,_=api_factory(Slow());b.act('reset');b.act('start_assessment',{'profile':'technical','use_case':'Synthetic service'})
    b.act('indicator_scope',{'technical_object':'Test model'});b.act('indicator_answer',{'text':'A test was performed.'});b.act('indicator_confirm')
    response=b.submit('indicator_suggest');assert begun.wait(2);b.read()
    blocked=b.submit('indicator_scope',{'technical_object':'Different model'})
    assert blocked.status_code==409 and blocked.json['error']['code']=='session_busy'
    release.set()
    for _ in range(40):
        time.sleep(.05);b.read()
        if not b.view['busy_job']:break
    b.act('indicator_scope',{'technical_object':'Different model'})
    assert b.view['indicator_assessment']['current']['tool'] is None
    assert b.view['indicator_assessment']['current']['scope']['technical_object']=='Different model'


@pytest.mark.parametrize('profile,scale',[('citizen','crl'),('organisational','orl'),('technical','trl')])
def test_failed_suggestion_remains_unavailable_while_participant_can_finish(api_factory,profile,scale):
    from iam_sra.assessment import AssessmentError
    class Broken(Client):
        def match(self,*args):raise AssessmentError('Synthetic evidence rejection.',code='evidence')
    b,_=api_factory(Broken());b.act('reset');b.act('start_assessment',{'profile':profile,'use_case':'Synthetic service'})
    if profile!='citizen':b.act('indicator_scope',{'organisation_or_unit':'Planning unit','responsibilities':'Planning','technical_object':'Test model'})
    b.act('indicator_answer',{'text':'I propose safeguards.'});b.act('indicator_confirm')
    response=b.submit('indicator_suggest')
    for _ in range(60):
        job=b.client.get('/v1/jobs/'+response.json['job_id']).json['job']
        if job['status']=='failed':break
        time.sleep(.05)
    assert job['status']=='failed';b.read();a=b.view['indicator_assessment']
    assert a['current']['suggestion_error']['status']=='unavailable' and a['current']['tool'] is None
    b.act('indicator_review',{'choice':'select','statement_id':f'indicator-01-{scale}-1','revision':a['revision']});b.act('complete_assessment')
    for fmt in ('json','jsonl'):
        data=json.loads(b.client.get('/v1/sessions/'+b.view['id']+'/export?format='+fmt).data)['indicator_assessment']['results'][0]
        assert data['participant']['statement']['level']==1 and data['tool'] is None
        assert data['suggestion_error']['status']=='unavailable'


@pytest.mark.parametrize('profile,scale',[('citizen','crl'),('organisational','orl'),('technical','trl')])
def test_optional_case_scope_and_judgments_survive_both_api_exports(api_factory,profile,scale):
    from indicator_fixtures import scenario_cases
    b,m=api_factory();b.act('reset')
    m.records[b.view['id']].engine.collection['scenarios']+=scenario_cases()
    b.act('start_assessment',{'profile':profile,'use_case':'Confirmed local proposal','indicator_ids':['indicator-07','indicator-08']})
    if profile!='citizen':b.act('indicator_scope',{'organisation_or_unit':'Planning unit','responsibilities':'Planning','technical_object':'Test model'})
    assert b.submit('indicator_case',{'scenario_id':'unknown'}).status_code==409
    b.act('indicator_case',{'scenario_id':'expansion-04'})
    assert b.view['indicator_assessment']['current']['scope']['use_case']=='Confirmed local proposal'
    # The card alone never becomes respondent evidence or an ORL/TRL judgment.
    b.act('indicator_finish');b.act('indicator_suggest')
    a=b.view['indicator_assessment'];assert a['current']['tool']['status']=='abstained'
    b.act('indicator_review',{'choice':'select','statement_id':f'indicator-07-{scale}-1','revision':a['revision']})
    selected=b.view['indicator_assessment']['current']['participant']
    b.act('indicator_case',{'scenario_id':'expansion-04'})
    assert b.view['indicator_assessment']['current']['participant']==selected
    b.act('complete_assessment')
    for fmt in ('json','jsonl'):
        data=json.loads(b.client.get('/v1/sessions/'+b.view['id']+'/export?format='+fmt).data)['indicator_assessment'];r=data['results'][0]
        assert r['scope']['illustrative_case']['id']=='expansion-04'
        assert r['scope']['illustrative_case']['source_verification']=='unverified_draft_adaptation'
        assert r['participant']['statement']['level']==1 and r['tool']['statement'] is None
        assert data['presented_cases'][0]['text']==scenario_cases()[3]['text']
    b.act('indicator_case',{'scenario_id':None})
    assert b.view['indicator_assessment']['current']['tool'] is None and b.view['indicator_assessment']['current']['participant'] is None
