"""One-step citizen flow; numeric/audit details are explicit developer mode only."""
import os
import streamlit as st
from iam_sra.session import Session, State
from iam_sra.conversation_client import ConversationClient
from iam_sra.settings import SCENARIO, CONCERNS, config
from iam_sra.assessment import AssessmentError
from iam_sra.reporting import final_summary

st.set_page_config(page_title='IAM · Your perspective',page_icon='◈',layout='centered')
st.title('IAM · Your perspective')
st.caption('Experimental scenario assessment. There are no preferred answers.')
mock=os.getenv('IAM_MOCK','0')=='1'
developer=os.getenv('IAM_DEVELOPER','0')=='1'
if mock:
    from iam_sra.mock import MockConversationClient
    client=MockConversationClient()
    st.warning('MOCK MODE — fixed test fixture; this does not evaluate your views.')
else:client=ConversationClient()
if 'session' not in st.session_state:st.session_state.session=Session()
s=st.session_state.session
st.button('Start over',on_click=st.session_state.clear)
labels={State.SCENARIO:'The proposal',State.ANSWER:'Your answer',State.INTERPRETATION:'Understanding your view',State.CONFIRMED:'Review saved',State.INITIAL:'Preparing questions',State.FOLLOWUPS:'A few follow-ups',State.UPDATED:'Reviewing the outcome',State.UPDATE_CONFIRMED:'Review saved',State.FINAL:'Complete'}
st.progress((list(State).index(s.state)+1)/len(State),text=labels[s.state])

PLAIN={'supported':'acceptable','opposed':'unacceptable','mixed':'acceptable in some respects, with changes needed in others','uncertain':'still undecided','unassessed':'not yet clear'}
ASPECTS={'personal_privacy':'viewing private spaces','perceived_safety':'feeling physically safe','data_security':'security and access to data','system_reliability':'reliability and physical safety','medical_public_benefit':'the medical public benefit','distributive_equity':'fair distribution of benefits','acoustic_impact':'the sound of the flights'}

def plain(text):
    for cid,c in CONCERNS.items():text=text.replace(cid,c['label'])
    for c in CONCERNS.values():
        for f in c['facets']:text=text.replace(f,ASPECTS.get(f,f.replace('_',' ')))
    return text


def perform(action,*args):
    st.session_state.pop('action_error',None)
    try:
        with st.spinner('Working on your answer…'):action(*args)
    except (AssessmentError,ValueError) as exc:
        st.session_state.developer_error=str(exc)
        code=getattr(exc,'code',None)
        if code=='budget':message='Please shorten your answer and try Continue again. Your draft is saved; we do not cut your words.'
        elif code in {'transport','timeout','schema','truncated','thinking'}:message='We could not complete this safely. Your answers and any saved confirmation are retained. Retry Continue, or use Edit to clarify your view.'
        else:message='Please choose an answer or clarify the indicated view before continuing. Your draft is retained; you can also Skip where offered.'
        st.session_state.action_error=message


def summary(meaning,context):
    st.write('**'+context+'**')
    st.write('• You find this proposal '+PLAIN[meaning.current_route_stance.interpretation]+'.')
    benefit=meaning.medical_public_benefit_support.interpretation
    if benefit!='unassessed':st.write('• The medical public benefit is '+PLAIN[benefit]+' to you.')
    for c in meaning.concerns:
        if c.status=='needs_clarification' and not c.excerpts:continue
        st.write('• '+CONCERNS[c.concern_id]['label']+': '+plain(c.rationale))
    with st.expander('Your supporting words'):
        refs=list(dict.fromkeys(r for c in meaning.concerns for r in c.excerpts+c.conditions))
        for r in refs:st.text(s.evidence[r].text)
        if not refs:st.write('No specific topic has been established. Unmentioned topics remain unknown.')


def edit(modified=False):
    with st.expander('Edit this interpretation'+(' for the changed proposal' if modified else '')):
        tag='modified' if modified else 'original'
        with st.form('edit_'+tag):
            targets=['current_route_stance','medical_public_benefit_support','awareness_understanding']+list(CONCERNS)
            names={'current_route_stance':'Position on the proposal','medical_public_benefit_support':'Medical public benefit','awareness_understanding':'What I understand'}
            st.selectbox('What should we correct?',targets,format_func=lambda t:CONCERNS[t]['label'] if t in CONCERNS else names[t],key='target_'+tag)
            st.text_area('Tell us what you meant',key='edit_text_'+tag)
            def save():perform(s.correct_modified if modified else s.correct,st.session_state['target_'+tag],st.session_state['edit_text_'+tag],'Citizen correction of displayed meaning',client)
            st.form_submit_button('Save edit',on_click=save)
        if not modified:
            for cid,b in s.blockers.items():
                st.write(CONCERNS[cid]['label']+' alone makes the original unacceptable: '+{'yes':'Yes','no':'No','unsure':'Unsure'}[b['status']])
                with st.form('boundary_'+cid):
                    st.radio('Correct this boundary',['yes','no','unsure'],format_func=lambda v:v.capitalize(),index=None,key='boundary_'+cid)
                    st.text_area('Optional explanation',key='boundary_text_'+cid)
                    def save_boundary(c=cid):perform(s.correct_blocker,c,st.session_state['boundary_'+c],st.session_state['boundary_text_'+c])
                    st.form_submit_button('Save boundary edit',on_click=save_boundary)


