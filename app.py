import os
import streamlit as st
from iam_sra.session import Session, State
from iam_sra.conversation_client import ConversationClient
from iam_sra.settings import SCENARIO, CONCERNS, POLICY, BASE_URL, config
from iam_sra.assessment import AssessmentError
from iam_sra.interpretation import comparison
from iam_sra.validation import conclusions
from iam_sra.schemas import Assessment

st.set_page_config(page_title='IAM · Research demo',page_icon='◈',layout='centered')
st.title('IAM · A citizen perspective')
st.caption('Experimental scenario assessment · confirmation checks meaning, not scientific validity.')
mock=os.getenv('IAM_MOCK','0')=='1'
if mock:
    st.warning('MOCK MODE — fixed uncertain interpretation for GPU-free UI/CI; no Qwen inference.')
    from iam_sra.mock import MockConversationClient
    client=MockConversationClient()
else:client=ConversationClient()
if 'session' not in st.session_state:st.session_state.session=Session()
s=st.session_state.session
st.button('Reset session',on_click=st.session_state.clear)
steps=list(State)
st.progress((steps.index(s.state)+1)/len(steps),text=s.state.value.replace('_',' ').title())
with st.expander(SCENARIO['title'],expanded=s.state in {State.SCENARIO,State.ANSWER}):
    st.write(SCENARIO['text'])
    st.caption('All route details and later modifications are hypothetical assumptions.')
if s.text:
    with st.expander('Your original testimony'):st.text(s.text)

def perform(action,*args):
    st.session_state.pop('action_error',None)
    try:action(*args)
    except (AssessmentError,ValueError) as exc:st.session_state.action_error=str(exc)

def show_meaning(meaning,title):
    st.subheader(title)
    st.caption('Model-proposed wording below. Evidence passages are citizen testimony; confirming wording does not create new testimony.')
    def cite(refs):
        for ref in refs:
            item=s.evidence[ref]
            st.caption(ref+' · '+item.source+' · '+item.context)
            st.text(item.text)
    for name,label in [('current_route_stance','Position on this proposal'),('medical_public_benefit_support','Medical/public-benefit support'),('awareness_understanding','Awareness and understanding')]:
        dim=getattr(meaning,name);st.write('**'+label+':** '+dim.interpretation);st.write(dim.rationale);cite(dim.excerpts)
    for c in meaning.concerns:
        st.write('**'+CONCERNS[c.concern_id]['label']+'**')
        st.write(c.rationale)
        st.caption('Stance: '+c.position+' · Conditional willingness: '+c.conditional_willingness.replace('_',' ')+' · Facets: '+', '.join(c.facets))
        cite(c.excerpts)
        if c.conditions:st.write('**Acceptance conditions**');cite(c.conditions)
        if c.status=='needs_clarification':st.info('Ambiguous mapping — clarify or leave not assessed.')
    mentioned={c.concern_id for c in meaning.concerns}
    with st.expander('Topics without evidence'):
        st.write(', '.join(CONCERNS[i]['label'] for i in CONCERNS if i not in mentioned) or 'All topics mentioned; mention does not establish score eligibility.')

def correction_form(modified=False):
    with st.expander('Correct a meaning or add an omitted concern'+(' under the modified proposal' if modified else ' in the original proposal')):
        targets=['current_route_stance','medical_public_benefit_support','awareness_understanding']+list(CONCERNS)
        tag='modified' if modified else 'original'
        with st.form('correction_'+tag):
            target=st.selectbox('Interpretation to correct',targets,format_func=lambda t:CONCERNS[t]['label'] if t in CONCERNS else t.replace('_',' ').title(),key='target_'+tag)
            text=st.text_area('Your own words about this meaning',key='correction_'+tag)
            reason=st.text_input('Reason for the correction',key='reason_'+tag)
            def save():
                action=s.correct_modified if modified else s.correct
                perform(action,st.session_state['target_'+tag],st.session_state['correction_'+tag],st.session_state['reason_'+tag],client)
            st.form_submit_button('Record correction',on_click=save)

