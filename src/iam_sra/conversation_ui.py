"""Short citizen screens for the complete retrieved demonstration."""
import json
import logging
import streamlit as st
from .settings import config
from .privacy import NOTICE,PrivacyError,safe_message,safe_diagnostics
from .privacy_ui import invoke,preview_control,download_button
from .assessment import AssessmentError
from .ui_errors import user_error
from .ui_presentation import restart_control,footer


def render(s,client,planner,developer=False):
    restart_control()
    def perform(action,*args):
        st.session_state.pop('conversation_error',None)
        try:
            with st.spinner('Reading and preparing the next step…'):return invoke(action,*args)
        except (AssessmentError,ValueError) as exc:
            st.session_state.conversation_error=safe_message(exc) if isinstance(exc,PrivacyError) else user_error(exc) if isinstance(exc,AssessmentError) else safe_message(exc)
            diagnostic=safe_diagnostics({'code':getattr(exc,'code','validation'),
                'privacy_findings':list(getattr(exc,'findings',())),
                'diagnostics':getattr(client,'last_diagnostics',[]),'stage':s.stage})
            st.session_state.conversation_diagnostic=diagnostic
            logging.getLogger(__name__).warning('Conversation step failed: %s',diagnostic)
    preview_control(perform)
    if st.session_state.get('conversation_error'):st.warning(st.session_state.conversation_error)
    if developer and st.session_state.get('conversation_diagnostic'):
        with st.expander('Technical diagnostics'):st.json(st.session_state.conversation_diagnostic)

    def summary():
        labels=s.general.instrument['dimensions'];p=s.profile();unknown=[]
        st.text(' · '.join([s.general.instrument['perspectives'][s.respondent['perspective']],
            s.general.instrument['stakeholders'][s.respondent['stakeholder_category']],
            s.respondent['broad_place'] or s.general.instrument['cities'][s.respondent['city']]]))
        view=s.proposal_view()
        if s.scenario:
            st.write('**Your views of the illustrative proposal**')
            st.text({'supported':'You support the example proposal.','opposed':'You oppose the example proposal.',
                'mixed':'You expressed mixed views.','uncertain':'You are unsure about the proposal.',
                'not_stated':'You have not stated an overall position.'}[view['stance']])
            for c in (view['concerns']+view['conditions']+view['medical_purpose_support'])[:4]:st.text(c['interpretation'])
        st.write('**What you told us about understanding and participation**')
        for dim,label in labels.items():
            rows=[c for c in p['claims'] if c['dimension']==dim]
            texts=list(dict.fromkeys(c['interpretation'] for c in rows))
            if texts:
                st.write('**'+label+'**')
                for text in texts[:2]:st.text(text)
                if len(texts)>2:
                    with st.expander('More about '+label.lower()):
                        for text in texts[2:]:st.text(text)
            else:unknown.append(label)
        if s.failed_attempt or any(e['resolution'].startswith('unresolved') for e in s.failure_history):
            st.warning('An answer is retained without a completed interpretation. This is a partial assessment.')
        if p['unresolved_scope']:st.write('Some activity or time details remain unclear; the reports have not been treated as a proven contradiction.')
        if unknown:
            with st.expander('What remains unclear or was not discussed'):
                for label in unknown:st.text(label+': not established in this interview; no limitation in ability is inferred.')
        if s.scenario and s.baseline_snapshot:
            before={c['evidence_id'] for c in s.baseline_snapshot['claims']}
            added=[c for c in p['claims'] if c['evidence_id'] not in before and c['dimension']!='proposal']
            if added:st.write('The follow-ups added detail to this assessment. More detail does not by itself show personal development over time.')

    def edits():
        rows=[(stage,e) for stage,phase in [('general',s.general),('scenario',s.scenario)] if phase
              for e in phase.events if e['active'] and e['confirmed']]
        if not rows and not s.respondent:return
        with st.expander('Edit an earlier answer'):
            st.button('Edit your details',on_click=perform,args=(s.edit_context,))
            if not rows:return
            keys=[stage+':'+e['id'] for stage,e in rows]
            selected=st.selectbox('Choose an answer',keys,format_func=lambda key:next(e['question']['question_text'] for stage,e in rows if key==stage+':'+e['id']),key='conversation_edit_choice')
            def reopen():
                stage,eid=st.session_state.conversation_edit_choice.split(':',1)
                text=perform(s.edit_answer,stage,eid)
                if text is not None:st.session_state.conversation_answer_text=text
            st.button('Edit this answer',on_click=reopen)

    def information():
        if s.stage!='scenario' or s.pending:return
        with st.expander('Explain this example (optional)'):
            st.selectbox('Choose a question',s.instrument['information_questions'],key='conversation_information_choice')
            st.info(NOTICE)
            st.text_input('Your short question (optional)',key='conversation_information_text',max_chars=300)
            def show():
                from .readiness_retrieval import ExplanationClient
                if '_conversation_explainer' not in st.session_state:st.session_state._conversation_explainer=ExplanationClient()
                perform(s.ask_information,st.session_state.get('conversation_information_text','').strip() or st.session_state.conversation_information_choice,
                    st.session_state._conversation_explainer)
            st.button('Show sourced explanation',on_click=show)
            shown=[e for e in s.information_exposures if e['kind']=='explanation']
            if shown:
                e=shown[-1];result=e['content'];sources={p['id']:p for p in result['passages']}
                st.write('Draft explanation from the supplied material. Local policies and engineering guarantees may remain unknown.')
                st.text(result['notice'])
                for item in result['excerpts']:
                    st.text(item['quotation']);p=sources[item['passage_id']]
                    st.text(p['document_title']+' · '+p['location']+' · '+p['id'])
                st.button('I have read this',on_click=perform,args=(s.acknowledge,e['id']))
                st.button('Reflect on this information',on_click=perform,args=(s.start_reflection,))

    state=s.state
    if state in {'general_welcome','general_context'}:
        st.subheader('Before we begin')
        c=s.respondent or {};base=s.general.instrument
        for field,bank,label in [('perspective','perspectives','Are you answering personally or representing an organisation?'),
            ('role','stakeholders','Which of these best describes your role?'),('city','cities','Which city or region are you answering about?')]:
            value=c.get('stakeholder_category' if field=='role' else field);keys=list(base[bank])
            st.selectbox(label,keys,index=keys.index(value) if value in keys else None,format_func=lambda k,b=bank:base[b][k],key='conversation_'+field)
        if st.session_state.conversation_city=='other':
            st.info(NOTICE);st.text_input('Broad city or region (optional)',key='conversation_place_text',max_chars=80)
        if st.session_state.conversation_perspective=='organisation':
            st.info(NOTICE);st.text_input('Your function or responsibility (optional)',key='conversation_function_text',max_chars=240)
        def begin():perform(s.set_context,st.session_state.conversation_perspective,st.session_state.conversation_role,
            st.session_state.conversation_city,st.session_state.get('conversation_place_text','') if st.session_state.conversation_city=='other' else '',
            st.session_state.get('conversation_function_text','') if st.session_state.conversation_perspective=='organisation' else '')
        st.button('Begin',type='primary',on_click=begin)
    elif state in {'general_interview','scenario_interview'}:
        phase=s.phase;q=s.current_question
        st.subheader('A few questions' if s.stage=='general' else 'The illustrative example')
        if s.stage=='scenario':
            count=sum(e['active'] and e['confirmed'] for e in phase.events)
            if count==0:
                st.text(s.card.get('title',s.card['id']))
                st.text(s.card['text'])
                st.write('This is an illustrative example, not a confirmed local plan.')
                with st.expander('What is not specified'):st.text(', '.join(s.card['unknowns']))
            else:
                with st.expander('Read the example again'):st.text(s.card['text']);st.text('Unknown: '+', '.join(s.card['unknowns']))
            st.write('Your first view' if count==0 else f'Follow-up {count} · up to {s.instrument["scenario_followup_budget"]}')
        else:st.write(f'Question {sum(e["active"] and e["confirmed"] for e in phase.events)+1} · up to {s.instrument["general_budget"]}')
        st.text(q['question_text'])
        if q.get('format')=='selection':
            st.radio('Your answer',list(phase.instrument['familiarity']),index=None,format_func=lambda k:phase.instrument['familiarity'][k],key='conversation_familiarity')
            st.button('Continue',type='primary',on_click=lambda:perform(s.answer,st.session_state.get('conversation_familiarity') or '',client,planner))
        else:
            with st.form('conversation_answer_form'):
                st.info(NOTICE);st.text_area('Your answer',key='conversation_answer_text',height=150,max_chars=6000)
                def submit():
                    perform(s.answer,st.session_state.get('conversation_answer_text',''),client,planner)
                    if s.phase.state=='review':st.session_state.conversation_answer_text=''
                st.form_submit_button('Retry this answer' if s.failed_attempt else 'Continue',type='primary',on_click=submit)
        st.button('Skip',on_click=perform,args=(s.answer,'',client,planner,'skip'))
        st.button('Finish here',on_click=perform,args=(s.finish,))
        information();edits()
    elif state in {'general_review','scenario_review'}:
        pending=s.pending;st.subheader('Have we understood you correctly?');st.text(pending['question']['question_text'])
        lines=list(dict.fromkeys(c['interpretation'] for c in pending['claims']))
        if not lines:lines=[{'unsure':'You are unsure about this question.','declined':'You prefer not to answer.',
            'confused':'You did not understand this question.'}.get(pending['interaction'],'We have not captured a clear interpretation yet. You can correct it or ask us to read again.')]
        for line in lines:st.text(line)
        st.button('Confirm and continue',type='primary',on_click=perform,args=(s.confirm_answer,planner))
        with st.expander('Correct our interpretation or your answer'):
            st.info(NOTICE);st.text_area('What should we understand differently?',key='conversation_correction_text',max_chars=1500)
            st.button('Apply correction',on_click=lambda:perform(s.correct_interpretation,st.session_state.get('conversation_correction_text',''),client))
            st.button('Re-read my answer',on_click=perform,args=(s.correct_interpretation,'Re-read the original answer and retain only meanings supported by its exact passages.',client))
        with st.expander('Your original answer'):st.text(pending['text'])
    elif state=='general_baseline_review':
        st.subheader('Check your summary');summary()
        st.button('Confirm and see an example',type='primary',on_click=perform,args=(s.confirm_general,))
        def finish_general():
            perform(s.confirm_general)
            if s.stage=='offer':perform(s.decline_scenario)
        st.button('Finish without an example',on_click=finish_general);edits()
    elif state=='offer':
        st.subheader('Explore an illustrative example?')
        options=s.scenario_options();keys=[c['id'] for c in options]
        selected=st.selectbox('Choose an example',keys,index=keys.index(s.card['id']),
            format_func=lambda key:next(c.get('title',c['id']) for c in options if c['id']==key),key='conversation_scenario_choice')
        if selected!=s.card['id']:perform(s.select_scenario,selected)
        st.write('Examples are ordered by your selected city and the topics in your confirmed answers. You can choose another example.')
        st.text(s.card['text'])
        st.text(s.card['source']['document']+' · '+s.card['source']['locator'])
        st.write('A source-described plan or hypothetical example does not establish a current local service. For organisational respondents, this discussion does not audit the organisation or its technical system.')
        st.button('Continue with this example',type='primary',on_click=perform,args=(s.accept_scenario,planner))
        st.button('Finish here',on_click=perform,args=(s.decline_scenario,));edits()
    elif state in {'scenario_baseline_review','final_review'}:
        st.subheader('Check your final summary');summary()
        st.button('Confirm final summary',type='primary',on_click=perform,args=(s.confirm_final,))
        information();edits()
    elif state=='final':
        st.subheader('Your summary');summary()
        st.info('Continue with draft citizen indicator self-assessment below. This interview does not produce an overall societal readiness score.')
        from .indicator_ui import render_indicators
        render_indicators(s,perform)
        try:
            data=s.browser_export()
            download_button('Download interview (JSON)',json.dumps(data,ensure_ascii=False,indent=2),file_name='iam-conversation.json',mime='application/json')
            download_button('Download interview (JSONL)',json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',file_name='iam-conversation.jsonl',mime='application/x-ndjson')
        except PrivacyError as exc:st.warning(safe_message(exc))
        with st.expander('Evidence, sources and assessment limits'):
            for phase in [s.general]+([s.scenario] if s.scenario else []):
                for c in phase.current_profile['claims']:
                    st.text(c.get('span_quote') or phase.evidence.get(c['evidence_id'],''));st.text(c['interpretation'])
                    st.text(c['dimension']+' · '+c['evidence_status']+' · '+c['information_context']+' · confirmed meaning; external verification absent')
            st.write('Additional answers refine the assessment. Reading this example or completing the chat alone does not establish historical engagement, co-design or influence.')
            for source in s.collection['sources']:st.text(source['document'])
        if developer and s.respondent['perspective']=='personal':
            with st.expander('Historical global-anchor estimate (developer only; not v4)'):
                st.write('An evidence assessment against each draft workbook level, with a separate model check of supported levels. It may abstain and is not an approved rubric result or SRL.')
                def estimate():
                    from .readiness_score import WorkbookScoreClient
                    perform(s.provisional_estimate,WorkbookScoreClient())
                st.button('Request a provisional estimate',on_click=estimate)
                if s._provisional:
                    p=s._provisional;st.text('Draft citizen CRL estimate: '+str(p['crl']) if p['crl'] else 'A numerical estimate is unavailable.')
                    st.text(p['explanation']);st.text(p['uncertainty'])
                    if p['criterion']:st.text(p['criterion']['label']+': '+p['criterion']['description'])
                    st.text('Supporting answer IDs: '+', '.join(p['evidence_ids']))
                    anchors={a['level']:a for a in s.rubric['crl']}
                    for row in p.get('criteria',[]):
                        st.write('**CRL '+str(row['level'])+' · '+anchors[row['level']]['label']+' · '+row['status']+'**')
                        st.text(row['reason'])
                        for claim in row.get('supporting_evidence',[]):st.text(claim['span_quote'])
        edits()
    if state not in {'general_welcome','general_context'}:
        def back():
            text=perform(s.back)
            if text is not None:st.session_state.conversation_answer_text=text
        st.button('Back',on_click=back)
    if developer:
        with st.expander('FN concept example — historical illustrative scoring'):
            historical=next((p for p in s.collection['explanations'] if p['id']=='FN-HISTORICAL' and 'researcher_reference' in p['permitted_use']),None)
            if historical:
                st.text(historical['text']);st.text(historical['document_title']+' · '+historical['location'])
                st.write('These source-provided example values are not model outputs or a current readiness result. Medical-purpose support alone does not demonstrate equity knowledge. The example supplies no universal executable update formula.')
            else:st.write('The historical reference is unavailable in this collection.')
        with st.expander('Researcher collection and planning details'):
            st.json(s.collection['coverage']);st.json(s.plans)
            download_button('Download private corpus for internal review',json.dumps(s.collection,ensure_ascii=False,indent=2),file_name='iam-conversation-corpus.json',mime='application/json')
    footer(baseline=True)
