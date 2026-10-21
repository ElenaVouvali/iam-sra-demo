"""Streamlit presentation of the shared three-profile assessment controller."""
import streamlit as st
from .indicator_client import IndicatorClient
from .privacy import NOTICE


def render_start(session, perform):
    view = session.indicator_view()
    st.subheader('Begin an indicator assessment')
    if not view.get('available'):
        st.info(view['notice']); return
    st.info(view['introduction'])
    base = session.general.instrument
    st.selectbox('Response capacity', ['citizen','organisational','technical'], index=None, key='assessment_profile')
    st.text_input('Service or use case (general description)', max_chars=240, key='assessment_use_case')
    st.selectbox('Assessment area', list(base['cities']), format_func=base['cities'].get, key='assessment_city')
    st.text_input('Broad area (optional)', max_chars=80, key='assessment_area')
    st.selectbox('Broad stakeholder role', list(base['stakeholders']), format_func=base['stakeholders'].get, index=list(base['stakeholders']).index('withheld'), key='assessment_role')
    st.selectbox('Service discussion status', ['proposal','illustrative','pilot','operational','unsure'], key='assessment_status')
    if st.session_state.assessment_status=='illustrative':
        options={r['id']:r for r in view['illustrative_options']}
        st.selectbox('Illustrative alternative',list(options),format_func=lambda k:options[k]['title'],index=None,key='assessment_scenario')
        if st.session_state.get('assessment_scenario'):st.text(options[st.session_state.assessment_scenario]['text'])
        st.caption('Source-backed illustration, not evidence of current operations.')
    profile=st.session_state.get('assessment_profile')
    if profile=='organisational':
        st.text_input('Organisation or broad unit',max_chars=240,key='assessment_unit')
        st.text_input('General responsibilities',max_chars=240,key='assessment_responsibilities')
    if profile=='technical':
        st.text_input('Overall object or concept (if known)',max_chars=240,key='assessment_object')
        st.caption('Confirm object/version and environment per indicator; an absent object is not low TRL.')
    if profile=='citizen':st.checkbox('Include optional citizen self-report categories (never CRL)',key='assessment_likert')
    st.caption('All fifteen indicators are available in three sections. You may finish with a partial report. Sessions remain in memory; no durable cross-day resume is promised.')
    st.info(NOTICE)
    def begin():
        values={field:st.session_state.get('assessment_'+key,'') for field,key in [('use_case','use_case'),('area','area'),('organisation_or_unit','unit'),('responsibilities','responsibilities'),('technical_object','object')]}
        for key in ('use_case','area','unit','responsibilities','object'):
            if 'assessment_'+key in st.session_state:st.session_state['assessment_'+key]=''
        perform(session.start_assessment,profile=st.session_state.assessment_profile,city=st.session_state.assessment_city,
                stakeholder_role=st.session_state.assessment_role,discussion_status=st.session_state.assessment_status,
                likert_enabled=bool(st.session_state.get('assessment_likert')),scenario_id=st.session_state.get('assessment_scenario') if st.session_state.assessment_status=='illustrative' else None,**values)
    st.button('Begin indicator assessment',disabled=not profile or not st.session_state.get('assessment_use_case','').strip(),on_click=begin)


