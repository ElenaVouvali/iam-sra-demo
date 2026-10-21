"""Streamlit presentation of the same citizen indicator controller used by the API."""
import streamlit as st
from .indicator_client import IndicatorClient
from .privacy import NOTICE


def render_indicators(session, perform):
    view = session.indicator_view()
    st.subheader('Citizen indicator self-assessment')
    if not view.get('available'):
        st.info(view['notice'])
        return
    st.info(view['notice'])
    client = IndicatorClient()
    def edit(event_id, mode):
        text = perform(session.indicator_edit, event_id, mode)
        if mode == 'answer' and isinstance(text, str):
            st.session_state[f'indicator_answer_text_{session.indicators.revision}'] = text
    row = view['current']
    revision = view['revision']
    with st.expander('Choose indicators and assessment scope', expanded=row is None):
        options = {i['indicator_id']: i['name'] for i in view['coverage']}
        chosen = st.multiselect('Choose one to three indicators', list(options), format_func=options.get,
                                max_selections=3, key='indicator_selection')
        contexts = {'general_understanding': 'General understanding', 'illustrative_proposal': 'The illustrative proposal discussed',
                    'actual_experience': 'My actual experience'}
        context = st.selectbox('Assessment context', list(contexts), format_func=contexts.get, key='indicator_scope')
        st.text_input('Use case/context (optional, general description)', max_chars=240, key='indicator_context_text')
        reuse = {}
        for key in chosen:
            phase = session.scenario if context == 'illustrative_proposal' else session.general
            prior = {e['id']: e['text'] for e in phase.events if e['active'] and e['confirmed']} if phase else {}
            reuse[key] = st.multiselect('Reuse relevant confirmed answers for ' + options[key], list(prior),
                                       format_func=prior.get, max_selections=3, key='reuse_' + key)
        st.caption('You choose the individual citizen capacity. Linked answers still need to support the actual statement; topic tags are not sufficient.')
        st.button('Begin selected indicators', disabled=not chosen or bool(row and row['pending']), on_click=lambda:
                  perform(session.select_indicators, chosen, context, st.session_state.get('indicator_context_text', ''), reuse, 'citizen'))
    if row:
        st.write('**' + row['name'] + ' · Citizen / CRL**')
        st.text(row['scope']['context'] + ' · ' + row['scope']['use_case'])
        with st.expander('Definition, citizen criterion and all nine exact statements'):
            st.text(row['definition']); st.text(row['criterion']['text'])
            for statement in row['scale']:
                st.write('**CRL ' + str(statement['level']) + ' · ' + statement['label'] + '**')
                st.text(statement['statement'])
                st.caption(statement['source']['sheet'] + '!' + statement['source']['cell'] + ' · shared row review: ' + statement['row_review_status'])
        if row['question']:
            st.text(row['question']['question_text']); st.caption('Up to three short questions. Skip, uncertainty and early finish are available.')
            answer_key = f'indicator_answer_text_{revision}'
            st.text_area('Your indicator answer', max_chars=2000, key=answer_key)
            st.info(NOTICE)
            st.button('Submit indicator answer', on_click=lambda: perform(session.indicator_answer, st.session_state.get(answer_key, ''), client))
            for control, label in [('skip', 'Skip indicator question'), ('unsure', 'Not sure about this question'), ('decline', 'Prefer not to answer this question')]:
                st.button(label, on_click=perform, args=(session.indicator_answer, '', client, control))
            st.button('Finish indicator questions', on_click=perform, args=(session.indicator_finish,))
        if row['pending']:
            pending = row['pending']; st.write('**Check the indicator interpretation**'); st.text(pending['reading']['meaning'])
            st.caption('Check the meaning, whose reasoning or action is described, and whether it is actual or hypothetical. Correct mistakes before confirming.')
            for observation in pending['reading']['observations']:
                st.text(observation['quote']); st.text(observation['review_description'])
                for ambiguity in observation.get('ambiguities', []): st.text('Unresolved: ' + ambiguity)
            st.button('Confirm indicator interpretation', on_click=perform, args=(session.indicator_confirm,))
            with st.expander('Correct the indicator interpretation'):
                feedback_key = f'indicator_feedback_text_{revision}'
                st.text_area('What should we understand differently?', max_chars=1500, key=feedback_key)
                st.button('Apply indicator correction', on_click=lambda: perform(session.indicator_correct, st.session_state.get(feedback_key, ''), client))
                st.text(pending['text'])
        if row['state'] == 'ready' and row['tool'] is None:
            st.button('Request draft indicator suggestion', on_click=perform, args=(session.indicator_suggest, client))
        if row['participant']:
            participant = row['participant']; st.write('**Your individual self-assessment**')
            if participant['statement']:
                st.text('CRL ' + str(participant['statement']['level']) + ' · ' + participant['statement']['label'])
                st.text(participant['statement']['statement'])
            else: st.text('You remain unsure.' if participant['status'] == 'unsure' else 'You declined to give a level.')
        if row['tool']:
            with st.expander('Provisional tool suggestion and supporting evidence', expanded=True):
                tool = row['tool']; st.text(tool['statement']['statement'] if tool['statement'] else 'The tool abstained: no level suggested.')
                st.text(tool['explanation'])
                for gap in tool['gaps']: st.text(gap)
                for match in tool['assessments']:
                    st.caption(match['statement_id'] + ' · ' + match['status'] + ': ' + match['reason'])
                    for cite in match['evidence']: st.text(cite['quote'])
        if row['state'] in {'ready', 'review', 'complete'}:
            st.write('**Review your level**'); st.caption('Read all nine statements above. You may disagree or remain unsure. Add new evidence by editing an answer first.')
            choice_key = f'indicator_review_choice_{revision}'
            selected = st.selectbox('Your own statement selection', [None] + [s['id'] for s in row['scale']],
                                    format_func=lambda key: 'Choose a statement' if key is None else next('CRL ' + str(s['level']) + ' · ' + s['label'] for s in row['scale'] if s['id'] == key), key=choice_key)
            explanation_key = f'indicator_explanation_text_{revision}'
            st.text_area('Why does this fit, or why do you disagree? (optional)', max_chars=600, key=explanation_key)
            if row['tool'] and row['tool']['statement']:
                st.button('Confirm suggested statement', on_click=lambda: perform(session.indicator_review, 'endorse', revision, None, st.session_state.get(explanation_key, '')))
            st.button('Record my selected statement', disabled=selected is None, on_click=lambda:
                      perform(session.indicator_review, 'select', revision, st.session_state.get(choice_key), st.session_state.get(explanation_key, '')))
            for choice, label in [('unsure', 'Remain unsure about my level'), ('decline', 'Decline to give a level')]:
                st.button(label, on_click=lambda c=choice: perform(session.indicator_review, c, revision, None, st.session_state.get(explanation_key, '')))
        with st.expander('Indicator answers and corrections'):
            for event in row['events']:
                if not event['active']: continue
                st.text(event['text'] or event['reading']['meaning']); st.caption(event['reading']['meaning'] + ' · ' + event['information_context'])
                for observation in event['reading']['observations']:
                    st.text(observation['quote']); st.text(observation['review_description'])
                    for ambiguity in observation.get('ambiguities', []): st.text('Unresolved: ' + ambiguity)
                if event['origin'] == 'indicator_interview' and not row['pending']:
                    st.button('Edit indicator answer', key='edit_' + event['id'], on_click=edit, args=(event['id'], 'answer'))
                    st.button('Review indicator interpretation', key='read_' + event['id'], on_click=edit, args=(event['id'], 'interpretation'))
    with st.expander('Indicator coverage and results'):
        for entry in view['coverage']:
            st.text(entry['name'] + ': ' + entry['status'])
            if entry['participant'] and entry['participant']['statement']:
                st.text('Your selection: CRL ' + str(entry['participant']['statement']['level']))
            if entry['selected'] and (not row or entry['indicator_id'] != row['indicator_id']):
                st.button('Continue ' + entry['name'], on_click=perform, args=(session.indicator_next, entry['indicator_id']))
