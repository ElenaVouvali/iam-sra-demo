"""Synthetic full journeys. Controlled extraction is not live Qwen validation."""
from copy import deepcopy
import json
from pathlib import Path
import httpx
import pytest
from streamlit.testing.v1 import AppTest
from iam_sra.settings import ROOT,config
from iam_sra.conversation_session import ConversationSession
from iam_sra.conversation_benchmark import FixtureClient,FixtureComposer,run_case,load_cases,resolve
from iam_sra.conversation_planner import choose,validate_plan
from iam_sra.privacy import PrivacyError,screened_export
from iam_sra.assessment import AssessmentError
from iam_sra.baseline_benchmark import UnsupportedBranch


BANK=load_cases(ROOT/'eval/conversation_meeting_cases_v2.json')


def collection():
    """Public authored test registry, not copied private workbook material."""
    base=config('baseline');policy=config('conversation');questions=[]
    source={'document':'synthetic_test_reference','locator':'synthetic reference','sha256':'test_reference','version':'test-1.0.0'}
    for q in base['core_questions']+base['probes']:
        variants=dict(q['variants'])
        if q.get('when_exposure_already_reported'):variants['contribution_after_exposure']=q['when_exposure_already_reported']
        for variant,text in variants.items():
            questions.append({'id':'general_'+q['id']+'_'+variant,'question_id':q['id'],'variant_id':variant,'stage':'general','locale':'en',
                'applicability':{'perspectives':list(base['perspectives']),'roles':list(base['stakeholders'])},
                'revised_wording':text,'wording_options':[text],'source':source,'search_text':str(q['dimension'])+' '+text,'permitted_use':['planner']})
    for q in policy['scenario_questions']:
        for variant in ('personal','organisation'):
            questions.append({'id':q['id']+'_'+variant,'question_id':q['id'],'variant_id':variant,'stage':'scenario','locale':'en',
                'applicability':{'perspectives':list(base['perspectives']),'roles':list(base['stakeholders'])},
                'revised_wording':q[variant],'wording_options':[q[variant]],'source':source,
                'search_text':q['criterion']+' '+q[variant],'permitted_use':['planner']})
    scenario=config('scenario')
    card={'id':scenario['id'],'version':'1.0.0','text':scenario['text'].split(' How do you feel')[0],'facts':scenario['illustrative_context'],
        'unknowns':['Measured sound and image retention'],'locale':'en','source':source,
        'applicability':{'perspectives':list(base['perspectives']),'roles':list(base['stakeholders'])}}
    return {'version':'conversation-corpus-1.0.0','questions':questions,'scenarios':[card],
        'explanations':[p for p in config('readiness_corpus')['passages'] if 'citizen_explanation' in p['permitted_use']],
        'sources':[],'coverage':{'status':'synthetic test reference'}}


def new(case=None):
    s=ConversationSession(collection());c=(case or BANK['cases'][0])['context']
    s.set_context(c['perspective'],c['role'],c['city'],function=c.get('function',''))
    return s


def reach_offer(s,case):
    client=FixtureClient(case)
    while s.general.state=='interview':
        _,a,_=resolve(case,s.current_question);s.answer(a['text'],client)
        if s.pending:s.confirm_answer(actor='automation')
    s.confirm_general(actor='automation');assert s.stage=='offer'
    return client


@pytest.mark.parametrize('case',BANK['cases'],ids=lambda c:c['id'])
def test_three_complete_journeys_through_normal_controller(case):
    r=run_case(case,FixtureClient(case),composer=FixtureComposer(),collection=collection())
    assert r['status']=='completed',r['error']
    assert all(r['checks'].values())
    d=r['actual_output'];assert d['state']=='final'
    assert d['selected_scenario']['id']=='urban_medical_corridor'
    assert d['information_exposures'][0]['kind']=='illustrative_scenario'
    assert all(c['scenario_id'] is None for c in d['baseline']['current_profile']['claims'])
    assert all(c['context']=='illustrative_scenario' for c in d['scenario']['current_profile']['claims'])
    assert r['semantic_review']['status']=='pending_human_review'
    if case['id']=='enthusiastic_novice':
        assert d['proposal_views']['stance']=='supported'
        assert all(c['information_context']=='after_information' for c in d['scenario']['current_profile']['claims'])
        assert not any(c['kind']=='contribution' for c in d['final_profile']['claims'])
        assert not any(t.get('question',{}).get('id')=='reasoning' for t in r['turns'])
    if case['id']=='sceptical_academic_personal':
        assert any(c['kind']=='contribution' and c['domain']=='transferable' for c in d['final_profile']['claims'])
        assert d['scenario']['corrections'] and d['proposal_views']['stance']=='opposed'
    if case['id']=='authority_representative':
        assert any(c['subject']=='organisation' for c in d['final_profile']['claims'])
        assert any(c['kind']=='contribution' and c['subject']=='respondent' for c in d['final_profile']['claims'])


