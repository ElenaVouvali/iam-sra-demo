from pathlib import Path
from streamlit.testing.v1 import AppTest
from test_readiness_evidence_mode import Extractor, record


def start(monkeypatch, client):
    monkeypatch.delenv('IAM_ASSESSMENT_MODE',raising=False)
    monkeypatch.delenv('IAM_DEVELOPER',raising=False)
    monkeypatch.setenv('IAM_MOCK','0')
    monkeypatch.setattr('iam_sra.readiness_client.ReadinessClient',lambda:client)
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()


def click(app,label):
    next(b for b in app.button if b.label==label).click().run()
    assert not app.exception


def confirm(app):
    next(c for c in app.checkbox if c.label=='This reflects what I meant').check().run()
    click(app,'Confirm and continue')


def test_default_full_ui_no_numeric_results_and_export_agrees(monkeypatch):
    app=start(monkeypatch,Extractor([record()],concerns=['Repeated sound'],conditions=['Reduce exposure']))
    assert not app.metric and not app.exception
    app.text_area(key='readiness_answer').set_value('I oppose repeated flights because sound could interrupt rest.')
    click(app,'Continue');assert app.session_state.session.pending['text'].startswith('I oppose')
    confirm(app)
    assert app.session_state.session.current_question['criterion_id']=='information'
    click(app,'Finish questions')
    assert app.session_state.session.state=='final'
    assert not app.metric and not app.get('progress')
    titles=[e.value for e in app.subheader]
    assert 'Your view of the proposal' in titles and 'Your readiness evidence' in titles
    result=app.session_state.session.export()
    assert app.info[0].value==result['readiness_score_status']['reason']
    assert len(app.get('download_button'))==2
    assert not any('9/9' in e.value for e in app.markdown)


def test_followup_form_reads_submitted_value_and_skip_is_accessible(monkeypatch):
    client=Extractor(stance='supported');app=start(monkeypatch,client)
    app.text_area(key='readiness_answer').set_value('I accept this without concerns.');click(app,'Continue');confirm(app)
    q=app.session_state.session.current_question
    app.text_area(key='readiness_followup_'+q['id']).set_value('Neighbours working nights might rest during the day.')
    click(app,'Continue')
    assert app.session_state.session.pending['text']=='Neighbours working nights might rest during the day.'
    confirm(app);click(app,'Skip');click(app,'Finish questions')
    assert not app.metric


def test_model_error_keeps_input_and_no_historical_fallback(monkeypatch):
    from iam_sra.assessment import AssessmentError
    class Broken:
        def extract_readiness(self,*a,**kw):raise AssessmentError('offline',code='transport')
    app=start(monkeypatch,Broken());text='I am not ready to express a view.'
    app.text_area(key='readiness_answer').set_value(text);click(app,'Continue')
    assert app.error and app.text_area(key='readiness_answer').value==text
    assert app.session_state.session.state=='answer' and not app.metric


def test_mode_environment_change_does_not_change_existing_session(monkeypatch):
    app=start(monkeypatch,Extractor());assert app.session_state.session.assessment_mode=='acceptance_and_readiness_evidence'
    monkeypatch.setenv('IAM_ASSESSMENT_MODE','legacy_fn_acceptance_demo');app.run()
    assert app.session_state.session.assessment_mode=='acceptance_and_readiness_evidence'


def test_developer_mode_choice_precedes_session_creation(monkeypatch):
    monkeypatch.setenv('IAM_DEVELOPER','1');monkeypatch.setenv('IAM_MOCK','1')
    monkeypatch.delenv('IAM_ASSESSMENT_MODE',raising=False)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()
    assert 'session' not in app.session_state
    app.selectbox(key='assessment_mode_choice').select('legacy_fn_acceptance_demo').run()
    assert 'session' not in app.session_state
    click(app,'Start selected demo')
    assert app.session_state.session.assessment_mode=='legacy_fn_acceptance_demo'
    assert any(w.value=='Historical experimental acceptance index' for w in app.warning)


def test_failure_diagnostics_accessible_without_developer_mode(monkeypatch):
    from iam_sra.assessment import AssessmentError
    class Broken:
        last_request_context={'stage':'readiness_evidence'}
        last_diagnostics=[{'failure':'schema'}]
        def extract_readiness(self,*args,**kwargs):raise AssessmentError('Missing supporting citation',code='schema')
    app=start(monkeypatch,Broken());app.text_area(key='readiness_answer').set_value('I oppose the proposal.');click(app,'Continue')
    assert 'required format' in app.error[0].value
    assert any(e.label=='Technical details for this failed attempt' for e in app.expander)
    assert app.session_state.readiness_failure_details['error_code']=='schema'
    assert app.session_state.readiness_failure_details['message']=='Missing supporting citation'
    assert app.session_state.session.state=='answer'


def test_optional_learning_uses_a_bounded_question_and_preserves_initial(monkeypatch):
    app=start(monkeypatch,Extractor([record()]))
    app.text_area(key='readiness_answer').set_value('Repeated flights could disturb my rest.')
    click(app,'Continue');confirm(app)
    initial=app.session_state.session.initial_readiness
    click(app,'I have read this — reflect on it')
    q=app.session_state.session.current_question
    assert q['elicitation_context']=='after_information_exposure'
    assert 'In your own words' in q['question_text']
    assert app.session_state.session.initial_readiness==initial
    click(app,'Skip');click(app,'Finish questions')
    out=app.session_state.session.export()
    assert not out['information_exposures'][0]['understanding_verified']
    assert out['numerical_crl'] is None and not app.metric
