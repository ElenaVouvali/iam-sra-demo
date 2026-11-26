"""Focused invariants for the opt-in model-led FN interview strategy."""
from copy import deepcopy

import pytest

from iam_sra.assessment import AssessmentError
from iam_sra.chat_session import ChatSession
from iam_sra.chat_score import profile_match_schema, validate_profile_match
from iam_sra.chat_policy import rubric
from iam_sra.fn_interview import FNInterview
from indicator_fixtures import bank
from fn_fixture import reply


def _start(monkeypatch, depth='short'):
    monkeypatch.setenv('IAM_CHAT_INTERVIEW_STRATEGY','model_led_fn')
    s=ChatSession(bank(),depth,synthetic=True)
    return s


class PlanningClient:
    def __init__(self, target, question, *, kind='yes', status='explored', coverage=None, action='advance'):
        self.target=target;self.question=question;self.kind=kind;self.status=status
        self.coverage=coverage;self.action=action

    def turn(self,request):
        coverage=deepcopy(self.coverage)
        if coverage:
            for item in coverage:
                if item.get('evidence_id')=='m-test':item['evidence_id']=request['current_answer_id']
        out=reply(request,kind=self.kind,status=self.status,action=self.action,coverage=coverage)
        out['message']=self.question
        out['interpretation']['next_goal_id']=self.target
        out['interpretation']['question_purpose']='Resolve the next material evidence question.'
        return out


def _onboard_citizen(s,client):
    s.send('A. Citizen',client)
    s.send('Madrid',client)
    s.send('20 minutes',client)
    assert s.objective=='drone_recognition'


def _complete_pre_topic_stages(s):
    stages=s.fn.stages(s.profile,s.depth)
    topic_index=next(i for i,stage in enumerate(stages) if any(q['id'] in {
        'open_priorities','open_more','different_impacts','requirements_open'}
        for q in stage['questions']))
    for stage_index,stage in enumerate(stages[:topic_index]):
        for node_index,node in enumerate(stage['questions']):
            s.fn.record(node['id'],f'm-pre-{stage_index}-{node_index}','unknown','uncertain')


def test_strategy_is_opt_in_and_snapshot_contains_method_not_questionnaire(monkeypatch):
    monkeypatch.delenv('IAM_CHAT_INTERVIEW_STRATEGY',raising=False)
    baseline=FNInterview()
    assert baseline.strategy=='controller_fn'
    led=_start(monkeypatch)
    snap=led.fn.snapshot('citizen','short','drone_recognition',led.context,[],model_led_active=True)
    assert snap['strategy']=='model_led_fn' and snap['model_led_active']
    assert set(snap['allowed_objectives'])=={q['id'] for q in led.fn.nodes('citizen','short')}
    assert snap['stage_ledger'] and all('canonical_question' not in goal for stage in snap['stage_ledger'] for goal in stage['goals'])


@pytest.mark.parametrize(('answer','kind','target','question'),[
    ('Yes, I know what a drone is.','yes','drone_description','How would you describe it to someone who has not seen one?'),
    ('No, I am not familiar with drones.','no','drone_explanation','Would a brief explanation be helpful before we continue?'),
])
def test_same_question_can_lead_to_answer_dependent_valid_objectives(monkeypatch,answer,kind,target,question):
    s=_start(monkeypatch);onboarding=PlanningClient(None,'')
    _onboard_citizen(s,onboarding)
    client=PlanningClient(target,question,kind=kind)
    s.send(answer,client)
    assert s.objective==target
    if answer.startswith('No,'):
        assert 'Would you like a short explanation?' in s.messages[-1]['text']
        assert 'explanation' in s.messages[-1]['text'].casefold()
    else:
        assert s.messages[-1]['text']==question
    assert s.messages[-1]['source']['wording']=='Qwen proposed; FN harness validated'
    accepted=[e for e in s.routing_events if e['event']=='model_led_question_accepted']
    assert accepted[-1]['objective_id']==target


