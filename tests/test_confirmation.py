from copy import deepcopy
import json
import pytest
from iam_sra.session import Session, State
from iam_sra.schemas import MappingAssessment, MappingConcern, Assessment, Concern
from iam_sra.interpretation import EvidenceItem, freeze, verify
from iam_sra.settings import CONCERNS, QUESTIONS
from iam_sra.assessment import AssessmentError
from iam_sra.validation import select_questions


def meaning(eid='O.p001',scores=('noise',),position='opposed',facets=None):
    d={'interpretation':'unassessed','excerpts':[],'rationale':'Not stated.'}
    return MappingAssessment(scenario_id='urban_medical_corridor',concerns=[MappingConcern(concern_id=cid,status='mapped',position=position,
        facets=facets.get(cid) if facets and cid in facets else [CONCERNS[cid]['facets'][0]],excerpts=[eid],rationale='Explicit evidence.') for cid in scores],
        current_route_stance={'interpretation':position,'excerpts':[eid],'rationale':'Explicit position.'},
        awareness_understanding=d,medical_public_benefit_support=d,acceptance_conditions=[])

class Fake:
    def __init__(self,initial=None):self.calls=[];self.initial=initial or meaning();self.next=None
    def interpret(self,evidence,context='original',proposal=None,target=None):
        self.calls.append(('interpret',context,deepcopy(evidence)))
        if self.next:
            result=self.next;self.next=None;return result
        eid=next(iter(evidence))
        result=self.initial.model_copy(deep=True)
        for c in result.concerns:c.excerpts=[eid];c.conditions=[]
        result.current_route_stance.excerpts=[eid]
        if context=='modified':
            joint=next((item for item in evidence.values() if item.id.endswith('.choice') and item.question_id is None),None)
            if joint:
                result.current_route_stance.interpretation='supported' if 'I accept' in joint.text else 'opposed' if 'I reject' in joint.text else 'uncertain'
                result.current_route_stance.excerpts=[joint.id]
        return result
    def score(self,record,only=None,unavailable=None):
        self.calls.append(('score',record['context'],deepcopy(record),only))
        profile,evidence=verify(record)
        by={c.concern_id:c for c in profile.concerns}
        concerns=[]
        for cid in CONCERNS:
            c=by.get(cid)
            eligible=c and c.status=='mapped' and c.position!='uncertain' and cid not in (unavailable or set()) and (only is None or cid in only)
            score=(8 if c.position=='supported' else 2 if cid=='perceived_safety_privacy' else 3) if eligible else None
            concerns.append(Concern(concern_id=cid,status='assessed' if score else 'unassessed',score=score,position=c.position if c else 'unassessed',
                facets=c.facets if c else [],excerpts=[evidence[r].text for r in c.excerpts] if c else [],rationale='Test-only numeric review.',conditions=[]))
        dims={name:{**getattr(profile,name).model_dump(),'excerpts':[evidence[r].text for r in getattr(profile,name).excerpts]} for name in ['current_route_stance','awareness_understanding','medical_public_benefit_support']}
        return Assessment(scenario_id=profile.scenario_id,concerns=concerns,acceptance_conditions=[],**dims)

def started(client=None):
    c=client or Fake();s=Session();s.begin();s.submit('Noise bothers me.',c);return s,c

def initially_scored(client=None):
    s,c=started(client);s.finish_discovery();s.confirm(True);s.score_initial(c);return s,c

def test_submit_has_no_numbers_or_hidden_scoring():
    s,c=started()
    assert [call[0] for call in c.calls]==['interpret']
    assert s.initial is None and s.state==State.INTERPRETATION
    assert 'score' not in s.draft.model_dump_json()
    with pytest.raises(ValueError):s.score_initial(c)
    with pytest.raises(ValueError):s.confirm(False)


def test_edit_invalidates_confirmation_and_reaches_numeric_review():
    s,c=started();s.finish_discovery();s.confirm(True)
    c.next=meaning('C1.testimony',position='supported')
    s.correct('noise','I accept the hum.','The first interpretation was incorrect.',c)
    assert s.state==State.INTERPRETATION and s.confirmed is None and s.initial is None
    with pytest.raises(ValueError):s.score_initial(c)
    s.finish_discovery();s.confirm(True);s.score_initial(c)
    assert c.calls[-1][2]['meaning']['concerns'][0]['position']=='supported'
    assert 'C1.testimony' in c.calls[-1][2]['evidence']
    assert next(x for x in s.initial['assessment']['concerns'] if x['concern_id']=='noise')['score']==8
    assert len(s.corrections)==1 and len(s.confirmations)==2


