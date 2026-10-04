"""One-step citizen flow; numeric/audit details are explicit developer mode only."""
import os
import streamlit as st
from iam_sra.session import Session, State
from iam_sra.conversation_client import ConversationClient
from iam_sra.settings import SCENARIO, CONCERNS, config
from iam_sra.assessment import AssessmentError
from iam_sra.updates import facet_state
from iam_sra.reporting import final_summary, citizen_summary, aspect_label, clarification_needs

st.set_page_config(page_title='Medical drones in your neighborhood',page_icon='◈',layout='centered')
st.title('Medical drones in your neighborhood')
st.write('Share your views on a proposed hospital delivery route. A few questions will help us understand what matters to you—there are no right or wrong answers.')
mock=os.getenv('IAM_MOCK','0')=='1'
developer=os.getenv('IAM_DEVELOPER','0')=='1'
if mock:
    from iam_sra.mock import MockConversationClient
    if "_conversation_client" not in st.session_state:st.session_state._conversation_client=MockConversationClient()
    client=st.session_state._conversation_client
    st.warning('MOCK MODE — fixed test fixture; this does not evaluate your views.')
else:
    if "_conversation_client" not in st.session_state:st.session_state._conversation_client=ConversationClient()
    client=st.session_state._conversation_client
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
    return text.replace('boundary','condition').replace('facet','aspect').replace('eligibility','supported meaning')


def perform(action,*args):
    st.session_state.pop('action_error',None)
    progress=st.empty()
    client.progress=lambda stage:progress.caption({'mapping':'Understanding your answer…','scope_review':'Checking the supporting passages…','facets':'Checking your views with these changes…','scoring':'Preparing your assessment…','discovery':'Understanding what matters to you…'}.get(stage,'Working on your answer…'))
    try:
        with st.spinner('Working on your answer…'):action(*args)
    except (AssessmentError,ValueError) as exc:
        st.session_state.developer_error=str(exc)
        code=getattr(exc,'code',None)
        if code=='budget':message='Please shorten your answer and try Continue again. Your draft is saved; we do not cut your words.'
        elif code in {'transport','timeout','schema','truncated','thinking'}:message='We could not complete this safely. Your answers and any saved confirmation are retained. Retry Continue, or use Edit to clarify your view.'
        else:message='Please choose an answer or clarify the indicated view before continuing. Your draft is retained; you can also Skip where offered.'
        st.session_state.action_error=message
    finally:
        client.progress=None
        progress.empty()


def summary():
    view=citizen_summary(s)
    for line in view['lines']:st.write('• '+line)
    for aspect in view['remaining_objections']:st.write('• You still have a reservation about '+aspect+'.')
    for need in view['unresolved']:st.write('Not yet clear: '+plain(need['reason']))
    if s.draft.awareness_understanding.interpretation!='unassessed':
        st.write('**My understanding of the drone service**')
        st.write(plain(s.draft.awareness_understanding.rationale))
    with st.expander('Your supporting words'):
        refs=list(dict.fromkeys(r for f in s.original_facets.values() for r in f.evidence_ids))
        for ref in refs:st.text(s.evidence[ref].text)




def rewind_answer(key):
    old=next((r for r in s.responses if r['question_id']==key),None)
    discovery_old=next((r for r in s.discovery_responses if r['question_id']==key),None)
    if old:
        st.session_state['choice_'+key]=old['choice'];st.session_state['text_'+key]=old.get('clarification','')
    elif discovery_old:
        q=next(q for q in s.discovery_questions if q['id']==key)
        values=discovery_old['selections'];st.session_state[key+'_selection']=values if q['multiple'] else values[0] if values else None
        st.session_state[key+'_text']=discovery_old['free_text']
    elif key=='initial_answer':st.session_state.citizen_answer=s.text
    elif key=='combined_proposal' and s.joint:
        st.session_state.joint_choice=s.joint['choice'];st.session_state.joint_text=s.joint['clarification']
        st.session_state.joint_remaining=s.joint['remaining_concern_ids']
        for answer in s.joint.get('applicability_confirmations',[]):
            st.session_state['applies_'+answer['aspect_key']]=answer['response']
            st.session_state['applies_text_'+answer['aspect_key']]=answer['clarification']
    perform(s.rewind,key)

def answer_edits(label='Edit an earlier answer'):
    with st.expander(label):
        if 'initial_answer' in s._checkpoints:st.button('Edit your first answer',on_click=rewind_answer,args=('initial_answer',))
        for q in s.discovery_questions:
            if any(r['question_id']==q['id'] for r in s.discovery_responses):st.button('Edit answer: '+q['text'],key='edit_answer_'+q['id'],on_click=rewind_answer,args=(q['id'],))
        for q in s.presented_followups:
            if any(r['question_id']==q['id'] for r in s.responses):st.button('Edit answer: '+q['text'],key='edit_answer_'+q['id'],on_click=rewind_answer,args=(q['id'],))
        if s.joint and 'combined_proposal' in s._checkpoints:st.button('Edit your answer about the changes together',on_click=rewind_answer,args=('combined_proposal',))


