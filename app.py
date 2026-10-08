"""Guided citizen flow with initial/final assessments and developer diagnostics."""
import os
import json
import traceback
from contextlib import nullcontext
import streamlit as st
from iam_sra.session import Session, State
from iam_sra.conversation_client import ConversationClient
from iam_sra.settings import SCENARIO, CONCERNS, config
from iam_sra.assessment import AssessmentError
from iam_sra.reporting import final_summary, citizen_summary, aspect_label, clarification_needs
from iam_sra.assessment_review import final_review
from iam_sra.ui_errors import user_error

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
labels={State.SCENARIO:'The proposal',State.ANSWER:'Your answer',State.INTERPRETATION:'Understanding your view',State.CONFIRMED:'Review saved',State.INITIAL:'Your initial assessment',State.FOLLOWUPS:'A few follow-ups',State.UPDATED:'Reviewing the outcome',State.UPDATE_CONFIRMED:'Review saved',State.FINAL:'Complete'}
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
    st.session_state.pop('failure_details',None)
    client.last_request_context={}
    progress=st.empty()
    client.progress=lambda stage:progress.caption({'mapping':'Understanding your answer…','coverage_review':'Checking for missed points…','scope_review':'Checking the supporting passages…','facets':'Checking your views with these changes…','scoring':'Preparing your assessment…','discovery':'Understanding what matters to you…'}.get(stage,'Working on your answer…'))
    try:
        with st.spinner('Working on your answer…'):action(*args)
    except (AssessmentError,ValueError) as exc:
        st.session_state.developer_error=str(exc)
        st.session_state.action_error=user_error(exc)
        frames=traceback.extract_tb(exc.__traceback__)
        st.session_state.failure_details={
            'message':str(exc),
            'exception_type':type(exc).__name__,
            'action':getattr(action,'__qualname__',type(action).__name__),
            'session_state':s.state.value,
            'failure_location':{'file':frames[-1].filename,'line':frames[-1].lineno,'function':frames[-1].name} if frames else {},
            'error_code':getattr(exc,'code','validation'),
            'prompt_version':config('prompts')['version'],
            'request':getattr(client,'last_request_context',{}),
            'diagnostics':getattr(client,'last_diagnostics',[]) if getattr(client,'last_request_context',{}) else []}
    finally:
        client.progress=None
        progress.empty()


def summary(nested=False):
    view=citizen_summary(s)
    for line in view['lines']:st.write('• '+line)
    for aspect in view['remaining_objections']:st.write('• You still have a reservation about '+aspect+'.')
    with nullcontext() if nested else st.expander('Your supporting words'):
        if nested:st.write('**Your supporting words**')
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
            targets=['current_route_stance','medical_public_benefit_support']+list(CONCERNS)
            names={'current_route_stance':'Position on the proposal','medical_public_benefit_support':'Medical public benefit'}
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
    st.subheader('Clarify your answer')
    st.info('An initial score is not available yet. You can clarify your view or skip this question.')
    st.write(plain(q['text']))
    st.caption('Question '+str(len(s.discovery_responses)+1)+' of at most '+str(config('discovery')['maximum_questions']))
    labels=config('discovery')['choice_labels']
    label=lambda v:CONCERNS[v]['label'] if v in CONCERNS else config('discovery')['topic_choice_labels'][v] if q['kind']=='topic' else labels[v]
    with st.form('discovery_'+q['id'],clear_on_submit=False):
        if q['multiple']:st.multiselect('What matters to you?',q['choices'],format_func=label,key=q['id']+'_selection')
        else:st.radio('Your view',q['choices'],format_func=label,index=None,key=q['id']+'_selection')
        if q['kind']!='acceptance_check':st.text_area('Explain your answer, if you wish',key=q['id']+'_text')
        def answer():
            choice=st.session_state[q['id']+'_selection'];choice=choice if isinstance(choice,list) else [choice] if choice else []
            perform(s.respond_discovery,choice,st.session_state.get(q['id']+'_text',''),client)
        st.form_submit_button('Continue',on_click=answer)
    st.button('Skip',on_click=perform,args=(s.respond_discovery,[],'',client,None,True))
    st.button('Finish these questions',on_click=perform,args=(s.finish_discovery,))
    back()


