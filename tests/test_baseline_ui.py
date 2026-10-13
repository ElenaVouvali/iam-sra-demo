from pathlib import Path
from streamlit.testing.v1 import AppTest
from test_baseline import Extractor,claim


def start(monkeypatch,client=None):
    monkeypatch.delenv('IAM_ASSESSMENT_MODE',raising=False)
    monkeypatch.delenv('IAM_DEVELOPER',raising=False)
    monkeypatch.setenv('IAM_MOCK','0')
    monkeypatch.setattr('iam_sra.baseline_client.BaselineClient',lambda:client or Extractor())
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run()
    app.selectbox(key='baseline_perspective').select('personal').run()
    app.selectbox(key='baseline_stakeholder_category').select('citizen').run()
    app.selectbox(key='baseline_city').select('withheld').run()
    return app


def click(app,label):
    next(b for b in app.button if b.label==label).click().run()
    assert not app.exception


def test_default_context_scenario_free_confirm_complete_and_downloads(monkeypatch):
    app=start(monkeypatch,Extractor([claim()]))
    assert not app.exception
    assert app.session_state.session.assessment_mode=='general_baseline'
    content=' '.join(e.value for e in list(app.title)+list(app.markdown))
    assert 'medical delivery route' not in content and '60 meters' not in content
    assert not app.text_area
    assert not any('responsibility' in f.label for f in app.text_input)
    click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value('Repeated sound could interrupt rest.');click(app,'Continue')
    assert app.session_state.session.state=='review'
    assert any('interrupt rest' in e.value for e in app.text)
    click(app,'Confirm and continue');click(app,'Finish now')
    assert app.session_state.session.state=='baseline_review'
    click(app,'Confirm summary')
    assert app.session_state.session.state=='complete'
    assert len(app.get('download_button'))==2 and not app.metric
    assert app.session_state.session.export()['numerical_crl'] is None
    assert any(b.label=='Explore a hospital drone route' for b in app.button)


def test_org_optional_fields_edit_and_pending_specialised_route(monkeypatch):
    app=start(monkeypatch)
    app.selectbox(key='baseline_perspective').select('organisation').run()
    assert any('responsibility' in f.label for f in app.text_input)
    app.selectbox(key='baseline_city').select('other').run()
    app.text_input(key='baseline_place_text').set_value('Northern region')
    app.text_input(key='baseline_function_text').set_value('Service planning')
    click(app,'Begin');click(app,'Finish now');click(app,'Confirm summary')
    assert not any(b.label=='Explore a hospital drone route' for b in app.button)
    click(app,'Back');click(app,'Back')
    assert app.session_state.session.state=='context'
    assert app.session_state.session.completed_baseline is None


def test_privacy_rejected_answer_cleared_no_question_consumed(monkeypatch):
    client=Extractor();app=start(monkeypatch,client)
    click(app,'Begin');app.radio(key='baseline_familiarity').set_value('no');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value('My PIN is 1846.');click(app,'Continue')
    assert app.text_area(key='baseline_answer_text').value==''
    assert not client.calls and len(app.session_state.session.events)==1
    assert app.session_state.session.current_question['id']=='concept'


def test_address_cleaned_preview_requires_confirmation(monkeypatch):
    app=start(monkeypatch)
    app.selectbox(key='baseline_city').select('other').run()
    app.text_input(key='baseline_place_text').set_value('My address is 42 Example Street')
    click(app,'Begin')
    assert app.session_state.session.state=='welcome'
    assert app.text_input(key='baseline_place_text').value==''
    assert any(b.label=='Confirm cleaned text' for b in app.button)
    click(app,'Confirm cleaned text')
    assert app.session_state.session.state=='interview'
    assert '42 Example Street' not in app.session_state.session.json()


def test_pending_correction_uses_same_prompt_and_does_not_confirm_automatically(monkeypatch):
    app=start(monkeypatch);click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value('I am unsure.');click(app,'Continue')
    before=app.session_state.session.prompt_hashes.copy()
    app.text_area(key=f"baseline_interpretation_{app.session_state.session.pending['id']}_0").set_value('I have not formed an understanding yet.')
    click(app,'Apply my correction')
    assert app.session_state.session.state=='review' and app.session_state.session.prompt_hashes==before
    click(app,'Confirm and continue')
    assert app.session_state.session.events[-1]['text']=='I am unsure.'
    assert app.session_state.session.interpretation_reviews[-1]['feedback']=='I have not formed an understanding yet.'


def test_no_small_notes_supporting_words_or_phase_labels(monkeypatch):
    app=start(monkeypatch,Extractor([claim()]))
    assert not app.caption
    click(app,'Begin');app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value('Sound could interrupt rest.');click(app,'Continue')
    assert not any('Supporting words' in e.label for e in app.expander)
    assert not app.caption
    click(app,'Confirm and continue');click(app,'Finish now');click(app,'Confirm summary')
    assert not any('Supporting words' in e.label for e in app.expander)
    visible=' '.join(e.value for e in list(app.markdown)+list(app.subheader)+list(app.text))
    assert 'Phase 1' not in visible and 'baseline' not in visible.lower()