def back():
    key='combined_proposal' if s.joint else s.responses[-1]['question_id'] if s.responses else s.discovery_responses[-1]['question_id'] if s.discovery_responses else 'initial_answer'
    if key in s._checkpoints:st.button('← Back to previous question',on_click=rewind_answer,args=(key,))


def edit(modified=False):
    focus=st.session_state.get('clarify_focus')
    with st.expander('Correct something'+(' about the changed proposal' if modified else ''),expanded=bool(focus)):
        tag='modified' if modified else 'original'
        with st.form('edit_'+tag):
            targets=['current_route_stance','medical_public_benefit_support']+(['awareness_understanding'] if s.draft.awareness_understanding.interpretation!='unassessed' else [])+list(CONCERNS)
            names={'current_route_stance':'Position on the proposal','medical_public_benefit_support':'Medical public benefit','awareness_understanding':'My understanding of the drone service'}
            if s.conditional_draft:st.radio('Which proposal?',['original','modified'],format_func=lambda v:'Unchanged original proposal' if v=='original' else 'Changes together',index=1 if modified else 0,key='edit_context_'+tag)
            st.selectbox('What should we correct?',targets,index=targets.index(focus['concern_id']) if focus and focus['concern_id'] in targets else 0,format_func=lambda t:CONCERNS[t]['label'] if t in CONCERNS else names[t],key='target_'+tag)
            st.text_area('Tell us what you meant',key='edit_text_'+tag)
            def save():perform(s.correct_modified if st.session_state.get('edit_context_'+tag,tag)=='modified' else s.correct,st.session_state['target_'+tag],st.session_state['edit_text_'+tag],'Citizen correction of displayed meaning',client)
            st.form_submit_button('Save edit',on_click=save)
        if not modified:
            for cid,b in s.blockers.items():
                st.write(CONCERNS[cid]['label']+' would make you oppose the original route even if other issues were resolved: '+{'yes':'Yes','no':'No','unsure':'Unsure'}[b['status']])
                with st.form('boundary_'+cid):
                    st.radio('Would this issue alone make you oppose the original route?' ,['yes','no','unsure'],format_func=lambda v:v.capitalize(),index=None,key='boundary_'+cid)
                    st.text_area('Explain your answer, if you wish',key='boundary_text_'+cid)
                    def save_boundary(c=cid):perform(s.correct_blocker,c,st.session_state['boundary_'+c],st.session_state['boundary_text_'+c])
                    st.form_submit_button('Save answer',on_click=save_boundary)


def discovery():
    q=s.discovery_question
    if q is None:
        s.finish_discovery('sufficient');st.rerun()
    st.info('A few questions will help us understand your position; there are no preferred answers.')
    st.write(plain(q['text']))
    st.caption('Question '+str(len(s.discovery_responses)+1)+' of at most '+str(config('discovery')['maximum_questions']))
    labels=config('discovery')['choice_labels']
    label=lambda v:CONCERNS[v]['label'] if v in CONCERNS else config('discovery')['topic_choice_labels'][v] if q['kind']=='topic' else labels[v]
    with st.form('discovery_'+q['id'],clear_on_submit=False):
        if q['multiple']:st.multiselect('What matters to you?',q['choices'],format_func=label,key=q['id']+'_selection')
        else:st.radio('Your view',q['choices'],format_func=label,index=None,key=q['id']+'_selection')
        st.text_area('Explain your answer, if you wish',key=q['id']+'_text')
        def answer():
            choice=st.session_state[q['id']+'_selection'];choice=choice if isinstance(choice,list) else [choice] if choice else []
            perform(s.respond_discovery,choice,st.session_state[q['id']+'_text'],client)
        st.form_submit_button('Continue',on_click=answer)
    st.button('Skip',on_click=perform,args=(s.respond_discovery,[],'',client,None,True))
    st.button('Finish these questions',on_click=perform,args=(s.finish_discovery,))
    back()


