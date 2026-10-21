"""Actual Streamlit continuation using the shared controller and synthetic bank."""
from streamlit.testing.v1 import AppTest
from indicator_fixtures import Client


def test_streamlit_shared_indicator_journey_and_correction(monkeypatch):
    monkeypatch.setattr('iam_sra.indicator_ui.IndicatorClient',lambda:Client())
    app=AppTest.from_string('''
import streamlit as st
from indicator_fixtures import engine
from iam_sra.conversation_ui import render
from iam_sra.baseline_client import MockBaselineClient
if 'demo' not in st.session_state:st.session_state.demo=engine()
render(st.session_state.demo,MockBaselineClient(),None)
''',default_timeout=20).run()
    def click(label):
        next(b for b in app.button if b.label==label).click().run()
        assert not app.exception
    assert not app.exception
    assert not any('Request a provisional estimate'==b.label for b in app.button)
    app.multiselect(key='indicator_selection').set_value(['indicator-07']).run()
    click('Begin selected indicators')
    s=app.session_state.demo
    app.text_area(key=f'indicator_answer_text_{s.indicators.revision}').set_value('I propose protections for rest.')
    click('Submit indicator answer')
    assert any('Proposed condition or safeguard' in t.value and 'your own reasoning or action' in t.value for t in app.text)
    click('Confirm indicator interpretation');click('Finish indicator questions')
    click('Request draft indicator suggestion')
    assert s.indicators.current['participant'] is None
    app.selectbox(key=f'indicator_review_choice_{s.indicators.revision}').set_value('indicator-07-crl-3').run()
    click('Record my selected statement')
    assert s.indicators.current['participant']['statement']['level']==3
    assert s.indicators.current['tool']['statement']['level']==5
    assert len(app.get('download_button'))==2
    click('Edit indicator answer')
    assert s.indicators.current['participant'] is None and s.indicators.current['tool'] is None
    assert app.text_area(key=f'indicator_answer_text_{s.indicators.revision}').value=='I propose protections for rest.'
