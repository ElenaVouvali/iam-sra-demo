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
    assert 'Your views of this proposal' in titles and 'What you told us about understanding and participation' in titles
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


def test_failure_diagnostics_hidden_without_developer_mode(monkeypatch):
    from iam_sra.assessment import AssessmentError
    class Broken:
        last_request_context={'stage':'readiness_evidence'}
        last_diagnostics=[{'failure':'schema'}]
        def extract_readiness(self,*args,**kwargs):raise AssessmentError('Missing supporting citation',code='schema')
    app=start(monkeypatch,Broken());app.text_area(key='readiness_answer').set_value('I oppose the proposal.');click(app,'Continue')
    assert 'finish reading' in app.error[0].value
    assert not any(e.label=='Technical details for this failed attempt' for e in app.expander)
    assert not app.json
    assert app.session_state.readiness_failure_details['error_code']=='schema'
    assert app.session_state.readiness_failure_details['message']=='Missing supporting citation'
    assert app.session_state.session.state=='answer'


def test_optional_learning_uses_a_bounded_question_and_preserves_initial(monkeypatch):
    app=start(monkeypatch,Extractor([record()]))
    app.text_area(key='readiness_answer').set_value('Repeated flights could disturb my rest.')
    click(app,'Continue');confirm(app)
    initial=app.session_state.session.initial_readiness
    click(app,'Show explanation')
    click(app,'Read and reflect')
    q=app.session_state.session.current_question
    assert q['elicitation_context']=='after_information_exposure'
    assert 'In your own words' in q['question_text']
    assert app.session_state.session.initial_readiness==initial
    click(app,'Skip');click(app,'Finish questions')
    out=app.session_state.session.export()
    assert not out['information_exposures'][0]['understanding_verified']
    assert out['numerical_crl'] is None and not app.metric


def test_start_over_needs_explicit_confirmation_and_cancel_keeps_draft(monkeypatch):
    app=start(monkeypatch,Extractor())
    app.text_area(key='readiness_answer').set_value('My draft matters.')
    sid=app.session_state.session.session_id
    click(app,'Start over')
    assert app.session_state.session.session_id==sid
    assert app.text_area(key='readiness_answer').value=='My draft matters.'
    click(app,'Keep this session')
    assert app.session_state.session.session_id==sid
    assert app.text_area(key='readiness_answer').value=='My draft matters.'
    click(app,'Start over');click(app,'Discard and restart')
    assert app.session_state.session.session_id!=sid
    assert app.text_area(key='readiness_answer').value==''


def test_correction_from_summary_invalidates_results_and_retains_initial(monkeypatch):
    app=start(monkeypatch,Extractor([record()]))
    app.text_area(key='readiness_answer').set_value('Repeated sound could disturb rest.')
    click(app,'Continue');confirm(app);click(app,'Finish questions')
    initial=app.session_state.session.initial_readiness
    click(app,'Your first answer')
    assert app.session_state.session.final_readiness is None
    assert app.session_state.session.initial_readiness==initial
    assert not app.get('download_button')
    assert app.text_area(key='readiness_answer').value=='Repeated sound could disturb rest.'
    app.text_area(key='readiness_answer').set_value('I want to correct that answer.')
    click(app,'Continue');confirm(app)
    assert app.session_state.session.corrections
    assert app.session_state.session.events[0]['active'] is False


def test_unsure_skip_and_finish_remain_distinct_in_export(monkeypatch):
    app=start(monkeypatch,Extractor())
    app.text_area(key='readiness_answer').set_value('I am unsure.')
    click(app,'Continue');confirm(app)
    click(app,'Unsure');click(app,'Skip');click(app,'Finish questions')
    out=app.session_state.session.export()
    assert [a['control'] for a in app.session_state.session.answers]==['unsure','skip']
    assert out['stop_reason']=='user_finish'
    assert out['numerical_crl'] is None and out['numerical_srl'] is None
    assert not app.json
    assert len(app.get('download_button'))==2


def test_long_text_is_not_cut_and_every_screen_has_one_main_action(monkeypatch):
    long='Possible effects on rest need checking. '*6
    app=start(monkeypatch,Extractor([record(interpretation=long)],concerns=['Unbroken'+('x'*500)]))
    text='I have a view about these flights. '*40
    app.text_area(key='readiness_answer').set_value(text)
    assert sum(b.proto.type=='primary' for b in app.button)==1
    click(app,'Continue')
    assert any(long.strip()==t.value for t in app.text)
    assert not any(e.label=='Your supporting words' for e in app.expander)
    assert not any(text.strip()==t.value for t in app.text)
    assert app.session_state.session.pending['text']==text
    assert sum(b.proto.type=='primary' for b in app.button)==1
    confirm(app)
    assert sum(b.proto.type=='primary' for b in app.button)==1


def test_developer_can_inspect_failure_details_without_citizen_exposure(monkeypatch):
    from iam_sra.assessment import AssessmentError
    class Broken:
        def extract_readiness(self,*args,**kwargs):raise AssessmentError('schema detail',code='schema')
    app=start(monkeypatch,Broken())
    monkeypatch.setenv('IAM_DEVELOPER','1');app.run()
    app.text_area(key='readiness_answer').set_value('My view.')
    click(app,'Continue')
    assert any(e.label=='Technical details for this failed attempt' for e in app.expander)
    assert app.json