def render_indicators(session, perform):
    view = session.indicator_view()
    st.subheader('Individual indicator self-assessment')
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
    with st.expander('Deliberately change assessment profile or scope' if view.get('direct_entry') else 'Choose indicators and assessment scope', expanded=row is None):
        options = {i['indicator_id']: i['name'] for i in view['coverage']}
        chosen = st.multiselect('Choose indicators to include (up to fifteen)', list(options), format_func=options.get,
                                max_selections=15, key='indicator_selection')
        contexts = {'general_understanding': 'General understanding', 'illustrative_proposal': 'The illustrative proposal discussed',
                    'actual_experience': 'My actual experience'}
        st.selectbox('Assessment response capacity',['citizen','organisational','technical'],index=['citizen','organisational','technical'].index(view['profile']),key='indicator_profile')
        context = st.selectbox('Assessment context', list(contexts), format_func=contexts.get, key='indicator_scope')
        st.text_input('Use case/context (optional, general description)', max_chars=240, key='indicator_context_text')
        reuse = {}
        for key in chosen:
            phase = session.scenario if context == 'illustrative_proposal' else session.general
            prior = {e['id']: e['text'] for e in phase.events if e['active'] and e['confirmed']} if phase else {}
            reuse[key] = st.multiselect('Reuse relevant confirmed answers for ' + options[key], list(prior),
                                       format_func=prior.get, max_selections=3, key='reuse_' + key)
        st.caption('Choose the response capacity explicitly. Linked answers must fit the profile, object and actual criterion; topic tags are insufficient.')
        st.button('Begin selected indicators', disabled=not chosen or bool(row and row['pending']), on_click=lambda:
                  perform(session.select_indicators, chosen, context, st.session_state.get('indicator_context_text', ''), reuse, st.session_state.indicator_profile))
    scale_name = view['scale_name']
    if view['report_finished']:
        st.subheader('Your individual indicator profile')
        st.text(view['profile'] + ' · ' + view['scope']['use_case'])
    if row and not view['report_finished']:
        st.write('**' + row['name'] + ' · ' + scale_name + '**')
        st.caption(row['scope_note'])
        with st.expander('Optional illustrative case for this indicator'):
            cases={c['id']:c for c in view['illustrative_options']}
            st.selectbox('Optional case',list(cases),format_func=lambda k:cases[k]['title'],index=None,key='indicator_case_id')
            st.caption('The confirmed use case stays primary. Changing a case deliberately invalidates this indicator’s dependent evidence and judgments.')
            st.button('Use optional case for this indicator',disabled=not st.session_state.get('indicator_case_id') or bool(row['pending']),on_click=lambda:perform(session.indicator_case,st.session_state.indicator_case_id))
            st.button('Continue without an optional case',disabled=not row['scope'].get('illustrative_case') or bool(row['pending']),on_click=perform,args=(session.indicator_case,None))
        if row['scope'].get('illustrative_case'):
            case=row['scope']['illustrative_case']
            st.text(case['title']);st.caption(case.get('source_status','Source illustration')+' · '+case.get('source_verification','Source-described illustration'))
            with st.expander('Case text, unknowns and sources',expanded=not any(e.get('already_presented') for e in row['information'] if e['kind']=='case')):
                st.text(case['text']);st.text('Unknown: '+'; '.join(case['unknowns']))
                for ref in case.get('source_refs',[]):st.text((ref.get('local_document') or ref['package_document'])+' · '+ref['locator']+' · '+ref['verification_status'])
                st.caption('Illustrative information, not actual activity, a VR evaluation or technical validation.')
        if view['profile']!='citizen':
            with st.expander('Confirm or deliberately edit indicator scope',expanded=row['state']=='scope'):
                revision_key=str(revision)
                availability=st.selectbox('Scope availability',['ready_to_discuss']+(['outside_role'] if view['profile']=='organisational' else ['no_technical_object_identified'])+['not_applicable_explained'],key='availability_'+revision_key)
                scope_fields=['organisation_or_unit','responsibilities'] if view['profile']=='organisational' else ['technical_object','object_version','intended_environment']
                for field in scope_fields:st.text_input(field.replace('_',' ').capitalize(),value=row['scope'].get(field,''),max_chars=240,key=field+'_'+revision_key)
                if view['profile']=='technical':st.selectbox('Object scope',['component','system','model','tool','concept','unsure'],index=['component','system','model','tool','concept','unsure'].index(row['scope'].get('component_scope','unsure')),key='component_'+revision_key)
                def confirm_scope():
                    values={f:st.session_state[f+'_'+revision_key] for f in scope_fields}
                    for f in scope_fields:st.session_state[f+'_'+revision_key]=''
                    perform(session.indicator_scope,availability=st.session_state['availability_'+revision_key],component_scope=st.session_state.get('component_'+revision_key,'unsure'),**values)
                st.button('Confirm indicator scope',on_click=confirm_scope)
        st.button('Read more: neutral definition',on_click=perform,args=(session.indicator_information,'definition'))
        for entry in row['information']:
            if entry['kind']=='definition':st.text(entry['text']);st.caption('Supplied source information, not prior competence.')
        if view['reusable_answers'] and not row['pending']:
            with st.expander('Reuse equivalent confirmed answers'):
                options={e['id']:e['text'] for e in view['reusable_answers']}
                st.multiselect('Answers equivalent to this opening',list(options),format_func=options.get,max_selections=3,key='indicator_link_ids')
                st.button('Use selected answers for this opening',disabled=not st.session_state.get('indicator_link_ids'),on_click=lambda:perform(session.indicator_link,st.session_state.indicator_link_ids))
        st.text(row['scope']['context'] + ' · ' + row['scope']['use_case'])
        if row['state'] in {'ready','review','complete'}:st.button('Read all nine source statements',on_click=perform,args=(session.indicator_information,'scale'))
        if any(e['kind']=='scale' for e in row['information']):
            with st.expander('Definition, profile criterion and all nine exact statements'):
                st.text(row['definition']); st.text(row['criterion']['text'])
                for statement in row['scale']:
                    st.write('**' + scale_name + ' ' + str(statement['level']) + ' · ' + statement['label'] + '**')
                    st.text(statement['statement'])
                    st.caption(statement['source']['sheet'] + '!' + statement['source']['cell'] + ' · shared row review: ' + statement['row_review_status'])
        if row['question']:
            st.text(row['question']['question_text']); st.caption('Up to three short questions. Skip, uncertainty and early finish are available.')
            answer_key = f'indicator_answer_text_{revision}'
            if row['question']['format']=='likert':
                st.selectbox('Optional self-report category',list(row['question']['options']),format_func=row['question']['options'].get,index=None,key=answer_key)
            else:st.text_area('Your indicator answer', max_chars=2000, key=answer_key)
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
            if pending.get('correction_offer'):st.info(pending['correction_offer']['notice'])
            st.caption('The full original answer is authoritative; missing observations are not missing evidence.')
            st.button('Confirm indicator interpretation', on_click=perform, args=(session.indicator_confirm,))
            with st.expander('Correct the indicator interpretation'):
                feedback_key = f'indicator_feedback_text_{revision}'
                st.text_area('What should we understand differently?', max_chars=1500, key=feedback_key)
                st.button('Apply indicator correction', on_click=lambda: perform(session.indicator_correct, st.session_state.get(feedback_key, ''), client))
                st.button('Add this information to my answer',on_click=lambda:perform(session.indicator_add_information,st.session_state.get(feedback_key,''),client))
                if pending.get('correction_offer'):st.button('Use offered addition and check again',on_click=perform,args=(session.indicator_add_information,pending['correction_offer']['text'],client))
                st.text(pending['text'])
        if row['state'] == 'ready' and row['tool'] is None:
            if row.get('suggestion_error'):st.warning(row['suggestion_error']['notice'])
            st.button('Request draft indicator suggestion', on_click=perform, args=(session.indicator_suggest, client))
        if row['participant']:
            participant = row['participant']; st.write('**Your individual self-assessment**')
            if participant['statement']:
                st.text(scale_name + ' ' + str(participant['statement']['level']) + ' · ' + participant['statement']['label'])
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
                                    format_func=lambda key: 'Choose a statement' if key is None else next(scale_name + ' ' + str(s['level']) + ' · ' + s['label'] for s in row['scale'] if s['id'] == key), key=choice_key)
            explanation_key = f'indicator_explanation_text_{revision}'
            st.text_area('Why does this fit, or why do you disagree? (optional)', max_chars=600, key=explanation_key)
            if row['tool'] and row['tool']['statement']:
                st.button('Confirm suggested statement', on_click=lambda: perform(session.indicator_review, 'endorse', revision, None, st.session_state.get(explanation_key, '')))
            st.button('Record my selected statement', disabled=selected is None or row['disposition'] in {'outside_role','no_technical_object_identified','not_applicable_explained'}, on_click=lambda:
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
                st.text('Your selection: ' + scale_name + ' ' + str(entry['participant']['statement']['level']));st.text(entry['participant']['statement']['statement'])
            if entry.get('scope'):
                st.caption('Object: ' + entry['scope'].get('technical_object','') + ' · Unit: ' + entry['scope'].get('organisation_or_unit',''))
            if entry['tool']:st.text('Tool: ' + entry['tool']['explanation'])
            elif entry.get('suggestion_error'):st.text(entry['suggestion_error']['notice'])
            if entry['selected']:
                st.button('Continue ' + entry['name'], on_click=perform, args=(session.indicator_next, entry['indicator_id']))

    if row and not view['report_finished']:st.button('Finish with my current indicator profile',on_click=perform,args=(session.complete_assessment,))