def test_frozen_record_mutation_is_detected():
    s,c=started();s.finish_discovery();s.confirm(True);s.confirmed['meaning']['concerns'][0]['position']='supported'
    with pytest.raises(AssessmentError,match='changed'):s.score_initial(c)
    assert not any(call[0]=='score' for call in c.calls)


def test_no_new_original_evidence_carries_all_scores_and_snapshot_is_isolated():
    s,c=initially_scored();initial=s.initial
    copied=s.initial;copied['assessment']['concerns'][0]['score']=9
    assert s.initial==initial
    s.begin_followups()
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][0],'',c)
    s.record_joint('unsure',[],'',c);s.confirm_updated(True)
    before=sum(call[0]=='score' for call in c.calls);s.score_final(c)
    assert sum(call[0]=='score' for call in c.calls)==before
    assert s.initial==initial and s.final['assessment']==initial['assessment'] and s.conditional is None
    assert s.final['aggregate']==initial['aggregate']


def test_followup_clarification_has_stable_original_evidence_and_changes_only_affected():
    s,c=initially_scored(Fake(meaning(scores=('noise','welfare_equity'))));s.begin_followups(True)
    c.next=meaning('q1.choice',scores=('noise',))
    s.respond(s.questions[0]['choices'][0],'',c)
    # q2 choice keeps noise opposition; original text provides extra evidence.
    c.initial=meaning(scores=('noise',))
    s.respond(s.questions[1]['choices'][2],'The evening hum is unacceptable unless it is removed.',c,'original')
    assert s.evidence['q2.clarification'].context=='original'
    assert s.draft.concerns[0].excerpts==['q2.clarification']
    s.respond(s.questions[2]['choices'][2],'',c)
    if s.state==State.FOLLOWUPS:s.stop_followups()
    s.record_joint('unsure',[],'',c);s.confirm_updated(True);s.score_final(c)
    final_call=next(call for call in reversed(c.calls) if call[0]=='score')
    assert final_call[3]=={'noise'}
    assert s.final['assessment']['concerns'][-1]['score']==s.initial['assessment']['concerns'][-1]['score']
    assert next(x for x in s.initial['assessment']['concerns'] if x['concern_id']=='noise')['excerpts']==['Noise bothers me.']


def test_conflicting_original_text_requires_targeted_clarification():
    s,c=initially_scored();s.begin_followups()
    # First choice mapping supported, clarification opposed: use original initial opposed vs new supported.
    c.initial=meaning(position='supported')
    s.respond(s.questions[0]['choices'][0],'I accept the original noise.',c,'original')
    assert 'original:noise' in s.conflicts
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][-1],'',c)
    with pytest.raises(ValueError,match='conflicting'):s.confirm_updated(True)
    c.next=meaning('C1.testimony',position='supported')
    s.resolve_conflict('original:noise','I confirm that the original hum is acceptable.',c)
    s.resolve_conflict('original:current_route_stance','I support the original route.',c)
    assert not s.conflicts
    s.record_joint('unsure',[],'',c);s.confirm_updated(True);s.score_final(c)
    assert next(x for x in s.initial['assessment']['concerns'] if x['concern_id']=='noise')['score']==3
    assert next(x for x in s.final['assessment']['concerns'] if x['concern_id']=='noise')['score']==8


def test_choice_and_hypothetical_text_conflict_not_silently_overwritten():
    s,c=initially_scored();s.begin_followups()
    original_interpret=c.interpret
    count=0
    def interpret(*args,**kwargs):
        nonlocal count
        count+=1
        return meaning('q2.choice' if count==1 else 'q2.clarification',position='supported' if count==1 else 'opposed')
    c.interpret=interpret
    s.respond(s.questions[0]['choices'][0],'Actually I still reject that sound.',c)
    assert 'q2:noise' in s.conflicts
    assert s.draft.concerns[0].position=='opposed'