def discovery():
    q=s.discovery_question
    if q is None:
        s.finish_discovery('sufficient');st.rerun()
    st.info('A few questions will help us understand your position; there are no preferred answers.')
    st.write(q['text'])
    st.caption('Question '+str(len(s.discovery_responses)+1)+' of at most '+str(config('discovery')['maximum_questions']))
    labels=config('discovery')['choice_labels']
    label=lambda v:CONCERNS[v]['label'] if v in CONCERNS else config('discovery')['topic_choice_labels'][v] if q['kind']=='topic' else labels[v]
    with st.form('discovery_'+q['id'],clear_on_submit=False):
        if q['multiple']:st.multiselect('What matters to you?',q['choices'],format_func=label,key=q['id']+'_selection')
        else:st.radio('Your view',q['choices'],format_func=label,index=None,key=q['id']+'_selection')
        st.text_area('Anything to add? (optional)',key=q['id']+'_text')
        def answer():
            choice=st.session_state[q['id']+'_selection'];choice=choice if isinstance(choice,list) else [choice] if choice else []
            perform(s.respond_discovery,choice,st.session_state[q['id']+'_text'],client)
        st.form_submit_button('Continue',on_click=answer)
    st.button('Skip',on_click=perform,args=(s.respond_discovery,[],'',client,None,True))
    st.button('Finish these questions',on_click=perform,args=(s.finish_discovery,))


def confirmation(updated=False):
    st.subheader('Have we understood you correctly?')
    summary(s.draft,'The unchanged original proposal')
    if updated and s.conditional_draft:
        summary(s.conditional_draft,'The combined hypothetical proposal')
        for f in s.facet_meanings:
            if f.position!='unassessed' and f.applicability_explicit:st.write('• For '+ASPECTS.get(f.facet,f.facet.replace('_',' '))+', your view of the changed proposal is '+PLAIN[f.position]+'.')
        for f in s.facet_meanings:
            if not f.applicability_explicit or f.position in {'uncertain','unassessed'}:st.write('• Your position on '+ASPECTS.get(f.facet,f.facet.replace('_',' '))+' under the combination still needs clarification.')
        from iam_sra.updates import blocker_report
        for cid,boundary in blocker_report(s)['modified'].items():
            st.write('• '+CONCERNS[cid]['label']+' under the combined changes: '+{'unresolved':'the earlier boundary is still unresolved','remaining':'an objection remains','addressed_under_modification':'the earlier boundary is addressed under these assumptions'}[boundary['status']]+'.')
        edit(True)
    for cid,b in s.blockers.items():
        if b['status']=='yes':st.write('• '+CONCERNS[cid]['label']+' alone would make the original proposal unacceptable to you.')
        elif b['status']=='unsure':st.write('• You have not decided whether '+CONCERNS[cid]['label'].lower()+' alone would be decisive.')
    edit()
    key=('updated_confirm_' if updated else 'confirm_')+str(s.version)
    saved=s.state in {State.CONFIRMED,State.UPDATE_CONFIRMED,State.INITIAL}
    if saved:st.caption('Your confirmation is saved. Continue retries the unfinished step; Edit requires a new confirmation.')
    else:st.checkbox('This reflects what I meant',key=key)
    with st.expander('Question options'):
        if not updated:st.checkbox('Use the original FN reference questions',key='reference_mode')
    def go():
        agreed=True if saved else st.session_state.get(key,False)
        perform(s.continue_final if updated else s.continue_initial,*((agreed,client) if updated else (agreed,client,st.session_state.get('reference_mode',False))))
    st.button('Continue',on_click=go,type='primary')
    st.caption('Confirmation checks meaning. It does not validate the measurement.')


def combined_question():
    st.subheader('Consider these changes together')
    changes=[q['contract']['modification'] for q in s.presented_followups if q.get('apply_to_joint')]
    for change in changes:st.write('• '+plain(change))
    with st.expander('Full combined proposal'):st.write(s.combined_proposal)
    st.caption('These are hypothetical assumptions. Accepting separate changes does not mean accepting their combination.')
    with st.form('joint',clear_on_submit=False):
        st.radio('Do you accept this exact combined proposal?',['accept','reject','unsure'],format_func=lambda v:{'accept':'Accept','reject':'Reject','unsure':'Unsure'}[v],index=None,key='joint_choice')
        st.multiselect('Which issues remain? (optional)',list(CONCERNS),format_func=lambda cid:CONCERNS[cid]['label'],key='joint_remaining')
        st.text_area('Remaining conditions or anything to clarify (optional)',key='joint_text')
        def go():perform(s.record_joint,st.session_state.joint_choice,st.session_state.joint_remaining,st.session_state.joint_text,client)
        st.form_submit_button('Continue',on_click=go)