def confirmation(updated=False):
    st.subheader('Have we understood you correctly?')
    summary()
    if updated and s.joint:
        for need in clarification_needs(s):
            key=need['concern_id']+':'+need['facet']
            if need['context']=='modified' and key in s.unchanged_aspects():
                st.button('Clarify whether '+aspect_label(need['facet'])+' still applies',key='review_applies_'+key,on_click=rewind_answer,args=('combined_proposal',))
    edit(bool(updated and s.conditional_draft))
    answer_edits()
    back()
    key=('updated_confirm_' if updated else 'confirm_')+str(s.version)
    saved=s.state in {State.CONFIRMED,State.UPDATE_CONFIRMED,State.INITIAL}
    if saved:st.caption('Your confirmation is saved. Continue retries the unfinished step; Edit requires a new confirmation.')
    else:st.checkbox('This reflects what I meant',key=key)
    if developer and not updated:
        with st.expander('Question options'):st.checkbox('Use the original FN reference questions',key='reference_mode')
    def go():
        agreed=True if saved else st.session_state.get(key,False)
        perform(s.continue_final if updated else s.continue_initial,*((agreed,client) if updated else (agreed,client,st.session_state.get('reference_mode',False))))
    st.button('Confirm and finish' if updated else 'Continue',on_click=go,type='primary')


def combined_question():
    st.subheader('Consider these changes together')
    changes=[q['contract']['modification'] for q in s.presented_followups if q.get('apply_to_joint')]
    for change in changes:st.write('• '+plain(change))
    with st.expander('Full combined proposal'):st.write(s.combined_proposal)
    st.write('All other details of the original proposal stay the same.')
    with st.form('joint',clear_on_submit=False):
        st.radio('With these changes together, would you accept this route?' ,['accept','reject','unsure'],format_func=lambda v:{'accept':'Accept','reject':'Reject','unsure':'Unsure'}[v],index=None,key='joint_choice')
        st.multiselect('Which issues remain? (optional)',list(CONCERNS),format_func=lambda cid:CONCERNS[cid]['label'],key='joint_remaining')
        st.text_area('What, if anything, would still concern you?',key='joint_text')
        unchanged=s.unchanged_aspects()
        for key,fact in unchanged.items():
            st.radio(s.applicability_statement(fact),['yes','changed','unsure','skip'],format_func=lambda v:{'yes':'Yes','changed':'My view has changed','unsure':'I’m unsure','skip':'Skip'}[v],index=None,key='applies_'+key)
            # Keep the draft visible; a changed response requires this explanation.
            st.text_area('If your view has changed, please explain',key='applies_text_'+key)
        def go():
            answers={key:{'response':st.session_state.get('applies_'+key),'clarification':st.session_state.get('applies_text_'+key,'')} for key in unchanged}
            if any(a['response'] is None for a in answers.values()):
                st.session_state.action_error='Please answer each earlier-view question, or choose Skip. Your answers are saved.'
                return
            perform(s.record_joint,st.session_state.joint_choice,st.session_state.joint_remaining,st.session_state.joint_text,client,answers)
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
    if len(s.responses)==0:st.info('The next questions consider possible changes, assumed to work as described.')
    st.write(plain(q['text']))
    with st.form('followup_'+q['id'],clear_on_submit=False):
        st.radio('Your view',q['choices'],index=None,key='choice_'+q['id'])
        st.text_area('Explain your answer, if you wish',key='text_'+q['id'])
        def go():perform(s.respond,st.session_state['choice_'+q['id']],st.session_state['text_'+q['id']],client,'hypothetical' if q['contract']['context']=='hypothetical' else 'original')
        st.form_submit_button('Continue',on_click=go)
    st.button('Skip',on_click=perform,args=(s.skip_followup,))
    st.button('Finish questions',on_click=perform,args=(s.stop_followups,))
    back()
    answer_edits('Correct an earlier answer')
    if developer and q.get('reference_text'):
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
    summary()
    if result['modified_assessment_attempted'] and not result['modified_aggregate_available']:st.info('There is not enough clear evidence to calculate a score for the changed proposal. Any displayed score describes the unchanged original proposal.')
    if result['clarification_needs'] or result['headline_score'] is None:
        for need in result['clarification_needs']:
            st.write(plain(need['question']))
            def focus(n=need):
                key=n['concern_id']+':'+n['facet']
                if n['context']=='modified' and key in s.unchanged_aspects() and 'combined_proposal' in s._checkpoints:
                    rewind_answer('combined_proposal')
                    return
                tag='modified' if s.conditional_draft else 'original'
                st.session_state.clarify_focus=n
                st.session_state['target_'+tag]=n['concern_id']
                if s.conditional_draft:st.session_state['edit_context_'+tag]=n['context']
            st.button('Clarify '+aspect_label(need['facet']),key='clarify_'+need['context']+'_'+need['concern_id']+'_'+need['facet'],on_click=focus)
        st.write('You can clarify a specific view or add an omitted topic below.')
        edit(bool(s.conditional_draft))
    answer_edits()
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