def test_negative_drone_recognition_cannot_skip_fn_explanation_offer(monkeypatch):
    s=_start(monkeypatch);_onboard_citizen(s,PlanningClient(None,''))
    # Even if Qwen proposes moving to healthcare awareness, the controller
    # requires FN's optional explanation offer after explicit unfamiliarity.
    s.send('No, I do not know what a drone is.',PlanningClient('healthcare_awareness',
        'Have you heard of healthcare drone services?',kind='no'))
    assert s.objective=='drone_explanation'
    assert 'explanation' in s.messages[-1]['text'].casefold()
    assert s.fn.coverage['drone_recognition']['status'] in {'explored','unknown'}


def test_one_answer_can_ground_multiple_applicable_goals_and_avoid_reasking(monkeypatch):
    s=_start(monkeypatch);_onboard_citizen(s,PlanningClient(None,''))
    answer='Yes, a drone is an aircraft without a pilot, and I have heard of photography uses.'
    eid='m-test'
    coverage=[{'goal':goal,'evidence_id':eid,'quote':answer,'status':'explored',
               'answer_kind':'yes' if goal=='drone_recognition' else 'substantive'}
              for goal in ('drone_recognition','drone_description','drone_uses')]
    client=PlanningClient('healthcare_awareness','Before today, had you heard of healthcare deliveries?',
        kind='yes',coverage=coverage)
    s.send(answer,client)
    assert {'drone_recognition','drone_description','drone_uses'} <= set(s.fn.coverage)
    assert s.objective=='healthcare_awareness'