def confirmation(updated=False):
    st.subheader('Have we understood you correctly?')
    if not updated and getattr(s,'mapping_review_errors',{}):
        st.warning('The model did not complete this interpretation. Use “Edit an earlier answer” to retry your saved answer; rewriting it is not required. This incomplete interpretation cannot be scored.')
    summary()
    if updated:
        st.write('Review your follow-up answers. Hypothetical changes do not rewrite your initial assessment.')
        for answer in s.responses:
            question=answer['presented_question']
            topic='Policy priority' if question['id'] in {'macro_policy','q3'} else ', '.join(CONCERNS[c]['label'] for c in question['relevant_concerns'])
            st.write('**'+topic+'**: '+(answer['choice'] or 'Skipped'))
            if answer.get('clarification'):st.write(answer['clarification'])
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
    else:
        st.checkbox('This reflects what I meant',key=key)
        if not st.session_state.get(key,False):st.caption('Tick “This reflects what I meant” to confirm this review and continue.')
    if developer and not updated:
        with st.expander('Question options'):st.checkbox('Use the original FN reference questions',key='reference_mode')
    def go():
        agreed=True if saved else st.session_state.get(key,False)
        if updated:perform(s.continue_final,agreed,client)
        else:
            def prepare():
                if s.state==State.INTERPRETATION:s.confirm(agreed,defer_discovery=s.initial is None)
                existing=s.initial is not None
                s.score_initial(client)
                if existing and s.discovery_deferred:s.begin_followups(st.session_state.get('reference_mode',False))
            perform(prepare)
    st.button('Confirm and finish' if updated else 'Continue',on_click=go,type='primary',disabled=not saved and not st.session_state.get(key,False))


def combined_question():
    st.subheader('Consider these changes together')
    changes=[q['contract']['modification'] for q in s.presented_followups if q.get('apply_to_joint')]
    for change in changes:st.write('• '+change)
    with st.expander('Full combined proposal'):st.write(s.combined_proposal)
    st.write('All other details of the original proposal stay the same.')
    with st.form('joint',clear_on_submit=False):
        st.radio('With these changes together, would you accept this route?' ,['accept','reject','unsure'],format_func=lambda v:{'accept':'Accept','reject':'Reject','unsure':'Unsure'}[v],index=None,key='joint_choice')
        st.multiselect('Which issues remain? (optional)',list(CONCERNS),format_func=lambda cid:CONCERNS[cid]['label'],key='joint_remaining')
        st.text_area('What, if anything, would still concern you?',key='joint_text')
        unchanged=s.unchanged_aspects()
        for key,fact in unchanged.items():
            st.radio(s.applicability_statement(fact),['yes','changed','unsure','skip'],format_func=lambda v:{'yes':'Yes','changed':'No','unsure':'I’m unsure','skip':'Skip'}[v],index=None,key='applies_'+key)
            st.text_area('If your answer is different now, what changed? (optional)',key='applies_text_'+key)
        def go():
            answers={key:{'response':st.session_state.get('applies_'+key),'clarification':st.session_state.get('applies_text_'+key,'')} for key in unchanged}
            if any(a['response'] is None for a in answers.values()):
                st.session_state.action_error='Please answer each earlier-view question, or choose Skip. Your answers are saved.'
                return
            perform(s.record_joint,st.session_state.joint_choice,st.session_state.joint_remaining,st.session_state.joint_text,client,answers)
        st.form_submit_button('Continue',on_click=go)


# Submitting the last fixed-choice answer is sufficient for deterministic updates.
# Added testimony and explicitly requested combined assessments retain review.
choice_only_outcome=(s.state in {State.UPDATED,State.UPDATE_CONFIRMED}
    and not s.conflicts and not s.joint_confirmation_required and s.joint is None
    and all(not r.get('clarification','').strip() for r in s.responses))
if choice_only_outcome and not st.session_state.get('action_error'):
    perform(s.continue_final,True,client)
    if s.state==State.FINAL:st.rerun()

if st.session_state.get('action_error'):
    st.error(st.session_state.action_error)
    if st.session_state.get('failure_details'):
        with st.expander('Technical details for this failed attempt'):
            st.code(json.dumps(st.session_state.failure_details,indent=2),language='json')
if s.state==State.SCENARIO:
    st.subheader(SCENARIO['title']);st.write(SCENARIO['text'])
    st.button('Continue',on_click=perform,args=(s.begin,),type='primary')
elif s.state==State.ANSWER:
    with st.expander('The proposal'):st.write(SCENARIO['text'])
    with st.form('answer',clear_on_submit=False):
        st.text_area('How do you feel about this proposal? What would make it acceptable?',key='citizen_answer')
        def submit():perform(s.submit,st.session_state.citizen_answer,client)
        st.form_submit_button('Continue',on_click=submit)
elif s.state==State.INTERPRETATION and not s.discovery_finished and s.initial is not None:
    if s.initial['aggregate']['trace']['denominator']>0:
        # Resume existing sessions that were already in the removed first set.
        # Earlier answers remain in the audit; no new blocker is inferred.
        s.state=State.INITIAL
        s.continue_initial_review(st.session_state.get('reference_mode',False))
        st.rerun()
    else:discovery()