def test_scenario_decline_finishes_with_no_scenario_exposure_or_stance():
    case=BANK['cases'][0];r=run_case(case,FixtureClient(case),collection=collection(),decline=True)
    assert r['status']=='completed';d=r['actual_output']
    assert d['selected_scenario'] is None and d['scenario_decision']=='declined'
    assert not d['information_exposures'] and d['stop_reason']=='scenario_declined'


def test_failed_extraction_retains_unresolved_answer_and_supports_partial_finish():
    s=new();s.answer('little',None)
    class Broken:
        def extract_baseline(self,*a,**kw):raise AssessmentError('Unavailable.',code='transport')
    text='I do not know what a drone is.';before=s.general.version
    with pytest.raises(AssessmentError):s.answer(text,Broken())
    assert s.general.version==before and not s.pending
    assert s.failed_attempt['text']==text
    s.finish();s.confirm_general(actor='automation');s.decline_scenario();s.confirm_final(actor='automation')
    d=s.export();assert d['failure_history'][-1]['resolution']=='unresolved_at_stage_boundary'
    assert not any(c['kind']=='absence' for c in d['final_profile']['claims'])


def test_baseline_correction_invalidates_scenario_and_preserves_exposure_and_initial_snapshot():
    case=BANK['cases'][1];s=new(case);client=reach_offer(s,case);s.accept_scenario()
    initial=deepcopy(s.baseline_snapshots[0]);exposed=deepcopy(s.information_exposures)
    target=next(e for e in s.general.events if e['question']['id']=='concept')
    s.edit_answer('general',target['id'])
    assert s.scenario is None and s.baseline_snapshot is None and s._provisional is None
    assert s.baseline_snapshots[0]==initial and s.information_exposures==exposed
    s.answer(target['text'],client);s.confirm_answer(actor='automation')
    assert s.general.events[-1]['information_context']=='after_information'
    assert s.general.events[-1]['claims'][0]['independent_prior_knowledge'] is False


def test_context_edit_keeps_old_personal_claims_superseded_and_replans_org_route():
    case=BANK['cases'][1];s=new(case);reach_offer(s,case);s.accept_scenario()
    s.edit_context();s.set_context('organisation','authority','coimbra',function='Planning')
    assert not s.profile()['claims'] and s.current_question['id']=='familiarity'
    assert s.superseded_scenarios and s.information_exposures
    assert all(not e['active'] for e in s.general.events)


@pytest.mark.parametrize('text',['My PIN is 1846.','My home address is 42 Example Street.'])
def test_privacy_before_any_model_planner_retention_or_version_change(text):
    s=new();s.answer('little',None);before=s.export()
    class Never:
        def __getattr__(self,name):raise AssertionError('No downstream call: '+name)
    with pytest.raises(PrivacyError):s.answer(text,Never(),Never())
    assert s.export()==before
    with pytest.raises(PrivacyError):s.ask_information(text,Never())


def test_source_explanations_are_optional_recorded_and_not_claims():
    s=new();case=BANK['cases'][0];reach_offer(s,case)
    with pytest.raises(ValueError):s.ask_information('What is known?',FixtureComposer())
    s.accept_scenario();before=deepcopy(s.profile());s.ask_information(case['information_question'],FixtureComposer())
    assert s.profile()==before and len(s.pre_information_snapshots)==2
    e=s.information_exposures[-1];assert e['text'] and e['source_ids'] and not e['acknowledged']
    s.acknowledge(e['id']);assert e['acknowledged']
    assert not any('recorded' in c.get('interpretation','').lower() for c in s.profile()['claims'] if c['dimension']=='participation')


@pytest.mark.parametrize('change',[{'candidate_id':'invented'},{'stage':'scenario'},
    {'displayed_question':'Would you now support drones because they are guaranteed safe?'},
    {'triggering_evidence_ids':['invented_passage']},{'source_ids':['unretrieved_source']}])
