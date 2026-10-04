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