def test_downloads_are_complete_exports_and_summary_is_not_a_score(monkeypatch):
    import json
    import streamlit as st
    captured={};original=st.download_button
    def download(label,data,*args,**kwargs):
        captured[label]=data
        return original(label,data,*args,**kwargs)
    monkeypatch.setattr(st,'download_button',download)
    app=start(monkeypatch,Extractor(stance='supported'))
    app.text_area(key='readiness_answer').set_value('I support it but have no other details.')
    click(app,'Continue');confirm(app);click(app,'Finish questions')
    out=app.session_state.session.export()
    assert json.loads(captured['Download JSON'])==out
    assert json.loads(captured['Download JSONL'])==out
    assert out['readiness_score_status']['reason']==app.info[0].value
    assert out['instrument']['initial_invitation']== 'What do you think about this proposal? What matters most to you?'
    assert out['numerical_crl'] is None and out['numerical_srl'] is None


def test_existing_instrument_keeps_previous_invitation(monkeypatch):
    app=start(monkeypatch,Extractor())
    s=app.session_state.session
    s.instrument.pop('initial_invitation')
    s.instrument['version']='1.2.1'
    app.run()
    assert app.text_area(key='readiness_answer').label=='How do you feel about this proposal? What would make it acceptable?'
    assert app.warning
    assert app.session_state.session.instrument['version']=='1.2.1'


def test_optional_information_needs_explicit_logged_display(monkeypatch):
    app=start(monkeypatch,Extractor([record()]))
    app.text_area(key='readiness_answer').set_value('Sound could interrupt rest.')
    click(app,'Continue');confirm(app)
    s=app.session_state.session
    # Streamlit executes collapsed expanders too: content must be absent, not hidden.
    assert not s.information_exposures
    assert not any('example specifies up to 15' in e.value for e in app.markdown)
    assert not any(b.label=='Read and reflect' for b in app.button)
    click(app,'Show explanation')
    s=app.session_state.session
    assert s.information_exposures[-1]['source']=='controlled_demo_explanation_display'
    assert any('example specifies up to 15' in e.value for e in app.markdown)
    assert not s.information_acknowledgements
    click(app,'I have read this')
    assert len(app.session_state.session.information_acknowledgements)==1


def test_optional_retrieval_failure_shows_sources_and_logs_exact_content(monkeypatch):
    from test_readiness_retrieval import Composer
    monkeypatch.setattr('iam_sra.readiness_retrieval.ExplanationClient',Composer)
    app=start(monkeypatch,Extractor([record()]))
    app.text_area(key='readiness_answer').set_value('Sound could interrupt rest.')
    click(app,'Continue');confirm(app)
    initial=app.session_state.session.initial_readiness
    app.text_input(key='information_custom').set_value('Are camera images recorded or retained?')
    click(app,'Show sourced answer')
    s=app.session_state.session;exposure=s.information_exposures[-1]
    assert exposure['source']=='local_retrieval_display'
    assert exposure['content']['excerpts'] and s.initial_readiness==initial
    assert len(s.answers)==0 and not app.exception
    assert not any(e.label=='Researcher evidence report' for e in app.expander)
    assert not any(e.label=='FN historical reference comparison' for e in app.expander)


def test_developer_reference_and_report_do_not_change_citizen_session(monkeypatch):
    client=Extractor(stance='opposed');app=start(monkeypatch,client)
    app.text_area(key='readiness_answer').set_value('I oppose this route.');click(app,'Continue');confirm(app)
    click(app,'Finish questions')
    before=app.session_state.session.export()
    monkeypatch.setenv('IAM_DEVELOPER','1');app.run()
    assert not app.exception
    assert any(e.label=='FN historical reference comparison' for e in app.expander)
    assert any(e.label=='Researcher evidence report' for e in app.expander)
    assert app.session_state.session.export()==before
    click(app,'Interpret reference answer')
    reference=app.session_state.fn_reference_interpretation
    assert reference['confirmation'].startswith('Unconfirmed')
    assert reference['pending_interpretation']['text'].startswith('Look, I get')
    assert app.session_state.session.export()==before


def test_initial_review_does_not_describe_proposal_views_as_no_further_details(monkeypatch):
    app=start(monkeypatch,Extractor(stance='opposed',concerns=['Noise interrupts rest','Cameras view private spaces'],conditions=['Use a different route']))
    app.text_area(key='readiness_answer').set_value('I oppose noise and cameras over my home; use another route.')
    click(app,'Continue')
    text=' '.join(e.value for e in list(app.markdown)+list(app.text))
    assert 'adds no further details' not in text
    assert 'Noise interrupts rest' in text and 'Cameras view private spaces' in text
    click(app,'Re-read my answer')
    assert app.session_state.session.state=='review'
    assert not app.session_state.session.answers and not app.session_state.session.events
