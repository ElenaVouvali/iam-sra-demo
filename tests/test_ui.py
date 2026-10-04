from pathlib import Path
from streamlit.testing.v1 import AppTest

def click(app,label):
    next(b for b in app.button if b.label==label).click().run()
    assert not app.exception

def test_guided_mock_session(monkeypatch):
    monkeypatch.setenv('IAM_MOCK','1')
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()
    click(app,'Begin')
    app.text_area(key='citizen_answer').set_value('I am unsure about this route.')
    click(app,'Interpret response')
    assert app.session_state.session.initial is None
    assert not app.metric
    if any(b.label=='Finish discovery' for b in app.button):click(app,'Finish discovery')
    next(c for c in app.checkbox if c.label=='This interpretation reflects what I meant').check().run()
    click(app,'Confirm meaning')
    assert app.session_state.session.initial is None
    click(app,'Calculate initial provisional scores')
    click(app,'Continue to follow-ups')
    next(c for c in app.checkbox if c.label=='The updated original and hypothetical interpretations reflect what I meant').check().run()
    click(app,'Confirm updated meaning')
    click(app,'Calculate final provisional scores')
    assert app.session_state.session.state.value=='comparison_export'
    assert app.session_state.session.export()['initial']['aggregate']['rounded'] is None
    assert len(app.dataframe)==1 and len(app.dataframe[0].value)==15
    assert len(app.get('download_button'))==2


def test_discovery_ui_preserves_draft_after_controlled_error(monkeypatch):
    from test_discovery import DiscoveryFake
    from test_confirmation import meaning
    from iam_sra.assessment import AssessmentError
    client=DiscoveryFake(meaning(scores=()))
    monkeypatch.setenv('IAM_MOCK','0')
    monkeypatch.setattr('iam_sra.conversation_client.ConversationClient',lambda:client)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()
    click(app,'Begin');app.text_area(key='citizen_answer').set_value('I reject.')
    click(app,'Interpret response')
    assert not app.metric and any('A few questions' in i.value for i in app.info)
    app.multiselect(key='D1_selection').set_value(['noise']);click(app,'Record discovery answer')
    app.text_area(key='D2_text').set_value('The hum disrupts me.')
    def fail(*args,**kwargs):raise AssessmentError('Internal schema diagnostic',code='schema')
    client.interpret=fail;click(app,'Record discovery answer')
    assert app.text_area(key='D2_text').value=='The hum disrupts me.'
    assert app.error and 'schema' not in app.error[0].value
    assert not app.session_state.session.discovery_responses[-1]['question_id']=='D2'
    click(app,'Skip this question');click(app,'Finish discovery') if any(b.label=='Finish discovery' for b in app.button) else None
    assert any(c.label=='This interpretation reflects what I meant' for c in app.checkbox)
