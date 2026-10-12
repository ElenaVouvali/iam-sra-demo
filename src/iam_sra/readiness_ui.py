"""Citizen UI backed by the same policy/result data as the JSON export."""
import json
from copy import deepcopy
import streamlit as st
from .readiness import citizen_result
from .settings import config
from .assessment import AssessmentError
from .ui_presentation import navigation, restart_control, findings, footer


def render(session, client, developer=False):
    s = session
    if restart_control():
        footer()
        return
    navigation(s.state)
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
                'schema': 'We could not finish reading your answer.',
                'evidence': 'We could not reliably connect our interpretation to your words.',
                'budget': 'This answer is too long for this step. Please shorten it and try again.',
                'truncated': 'We could not finish reading your answer.'}
            guidance = 'Your answer is retained. Select Continue to retry.' if s.state in {'answer', 'correction'} else 'Your answer is retained. Retry, correct it, or skip this question.'
            st.session_state.readiness_error = messages.get(code, 'We could not complete this step.') + ' ' + guidance
            st.session_state.readiness_diagnostic = str(exc)
            st.session_state.readiness_failure_details = detail

    if st.session_state.get('readiness_error'):
        with st.container(key='iam_error'):
            st.error(st.session_state.readiness_error, icon='⚠️')
        if developer:
            details = st.session_state.get('readiness_failure_details', {'message': st.session_state.get('readiness_diagnostic')})
            with st.expander('Technical details for this failed attempt'):
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
        from .readiness_retrieval import corpus, ExplanationClient
        with st.expander('Optional: learn more about this example'):
            module = getattr(s, 'information_module', config('readiness_information'))
            collection = getattr(s, 'retrieval_corpus', corpus())
            st.caption('Draft demo explanations, awaiting FN review. Optional; your view can stay the same.')
            st.button('Show explanation', on_click=perform, args=(s.display_information,))
            displays = [e for e in s.information_exposures if e['source'] == 'controlled_demo_explanation_display']
            if displays:
                for paragraph in displays[-1]['content']['paragraphs']: st.write(paragraph)
                for ref in module['source_references']: st.caption(ref['document'] + ' · ' + ref['location'])
                st.button('I have read this', on_click=perform, args=(s.acknowledge_information, displays[-1]['exposure_id']))
                check_done = any(a['question']['id'] == module['understanding_check']['id'] for a in s.answers)
                st.caption('Reading adds no readiness evidence. Optional reflection uses the existing interview question budget.')
                if len(s.answers) >= s.question_budget or check_done:
                    st.write('No additional reflection question will be asked in this session.')
                    st.button('Record reading', on_click=perform, args=(s.record_information_exposure,))
                else:
                    st.button('Read and reflect', on_click=perform, args=(s.start_learning,))
            st.selectbox('Suggested question', collection['suggested_questions'], key='information_question')
            st.text_input('Your short question (optional)', max_chars=collection['maximum_question_characters'], key='information_custom')
            count = sum(e['source'] == 'local_retrieval_display' for e in s.information_exposures)
            def ask():
                if '_explanation_client' not in st.session_state: st.session_state._explanation_client = ExplanationClient()
                perform(s.ask_information, st.session_state.get('information_custom', '').strip() or st.session_state.information_question,
                        st.session_state._explanation_client)
            st.button('Show sourced answer', on_click=ask, disabled=count >= collection['maximum_requests_per_session'])
            st.caption('At most four optional information requests, separate from interview questions. No answer from model memory.')
            retrieved = [e for e in s.information_exposures if e['source'] == 'local_retrieval_display']
            if retrieved:
                exposure = retrieved[-1]; answer = exposure['content']
                st.caption(answer['label']); st.text(answer['question']); st.write(answer['notice'])
                sources = {p['id']:p for p in answer['passages']}
                for item in answer['excerpts']:
                    st.text(item['quotation']); source = sources[item['passage_id']]
                    st.caption(source['id'] + ' · ' + source['document_title'] + ' · ' + source['location'] + ' · ' + source['review_status'])
                st.button('Acknowledge answer', on_click=perform, args=(s.acknowledge_information, exposure['exposure_id']))

    if s.state == 'answer':
        st.subheader('The proposal')
        st.write(s.scenario['text'])
        st.write('An illustrative scenario, not a confirmed plan in a named city.')
        with st.container(key='iam_accent'):
            with st.form('readiness_initial'):
                st.text_area(s.instrument.get('initial_invitation', 'How do you feel about this proposal? What would make it acceptable?'), key='readiness_answer', height=180)
                st.form_submit_button('Continue', type='primary', on_click=lambda: perform(s.submit, st.session_state.get('readiness_answer', ''), client))
    elif s.state == 'review':
        st.subheader('Have we understood you correctly?')
        pending = s.pending
        view = pending['acceptance']
        if view['stance'] != 'not_stated':
            st.write('Your view of the proposal: ' + {'supported': 'support', 'opposed': 'opposition', 'mixed': 'mixed views', 'uncertain': 'uncertain'}[view['stance']])
        findings('What matters to you', view['concerns'])
        findings('Changes you asked for', view['conditions'])
        if view.get('medical_public_benefit_support') == 'supported': st.write('You support the medical purpose of the service.')
        findings('What we heard', [r['interpretation'] for r in pending['records']])
        interaction = pending.get('interaction', 'substantive')
        if interaction == 'confused': st.write('The question was unclear to you. This does not change the evidence you already shared.')
        elif interaction in {'declined', 'already_answered'}: st.write('You do not want to repeat this answer. We will move on.')
        elif not pending['records']: st.write('This answer adds no further details about understanding or participation.')
        st.caption('Confirm whether we understood you. This does not independently verify events you described.')
        key = 'readiness_confirm_' + str(pending['version'])
        st.checkbox('This reflects what I meant', key=key)
        with st.container(key='iam_accent'):
            st.button('Confirm and continue', type='primary', on_click=perform, args=(s.confirm, st.session_state.get(key, False)), disabled=not st.session_state.get(key, False))
        with st.expander('Correct this interpretation'):
            with st.form('correct_pending'):
                correction_key = 'readiness_correction_' + str(pending['version'])
                st.text_area('Tell us what to correct', key=correction_key)
                st.form_submit_button('Save correction', on_click=lambda: perform(s.correct, st.session_state.get(correction_key, ''), client))
        edit_answers()
    elif s.state == 'correction':
        st.subheader('Correct your earlier answer')
        with st.container(key='iam_accent'):
            with st.form('correct_answer'):
                st.text_area('Your corrected answer', key='readiness_answer', height=180)
                st.form_submit_button('Continue', type='primary', on_click=lambda: perform(s.correct, st.session_state.get('readiness_answer', ''), client))
    elif s.state == 'interview':
        q = s.current_question
        if q is None:
            s.finish('sufficient_evidence_or_no_eligible_questions'); st.rerun()
        st.subheader('A few questions about your experience')
        st.caption(f'Question {len(s.answers) + 1} of at most {s.question_budget} · Interview progress, not a readiness rating')
        st.write(q['question_text'])
        with st.container(key='iam_accent'):
            with st.form('readiness_' + q['id']):
                st.text_area('Your answer', key='readiness_followup_' + q['id'], height=140)
                st.form_submit_button('Continue', type='primary', on_click=lambda: perform(s.respond, st.session_state.get('readiness_followup_' + q['id'], ''), client))
        st.button('Unsure', on_click=perform, args=(s.skip, True))
        st.button('Skip', on_click=perform, args=(s.skip,))
        st.button('Finish questions', on_click=perform, args=(s.finish,))
        learning_option()
        edit_answers()
    else:
        result = citizen_result(s)
        st.subheader('Your views of this proposal')
        original = result['acceptance']['original_proposal']
        st.write({'supported': 'You support the proposal.', 'opposed': 'You oppose the proposal.', 'mixed': 'You have mixed views of the proposal.',
                  'uncertain': 'You are unsure about the proposal.', 'not_stated': 'Your position on the proposal is not yet stated.'}[original['stance']])
        if original['unresolved_stance_conflict']: st.write('Your statements about the proposal differ; you can correct an earlier answer.')
        if original.get('medical_public_benefit_support') == 'supported': st.write('You support the medical purpose of the service.')
        findings('What matters to you', original['concerns'])
        findings('Changes you asked for', original['conditions'])
        findings('Your priorities', original['policy_preferences'])
        st.subheader('What you told us about understanding and participation')
        names = {'understanding': 'Understanding of possible impacts', 'information': 'Information and evidence needs',
                 'participation': 'Participation and contributions', 'influence': 'Influence on decisions', 'opportunity': 'Ways to participate and barriers'}
        gaps = {'not_asked': 'We did not ask about this, or you have not described it.',
                'unsupported': 'You have not described this in enough detail to summarise it.', 'unclear': 'This remains unclear. You can edit an answer if you wish.',
                'conflicting': 'Some statements differ. You can edit an earlier answer to clarify.', 'skipped': 'You chose to skip this question.'}
        for item in result['readiness']:
            st.write('**' + names[item['criterion_id']] + '**')
            for text in item['interpretations']: st.text(text)
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
                    st.text_area('Explanation (optional)', key='optional_text')
                    st.form_submit_button('Record this view', on_click=lambda: perform(s.explore_acceptance, facet, st.session_state.get('optional_choice'), st.session_state.get('optional_text', ''), client))
            else: st.write('No further concern changes are selected for this interview.')
        st.subheader('Save your summary')
        st.caption('Downloads include your answers, interpretations and the complete assessment audit.')
        with st.container(key='iam_accent'):
            st.download_button('Download JSON', s.json(), file_name='iam-evidence.json', mime='application/json', type='primary')
        st.download_button('Download JSONL', s.jsonl(), file_name='iam-evidence.jsonl', mime='application/x-ndjson')
        with st.expander('About this summary'):
            st.write(s.assessment_participation['note'])
            st.write('Thematic areas are topics, not CRL maturity stages.')
    if developer:
        from .readiness_report import evidence_report, markdown_report, fn_reference
        with st.expander('Researcher evidence report'):
            report = evidence_report(s.export())
            st.caption(report['note'])
            st.json(report)
            st.download_button('Download evidence report', markdown_report(s.export()), file_name='iam-researcher-report.md')
        with st.expander('FN historical reference comparison'):
            reference = fn_reference()
            st.write(reference['label']); st.caption('SRA_LLM_FN_concept.pdf · pp.6–7 · source checked, not an approved instrument')
            st.json(reference['source_scores']); st.write(reference['arithmetic'])
            for difference in reference['differences']: st.write(difference)
            st.caption('Separate reference session; values above never enter the citizen assessment. Model interpretation remains unconfirmed.')
            def run_reference():
                from .readiness_session import ReadinessSession
                from .readiness_client import ReadinessClient
                comparison = ReadinessSession()
                comparison.submit(reference['source_citizen_text'], ReadinessClient())
                st.session_state.fn_reference_interpretation = {'pending_interpretation':comparison.pending,
                    'instrument_version':comparison.instrument['version'], 'provenance':comparison.export()['provenance'],
                    'confirmation':'Unconfirmed model interpretation; not citizen validation'}
            st.button('Interpret reference answer', on_click=perform, args=(run_reference,))
            if st.session_state.get('fn_reference_interpretation'):
                st.json(st.session_state.fn_reference_interpretation)
            else: st.caption(reference['current_model_output_status'])
        with st.expander('Developer diagnostics'):
            st.json({'assessment_mode': s.assessment_mode, 'inference': s.inference, 'last_error': st.session_state.get('readiness_diagnostic')})
            if s.final_readiness:
                st.json({'coverage': s.final_readiness['criterion_coverage'], 'changes': s.export()['readiness_changes'], 'stop_reason': s.stop_reason})
    footer()