def show_score(snapshot,title):
    if not snapshot:return
    totals=snapshot['aggregate'];st.subheader(title)
    st.metric('Provisional scenario-readiness score',str(totals['rounded'])+'/9' if totals['rounded'] is not None else 'Insufficient evidence')
    st.caption('Coverage: '+totals['coverage']+' · ordinal-score index; coverage differences do not imply personal improvement or decline.')
    with st.expander(title+' · phase summaries and arithmetic'):st.json(totals)

def joint_form():
    st.subheader('The exact combined hypothetical proposal')
    st.write(s.combined_proposal)
    st.caption('Separate acceptance of earlier questions does not establish acceptance of their combination. Q3 remains a policy preference, not an engineering change.')
    with st.form('joint'):
        st.radio('Do you accept this exact combined proposal?',['accept','reject','unsure'],index=None,key='joint_choice')
        st.multiselect('Which concerns remain?',list(CONCERNS),format_func=lambda t:CONCERNS[t]['label'],key='joint_remaining')
        st.text_area('Clarify remaining concerns or conditions in your own words',key='joint_text')
        def save_joint():perform(s.record_joint,st.session_state.joint_choice,st.session_state.joint_remaining,st.session_state.joint_text,client)
        st.form_submit_button('Interpret combined-proposal response',on_click=save_joint)

if st.session_state.get('action_error'):st.error(st.session_state.action_error)
if s.state==State.SCENARIO:st.button('Begin',on_click=perform,args=(s.begin,))
elif s.state==State.ANSWER:
    with st.form('answer'):
        st.text_area('Your response',key='citizen_answer',help='Maximum 4000 UTF-8 bytes; the complete request must fit4096 tokens. No silent truncation.')
        def submit():perform(s.submit,st.session_state.citizen_answer,client)
        st.form_submit_button('Interpret response',on_click=submit)
elif s.state in {State.INTERPRETATION,State.CONFIRMED}:
    show_meaning(s.draft,'Check the interpretation — no scores yet')
    correction_form()
    if s.state==State.INTERPRETATION:
        key='confirm_'+str(s.version)
        st.checkbox('This interpretation reflects what I meant',key=key)
        def confirm():perform(s.confirm,st.session_state[key])
        st.button('Confirm meaning',on_click=confirm)
    else:
        st.success('Meaning confirmed. Numeric review has not run yet.')
        st.button('Calculate initial provisional scores',on_click=perform,args=(s.score_initial,client))
elif s.state==State.INITIAL:
    show_score(s.initial,'Initial assessment — immutable snapshot')
    st.dataframe([{'Concern':CONCERNS[c['concern_id']]['label'],'Initial score':str(c['score']) if c['score'] is not None else 'Not assessed','Reason':c['rationale']} for c in s.initial['assessment']['concerns']],hide_index=True)
    st.checkbox('Consider all three FN reference questions',key='all_questions')
    def followups():perform(s.begin_followups,st.session_state.all_questions)
    st.button('Continue to follow-ups',on_click=followups)
elif s.state==State.FOLLOWUPS:
    q=s.questions[len(s.responses)]
    st.subheader('Follow-up '+q['id'].upper());st.write(q['text'])
    st.caption('FN reference, PDF pp.'+', '.join(map(str,q['source_pages']))+' · hypothetical assumptions. Original scores remain preserved.')
    with st.form('followup_'+q['id']):
        st.radio('Your view',q['choices'],index=None,key='choice_'+q['id'])
        st.text_area('Optional clarification',key='text_'+q['id'])
        st.radio('This clarification describes',['hypothetical','original'],format_func=lambda x:'This hypothetical modification' if x=='hypothetical' else 'My position on the unchanged original proposal',key='context_'+q['id'])
        def respond():perform(s.respond,st.session_state['choice_'+q['id']],st.session_state['text_'+q['id']],client,st.session_state['context_'+q['id']])
        st.form_submit_button('Interpret and record follow-up',on_click=respond)
