"""Offline full validation flow through the actual Streamlit UI."""
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from test_core import payload

def test_ui_full_validation_and_export(monkeypatch):
    from iam_sra.assessment import parse_assessment
    def interpret(self,text):
        return parse_assessment(json.dumps(payload({'noise':3,'visual_pollution':4,'perceived_safety_privacy':2},text)),text)
    monkeypatch.setenv('IAM_MOCK','0')
    monkeypatch.setattr('iam_sra.llm_client.LLMClient.__call__',interpret)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    app.button[1].click().run()
    app.text_area[0].set_value('Noise, visible drones and cameras worry me.')
    app.button[1].click().run()
    assert not app.exception
    original=app.session_state.session.original.model_dump()
    next(b for b in app.button if b.label=='Continue to hypothetical questions').click().run()
    app.run()
    for index in [0,1,1]:
        app.radio[0].set_value(app.radio[0].options[index])
        next(b for b in app.button if b.label=='Record and continue').click().run()
        assert not app.exception
        app.run()
    session=app.session_state.session
    assert session.state.value=='final_report'
    assert len(session.responses)==3 and session.original.model_dump()==original
    assert 'Visual clutter remains' in session.responses[1]['outcome']
    assert all(r['numerical_update'] is None for r in session.responses)
