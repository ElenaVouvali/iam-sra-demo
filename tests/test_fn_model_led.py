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
    assert s.messages[-1]['text']==question
    assert s.messages[-1]['source']['wording']=='Qwen proposed; FN harness validated'
    accepted=[e for e in s.routing_events if e['event']=='model_led_question_accepted']
    assert accepted[-1]['objective_id']==target


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
    assert s.messages[-1]['act']=='authored_fallback'
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
        if node:
            s.fn.record(node['id'],f'm{index+1}','explored')
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
