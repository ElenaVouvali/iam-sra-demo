"""Scenario-free baseline screens; substantive confirmation and explicit handoff."""
import streamlit as st
from .privacy import NOTICE, PrivacyError, safe_message, safe_diagnostics
from .privacy_ui import invoke, preview_control, download_button
from .assessment import AssessmentError
from .ui_presentation import restart_control, footer


def render(s,client,developer=False):
    restart_control()
    def perform(action,*args):
        st.session_state.pop('baseline_error',None)
        st.session_state.pop('baseline_diagnostics',None)
        try:
            with st.spinner('Reading your answer…'):return invoke(action,*args)
        except (AssessmentError,ValueError) as exc:
            from .ui_errors import user_error
            st.session_state.baseline_error=(safe_message(exc) if isinstance(exc,PrivacyError) else user_error(exc) if isinstance(exc,AssessmentError) else safe_message(exc))
            if developer:st.session_state.baseline_diagnostics=safe_diagnostics({'code':getattr(exc,'code','validation'),'diagnostics':getattr(client,'last_diagnostics',[]),'message':safe_message(exc)})
    preview_control(perform)
    if st.session_state.get('baseline_error'):st.warning(st.session_state.baseline_error)
    if developer and st.session_state.get('baseline_diagnostics'):
        with st.expander('Developer diagnostics'):st.json(st.session_state.baseline_diagnostics)

    def summary():
        c=s.respondent
        st.write('**About you**')
        st.text(s.instrument['perspectives'][c['perspective']]+' · '+s.instrument['stakeholders'][c['stakeholder_category']])
        st.text(c['broad_place'] or s.instrument['cities'][c['city']])
        if c['function']:st.text(c['function'])
        p=s.current_profile
        gaps=[]
        for dim,label in s.instrument['dimensions'].items():
            rows=[r for r in p['claims'] if r['dimension']==dim and not r.get('clarified_by_evidence_ids')]
            if not rows:
                status=p['coverage'][dim]['status']
                description={'not_asked':'We did not ask about this.','skipped':'You skipped this question.',
                    'declined':'You preferred not to answer.','unknown':'You were unsure.',
                    'unclear':'We have not captured this clearly yet.'}.get(status,'We have not discussed this yet.')
                gaps.append((label,description));continue
            st.write('**'+label+'**')
            for text in dict.fromkeys(r['interpretation'] for r in rows):st.text(text)
            if p['coverage'][dim]['status']=='scope_unclear':
                st.write('We still need to clarify whether these reports refer to different activities or times.')
        if gaps:
            with st.expander('What we have not discussed'):
                for label,description in gaps:st.write(label+': '+description)

    if s.state in {'welcome','context'}:
        st.subheader('Before we begin')
        current=s.respondent or {}
        with st.container():
            values={}
            for field,bank,label in [('perspective','perspectives','Are you answering personally or representing an organisation?'),
                ('stakeholder_category','stakeholders','Which of these best describes your role?'),
                ('city','cities','Which city or region are you answering about?')]:
                keys=list(s.instrument[bank]);default=current.get(field)
                values[field]=st.selectbox(label,keys,index=keys.index(default) if default in keys else None,format_func=lambda k,b=bank:s.instrument[b][k],key='baseline_'+field)
            if values['city']=='other':
                st.text_input('Broad city or region name (optional)',value=current.get('broad_place') or '',key='baseline_place_text',max_chars=80)
            if values['perspective']=='organisation':
                st.text_input('Function or responsibility (optional)',value=current.get('function') or '',key='baseline_function_text',max_chars=240)
            if values['city']=='other' or values['perspective']=='organisation':st.info(NOTICE)
            def save_context():
                perform(s.set_context,st.session_state.baseline_perspective,st.session_state.baseline_stakeholder_category,
                    st.session_state.baseline_city,st.session_state.get('baseline_place_text','') if st.session_state.baseline_city=='other' else '',st.session_state.get('baseline_function_text','') if st.session_state.baseline_perspective=='organisation' else '')
            st.button('Begin',type='primary',on_click=save_context)
    elif s.state=='interview':
        q=s.current_question
        count=sum(e['active'] and e['confirmed'] for e in s.events)
        st.subheader('A few questions')
        st.write(f'Question {count+1}')
        st.write(q['question_text'])
        if q['id']=='familiarity':
            st.radio('Your answer',list(s.instrument['familiarity']),format_func=lambda key:s.instrument['familiarity'][key],key='baseline_familiarity',index=None)
            def select():perform(s.answer,st.session_state.get('baseline_familiarity') or '',client)
            st.button('Continue',type='primary',on_click=select)
        else:
            with st.form('baseline_response'):
                st.info(NOTICE)
                st.text_area('Your answer',key='baseline_answer_text',height=140,max_chars=6000)
                def submit():
                    before=s.state;perform(s.answer,st.session_state.get('baseline_answer_text',''),client)
                    if s.state!=before:st.session_state.baseline_answer_text=''
                st.form_submit_button('Continue',type='primary',on_click=submit)
        if st.session_state.get('baseline_error') and q['id']!='familiarity':
            def retry():
                before=s.state;perform(s.answer,st.session_state.get('baseline_answer_text',''),client)
                if s.state!=before:st.session_state.baseline_answer_text=''
            st.button('Try reading my answer again',on_click=retry)
        controls=st.columns(3)
        for col,label,control in zip(controls,['Unsure','Skip','Prefer not to answer'],['unsure','skip','decline']):
            def skip(ctrl=control):
                perform(s.answer,'',client,ctrl);st.session_state.baseline_answer_text=''
            col.button(label,on_click=skip)
        st.button('Finish now',on_click=perform,args=(s.finish,))
        if 'definition' in s.instrument and (q['id']=='concept' or any(e['active'] and e['question']['id']=='concept' and (e['control'] in {'unsure','skip'} or e.get('interaction') in {'unsure','confused'} or any(c['kind'] in {'unknown','absence'} for c in e['claims'])) for e in s.events)):
            with st.expander('What does “drone” mean? (optional)'):
                st.write('You can keep going without an explanation, or ask for a short definition. We record when it is shown.')
                st.button('Show definition',on_click=perform,args=(s.show_definition,))
        if s.information_exposures:
            st.text(s.information_exposures[-1]['text'])
            st.write('Draft explanation — awaiting review.')
    elif s.state=='review':
        st.subheader('Check our interpretation')
        st.write(s.pending['question']['question_text'])
        with st.expander('Your answer'):
            st.text(s.pending['text'])
        current_interpretation='\n'.join(dict.fromkeys(c['interpretation'] for c in s.pending['claims']))
        revision=s.pending.get('interpretation_revision',0)
        edit_key=f"baseline_interpretation_{s.pending['id']}_{revision}"
        if current_interpretation:
            st.text_area('Edit our interpretation',value=current_interpretation,
                         key=edit_key,max_chars=1500,height=120)
            st.write('Your edit guides a fresh reading; your original answer stays unchanged.')
        else:
            st.write('We could not summarize this answer yet. You can tell us what we missed, or ask us to re-read it.')
            st.text_area('What did we miss?',value='',key=edit_key,max_chars=1500,height=120)
        st.button('Confirm and continue',type='primary',on_click=perform,args=(s.confirm,True))
        st.button('Re-read my answer',on_click=perform,
                  args=(s.correct_interpretation,
                        'Re-read the original answer. Revise your interpretation only where the answer supports it; do not add facts.',client))
        def correct():
            feedback=st.session_state.get(edit_key,current_interpretation)
            if feedback.strip():perform(s.correct_interpretation,feedback,client)
        st.button('Apply my correction',on_click=correct,disabled=not bool(current_interpretation) and not bool(st.session_state.get(edit_key,'')))
    elif s.state=='baseline_review':
        st.subheader('Check your summary')
        summary()
        st.button('Confirm summary',type='primary',on_click=perform,args=(s.complete,))
        interpretations=[e for e in s.events if e['active'] and e['confirmed'] and e['claims'] and e['question']['id']!='familiarity']
        if interpretations:
            with st.expander('Correct an interpretation in this summary'):
                selected=st.selectbox('Which interpretation?', [e['id'] for e in interpretations],
                    format_func=lambda key:next(e['claims'][0]['interpretation'] for e in interpretations if e['id']==key))
                st.button('Review this interpretation',on_click=perform,args=(s.review_interpretation,selected))
    elif s.state=='complete':
        st.subheader('Your summary')
        summary()
        st.info('This summary describes what you told us. It does not assign a readiness score.')
        try:
            data=s.json();download_button('Download answers and record (JSON)',data,file_name='iam-baseline.json',mime='application/json')
            download_button('Download answers and record (JSONL)',s.jsonl(),file_name='iam-baseline.jsonl',mime='application/x-ndjson')
        except PrivacyError as exc:
            st.warning(safe_message(exc));footer(baseline=True);return
        st.write('**Optional next step**')
        if s.respondent['perspective']=='personal':
            st.write('If you wish, explore a fictional hospital drone route and share your views. Your answers here will remain separate.')
            def continuation():
                try:st.session_state.session=s.continue_scenario()
                except (PrivacyError,ValueError) as exc:st.session_state.baseline_error=safe_message(exc)
            st.button('Explore a hospital drone route',type='primary',on_click=continuation)
        else:st.write('Thank you. You can download your answers below.')
    if s.state in {'interview','review','baseline_review','complete'}:
        def back():
            text=perform(s.back)
            if text is not None:
                st.session_state.baseline_answer_text=text
                if s.current_question and s.current_question['id']=='familiarity':
                    st.session_state.baseline_familiarity=text or None
        st.button('Back',on_click=back)
    footer(baseline=True)