def test_welcome_title_eight_budget_and_explicit_definition_display(monkeypatch):
    app=start(monkeypatch)
    assert app.title[0].value=='Drones in your community'
    assert any('No technical knowledge is needed' in x.value for x in app.markdown)
    click(app,'Begin');app.radio(key='baseline_familiarity').set_value('no');click(app,'Continue')
    assert not any('up to 8' in x.value for x in app.markdown)
    assert not app.session_state.session.information_exposures
    assert not any('without a person on board' in x.value for x in app.text)
    click(app,'Show definition')
    assert len(app.session_state.session.information_exposures)==1
    assert any('without a person on board' in x.value for x in app.text)
    click(app,'Skip');click(app,'Finish now');click(app,'Confirm summary')
    assert any(e.label=='What we have not discussed' for e in app.expander)
    assert len(app.get('download_button'))==2


def test_back_reopens_answer_and_previous_question_without_inference(monkeypatch):
    client=Extractor([claim()]);app=start(monkeypatch,client)
    click(app,'Begin');click(app,'Back')
    assert app.session_state.session.state=='context'
    click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value('Repeated sound could interrupt rest.');click(app,'Continue')
    calls=len(client.calls)
    click(app,'Back')
    assert app.session_state.session.state=='interview'
    assert app.text_area(key='baseline_answer_text').value=='Repeated sound could interrupt rest.'
    assert len(client.calls)==calls
    click(app,'Continue');click(app,'Confirm and continue')
    snapshot=app.session_state.session.initial_baseline
    click(app,'Back')
    assert app.session_state.session.current_question['id']=='concept'
    assert app.text_area(key='baseline_answer_text').value=='Repeated sound could interrupt rest.'
    assert app.session_state.session.initial_baseline==snapshot


def test_back_from_completed_summary_requires_confirmation_again(monkeypatch):
    app=start(monkeypatch);click(app,'Begin');click(app,'Finish now');click(app,'Confirm summary')
    s=app.session_state.session
    snapshot=s.completed_snapshots.copy()
    click(app,'Back')
    assert s.state=='baseline_review' and s.completed_baseline is None
    assert s.completed_snapshots==snapshot and s.handoff_record is None
    click(app,'Back')
    assert s.state=='context'


def test_privacy_notice_is_information_box_and_preview_explains_next_step(monkeypatch):
    from iam_sra.privacy import NOTICE
    app=start(monkeypatch);click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    assert any(e.value==NOTICE for e in app.info)
    app.text_area(key='baseline_answer_text').set_value('Drones could help deliveries. My home address is 42 Example Street.');click(app,'Continue')
    assert any('has not been submitted for assessment' in e.value for e in app.info)
    assert not app.session_state.session.pending
    click(app,'Write a general description instead')
    assert 'privacy_prepared' not in app.session_state
    assert app.text_area(key='baseline_answer_text').value==''
    assert app.session_state.session.current_question['id']=='concept'


def test_address_only_answer_requests_resubmission_without_consuming_question(monkeypatch):
    client=Extractor();app=start(monkeypatch,client);click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    before=len(app.session_state.session.events)
    app.text_area(key='baseline_answer_text').set_value('My home address is 42 Example Street.');click(app,'Continue')
    assert any('leaving no answer to assess' in e.value for e in app.warning)
    assert not any(b.label=='Confirm cleaned text' for b in app.button)
    assert 'privacy_prepared' not in app.session_state
    assert len(app.session_state.session.events)==before
    assert app.session_state.session.current_question['id']=='concept'
    assert not client.calls
    assert app.text_area(key='baseline_answer_text').value==''
    app.text_area(key='baseline_answer_text').set_value('An aircraft without a pilot on board.');click(app,'Continue')
    assert app.session_state.session.state=='review'


def test_organisational_role_variant_and_interleaved_outcome_journey(monkeypatch):
    client=Extractor([claim('participation','contribution',subject='organisation',temporality='actual',domain='IAM',topic_ids=[],interpretation='Your team submitted consultation comments.')])
    app=start(monkeypatch,client)
    app.selectbox(key='baseline_perspective').select('organisation').run()
    app.selectbox(key='baseline_stakeholder_category').select('authority').run()
    click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    while app.session_state.session.current_question['id']!='experience':click(app,'Skip')
    assert any('Has your authority considered' in e.value for e in app.markdown)
    app.text_area(key='baseline_answer_text').set_value('Our team submitted consultation comments.');click(app,'Continue')
    assert app.session_state.session.state=='review'
    click(app,'Confirm and continue')
    assert app.session_state.session.current_question['id']=='influence'
    click(app,'Unsure')
    assert app.session_state.session.current_question['id']=='needs'
    click(app,'Skip');click(app,'Skip');click(app,'Confirm summary')
    data=app.session_state.session.export()
    assert data['role_mapping']['mapped_role']=='authority'
    assert data['current_profile']['coverage']['influence']['status']=='unknown'
    assert data['numerical_orl'] is None
    assert len(app.get('download_button'))==2
