"""Citizen UI backed by the same policy/result data as the JSON export."""
import json
from copy import deepcopy
import streamlit as st
from .readiness import citizen_result
from .settings import SCENARIO, CONCERNS, config
from .assessment import AssessmentError


def render(session, client, developer=False):
    s = session
    st.button('Start over', on_click=st.session_state.clear)
    st.caption('Draft demo questions · criteria awaiting FN review')
    if s.instrument['version'] != config('readiness')['version']:
        st.warning('This session uses an earlier draft instrument. Its saved evidence is retained. Use Start over to test the revised interview.')

    def perform(action, *args):
        st.session_state.pop('readiness_error', None)
        st.session_state.pop('readiness_failure_details', None)
        try:
            with st.spinner('Reading your answer…'): action(*args)
        except (AssessmentError, ValueError) as exc:
            code = getattr(exc, 'code', 'validation')
            detail = {'error_code': code, 'message': str(exc), 'exception_type': type(exc).__name__,
                'cause': str(exc.__cause__) if exc.__cause__ else None,
                'action': getattr(action, '__qualname__', str(action)), 'state': s.state,
                'request': deepcopy(getattr(client, 'last_request_context', {})),
                'diagnostics': deepcopy(getattr(client, 'last_diagnostics', [])),
                'transport': deepcopy(getattr(client, 'last_settings', {}).get('transport_error'))}
            messages = {'transport': 'The model service could not be reached or complete the request.',
                'timeout': 'The model request reached its time limit.',
                'schema': 'The model response did not match the required format.',
                'evidence': 'The model response did not cite valid supporting passages.',
                'budget': 'This request exceeded the model context limit.',
                'truncated': 'The model response stopped before it was complete.'}
            guidance = 'Retry with Continue. Your answer is retained.' if s.state == 'answer' else 'Your answer is retained. Retry, correct it, or skip a follow-up.'
            st.session_state.readiness_error = messages.get(code, 'We could not complete this step.') + ' ' + guidance
            st.session_state.readiness_diagnostic = str(exc)
            st.session_state.readiness_failure_details = detail

    if st.session_state.get('readiness_error'):
        st.error(st.session_state.readiness_error)
        with st.expander('Technical details for this failed attempt'):
            details = st.session_state.get('readiness_failure_details', {'message': st.session_state.get('readiness_diagnostic')})
            st.json(details)
            st.download_button('Download failure details', json.dumps(details, indent=2), file_name='iam-readiness-failure.json', mime='application/json')

    def edit_answers():
        with st.expander('Edit an earlier answer'):
            for e in s.events:
                if e['active']:
                    def edit(event=e):
                        perform(s.edit_answer, event['id'])
                        st.session_state['readiness_answer'] = event['text']
                    label = 'Your first answer' if e['kind'] == 'initial' else e['question']['question_text']
                    st.button(label, key='edit_' + e['id'], on_click=edit)

    def learning_option():
        with st.expander('Optional: learn more about this example'):
            module = getattr(s, 'information_module', config('readiness_information'))
            st.caption('Draft explanation · does not answer all technical questions or ask you to support the proposal.')
            for paragraph in module['paragraphs']: st.write(paragraph)
            st.caption('Reading is recorded separately from understanding. Any optional question uses the same total question budget.')
            check_done = any(a['question']['id'] == module['understanding_check']['id'] for a in s.answers)
            if len(s.answers) >= s.question_budget or check_done:
                st.write('No additional reflection question will be asked in this session.')
                st.button('I have read this explanation', on_click=s.record_information_exposure)
            else:
                st.button('I have read this — reflect on it', on_click=perform, args=(s.start_learning,))

    if s.state == 'answer':
        st.subheader('The proposal')
        st.write(SCENARIO['text'])
        st.caption('An illustrative scenario, not a confirmed plan in a named city.')
        with st.form('readiness_initial'):
            st.text_area('How do you feel about this proposal? What would make it acceptable?', key='readiness_answer')
            st.form_submit_button('Continue', on_click=lambda: perform(s.submit, st.session_state.get('readiness_answer', ''), client))
    elif s.state == 'review':
        st.subheader('Have we understood you correctly?')
        pending = s.pending
        view = pending['acceptance']
        if view['stance'] != 'not_stated':
            st.write('Your view of the proposal: ' + {'supported': 'support', 'opposed': 'opposition', 'mixed': 'mixed views', 'uncertain': 'uncertain'}[view['stance']])
        for item in view['concerns']: st.write('Concern: ' + item)
        for item in view['conditions']: st.write('Condition: ' + item)
        if view.get('medical_public_benefit_support') == 'supported': st.write('You support the medical purpose of the service.')
        for text in dict.fromkeys(r['interpretation'] for r in pending['records']): st.write(text)
        interaction = pending.get('interaction', 'substantive')
        if interaction == 'confused': st.write('The question was unclear to you. This does not change the evidence you already shared.')
        elif interaction in {'declined', 'already_answered'}: st.write('You do not want to repeat this answer. We will move on.')
        elif not pending['records']: st.write('No additional readiness evidence was established in this answer.')
        with st.expander('Your supporting words'): st.write(pending['text'])
        st.caption('Confirmation agrees with the interpretation; it does not verify external events or assessment criteria.')
        key = 'readiness_confirm_' + str(pending['version'])
        st.checkbox('This reflects what I meant', key=key)
        st.button('Confirm and continue', on_click=perform, args=(s.confirm, st.session_state.get(key, False)), disabled=not st.session_state.get(key, False))
        with st.form('correct_pending'):
            st.text_area('Correct this interpretation in your own words', key='readiness_correction')
            st.form_submit_button('Save correction', on_click=lambda: perform(s.correct, st.session_state.get('readiness_correction', ''), client))
        edit_answers()
    elif s.state == 'correction':
        st.subheader('Correct your earlier answer')
        with st.form('correct_answer'):
            st.text_area('Your corrected answer', key='readiness_answer')
            st.form_submit_button('Continue', on_click=lambda: perform(s.correct, st.session_state.get('readiness_answer', ''), client))
    elif s.state == 'interview':
        q = s.current_question
        if q is None:
            s.finish('sufficient_evidence_or_no_eligible_questions'); st.rerun()
        st.subheader('Your readiness evidence')
        st.caption(f'Question {len(s.answers) + 1} of at most {s.question_budget}. This counts questions, not readiness.')
        st.write(q['question_text'])
        with st.form('readiness_' + q['id']):
            st.text_area('Your answer', key='readiness_followup_' + q['id'])
            st.form_submit_button('Continue', on_click=lambda: perform(s.respond, st.session_state.get('readiness_followup_' + q['id'], ''), client))
        st.button('Unsure', on_click=perform, args=(s.skip, True))
        st.button('Skip', on_click=perform, args=(s.skip,))
        st.button('Finish questions', on_click=perform, args=(s.finish,))
        learning_option()
        edit_answers()
    else:
        result = citizen_result(s)
        st.subheader('Your view of the proposal')
        original = result['acceptance']['original_proposal']
        st.write({'supported': 'You support the proposal.', 'opposed': 'You oppose the proposal.', 'mixed': 'You have mixed views of the proposal.',
                  'uncertain': 'You are unsure about the proposal.', 'not_stated': 'Your position on the proposal is not yet stated.'}[original['stance']])
        if original['unresolved_stance_conflict']: st.write('Your statements about the proposal differ; you can correct an earlier answer.')
        if original.get('medical_public_benefit_support') == 'supported': st.write('You support the medical purpose of the service.')
        for item in original['concerns']: st.write('Concern: ' + item)
        for item in original['conditions']: st.write('Condition: ' + item)
        for item in original['policy_preferences']: st.write('Policy preference: ' + item)
        st.subheader('Your readiness evidence')
        names = {'understanding': 'Understanding of possible impacts', 'information': 'Information and evidence needs',
                 'participation': 'Participation and contributions', 'influence': 'Influence on decisions', 'opportunity': 'Ways to participate and barriers'}
        gaps = {'not_asked': 'Not established in this interview; no limitation in ability is inferred.',
                'unsupported': 'No evidence recorded from the answer.', 'unclear': 'This remains unclear.',
                'conflicting': 'Some statements differ and remain unresolved.', 'skipped': 'You skipped this question; no capability is inferred.'}
        for item in result['readiness']:
            st.write('**' + names[item['criterion_id']] + '**')
            for text in item['interpretations']: st.write(text)
            if item['status'] in gaps: st.write(gaps[item['status']])
        st.info(result['note'])
        learning_option()
        edit_answers()
        with st.expander('Optional: explore changes to the proposal'):
            st.caption('Hypothetical changes; feasibility is unverified. These choices do not establish readiness or acceptance of all changes together.')
            facets = [f for f in original.get('concern_facets', []) if f in config('updates')['mitigations']]
            if facets and sum(e['active'] and e['kind'] == 'optional_acceptance' for e in s.events) < 2:
                from .reporting import aspect_label
                facet = st.selectbox('Which aspect would you like to explore?', facets, format_func=aspect_label)
                st.write(config('updates')['mitigations'][facet])
                with st.form('optional_acceptance'):
                    st.radio('Would this change address your concern?', ['Would address my concern', 'Would partly address my concern', 'Would not address my concern', 'Unsure'], index=None, key='optional_choice')
                    st.text_area('Explain, if you wish', key='optional_text')
                    st.form_submit_button('Record this view', on_click=lambda: perform(s.explore_acceptance, facet, st.session_state.get('optional_choice'), st.session_state.get('optional_text', ''), client))
            else: st.write('No further concern changes are selected for this interview.')
        with st.expander('Details and downloads'):
            st.write(s.assessment_participation['note'])
            st.write('Thematic areas are topics, not CRL maturity stages.')
            st.json({'coverage': s.final_readiness['criterion_coverage'], 'changes': s.export()['readiness_changes'], 'stop_reason': s.stop_reason})
            st.download_button('Download readable JSON', s.json(), file_name='iam-evidence.json', mime='application/json')
            st.download_button('Download assessment JSONL', s.jsonl(), file_name='iam-evidence.jsonl', mime='application/x-ndjson')
    if developer:
        with st.expander('Developer diagnostics'):
            st.json({'assessment_mode': s.assessment_mode, 'inference': s.inference, 'last_error': st.session_state.get('readiness_diagnostic')})
