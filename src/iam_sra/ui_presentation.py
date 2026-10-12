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
    st.subheader(stage)


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
        st.write('IAM-SRA2 is the overall tool. This internal demo implements its citizen component: proposal views and partial evidence relevant to Citizen Readiness Levels (CRL). Societal Readiness (SRL) is broader and draws on technical (TRL), organisational (ORL) and citizen readiness; this interview is not a city SRL.')
        st.write('Five interview dimensions do not cover all nine CRL levels or all 15 topics. Numerical criteria await agreement.')
        st.write('Local screening can miss private information. Masked text is not necessarily anonymous.')
        st.write('Reset is not secure erasure. Downloads remain with their recipients.')


def proposal_summary(view):
    statements = [{'supported':'You support the proposed route.', 'opposed':'You oppose the proposed route.',
        'mixed':'You have mixed views about the proposed route.', 'uncertain':'You are unsure about the proposed route.',
        'not_stated':'Your overall position on the route is not yet stated.'}[view['stance']]]
    if view.get('medical_public_benefit_support') == 'supported':
        statements.append('You support its medical purpose.')
    if view.get('concerns'):
        statements.append('What matters to you: ' + '; '.join(dict.fromkeys(view['concerns'])))
    if view.get('conditions'):
        statements.append('The changes you asked for: ' + '; '.join(dict.fromkeys(view['conditions'])))
    return '\n\n'.join(statements)