def test_joint_is_required_and_never_inferred_from_separate_yes_answers():
    s,c=initially_scored();s.begin_followups()
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][0],'',c)
    with pytest.raises(ValueError,match='combined'):s.confirm_updated(True)
    assert s.joint is None and s.conditional is None
    s.record_joint('accept',[],'The modified noise is acceptable.',c)
    assert s.joint['choice']=='accept'
    s.confirm_updated(True);s.score_final(c)
    assert s.conditional['context']=='modified'
    assert next(x for x in s.initial['assessment']['concerns'] if x['concern_id']=='noise')['score']==3
    assert len(s.legacy_export()['comparison'])==15


def test_context_isolation_and_untested_privacy_facets():
    profile=meaning(scores=('perceived_safety_privacy','noise','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy','perceived_safety']})
    s,c=initially_scored(Fake(profile));s.begin_followups(True)
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][0],'',c)
    c.initial=meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['personal_privacy']})
    s.record_joint('accept',[],'',c);s.confirm_updated(True);s.score_final(c)
    privacy=next(x for x in s.conditional['assessment']['concerns'] if x['concern_id']=='perceived_safety_privacy')
    assert privacy['score'] is None
    assert 'perceived_safety_privacy' in s.conditional['scoring_exclusions']
    assert s.final['aggregate']==s.initial['aggregate']


def test_unknown_and_insufficient_coverage_export_jsonl_one_complete_line():
    s,c=initially_scored(Fake(meaning(position='uncertain')));s.begin_followups()
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][-1],'',c)
    if s.joint_required:s.record_joint('unsure',[],'',c)
    s.confirm_updated(True);s.score_final(c)
    assert s.initial['aggregate']['rounded'] is None
    assert s.final['aggregate']['rounded'] is None
    assert len(s.jsonl().splitlines())==1
    assert json.loads(s.jsonl())==json.loads(s.json())
    assert len(s.legacy_export()['comparison'])==15


def test_wrong_context_evidence_and_question_citations_rejected():
    m=meaning('Q.choice');e={'Q.choice':EvidenceItem(id='Q.choice',text='yes',source='citizen_choice',context='modified')}
    with pytest.raises(AssessmentError,match='wrong-context'):freeze(m,e,1,'original','original')
    e={'Q.choice':EvidenceItem(id='Q.choice',text='What do you think?',source='question',context='original')}
    with pytest.raises(AssessmentError,match='non-citizen'):freeze(m,e,1,'original','original')


def test_q1_needs_privacy_facet_not_personal_safety_only():
    m=meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['perceived_safety']})
    assert 'q1' not in [q['id'] for q in select_questions(m)]


def test_session_isolation():
    a,c=started();b=Session();a.finish_discovery();a.confirm(True)
    assert b.evidence=={} and b.confirmations==[] and b.state==State.SCENARIO


def test_caps_recomputed_per_profile_without_question_bonuses():
    profile=meaning(scores=('perceived_safety_privacy','noise','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']})
    c=Fake(profile)
    real_score=c.score
    def score(record,only=None,unavailable=None):
        result=real_score(record,only,unavailable)
        for item in result.concerns:
            if item.concern_id=='welfare_equity' and item.status=='assessed':item.score=8
        return result
    c.score=score
    s,c=initially_scored(c);initial=s.initial
    assert initial['aggregate']['cap']==4 and initial['aggregate']['rounded']==4
    s.begin_followups(True)
    while s.state==State.FOLLOWUPS:
        q=s.questions[len(s.responses)];s.respond(q['choices'][0] if q['contract']['context']=='original' else q['choices'][-1],'',c)
    c.next=meaning('C1.testimony',scores=('perceived_safety_privacy',),position='supported',facets={'perceived_safety_privacy':['personal_privacy']})
    s.correct('perceived_safety_privacy','I meant that I am comfortable with the original viewing cameras.','Correction of original interpretation',c)
    s.record_joint('unsure',[],'',c);s.confirm_updated(True);s.score_final(c)
    assert s.initial==initial and s.final['aggregate']['cap'] is None
    assert s.final['aggregate']['mean']==pytest.approx((8+3+8)/3)
    assert s.final['aggregate']['rounded']==6


def test_scoring_insufficiency_returns_to_clarification_and_saves_no_result():
    s,c=started();s.finish_discovery();s.confirm(True)
    def reject(*args,**kwargs):raise AssessmentError('Clarify noise: insufficient evidence',code='clarification')
    c.score=reject
    with pytest.raises(AssessmentError):s.score_initial(c)
    assert s.state==State.CONFIRMED and s.initial is None and s.confirmed is not None


