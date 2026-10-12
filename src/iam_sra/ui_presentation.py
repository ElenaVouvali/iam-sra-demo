"""Presentation only: IAM-CC guide v1.0, with documented missing kit assets."""
import streamlit as st
from .settings import ROOT

TITLE = 'IAM-SRA2 | IAM-CC'
SUBTITLE = 'Medical drones in your neighborhood'


def header():
    st.html('<style>' + (ROOT / 'assets/ui/iam-cc.css').read_text() + '</style>')
    # Plain project identity, not a substitute/recreation of the unsupplied logo.
    st.html('<header class="iam-header"><span>IAM-CC</span><span aria-hidden="true">|</span>'
            '<strong>IAM-SRA2</strong><a href="https://hub.iamcc.eu" target="_blank" '
            'rel="noopener noreferrer">IAM-CC hub</a></header>')
    st.title(SUBTITLE)
    st.write('Share your views on this illustrative hospital delivery route. There are no right or wrong answers.')


def navigation(state):
    stage = {'answer': 'Proposal and your views', 'review': 'Check our interpretation',
             'correction': 'Correct an answer', 'interview': 'Relevant questions',
             'final': 'Your summary'}.get(state, 'Your summary')
    st.caption('Current step: ' + stage)
    with st.expander('About this interview'):
        st.write('Read the proposal, share your views, check our interpretation, answer relevant questions, and review your summary. You may check interpretations more than once.')
        st.write('Questions and criteria are draft proposals awaiting FN review. Question counts show where you are in the interview, not your readiness.')


def restart_control():
    """Native modal keeps the underlying form mounted, including unsent drafts."""
    @st.dialog('Start a new interview?')
    def confirm_reset():
        with st.container(key='iam_reset'):
            st.warning('This discards this session and unsaved answers. Downloaded files are not deleted.', icon='⚠️')
            if st.button('Discard and restart', on_click=st.session_state.clear):
                st.rerun()
        if st.button('Keep this session'): st.rerun()

    if st.button('Start over'): confirm_reset()
    return False


def findings(label, values):
    values = list(dict.fromkeys(values))
    if not values: return
    st.write('**' + label + '**')
    # st.text prevents model/testimony markdown from creating links or HTML.
    for value in values[:3]: st.text(value)
    if len(values) > 3:
        with st.expander('More ' + label.lower()):
            for value in values[3:]: st.text(value)


def footer():
    st.divider()
    st.caption('Funded by the European Union under Grant Agreement No 101271620. Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority. Neither the European Union nor the granting authority can be held responsible for them.')
    with st.expander('Privacy and project information'):
        st.write('Your answers are held in this app session and sent to the configured model service, localhost by default. Downloads include your answers and the assessment audit. Start over clears the app session but cannot remove files you already downloaded.')
        st.write('This local demo is not a confirmed deployment plan or an approved numerical citizen-readiness assessment.')
