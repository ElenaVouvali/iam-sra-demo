from pathlib import Path
from streamlit.testing.v1 import AppTest

def click(app,label='Continue'):
    next(b for b in app.button if b.label==label or label=='Continue' and b.label=='Confirm and finish').click().run()
    assert not app.exception

def fresh(monkeypatch,client=None):
    monkeypatch.delenv('IAM_DEVELOPER',raising=False)
    monkeypatch.setenv('IAM_MOCK','0' if client else '1')
    if client:monkeypatch.setattr('iam_sra.conversation_client.ConversationClient',lambda:client)
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()

def assert_simple(app):
    assert not app.metric and not app.dataframe and not app.json
    assert not any(e.label=='Developer diagnostics' for e in app.expander)


def test_guided_mock_session(monkeypatch):
    app=fresh(monkeypatch);click(app)
    app.text_area(key='citizen_answer').set_value('I am unsure about this route.');click(app)
    assert_simple(app);assert app.session_state.session.initial is None
    click(app,'Finish these questions')
    app.checkbox(key='confirm_'+str(app.session_state.session.version)).check().run();click(app)
    assert app.session_state.session.initial is not None
    assert_simple(app)
    app.checkbox(key='updated_confirm_'+str(app.session_state.session.version)).check().run();click(app)
    assert app.session_state.session.state.value=='comparison_export'
    assert not app.metric and not app.dataframe and not app.json
    assert any(x.value=='Insufficient evidence for a numerical assessment' for x in app.subheader)
    assert len(app.get('download_button'))==2
    assert len(app.session_state.session.export()['domain_assessments'])==15


def test_discovery_ui_preserves_draft_after_controlled_error(monkeypatch):
    from test_discovery import DiscoveryFake
    from test_confirmation import meaning
    from iam_sra.assessment import AssessmentError
    client=DiscoveryFake(meaning(scores=()));app=fresh(monkeypatch,client)
    click(app);app.text_area(key='citizen_answer').set_value('I reject.');click(app)
    assert_simple(app)
    app.multiselect(key='D1_selection').set_value(['noise']);click(app)
    app.text_area(key='D2_text').set_value('The hum disrupts me.')
    def fail(*args,**kwargs):raise AssessmentError('Internal schema diagnostic',code='schema')
    client.interpret=fail;click(app)
    assert app.text_area(key='D2_text').value=='The hum disrupts me.'
    assert app.error and 'schema' not in app.error[0].value
    click(app,'Skip')
    if any(b.label=='Finish these questions' for b in app.button):click(app,'Finish these questions')
    assert any(c.label=='This reflects what I meant' for c in app.checkbox)


def test_retry_keeps_confirmation_and_never_displays_initial_scores(monkeypatch):
    from test_confirmation import Fake,meaning
    from iam_sra.assessment import AssessmentError
    client=Fake(meaning(position='supported'));app=fresh(monkeypatch,client)
    click(app);app.text_area(key='citizen_answer').set_value('The hum is acceptable.');click(app)
    app.checkbox(key='confirm_1').check().run()
    original=client.score
    client.score=lambda *args,**kwargs:(_ for _ in ()).throw(AssessmentError('transport',code='transport'))
    click(app)
    s=app.session_state.session
    assert s.state.value=='confirmed_interpretation' and len(s.confirmations)==1 and s.initial is None
    assert_simple(app)
    client.score=original;click(app)
    assert len(s.confirmations)==1 and s.initial is not None
    assert_simple(app)