if st.session_state.get('action_error'):st.error(st.session_state.action_error)
if s.state==State.SCENARIO:
    st.subheader(SCENARIO['title']);st.write(SCENARIO['text'])
    st.caption('The route details are scenario assumptions.')
    st.button('Continue',on_click=perform,args=(s.begin,),type='primary')
elif s.state==State.ANSWER:
    with st.expander('The proposal'):st.write(SCENARIO['text'])
    with st.form('answer',clear_on_submit=False):
        st.text_area('How do you feel about this proposal? What would make it acceptable?',key='citizen_answer')
        def submit():perform(s.submit,st.session_state.citizen_answer,client)
        st.form_submit_button('Continue',on_click=submit)
elif s.state==State.INTERPRETATION and not s.discovery_finished:
    discovery()
elif s.state in {State.INTERPRETATION,State.CONFIRMED,State.INITIAL}:
    if s.conflicts:
        problem=next(iter(s.conflicts.values()));st.info(problem['question']);edit()
    else:confirmation()
elif s.state==State.FOLLOWUPS:
    q=s.current_question
    st.write(q['text'])
    st.caption('Unchanged original proposal' if q['contract']['context']=='original' else 'Hypothetical question; feasibility is not established.')
    with st.form('followup_'+q['id'],clear_on_submit=False):
        st.radio('Your view',q['choices'],index=None,key='choice_'+q['id'])
        st.text_area('Anything to clarify? (optional)',key='text_'+q['id'])
        if q['contract']['context']=='hypothetical':st.radio('Your added words describe',['hypothetical','original'],format_func=lambda v:'This hypothetical change' if v=='hypothetical' else 'The unchanged original proposal',key='context_'+q['id'])
        def go():perform(s.respond,st.session_state['choice_'+q['id']],st.session_state['text_'+q['id']],client,st.session_state.get('context_'+q['id'],'original'))
        st.form_submit_button('Continue',on_click=go)
    st.button('Skip',on_click=perform,args=(s.skip_followup,))
    st.button('Finish questions',on_click=perform,args=(s.stop_followups,))
    if q.get('reference_text'):
        with st.expander('Reference wording'):st.write(q['reference_text'])
elif s.state in {State.UPDATED,State.UPDATE_CONFIRMED}:
    if s.conflicts:
        key,problem=next(iter(s.conflicts.items()));st.info(problem['question'])
        with st.form('resolve_'+key,clear_on_submit=False):
            st.text_area('Clarify what you mean',key='resolve_'+key)
            def resolve():perform(s.resolve_conflict,key,st.session_state['resolve_'+key],client)
            st.form_submit_button('Continue',on_click=resolve)
    elif s.joint_required and s.joint is None:combined_question()
    else:confirmation(True)
else:
    result=final_summary(s)
    if result['headline_score'] is None:st.subheader('Insufficient evidence for a numerical assessment')
    else:st.metric('Provisional scenario-readiness score',str(result['headline_score'])+'/9')
    st.write('**Proposal context:** '+('Combined hypothetical proposal' if result['selected_profile']=='conditional_modified' else 'Unchanged original proposal' if result['selected_profile']=='final_original' else 'Your original and hypothetical views, where discussed'))
    st.write(result['explanation'])
    st.write('Your view of the original route: '+PLAIN[result['original_route_position']]+'.')
    if result['modified_route_position']:st.write('Your view of the combined changes: '+PLAIN[result['modified_route_position']]+'.')
    if result['modified_assessment_attempted'] and not result['modified_aggregate_available']:st.info('The modified proposal was considered, but there is insufficient evidence for its numerical assessment. Any displayed score is for the original proposal.')
    for condition in result['remaining_conditions']:st.write('Condition you stated: '+condition['citizen_quote'])
    for cid in result['decisive_remaining_boundaries']:st.write('Acceptance boundary still remaining or unresolved: '+CONCERNS[cid]['label']+'.')
    for cid in result['remaining_modified_topics']:st.write('Remaining issue under the changes: '+CONCERNS[cid]['label']+'.')
    st.download_button('Download assessment JSONL',s.jsonl(),file_name='iam-assessment.jsonl',mime='application/x-ndjson')
    with st.expander('More about this result'):
        st.write('Coverage: '+str(result['coverage'] or 'Insufficient evidence'))
        for limitation in result['limitations']:st.caption(limitation)
        for issue in s.unmapped_issues:st.write('Recorded issue: '+issue['wording'])
        st.download_button('Download readable JSON',s.json(),file_name='iam-assessment.json',mime='application/json')
if developer:
    with st.expander('Developer diagnostics'):
        st.json({'state':s.state.value,'last_error':st.session_state.get('developer_error'),'model':config('model'),'policy':config('updates'),'inference':s.inference})
        if s.state==State.FINAL:st.json(s.export()['aggregation'])
