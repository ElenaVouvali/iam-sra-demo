"""Actual Streamlit continuation using the shared controller and synthetic bank."""
import pytest
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
    click('Confirm indicator interpretation')
    assert s.indicators.current['state']=='ready'  # No unresolved follow-up was proposed by the fixture.
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


def test_streamlit_direct_route_all_three_profiles(monkeypatch):
    monkeypatch.setattr('iam_sra.indicator_ui.IndicatorClient',lambda:Client())
    for profile in ('citizen','organisational','technical'):
        app=AppTest.from_string('''
import streamlit as st
from indicator_fixtures import bank, questionnaire
from iam_sra.indicator_assessment import IndicatorAssessment
from iam_sra.conversation_session import ConversationSession
from iam_sra.synthetic_runner import synthetic_collection
from iam_sra.conversation_ui import render
from iam_sra.baseline_client import MockBaselineClient
if 'demo' not in st.session_state:
    st.session_state.demo=ConversationSession(synthetic_collection())
    st.session_state.demo.indicators=IndicatorAssessment(bank(),questionnaire())
render(st.session_state.demo,MockBaselineClient(),None)
''',default_timeout=20).run()
        def click(label):
            next(b for b in app.button if b.label==label).click().run()
            assert not app.exception
        app.selectbox(key='assessment_profile').set_value(profile).run()
        app.text_input(key='assessment_use_case').set_value('Synthetic service')
        click('Begin indicator assessment');s=app.session_state.demo
        assert s.indicators.profile==profile and len(s.indicators.selected)==15 and not s.general.events
        if profile!='citizen':
            revision=str(s.indicators.revision)
            if profile=='organisational':
                app.text_input(key='organisation_or_unit_'+revision).set_value('Planning unit')
                app.text_input(key='responsibilities_'+revision).set_value('Planning')
            else:app.text_input(key='technical_object_'+revision).set_value('Test model')
            click('Confirm indicator scope')
        app.text_area(key=f'indicator_answer_text_{s.indicators.revision}').set_value('I propose safeguards.')
        click('Submit indicator answer');click('Confirm indicator interpretation');click('Request draft indicator suggestion');click('Remain unsure about my level')
        click('Finish with my current indicator profile')
        assert s.indicators.report_finished and s.indicators.current['participant']['status']=='unsure'
        assert len(app.get('download_button'))==2


@pytest.mark.parametrize("change_profile",[False,True])
def test_keyword_onboarding_privacy_preview_does_not_retain_original(monkeypatch,change_profile):
    app=AppTest.from_string('''
import streamlit as st
from indicator_fixtures import bank, questionnaire
from iam_sra.indicator_assessment import IndicatorAssessment
from iam_sra.conversation_session import ConversationSession
from iam_sra.synthetic_runner import synthetic_collection
from iam_sra.conversation_ui import render
from iam_sra.baseline_client import MockBaselineClient
if 'demo' not in st.session_state:
    st.session_state.demo=ConversationSession(synthetic_collection())
    st.session_state.demo.indicators=IndicatorAssessment(bank(),questionnaire())
render(st.session_state.demo,MockBaselineClient(),None)
''',default_timeout=20).run()
    def click(label):
        next(b for b in app.button if b.label==label).click().run()
        assert not app.exception
    app.selectbox(key='assessment_profile').set_value('citizen').run()
    app.text_input(key='assessment_use_case').set_value('Alice Example proposed a service.')
    click('Begin indicator assessment')
    assert app.session_state.demo.state=='general_welcome'
    assert 'Alice Example' not in app.session_state.privacy_preview
    assert app.text_input(key='assessment_use_case').value==''
    if change_profile:
        app.selectbox(key='assessment_profile').set_value('technical').run()
        assert 'privacy_prepared' not in app.session_state
        assert app.session_state.demo.state=='general_welcome'
        return
    click('Confirm cleaned text')
    assert app.session_state.demo.assessment_route
    assert '[private detail removed]' in app.session_state.demo.indicators.scope['use_case']
    assert 'Alice Example' not in repr(app.session_state.demo.export())
