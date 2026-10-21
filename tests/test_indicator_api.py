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
from indicator_fixtures import bank, Client
from test_api_integration import Browser, MockScore


def factory():
    s=ConversationSession(synthetic_collection());s.indicators=IndicatorAssessment(bank());return s


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
    assert b.view['indicator_assessment']['available'] is False
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
    assert '[private detail removed]' in preview['fields'][field]
    b.view=response.json['session'];b.act('confirm_cleaned',{'preview_id':preview['id']})
    assert 'Alice Example' not in json.dumps(b.view)


def test_unknown_or_wrong_profile_requests_are_rejected(api_factory):
    b,_=api_factory()
    assert b.submit('select_indicators',{'indicator_ids':['not-real'],'context':'general_understanding'}).status_code==409
    assert b.submit('select_indicators',{'profile':'technical','indicator_ids':['indicator-07'],'context':'general_understanding'}).status_code==400
    select(b);suggest(b)
    assert b.submit('indicator_review',{'choice':'select','statement_id':'indicator-08-crl-5','revision':b.view['indicator_assessment']['revision']}).status_code==409