def test_modified_edit_invalidates_final_confirmation_not_initial_snapshot():
    s,c=initially_scored();initial=s.initial;s.begin_followups()
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][-1],'',c)
    s.record_joint('accept',[],'The modified hum is tolerable.',c);s.confirm_updated(True)
    c.next=meaning('M1.testimony',position='uncertain')
    s.correct_modified('noise','I am unsure about sound in the modified proposal.','Clarification',c)
    assert s.state==State.UPDATED and s.updated_confirmed is None and s.conditional_confirmed is None
    assert s.initial==initial
    with pytest.raises(ValueError):s.score_final(c)


def test_conditional_failure_preserves_original_and_no_partial_final_snapshot():
    s,c=initially_scored();initial=s.initial;s.begin_followups()
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][-1],'',c)
    c.next=meaning('J1.clarification',position='supported')
    s.record_joint('accept',[],'The modified hum is tolerable.',c);s.confirm_updated(True)
    def reject(*args,**kwargs):raise AssessmentError('Clarify conditional noise',code='clarification')
    c.score=reject
    with pytest.raises(AssessmentError):s.score_final(c)
    assert s.initial==initial and s.final is None and s.conditional is None
    assert s.state==State.UPDATE_CONFIRMED


def test_joint_choice_text_conflict_requires_explicit_resolution():
    s,c=initially_scored();s.begin_followups()
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][-1],'',c)
    c.next=meaning('J1.clarification',position='opposed')
    s.record_joint('accept',[],'I actually reject the combined route.',c)
    assert 'joint:current_route_stance' in s.conflicts
    with pytest.raises(ValueError,match='conflicting'):s.confirm_updated(True)
    c.next=meaning('M1.testimony',position='opposed')
    s.resolve_conflict('joint:current_route_stance','To clarify, I reject this exact combined route.',c)
    assert not s.conflicts and s.conditional_draft.current_route_stance.interpretation=='opposed'
    assert s.joint['choice']=='accept'  # historical choice is never overwritten


def test_joint_revisions_preserve_unique_ids_testimony_and_history():
    s,c=initially_scored();initial=s.initial;s.begin_followups()
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][-1],'',c)
    s.record_joint('accept',[],'The modified hum is acceptable.',c)
    s.confirm_updated(True)
    s.record_joint('reject',['noise'],'I still reject this modified sound.',c)
    assert s.updated_confirmed is None and s.conditional_confirmed is None
    assert s.evidence['J1.choice'].text=='I accept this exact combined proposal.'
    assert s.evidence['J2.choice'].text=='I reject this exact combined proposal.'
    assert len(s.joint_history)==2 and s.joint_history[0]['choice']=='accept'
    assert s.initial==initial


def test_hypothetical_route_conflict_and_resolution_text_reach_joint_interpretation():
    s,c=initially_scored();s.begin_followups()
    replies=[meaning('q2.choice',position='supported'),meaning('q2.clarification',position='opposed')]
    saved=c.interpret
    c.interpret=lambda *args,**kwargs:replies.pop(0)
    s.respond(s.questions[0]['choices'][0],'I still reject this hypothetical route.',c)
    c.interpret=saved
    while s.state==State.FOLLOWUPS:s.respond(s.questions[len(s.responses)]['choices'][-1],'',c)
    assert 'q2:current_route_stance' in s.conflicts
    c.next=meaning('R1.testimony',position='supported')
    s.resolve_conflict('q2:noise','I mean the modified noise is acceptable.',c)
    c.next=meaning('R2.testimony',position='supported')
    s.resolve_conflict('q2:current_route_stance','I also accept this hypothetical route.',c)
    assert not s.conflicts
    s.record_joint('accept',[],'The combined proposal is acceptable.',c)
    evidence_sent=c.calls[-1][2]
    resolution_items=[v for v in evidence_sent.values() if v.source=='citizen_resolved_prior_gate']
    assert {v.text for v in resolution_items}=={'I mean the modified noise is acceptable.','I also accept this hypothetical route.'}
    assert s.responses[0]['resolutions'][1]['evidence_id']=='R2.testimony'