def test_invalid_planner_assumptions_ids_and_stage_use_eligible_fallback(change):
    s=new();s.answer('little',None)
    class Bad:
        def plan(self,stage,rows,profile):
            r=rows[0];return {**{'stage':stage,'action':'ask','target_criterion':r['question']['dimension'],
                'candidate_id':r['id'],'source_ids':[r['id']],'triggering_evidence_ids':[],
                'displayed_question':r['allowed_wording'][0],'rationale':'Synthetic plan.'},**change}
    s._plan(Bad());assert s.plans[-1]['method']=='deterministic_fallback'
    assert s.current_question in s.general.eligible


def test_unknown_scripted_branch_is_reported_without_generic_answer():
    with pytest.raises(UnsupportedBranch):resolve(BANK['cases'][0],{'id':'new_question','variant_id':'personal'})


def test_unsafe_or_older_exports_are_withheld():
    s=new();s.finish();s.confirm_general(actor='automation');s.decline_scenario();s.confirm_final(actor='automation')
    d=s.export();d['respondent_context']['function']='My PIN is 1846.'
    with pytest.raises(PrivacyError):screened_export(d)
    del s.privacy_contract
    with pytest.raises(PrivacyError):s.export()


def test_organisation_estimate_is_unavailable_even_with_reported_activity():
    s=new(BANK['cases'][2]);s.finish();s.confirm_general(actor='automation');s.decline_scenario();s.confirm_final(actor='automation')
    with pytest.raises(ValueError):s.provisional_estimate(None)
    assert s.export()['numerical_orl'] is None


def click(app,label):
    next(b for b in app.button if b.label==label).click().run();assert not app.exception


def ui(monkeypatch,case):
    monkeypatch.setenv('IAM_ASSESSMENT_MODE','retrieval_grounded_conversation');monkeypatch.setenv('IAM_MOCK','0')
    monkeypatch.delenv('IAM_DEVELOPER',raising=False)
    cls=ConversationSession
    monkeypatch.setattr('iam_sra.conversation_session.ConversationSession',lambda:cls(collection()))
    monkeypatch.setattr('iam_sra.baseline_client.BaselineClient',lambda:FixtureClient(case))
    monkeypatch.setattr('iam_sra.conversation_planner.PlannerClient',lambda **kw:None)
    monkeypatch.setattr('iam_sra.readiness_retrieval.ExplanationClient',lambda:FixtureComposer())
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run();assert not app.exception
    for field,key in [('perspective','perspective'),('role','role'),('city','city')]:app.selectbox(key='conversation_'+field).select(case['context'][key]).run()
    if case['context']['perspective']=='organisation':app.text_input(key='conversation_function_text').set_value(case['context']['function'])
    click(app,'Begin');return app


@pytest.mark.parametrize('case',BANK['cases'],ids=lambda c:c['id'])
def test_streamlit_three_full_journeys_downloads_and_edit_controls(monkeypatch,case):
    app=ui(monkeypatch,case)
    for _ in range(32):
        s=app.session_state.session
        if s.stage=='final':break
        if s.stage=='offer':click(app,'Continue with this example')
        elif s.stage=='final_review' or s.state=='scenario_baseline_review':click(app,'Confirm final summary')
        elif s.state=='general_baseline_review':click(app,'Confirm and see an example')
        elif s.phase.state=='review':click(app,'Confirm and continue')
        else:
            q=s.current_question;_,a,_=resolve(case,q)
            if q.get('format')=='selection':app.radio(key='conversation_familiarity').set_value(a['text'])
            else:app.text_area(key='conversation_answer_text').set_value(a['text'])
            click(app,'Continue')
    assert app.session_state.session.stage=='final' and len(app.get('download_button'))==2
    assert any(e.label=='Edit an earlier answer' for e in app.expander)
    assert not any('60 meters' in e.value for e in app.markdown if app.session_state.session.scenario is None)