elif s.state in {State.UPDATED,State.UPDATE_CONFIRMED}:
    for key,problem in s.conflicts.items():
        st.warning(problem['question'])
        with st.form('resolve_'+key):
            st.text_area('Your targeted clarification',key='resolve_text_'+key)
            def resolve(k=key):perform(s.resolve_conflict,k,st.session_state['resolve_text_'+k],client)
            st.form_submit_button('Resolve this interpretation',on_click=resolve)
    show_meaning(s.draft,'Refined interpretation of the ORIGINAL proposal')
    correction_form()
    for r in s.responses:
        with st.expander('Recorded '+r['question_id'].upper()+' · '+r['clarification_context']):
            st.write(r['choice']);st.text(r['clarification']);st.write(r['outcome'])
    if s.joint_required:joint_form()
    if s.conditional_draft:
        show_meaning(s.conditional_draft,'Interpretation under the MODIFIED proposal')
        correction_form(modified=True)
    if s.state==State.UPDATED:
        key='updated_confirm_'+str(s.version)
        st.checkbox('The updated original and hypothetical interpretations reflect what I meant',key=key)
        def confirm_updated():perform(s.confirm_updated,st.session_state[key])
        st.button('Confirm updated meaning',on_click=confirm_updated)
    else:
        st.success('Updated meaning confirmed. Final numerical review has not run yet.')
        st.button('Calculate final provisional scores',on_click=perform,args=(s.score_final,client))
else:
    show_score(s.initial,'Initial original proposal')
    show_score(s.final,'Final refined ORIGINAL proposal')
    show_score(s.conditional,'Separate CONDITIONAL proposal')
    if not s.conditional:st.info('Conditional assessment unavailable: no sufficiently confirmed modified-proposal position.')
    rows=comparison(s.initial,s.final,s.conditional,s.final['update_reasons'])
    st.subheader('All 15 concerns · provisional comparison')
    st.dataframe([{'Concern':r['concern'],'Initial':str(r['initial_score']) if r['initial_score'] is not None else 'Not assessed',
        'Final original':str(r['final_original_score']) if r['final_original_score'] is not None else 'Not assessed',
        'Conditional':str(r['conditional_score']) if r['conditional_score'] is not None else 'Not assessed',
        'Explanation of change':r['reason']+' Conditional: '+r['conditional_reason'],'Evidence':'\n'.join(dict.fromkeys(sum(r['evidence'].values(),[])))} for r in rows],hide_index=True)
    if s.joint:
        stance=s.conditional_confirmed['meaning']['current_route_stance']['interpretation'] if s.conditional_confirmed else 'unresolved'
        st.write('**Combined-proposal choice:** '+s.joint['choice']+' · Confirmed interpretation: '+stance);st.write(s.joint['proposal'])
        st.write('**Remaining concerns:** '+(', '.join(CONCERNS[c]['label'] for c in s.joint['remaining_concern_ids']) or 'None selected; see evidence and untested facets.'))
    tracking=conclusions(s.responses,Assessment.model_validate(s.initial['assessment']))
    with st.expander('Remaining conditions, validation assumptions and untested facets'):st.json(tracking)
    with st.expander('Confirmed interpretations, evidence IDs and correction history'):
        st.json({'confirmations':s.confirmations,'corrections':s.corrections})
    st.download_button('Export session JSON',s.json(),file_name='iam-session.json',mime='application/json')
    st.download_button('Export session JSONL',s.jsonl(),file_name='iam-session.jsonl',mime='application/x-ndjson')
with st.expander('Developer metadata'):
    st.json({'mode':'mock' if mock else 'live','endpoint':BASE_URL,'model':config('model'),'reassessment':config('reassessment')['version'],
        'state':s.state.value,'interpretation_version':s.version,'inference':s.inference})
    st.caption('In-memory session. Raw citizen text is omitted from routine logs; explicit exports contain testimony.')
