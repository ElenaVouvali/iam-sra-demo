"""Guided citizen flow with initial/final assessments and developer diagnostics."""
import os
import streamlit as st
from iam_sra.settings import config
from iam_sra.session import Session

from iam_sra.privacy import NOTICE, PrivacyError, check_contract, safe_message, safe_diagnostics
from iam_sra.ui_presentation import TITLE, header, restart_control, footer
st.set_page_config(page_title=TITLE,layout='centered')
header(baseline=getattr(st.session_state.get('session'),'assessment_mode',os.getenv('IAM_ASSESSMENT_MODE','general_baseline'))=='general_baseline')
mock=os.getenv('IAM_MOCK','0')=='1'
developer=os.getenv('IAM_DEVELOPER','0')=='1'
# Mode is selected only when creating a session. Existing sessions retain their
# original instrument, including historical sessions created before this update.
selected_mode=os.getenv('IAM_ASSESSMENT_MODE','general_baseline')
if 'session' not in st.session_state and selected_mode not in config('assessment_modes')['modes']:
    st.error('This mode is available on the legacy branch. Use general_baseline or acceptance_and_readiness_evidence here.')
    st.stop()
if developer and 'session' not in st.session_state:
    st.selectbox('Demo assessment mode',list(config('assessment_modes')['modes']),
        index=list(config('assessment_modes')['modes']).index(selected_mode),
        format_func=lambda m:config('assessment_modes')['modes'][m]['label'],key='assessment_mode_choice')
    def start_selected_demo():
        try: st.session_state.session=Session(assessment_mode=st.session_state.assessment_mode_choice)
        except PrivacyError as exc: st.session_state.privacy_start_error=str(exc)
    st.button('Start selected demo',on_click=start_selected_demo)
    if st.session_state.get('privacy_start_error'): st.error(st.session_state.privacy_start_error)
    st.stop()
if 'session' not in st.session_state:
    try: st.session_state.session=Session(assessment_mode=selected_mode)
    except PrivacyError as exc:
        st.info(NOTICE); st.error(str(exc)); footer(); st.stop()
try: check_contract(st.session_state.session)
except PrivacyError as exc:
    st.error(str(exc)); restart_control(); footer(); st.stop()
if getattr(st.session_state.session,'assessment_mode',None)=='general_baseline':
    from iam_sra.baseline_ui import render
    from iam_sra.baseline_client import BaselineClient, MockBaselineClient
    if '_baseline_client' not in st.session_state:
        st.session_state._baseline_client=MockBaselineClient() if mock else BaselineClient()
    if mock: st.warning('MOCK MODE — empty evidence fixture; not a semantic assessment.')
    render(st.session_state.session,st.session_state._baseline_client,developer)
    st.stop()
if getattr(st.session_state.session,'assessment_mode','legacy_fn_acceptance_demo')=='acceptance_and_readiness_evidence':
    from iam_sra.readiness_ui import render
    from iam_sra.readiness_client import ReadinessClient
    if '_readiness_client' not in st.session_state:
        st.session_state._readiness_client=ReadinessClient()
    if mock:
        from iam_sra.readiness_mock import MockReadinessClient
        st.session_state._readiness_client=MockReadinessClient()
        st.warning('MOCK MODE — empty evidence fixture; this does not evaluate your views.')
    render(st.session_state.session,st.session_state._readiness_client,developer)
    st.stop()
st.error('This session belongs to the legacy app. Start over to use the updated interview.')