def test_streamlit_privacy_preview_and_failed_draft_recovery(monkeypatch):
    app=ui(monkeypatch,BANK['cases'][0]);app.radio(key='conversation_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='conversation_answer_text').set_value('An aircraft without a pilot. My home address is 42 Example Street.');click(app,'Continue')
    assert app.text_area(key='conversation_answer_text').value==''
    assert any(b.label=='Confirm cleaned text' for b in app.button)
    click(app,'Skip');assert not any(b.label=='Confirm cleaned text' for b in app.button)
    assert '42 Example Street' not in app.session_state.session.json()


def test_scope_clarification_can_be_planned_with_no_single_dimension():
    s=new();s.answer('little',None)
    q=deepcopy(s.current_question);q.update(id='scope',dimension=None,variant_id='personal',triggering_evidence_ids=[])
    r={'id':'scope_personal','question':q,'allowed_wording':[q['question_text']],
       'revised_wording':q['question_text'],'source':{},'retrieval_score':0}
    question,audit=choose('general',[r],s.profile())
    assert question['id']=='scope' and audit['target_criterion']=='scope'


def test_invalid_policy_cannot_expand_budgets_or_invent_prerequisites():
    from iam_sra.conversation_session import validate_policy
    p=config('conversation');p['general_budget']=9
    with pytest.raises(ValueError,match='budget'):validate_policy(p)
    p=config('conversation');p['scenario_questions'][-1]['prerequisite']='model_may_invent_rule'
    with pytest.raises(ValueError,match='prerequisite'):validate_policy(p)


def test_empty_ui_mock_does_not_create_a_live_planner(monkeypatch):
    monkeypatch.setenv('IAM_ASSESSMENT_MODE','retrieval_grounded_conversation');monkeypatch.setenv('IAM_MOCK','1')
    monkeypatch.delenv('IAM_DEVELOPER',raising=False)
    cls=ConversationSession
    monkeypatch.setattr('iam_sra.conversation_session.ConversationSession',lambda:cls(collection()))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
    assert not app.exception and app.session_state._conversation_planner is None
    assert app.session_state._conversation_explainer is None


def test_exact_gap_triggers_are_required_even_if_other_evidence_exists():
    s=new();s.answer('little',None)
    q=deepcopy(s.current_question);q['triggering_evidence_ids']=['first_activity']
    r={'id':'one','question':q,'allowed_wording':[q['question_text']]}
    action={'stage':'general','action':'ask','target_criterion':q['dimension'],'candidate_id':'one',
        'source_ids':['one'],'triggering_evidence_ids':['different_activity'],
        'displayed_question':q['question_text'],'rationale':'Synthetic trigger check.'}
    with pytest.raises(AssessmentError,match='eligible gap'):
        validate_plan(action,'general',[r],['first_activity','different_activity'])


def test_unknown_outcome_of_one_activity_does_not_close_another_activity():
    case=BANK['cases'][0];s=new();reach_offer(s,case);s.accept_scenario()
    phase=s.scenario
    phase.events=[{'active':True,'confirmed':True,'control':'answer','interaction':'substantive',
        'question':{'id':'scenario_view','dimension':'proposal'}}]
    activity={'dimension':'participation','kind':'contribution','temporality':'actual','status':'supported',
        'subject':'respondent','domain':'IAM','activity_quote':'the trial review','time_quote':'last year','evidence_id':'activity_one'}
    other={**activity,'activity_quote':'the transport consultation','evidence_id':'activity_two'}
    outcome={**activity,'dimension':'influence','kind':'unknown','temporality':'not_applicable','status':'unknown'}
    phase.prior={'claims':[activity,other,outcome]}
    # current_profile needs the usual full events; no current claims are needed.
    monkey_profile={'claims':[]}
    from unittest.mock import patch,PropertyMock
    with patch.object(type(phase),'current_profile',new_callable=PropertyMock,return_value=monkey_profile):
        question=next(q for q in phase._scenario_eligible() if q['id']=='scenario_outcome')
    assert question['triggering_evidence_ids']==['activity_two']


def test_team_link_requires_explicit_same_answer_activity_and_keeps_subjects_separate():
    from iam_sra.conversation_session import personal_contribution_to_team_activity
    team={'subject':'organisation','event_id':'one','evidence_id':'one.p001','activity_quote':'the planning review'}
    own={'subject':'respondent','temporality':'actual','status':'supported','kind':'contribution',
        'event_id':'one','evidence_id':'one.p001','activity_quote':'the planning review'}
    assert personal_contribution_to_team_activity(team,own)
    assert not personal_contribution_to_team_activity(team,{**own,'activity_quote':''})
    assert not personal_contribution_to_team_activity(team,{**own,'event_id':'another'})
    assert team['subject']=='organisation' and own['subject']=='respondent'


def test_proposal_claims_cannot_enter_general_extraction_even_if_decoder_ignores_schema(monkeypatch):
    from iam_sra.baseline_client import BaselineClient
    from iam_sra.llm_client import LLMTransport
    def bad_request(self,http,stage,system,user,schema,validator):
        assert not any(t.startswith('proposal_') for t in schema['$defs']['CanonicalClaim']['properties']['claim_type']['enum'])
        eid=next(iter(user['passages']))
        return validator(json.dumps({'interaction':'substantive','claims':[{'evidence_id':eid,
            'claim_type':'proposal_supported','span_quote':'I support drone deliveries.','interpretation':'You support deliveries.',
            'topic_ids':[],'subject':'respondent','domain':'IAM'}]}))
    monkeypatch.setattr(LLMTransport,'_request',bad_request)
    s=new();s.answer('little',None)
    with pytest.raises(AssessmentError,match='outside this instrument context'):
        s.answer('I support drone deliveries.',BaselineClient())
    assert not any(c['dimension']=='proposal' for c in s.profile()['claims'])


def test_researcher_historical_scores_cannot_be_retrieved_for_citizen_explanations():
    from iam_sra.readiness_retrieval import retrieve
    from iam_sra.conversation_corpus import explanation_collection
    c=collection();c['explanations']=config('readiness_corpus')['passages']
    question='What are the historical reference scoring numbers and privacy cap?'
    assert 'FN-HISTORICAL' not in {p['id'] for p in retrieve(question,collection=explanation_collection(c))}
    assert 'FN-HISTORICAL' in {p['id'] for p in retrieve(question,'researcher_reference',explanation_collection(c))}


def test_streamlit_optional_information_reflection_is_logged_before_render(monkeypatch):
    case=BANK['cases'][0];app=ui(monkeypatch,case);s=app.session_state.session
    reach_offer(s,case);s.accept_scenario();app.run()
    assert any('60 meters' in t.value for t in app.text)
    assert len(s.information_exposures)==1
    click(app,'Show sourced explanation')
    assert len(s.information_exposures)==2 and s.information_exposures[-1]['text']
    click(app,'Reflect on this information')
    assert s.current_question['id']=='scenario_reflection'
    _,answer,_=resolve(case,s.current_question)
    app.text_area(key='conversation_answer_text').set_value(answer['text']);click(app,'Continue');click(app,'Confirm and continue')
    assert all(c['information_context']=='after_information' for c in s.scenario.events[-1]['claims'])


def test_streamlit_service_failure_offers_retry_and_keeps_screened_answer(monkeypatch):
    app=ui(monkeypatch,BANK['cases'][0]);s=app.session_state.session
    app.radio(key='conversation_familiarity').set_value('little');click(app,'Continue')
    class Broken:
        def extract_baseline(self,*a,**kw):raise AssessmentError('Local service unavailable.',code='transport')
    app.session_state._conversation_client=Broken()
    app.run()
    text='I do not know what a drone is.'
    app.text_area(key='conversation_answer_text').set_value(text);click(app,'Continue')
    assert s.failed_attempt['text']==text and app.text_area(key='conversation_answer_text').value==text
    assert any(b.label=='Retry this answer' for b in app.button)
    click(app,'Finish here');click(app,'Finish without an example');click(app,'Confirm final summary')
    assert s.stage=='final' and len(app.get('download_button'))==2
    assert any('partial assessment' in e.value for e in app.warning)


def test_scenario_inherits_frozen_instrument_and_prompts(monkeypatch):
    case=BANK['cases'][0];s=new();reach_offer(s,case)
    original=deepcopy(s.general.prompts);s.general.prompts['evidence']+='\nFrozen session marker.'
    s.general.instrument['version']='frozen-test-version'
    s.accept_scenario()
    assert s.scenario.prompts['evidence']==original['evidence']+'\nFrozen session marker.'
    assert s.scenario.instrument['version']=='frozen-test-version'
    assert s.scenario.current_question['elicitation_context']=='scenario_initial'


def test_optional_estimate_uses_only_personal_confirmed_evidence_and_exact_quotes():
    from iam_sra.readiness_score import ReadinessScore
    case=BANK['cases'][1];s=new(case);reach_offer(s,case);s.decline_scenario();s.confirm_final(actor='automation')
    # Third-party context is preserved in the interview but cannot be scored as
    # the citizen's own capability.
    event=next(e for e in s.general.events if e['question']['id']=='experience')
    event['claims'].append({**event['claims'][0],'subject':'organisation'})
    captured={}
    class Estimate:
        def assign(self,payload):
            captured.update(payload)
            return ReadinessScore(crl=None,explanation='The draft anchors do not establish a numerical result.',evidence_ids=[])
    s.provisional_estimate(Estimate())
    assert all(c['subject']=='respondent' and c['dimension']!='proposal' for c in captured['profile']['claims'])
    assert all(a['text_kind']=='exact_supporting_quotations' for a in captured['answers'])
    assert s._provisional['status']=='draft_provisional_model_judgement'
    assert s.export()['numerical_crl'] is None


@pytest.mark.presidio_live
def test_real_detector_new_planner_and_scenario_transport_envelopes(monkeypatch):
    """Real NLP, synthetic HTTP/claims; not Qwen semantic or token-budget accuracy."""
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    from iam_sra.baseline_client import BaselineClient
    from iam_sra.conversation_planner import PlannerClient
    real=httpx.Client;calls=[]
    text='I support this example but I do not know its effects.'
    def endpoint(req):
        calls.append(req.url.path)
        if req.url.path=='/tokenize':return httpx.Response(200,json={'count':200})
        payload=json.loads(json.loads(req.content)['messages'][-1]['content'])
        if 'confirmed_evidence' in payload:
            c=payload['candidates'][0]
            wire={'stage':payload['stage'],'action':'ask','target_criterion':c['criterion'],
                'candidate_id':c['candidate_id'],'source_ids':c['source_ids'],
                'triggering_evidence_ids':c['triggering_evidence_ids'],
                'displayed_question':c['allowed_wording'][0],'rationale':'Address an eligible evidence gap.'}
        elif 'candidates' in payload:
            wire={'decisions':[{'candidate':0,'supported':True,'claim_type':'proposal_supported','effect_quote':''}],
                'additional_claims':[]}
        else:
            wire={'interaction':'substantive','claims':[{'evidence_id':next(iter(payload['passages'])),
                'claim_type':'proposal_supported','span_quote':'I support this example',
                'effect_quote':'','interpretation':'You support the illustrative example.',
                'topic_ids':[],'subject':'respondent','domain':'IAM'}]}
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(wire)}}]})
    monkeypatch.setattr('iam_sra.baseline_client.httpx.Client',lambda **kw:real(transport=httpx.MockTransport(endpoint)))
    s=new();reach_offer(s,BANK['cases'][0]);s.accept_scenario(PlannerClient())
    client=BaselineClient()
    try:s.answer(text,client)
    except PrivacyError as exc:raise AssertionError(list(exc.findings)) from None
    assert s.pending['claims'][0]['kind']=='view_support'
    assert s.pending['claims'][0]['elicitation_context']=='scenario_initial'
    assert len(calls)==6
    with pytest.raises(PrivacyError):s.correct_interpretation('My PIN is 1846.',client)
    assert len(calls)==6 and all(trace['raw_output'] is None for trace in client.last_trace)