elif s.state==State.INITIAL:
    st.subheader('Your initial assessment')
    st.caption('Based on your first answer to the original proposal, before any follow-up questions.')
    snapshot=s.initial
    aggregation=snapshot['aggregate']
    rows=[]
    for concern in snapshot['assessment']['concerns']:
        rows.append({'Concern':CONCERNS[concern['concern_id']]['label'],'Phase':CONCERNS[concern['concern_id']]['phase'],
            'Score':str(concern['score'])+'/9' if concern['score'] is not None else 'Not assessed','Reason':plain(concern['rationale'])})
    st.dataframe(rows,hide_index=True,use_container_width=True)
    if aggregation['rounded'] is None:st.info('No concern has a valid score yet, so an overall score is unavailable.')
    else:st.metric('Initial scenario-readiness score',str(aggregation['rounded'])+'/9')
    trace=aggregation['trace']
    st.write('Aggregation: the equally weighted mean of assessed concerns. Unassessed concerns are excluded.')
    if aggregation['mean'] is not None:
        terms=' + '.join(str(item['score']) for item in trace['mean_inputs'])
        st.write('Mean: ('+terms+') / '+str(trace['denominator'])+' = '+format(aggregation['mean'],'.2f'))
    st.write('Bottleneck: take the lowest assessed concern score across all phases and add '+str(trace['offset'])+'. The result caps the mean; it never increases it.')
    if aggregation['cap'] is not None:
        names=', '.join(CONCERNS[item['concern_id']]['label']+' ('+str(item['score'])+')' for item in trace['eligible_blockers'])
        st.write('Eligible concerns: '+names+'. Cap: '+str(trace['selected_minimum'])+' + '+str(trace['offset'])+' = '+str(aggregation['cap'])+'.')
        if aggregation['adjusted'] is not None:st.write('Adjusted mean: min('+format(aggregation['mean'],'.2f')+', '+str(aggregation['cap'])+') = '+format(aggregation['adjusted'],'.2f'))
    else:st.write('No eligible concern triggers a cap in this assessment.')
    st.caption('Coverage: '+aggregation['coverage']+'. One assessed concern is sufficient. The adjusted mean is rounded to the nearest integer, with halves rounded down. This is an experimental index of the assessed topics.')
    st.button('Continue to follow-up questions',on_click=perform,args=(s.continue_initial_review,st.session_state.get('reference_mode',False)),type='primary')
    answer_edits()
elif s.state in {State.INTERPRETATION,State.CONFIRMED}:
    if s.conflicts:
        problem=next(iter(s.conflicts.values()));st.info(problem['question']);edit()
    else:confirmation()
elif s.state==State.FOLLOWUPS:
    q=s.current_question
    st.caption('Question '+str(len(s.responses)+1)+' of '+str(len(s.questions)))
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
    if choice_only_outcome:
        st.button('Retry final assessment',on_click=perform,args=(s.continue_final,True,client),type='primary')
        answer_edits()
    elif s.conflicts:
        key,problem=next(iter(s.conflicts.items()));st.info(problem['question'])
        with st.form('resolve_'+key,clear_on_submit=False):
            st.text_area('Clarify what you mean',key='resolve_'+key)
            def resolve():perform(s.resolve_conflict,key,st.session_state['resolve_'+key],client)
            st.form_submit_button('Continue',on_click=resolve)
    elif s.joint_confirmation_required and s.joint is None:combined_question()
    else:
        if s.joint_required and s.joint is None:
            with st.expander('Check whether changes work together (optional)'):
                st.write('Use this if changes interact or you want to assess acceptance of one combined proposal. Independent answers alone do not establish combined acceptance.')
                def request_combined():s.require_combined_review=True
                st.button('Assess the combined proposal',on_click=request_combined)
        confirmation(True)
else:
    result=final_summary(s)
    review=final_review(s)
    st.subheader('Your final assessment')
    value=lambda n:str(n)+'/9' if n is not None else 'Unavailable'
    st.metric('Updated SRL after follow-ups',value(review['final_headline']))
    if review['final_headline'] is None:
        st.info('An SRL is unavailable because there is not enough evidence to assess your view.')
    answer_edits()
    with st.expander('More about this result'):
        summary(nested=True)
        st.write('Coverage: '+str(result['coverage'] or 'Insufficient evidence'))
        for limitation in result['limitations']:st.caption(limitation)
        for issue in s.unmapped_issues:st.write('Recorded issue: '+issue['wording'])
        st.download_button('Download assessment JSONL',s.jsonl(),file_name='iam-assessment.jsonl',mime='application/x-ndjson')
        st.download_button('Download readable JSON',s.json(),file_name='iam-assessment.json',mime='application/json')
if developer:
    with st.expander('Developer diagnostics'):
        st.json({'state':s.state.value,'last_error':st.session_state.get('developer_error'),'model':config('model'),'policy':config('updates'),'inference':s.inference})
        if s.state==State.FINAL:st.json(s.export()['aggregation'])