def test_conclusion_proposal_cannot_bypass_fn_goals(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short'
    s.context['city']='Madrid';s.stage='conversation';s.objective='drone_recognition'
    s.fn.record('area','m1','explored');s.fn.record('drone_recognition','m2','explored','yes')
    s.fn.record('citizen_duration','m3','explored')
    result={'message':'Thank you.','interpretation':{'action':'conclude','next_goal_id':None,
        'question_purpose':'The goals are complete.'}}
    s._model_led_route(result)
    assert s.stage=='conversation'
    assert s.objective=='healthcare_awareness'
    assert s.messages[-1]['act']=='question'
    assert s._last_decision['model_led_transition']['rejection_reason']=='required_fn_stages_remain'


def test_model_led_allows_question_selection_across_unresolved_stages(monkeypatch):
    s=_start(monkeypatch);_onboard_citizen(s,PlanningClient(None,''))
    client=PlanningClient('opinion','Overall, what do you think about this service?',kind='yes')
    s.send('Yes, drones can be useful.',client)
    assert s.objective=='opinion'
    assert s._last_decision['model_led_transition']['accepted'] is True


def test_completion_requires_each_fn_stage_considered_not_every_question(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    for index,stage in enumerate(s.fn.stages('citizen','short')):
        node=next((q for q in stage['questions'] if s.fn.applicable(q,s.concerns)),None)
        if node:s.fn.record(node['id'],f'm{index+1}','explored')
    assert not s.fn.model_led_unconsidered_stages('citizen','short',s.concerns)
    assert s.fn.model_led_gaps('citizen','short',s.concerns)  # unasked optional/detail objectives remain
    result={'message':'Thank you for sharing your perspective.',
        'interpretation':{'action':'conclude','next_goal_id':None,'question_purpose':'All FN stages were considered.'}}
    s._report=lambda *args,**kwargs:setattr(s,'stage','ended')
    s._model_led_route(result)
    assert s.stage=='ended'
    assert s._last_decision['model_led_transition']['accepted'] is True


def test_stage_ledger_and_export_separate_considered_from_goal_completion(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    first=s.fn.stages('citizen','short')[0]['questions'][0]
    s.fn.record(first['id'],'m1','explored')
    snap=s.fn.snapshot('citizen','short',first['id'],{},[],model_led_active=True)
    assert snap['stage_ledger'][0]['methodological_status']=='considered'
    progression=s.fn.export('citizen','short',[],model_led=True)
    assert progression['stages'][0]['status']=='explored'
    assert progression['stages'][0]['methodological_status']=='considered'


def test_g7_g10_consistency_marker_rejects_contradictory_scoring_output():
    s=ChatSession(bank(),synthetic=True);s.profile='organisational'
    anchors=rubric(s.bank,'organisational','short')['anchors']
    payload={'anchors':anchors,'originals':[{'id':'m7','text':'A supervised pilot was completed; roles and procedures were tested.'}]}
    value={'selected_anchor_id':anchors[2]['id'],'boundary_direction':'higher','alternative_anchor_id':None,
        'citations':[{'evidence_id':'m7'}],
        'explanation':'The unit has identified requirements and gaps.',
        'boundary':'No planning or preparation has been demonstrated.',
        'material_conflict':False,'evidence_incomplete':False,
        'consistency_check':'contradiction','consistency_evidence_ids':['m7']}
    with pytest.raises(AssessmentError,match='conflicts with active respondent evidence'):
        validate_profile_match(value,payload)


def test_model_led_score_schema_requires_a_consistency_check_and_valid_ids():
    schema=profile_match_schema({'anchors':[{'id':'org-1'}],
        'originals':[{'id':'m7','text':'Reported pilot.'}]})
    assert {'consistency_check','consistency_evidence_ids'} <= set(schema['required'])
    assert schema['properties']['consistency_evidence_ids']['items']['enum']==['evidence-1']


def test_explicit_drone_explanation_is_supplied_once_without_becoming_prior_knowledge(monkeypatch):
    class ExplanationClient(PlanningClient):
        def turn(self,request):
            out=reply(request,kind='uncertain',status='unknown',action='explain')
            out['message']='Before today, had you heard about drones transporting healthcare items?'
            out['interpretation']['answer_polarity']='uncertain'
            out['interpretation']['next_goal_id']='healthcare_awareness'
            out['interpretation']['information_request']='drone_definition'
            out['interpretation']['information_request_quote']='Could you explain it simply?'
            return out
    s=_start(monkeypatch);_onboard_citizen(s,PlanningClient(None,''))
    client=ExplanationClient('healthcare_awareness','Before today, had you heard about healthcare drone services?')
    s.send("I don't know what a drone is. Could you explain it simply?",client)
    supplied=[m for m in s.messages if m.get('act')=='supplied_information']
    assert len(supplied)==1
    assert supplied[0]['text'].startswith('A drone is an aircraft that can fly without a pilot sitting inside it.')
    exposure=s.exposures[-1]
    assert exposure['prior_knowledge'] is False and exposure['newly_supplied_information'] is True
    assert exposure['request_evidence_id'] in s.fn.coverage['drone_recognition']['evidence_ids']
    assert s.fn.coverage['drone_recognition']['status']=='unknown'
    assert s.objective=='healthcare_awareness'
    assert not any('Would you like' in m['text'] for m in s.messages)
    assert s.fn.coverage['drone_description']['status']=='unknown'


def test_mixed_explicit_requests_get_bounded_answers_and_separate_exposures(monkeypatch):
    from iam_sra.chat_session import ChatSession
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.objective='healthcare_awareness';s.context['city']='Coimbra'
    text="I don't know what a drone is. Could you explain it, and give an example of how a clinic sample could reach a lab?"
    row={'id':'m-request','text':text}
    result={'interpretation':{'information_request':'drone_definition',
        'information_request_quote':'Could you explain it'},'source_ids':[]}
    assert s._respond_to_information_need(text,result,row,'healthcare_awareness',{})
    supplied=next(m for m in reversed(s.messages) if m.get('act')=='supplied_information')
    assert 'aircraft that can fly without a pilot sitting inside it' in supplied['text']
    assert 'clinic' in supplied['text'] and 'laboratory' in supplied['text']
    assert len(s.exposures)==2
    assert {e['categories'][0] for e in s.exposures}=={'drone_definition','sample_delivery_example'}
    assert all(e['request_evidence_id']=='m-request' and e['prior_knowledge'] is False
               and e['newly_supplied_information'] is True for e in s.exposures)


def test_no_question_means_no_unsolicited_background(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.objective='healthcare_awareness';s.context['city']='Coimbra'
    text='I had not heard about healthcare drones before.'
    assert not s._respond_to_information_need(text,{'interpretation':{}},{'id':'m-noask','text':text},
                                              'healthcare_awareness',{})
    assert not s.exposures


def test_model_information_label_cannot_add_definition_absent_from_quoted_request(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.objective='healthcare_awareness';s.context['city']='Coimbra'
    text='Could you explain how a medical sample might get from a clinic to a lab?'
    row={'id':'m-request','text':text}
    result={'interpretation':{'information_request':'drone_definition',
        'information_request_quote':text},'source_ids':[]}
    assert s._respond_to_information_need(text,result,row,'healthcare_awareness',{})
    supplied=next(m for m in reversed(s.messages) if m.get('act')=='supplied_information')
    assert 'clinic' in supplied['text'] and 'laboratory' in supplied['text']
    assert 'aircraft that can fly without a pilot' not in supplied['text']
    assert [e['categories'][0] for e in s.exposures]==['sample_delivery_example']


def test_information_answer_does_not_repeat_open_question_after_invalid_plan(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.context.update(city='Coimbra',scope_status='respondent_described')
    s.objective='healthcare_awareness';s.fn.record('area','m-area','explored')
    text='I do not know how this works. Could you explain medical deliveries?'
    row=s._user(text)
    result={'message':'', '_quality_issues':['eligibility'],
        '_model_led_plan_rejected':'invalid_message',
        'interpretation':{'action':'advance','next_goal_id':'healthcare_awareness',
            'question_purpose':'','coverage':[]}}
    assert s._respond_to_information_need(text,result,row,'healthcare_awareness',{})
    s.fn.record('healthcare_awareness',row['id'],'unresolved','uncertain')
    s._last_decision={}
    s._model_led_route(result)
    assert s.messages[-1]['text'] != s.fn.current(s.profile,s.depth,'healthcare_awareness')['canonical_question']
    assert s.fn.coverage['healthcare_awareness']['status']=='unresolved'


def test_bounded_question_generation_failure_retains_answer_and_uses_fn_bridge(monkeypatch):
    from iam_sra.assessment import AssessmentError
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.context.update(city='Coimbra',scope_status='respondent_described')
    for goal in ('area','citizen_duration','drone_recognition','drone_description','drone_uses',
                 'drone_explanation','healthcare_awareness','local_awareness'):
        s.fn.record(goal,f'm-{goal}','unknown','uncertain')
    s.objective='decisions'
    class InvalidQuestionClient:
        last_metrics={'generation_calls':2};last_diagnostics=[];last_context_selection={}
        def turn(self,request):raise AssessmentError('Generated question invalid.',code='eligibility',field='message')
    answer='I do not know how decisions about a service would be made here.'
    s._fn_turn(answer,InvalidQuestionClient())
    assert s.active_evidence()[-1]['text']==answer
    assert s.fn.coverage['decisions']['status']=='unresolved'
    assert s.failed_turn_id is None and s.stage=='conversation'
    assert s.objective!='decisions'
    assert s.messages[-1]['act']=='authored_fallback'
    assert s.routing_events[-1]['event']=='model_question_recovered'
    s._model_led_route({'message':'How are decisions made?','interpretation':{
        'action':'advance','next_goal_id':'decisions','question_purpose':'Repeat unresolved question.'}})
    assert s.objective!='decisions'


def test_documented_unresolved_goal_is_not_reasked_or_counted_as_readiness(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short'
    s.fn.record('area','m-area','unresolved','uncertain')
    assert 'area' not in s.fn.model_led_gaps('citizen','short',[])
    assert 'context' not in {stage['id'] for stage in
        s.fn.model_led_unconsidered_stages('citizen','short',[])}
    exported=s.fn.export('citizen','short',[],model_led=True)
    context=next(stage for stage in exported['stages'] if stage['id']=='context')
    area=next(goal for goal in context['goals'] if goal['id']=='area')
    assert area['status']=='unresolved' and context['methodological_status']=='considered'
    assert 'area' in exported['unresolved_gaps']


def test_model_led_cannot_repeat_prior_knowledge_probe_after_definition_was_supplied(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.context['city']='Madrid';s.objective='drone_recognition'
    s.fn.record('area','m1','explored');s.fn.record('citizen_duration','m2','explored')
    s.fn.record('drone_recognition','m3','unknown','uncertain')
    s.fn.record('drone_description','m3','unknown','uncertain')
    s.fn.record('drone_explanation','m3','provided','provided')
    s._model_led_route({'message':'Could you explain what a drone is?',
        'interpretation':{'action':'follow_up','next_goal_id':'drone_recognition',
            'question_purpose':'Ask the participant to define a drone again.'}})
    assert s._last_decision['model_led_transition']['accepted'] is False
    assert s._last_decision['model_led_transition']['rejection_reason']=='follow_up_not_materially_unresolved'
    assert s.objective!='drone_recognition'


@pytest.mark.parametrize(('profile','depth','later_goal'),[
    ('citizen','short','opinion'),('citizen','extended','opinion'),
    ('organisational','short','planning'),('technical','short','controlled')])
def test_fn_suggested_issue_prompt_is_used_when_no_concern_was_raised(monkeypatch,profile,depth,later_goal):
    s=_start(monkeypatch,depth);s.profile=profile;s.depth=depth;s.stage='conversation'
    s.context.update({'city':'Madrid','organisation_or_unit':'planning unit',
        'responsibilities':'advisory role','technical_object':'drone delivery subsystem'})
    _complete_pre_topic_stages(s)
    flow=s.fn.nodes(profile,depth)
    open_ids={'open_priorities','open_more','different_impacts','requirements_open'}
    for node in flow:
        if node['id'] in open_ids and s.fn.applicable(node,s.concerns):
            s.fn.record(node['id'],'m-open','explored')
    s.objective='open_more'
    result={'message':'Could you describe another readiness activity?',
        'interpretation':{'action':'advance','next_goal_id':later_goal,'question_purpose':'Explore another issue.'}}
    s._model_led_route(result)
    menu_id='priorities' if profile=='technical' else 'suggested_topics'
    assert s.objective==menu_id
    menu_node=s.fn.current(profile,depth,menu_id)
    assert menu_node['canonical_question'] in s.messages[-1]['text']
    assert any(row.startswith('• ') for row in s.messages[-1]['text'].splitlines())
    assert s.fn.coverage[menu_id]['status']=='provided' if profile!='technical' else menu_id not in s.fn.coverage
    assert s._last_decision['topic_sequence_bridge']['goal']==menu_id


@pytest.mark.parametrize(('profile','depth','later_goal'),[
    ('citizen','short','opinion'),('organisational','short','planning'),('technical','short','controlled')])
def test_fn_keeps_open_discussion_before_suggested_topics(monkeypatch,profile,depth,later_goal):
    s=_start(monkeypatch,depth);s.profile=profile;s.depth=depth;s.stage='conversation'
    s.context.update({'city':'Madrid','organisation_or_unit':'planning unit',
        'responsibilities':'advisory role','technical_object':'delivery subsystem'})
    _complete_pre_topic_stages(s)
    # Model routing is called after an answer. Keep the current answer in an
    # earlier, already-considered stage so open_priorities remains eligible.
    s.objective=next(q['id'] for stage in s.fn.stages(profile,depth)
        for q in stage['questions'] if q['id'] in s.fn.coverage)
    s._model_led_route({'message':'What issue should we discuss?',
        'interpretation':{'action':'advance','next_goal_id':later_goal,'question_purpose':'Move to later section.'}})
    assert s.objective=='open_priorities'
    assert s._last_decision['topic_sequence_bridge']['goal']=='open_priorities'


def test_model_led_candidate_set_excludes_closed_and_inapplicable_goals(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short'
    s.fn.record('area','m-area','explored')
    s.fn.record('drone_recognition','m-recognition','explored','yes')
    s.fn.asked.extend(['drone_recognition','healthcare_awareness'])
    candidates={n['id'] for n in s.fn.model_led_next_objectives('citizen','short',s.concerns,'healthcare_awareness')}
    assert 'drone_recognition' not in candidates
    assert 'healthcare_awareness' not in candidates
    assert 'drone_explanation' not in candidates
    assert 'conditions' in candidates


def test_model_led_candidate_set_is_bounded_and_preserves_stage_and_priority_choices(monkeypatch):
    fn=FNInterview();stages=[{'id':f'stage-{i}'} for i in range(3)]
    nodes=[{'id':f'g{stage}-{index}'} for stage in range(3) for index in range(8)]
    stage_by_goal={node['id']:f"stage-{node['id'][1]}" for node in nodes}
    monkeypatch.setattr(fn,'nodes',lambda profile,depth:nodes)
    monkeypatch.setattr(fn,'stages',lambda profile,depth:stages)
    monkeypatch.setattr(fn,'stage_for',lambda profile,depth,goal:{'id':stage_by_goal[goal]})
    monkeypatch.setattr(fn,'applicable',lambda node,concerns:True)
    monkeypatch.setattr(fn,'_priority_relevant',lambda node,concerns:node['id'].endswith('7'))
    selected=fn.model_led_next_objectives('citizen','short',[{'selected_priority':True}])
    assert len(selected)==16
    assert {stage_by_goal[node['id']] for node in selected}=={'stage-0','stage-1','stage-2'}
    assert all(f'g{stage}-7' in {node['id'] for node in selected} for stage in range(3))


def test_invalid_next_question_preserves_valid_evaluation_evidence(monkeypatch):
    """Question validation cannot erase the respondent's accepted evidence."""
    from iam_sra.chat_client import ChatClient
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.context.update(city='Coimbra',scope_status='respondent_described')
    s.objective='evaluation_evidence'
    s.fn.record('area','m-area','explored')
    s.fn.record('drone_recognition','m-recognition','explored','yes')
    answer='I would want an independent comparison of noise measurements and delivery times.'
    s._ask_fn(s.fn.current('citizen','short','evaluation_evidence'))
    def controlled_request(self, http_client, stage, system, request, schema, validator, retry_hint=None):
        raw=reply(request,kind='substantive',status='explored',action='advance',coverage=[{
            'goal':'evaluation_evidence','evidence_id':request['current_answer_id'],'quote':answer,
            'status':'explored','answer_kind':'substantive'}])
        raw['message']='Thank you.'  # invalid next-question wording, valid interpretation
        raw['interpretation']['next_goal_id']='evaluation_evidence'
        return validator(raw)
    monkeypatch.setattr(ChatClient,'_request',controlled_request)
    s._fn_turn(answer,ChatClient())
    assert s.fn.coverage['evaluation_evidence']['status']=='explored'
    assert s.objective!='evaluation_evidence'
    assert s._last_decision['next_goal_fallback']['fallback_source']=='eligible_fn_objective'


def test_grounded_multi_concerns_survive_missing_model_classification(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.objective='open_priorities'
    answer='I am concerned about noise near homes and who would be accountable if something went wrong.'
    row={'id':'m-concerns','text':answer}
    interpretation={'topics':[{'topic':'noise concerns','quote':answer,'topic_type':'other'}]}
    s._recover_explicit_topics(row,interpretation)
    # The explicit recovery adds the distinct accountability clause; label
    # variants of noise remain one issue.
    assert len(interpretation['topics'])==2
    s._fn_topics(row,interpretation)
    concerns=[c for c in s.concerns if c['topic_type']=='concern']
    assert {s._topic_identity(c['topic']) for c in concerns}=={'noise','accountability'}
    assert all('m-concerns' in c['evidence_ids'] for c in concerns)
    assert not any(c['selected_priority'] for c in concerns)


def test_multiple_concerns_route_to_natural_priority_choice(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation'
    s.objective='open_priorities'
    _complete_pre_topic_stages(s)
    s.concerns=[{'topic':'noise','topic_type':'concern','evidence_ids':['m1'],'kind':'emerging_topic'},
        {'topic':'accountability','topic_type':'concern','evidence_ids':['m1'],'kind':'emerging_topic'}]
    s.fn.record('area','m0','explored')
    for goal in ('drone_recognition','drone_description','drone_uses','healthcare_awareness','local_awareness'):
        s.fn.record(goal,'m0','unknown','uncertain')
    s.fn.record('open_priorities','m1','explored')
    s.fn.record('open_more','m1','explored')
    s.fn.record('different_impacts','m1','explored')
    bridge=s._required_topic_sequence_goal('advance','evaluation_evidence',None)
    assert bridge and bridge['id']=='priorities'


@pytest.mark.parametrize(('profile','depth','later_goal'),[
    ('citizen','short','opinion'),('organisational','short','planning'),('technical','short','controlled')])
def test_no_concerns_still_receives_fn_topic_menu_after_open_discussion(monkeypatch,profile,depth,later_goal):
    s=_start(monkeypatch,depth);s.profile=profile;s.depth=depth;s.stage='conversation'
    s.context.update({'city':'Madrid','organisation_or_unit':'advisory unit',
        'responsibilities':'advisory remit only','technical_object':'delivery subsystem'})
    _complete_pre_topic_stages(s)
    open_ids={'open_priorities','open_more','different_impacts','requirements_open'}
    for node in s.fn.nodes(profile,depth):
        if node['id'] in open_ids and s.fn.applicable(node,s.concerns):
            s.fn.record(node['id'],'m-none','explored')
    s.fn.facts['topic_scope_closed']=True
    s.objective='open_more'
    s._model_led_route({'message':'Thanks. What else should we discuss?',
        'interpretation':{'action':'advance','next_goal_id':later_goal,'question_purpose':'Continue interview.'}})
    menu_id='priorities' if profile=='technical' else 'suggested_topics'
    menu=s.fn.current(profile,depth,menu_id)
    assert s.objective==menu_id
    assert menu['canonical_question'] in s.messages[-1]['text']
    assert any(line.startswith('• ') for line in s.messages[-1]['text'].splitlines())


def test_benefit_alone_does_not_count_as_a_participant_concern_for_fn_topic_menu(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.stage='conversation';s.objective='open_priorities'
    _complete_pre_topic_stages(s)
    for goal in ('open_priorities','open_more','different_impacts'):
        s.fn.record(goal,'m-benefit','explored')
    s.concerns=[{'topic':'faster deliveries','topic_type':'benefit','evidence_ids':['m-benefit'],
        'kind':'emerging_topic','spontaneously_raised':True}]
    s._model_led_route({'message':'What do you think of the service?',
        'interpretation':{'action':'advance','next_goal_id':'opinion','question_purpose':'Overall opinion.'}})
    assert s.objective=='suggested_topics'


def test_mixed_local_process_request_keeps_answer_and_exposes_no_local_fact(monkeypatch):
    s=_start(monkeypatch);s.profile='citizen';s.depth='short';s.context['city']='Madrid'
    s.stage='conversation';s.objective='accountability'
    row=s._user("I would contact the city council, but I don't know which office handles complaints. Could you explain?",True)
    out={'interpretation':{'information_request':'local_process',
        'information_request_quote':'Could you explain?','action':'advance'},'message':'What should a good response provide?'}
    assert s._respond_to_information_need(row['text'],out,row,'accountability')
    assert 'do not have verified information' in s.messages[-1]['text']
    assert row['id']==s.active_evidence()[0]['id']
    assert s.exposures[-1]['prior_knowledge'] is False
    assert 'Madrid' not in s.exposures[-1]['text']


def test_registered_empowerment_anchor_needs_evidence_of_known_usable_route():
    from iam_sra.chat_score import validate_profile_match
    from iam_sra.chat_policy import rubric
    bank_data=bank();anchors=rubric(bank_data,'citizen','short')['anchors']
    empowerment=next(a for a in anchors if a['label']=='Empowerment')
    payload={'anchors':anchors,'originals':[
        {'id':'m1','text':'I would contact the city council if something went wrong.'},
        {'id':'m2','text':"I don't know which office deals with drone complaints."}]}
    value={'selected_anchor_id':empowerment['id'],'boundary_direction':'higher',
        'citations':[{'evidence_id':'m1'}],
        'explanation':'The participant can use an established route to raise concerns.',
        'boundary':'Continued involvement over time is not established.',
        'material_conflict':False,'evidence_incomplete':False,'consistency_check':'consistent',
        'consistency_evidence_ids':[]}
    with pytest.raises(AssessmentError,match='established route is known or usable'):
        validate_profile_match(value,payload)
    payload['originals']=[{'id':'m1','text':'I know how to use the city complaint form and received a response last year.'}]
    value['citations']=[{'evidence_id':'m1'}]
    assert validate_profile_match(value,payload)['selected_anchor_id']==empowerment['id']
