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
        try:
            with st.spinner('Reading your answer…'):invoke(action,*args)
        except (AssessmentError,ValueError) as exc:
            from .ui_errors import user_error
            st.session_state.baseline_error=(safe_message(exc) if isinstance(exc,PrivacyError) else user_error(exc)+' You can also choose Unsure or Skip.' if isinstance(exc,AssessmentError) else safe_message(exc))
            if developer:st.session_state.baseline_diagnostics=safe_diagnostics({'code':getattr(exc,'code','validation'),'message':safe_message(exc)})
    preview_control(perform)
    if st.session_state.get('baseline_error'):st.warning(st.session_state.baseline_error)
    if developer and st.session_state.get('baseline_diagnostics'):
        with st.expander('Developer diagnostics'):st.json(st.session_state.baseline_diagnostics)

    def edit_controls():
        with st.expander('Edit your details or an earlier answer'):
            st.button('Edit perspective or city',on_click=perform,args=(s.edit_context,))
            for e in s.events:
                if e['active'] and e['confirmed']:
                    def edit(event=e):
                        perform(s.edit_answer,event['id'])
                        st.session_state.baseline_answer_text=event['text']
                        if event['question']['id']=='familiarity':st.session_state.baseline_familiarity=event['text']
                    st.button(e['question']['question_text'],key='baseline_edit_'+e['id'],on_click=edit)

    def summary():
        c=s.respondent
        st.write('**About you**')
        st.text(s.instrument['perspectives'][c['perspective']]+' · '+s.instrument['stakeholders'][c['stakeholder_category']])
        st.text(c['broad_place'] or s.instrument['cities'][c['city']])
        if c['function']:st.text(c['function'])
        p=s.current_profile
        for dim,label in s.instrument['dimensions'].items():
            st.write('**'+{'familiarity':'What you had heard before','understanding':'What you know so far','information':'What you would like to know','exposure':'Your experience and learning','participation':'Activities and contributions','influence':'What changed after your contribution','opportunity':'Ways to take part and what makes it difficult'}.get(dim,label)+'**')
            rows=[r for r in p['claims'] if r['dimension']==dim]
            if rows:
                for text in dict.fromkeys(r['interpretation'] for r in rows):st.text(text)
            else:
                status=p['coverage'][dim]['status']
                st.text({'not_asked':'We did not ask about this.','skipped':'You skipped this item.',
                    'declined':'You preferred not to answer.','unknown':'You were unsure.',
                    'unclear':'We have not captured this clearly yet.'}.get(status,'We have not discussed this yet.'))
            if p['coverage'][dim]['status']=='scope_unclear':
                st.text('You described both having and not having experience. We still need to clarify whether you meant different activities or times.')

    if s.state in {'welcome','context'}:
        st.subheader('Before we begin')
        st.write('Tell us what you already know or have experienced about drones transporting goods or healthcare materials. No particular proposal is being assessed.')
        st.info(NOTICE)
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
            def save_context():
                perform(s.set_context,st.session_state.baseline_perspective,st.session_state.baseline_stakeholder_category,
                    st.session_state.baseline_city,st.session_state.get('baseline_place_text','') if st.session_state.baseline_city=='other' else '',st.session_state.get('baseline_function_text','') if st.session_state.baseline_perspective=='organisation' else '')
            st.button('Begin',type='primary',on_click=save_context)
    elif s.state=='interview':
        q=s.current_question
        count=sum(e['active'] and e['confirmed'] for e in s.events)
        st.subheader('A few questions')
        st.write(f'Question {count+1} of at most {s.maximum_questions}')
        st.write(q['question_text'])
        if q['id']=='familiarity':
            st.radio('Your answer',list(s.instrument['familiarity']),format_func=lambda key:s.instrument['familiarity'][key],key='baseline_familiarity',index=None)
            def select():perform(s.answer,st.session_state.get('baseline_familiarity') or '',client)
            st.button('Continue',type='primary',on_click=select)
        else:
            with st.form('baseline_response'):
                st.text_area('Your answer',key='baseline_answer_text',height=140,max_chars=6000)
                def submit():
                    before=s.state;perform(s.answer,st.session_state.get('baseline_answer_text',''),client)
                    if s.state!=before:st.session_state.baseline_answer_text=''
                st.form_submit_button('Continue',type='primary',on_click=submit)
        controls=st.columns(3)
        for col,label,control in zip(controls,['Unsure','Skip','Prefer not to answer'],['unsure','skip','decline']):
            def skip(ctrl=control):
                perform(s.answer,'',client,ctrl);st.session_state.baseline_answer_text=''
            col.button(label,on_click=skip)
        st.button('Finish now',on_click=perform,args=(s.finish,))
        edit_controls()
    elif s.state=='review':
        st.subheader('Have we understood you correctly?')
        if s.pending['claims']:
            for text in dict.fromkeys(c['interpretation'] for c in s.pending['claims']):st.text(text)
        else:st.write('We have not captured a clear summary of this answer. Please correct it if we missed something.')
        st.button('Confirm and continue',type='primary',on_click=perform,args=(s.confirm,True))
        with st.expander('Correct this answer'):
            st.text_area('Corrected answer',value=s.pending['text'],key='baseline_correction_text')
            def correct():perform(s.correct_pending,st.session_state.get('baseline_correction_text',''),client)
            st.button('Review correction',on_click=correct)
        edit_controls()
    elif s.state=='baseline_review':
        st.subheader('Check your summary')
        summary()
        st.button('Confirm summary',type='primary',on_click=perform,args=(s.complete,))
        edit_controls()
    elif s.state=='complete':
        st.subheader('Your summary')
        summary()
        st.info('This summary describes what you told us. It does not assign a readiness score.')
        edit_controls()
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
    footer(baseline=True)
