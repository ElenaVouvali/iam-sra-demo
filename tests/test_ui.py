from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_guided_mock_session(monkeypatch):
    monkeypatch.setenv('IAM_MOCK','1')
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    assert not app.exception
    app.button[1].click().run()
    app.text_area[0].set_value('I am unsure about this route.')
    app.button[1].click().run()
    assert not app.exception
    app.checkbox[0].check().run()
    next(b for b in app.button if b.label=='Continue to hypothetical questions').click().run()
    assert not app.exception
    assert app.session_state.session.state.value=='final_report'
    assert app.session_state.session.export()['original_aggregate']['rounded'] is None