@pytest.mark.presidio_live
def test_real_detector_source_collection_load_and_metadata_do_not_exempt_secrets():
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    from iam_sra.conversation_corpus import load_corpus
    from iam_sra.privacy import require_safe_data
    if not (ROOT/config('conversation')['corpus_path']).exists():pytest.skip('Private original/corpus not supplied on this host.')
    c=load_corpus();assert len(c['questions'])==65 and len(c['scenarios'])==9
    require_safe_data({'schema_version':config('conversation')['schema_version'],'source_locators':config('conversation')['source_locators']})
    with pytest.raises(PrivacyError):require_safe_data({'schema_version':'My PIN is 1846.'})
    with pytest.raises(PrivacyError):require_safe_data({'source_locator':'My home address is 42 Example Street.'})


@pytest.mark.presidio_live
def test_real_detector_optional_estimate_envelope_and_export(monkeypatch):
    """Real detector, controlled abstention; no claimed numerical/live accuracy."""
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    from iam_sra.readiness_score import WorkbookScoreClient
    from iam_sra.privacy import require_safe_data
    def controlled(self,http,stage,system,user,schema,validator):
        try:require_safe_data({'system':system,'user':user,'schema':schema})
        except PrivacyError as exc:raise AssertionError(json.dumps(list(exc.findings))) from None
        from iam_sra.citizen_score import empty_assessment
        return validator(json.dumps(empty_assessment('The available evidence does not establish a draft level.')))
    monkeypatch.setattr(WorkbookScoreClient,'_request',controlled)
    case=BANK['cases'][1];s=new(case);reach_offer(s,case);s.decline_scenario();s.confirm_final(actor='automation')
    try:s.provisional_estimate(WorkbookScoreClient())
    except PrivacyError as exc:raise AssertionError(list(exc.findings)) from None
    d=s.export();assert d['numerical_crl'] is None and d['provisional_citizen_estimate']['crl'] is None
