"""Deterministic contracts/transitions; fake completion is not semantic validity."""
import json
from copy import deepcopy
import pytest
from iam_sra.session import Session,State
from iam_sra.updates import FacetMeaning,FacetTarget,QuestionContract,choice_transition,enrich_fn,blocker_report,contract
from iam_sra.reporting import final_summary
from iam_sra.settings import QUESTIONS,CONCERNS,config
from iam_sra.assessment import AssessmentError
from test_confirmation import Fake,meaning,initially_scored

class FacetFake(Fake):
    def __init__(self,profile=None,positions=None):
        super().__init__(profile);self.positions=positions or {};self.reviewed=[]
    def interpret_facets(self,evidence,proposal,required):
        key=next(k for k,v in evidence.items() if v.source=='citizen_correction') if any(v.source=='citizen_correction' for v in evidence.values()) else next(k for k in evidence if k.endswith('.choice') and '.background.' not in k)
        return [FacetMeaning(concern_id=cid,facet=f,position=self.positions.get(f,'supported'),evidence_ids=[key],condition_ids=[],applicability_explicit=True,rationale='Explicit modified-context testimony.') for cid,f in required]
    def score(self,record,only=None,unavailable=None):
        result=super().score(record,only,unavailable)
        if record.get('facet_slice'):
            facet=record['facet_slice']['facet'];self.reviewed.append(facet)
            for c in result.concerns:
                if c.score is not None:c.score=2 if facet=='perceived_safety' else 8
        return result


def answer_all(s,c,index=0):
    while s.state==State.FOLLOWUPS:
        q=s.current_question;s.respond(q['choices'][index],'',c)


def finish_original(s,c):
    if s.state==State.FOLLOWUPS:s.stop_followups()
    if s.joint_required:s.record_joint('unsure',[],'',c)
    s.continue_final(True,c)

@pytest.mark.parametrize('q',QUESTIONS)
def test_reference_contract_preserves_exact_wording_and_provenance(q):
    enriched=enrich_fn(q,True)
    assert enriched['text']==q['text'] and enriched['choices']==q['choices']
    spec=contract(enriched)
    assert spec.context=='hypothetical' and spec.proposal_id and spec.targets and spec.cannot_establish
    assert spec.policy_version==config('updates')['version']

@pytest.mark.parametrize('qid,index,cid,facet,expected',[
 ('q1',0,'perceived_safety_privacy','personal_privacy','resolved_under_modification'),
 ('q1',0,'technical_safety_security_privacy','data_security','untested'),
 ('q1',0,'perceived_safety_privacy','perceived_safety','untested'),
 ('q1',1,'technical_safety_security_privacy','data_security','remaining_objection'),
 ('q2',0,'noise','acoustic_impact','resolved_under_modification'),
 ('q2',1,'noise','acoustic_impact','partially_resolved'),
 ('q2',2,'noise','acoustic_impact','partially_resolved'),
 ('q2',1,'visual_pollution','aesthetic_clutter','remaining_objection'),
 ('q2',3,'noise','acoustic_impact','unresolved'),
 ('q3',1,'welfare_equity','medical_public_benefit','untested')])
def test_facet_transition_rules(qid,index,cid,facet,expected):
    q=enrich_fn(next(q for q in QUESTIONS if q['id']==qid));code=contract(q).choices[index].code
    assert choice_transition(q,code,cid,facet)==expected


def test_invalid_canonical_facet_is_rejected():
    with pytest.raises(ValueError):FacetTarget(concern_id='noise',facet='data_security')

@pytest.mark.parametrize('cid,facet',[
 ('cost_roi_business','cost_financing'),('welfare_equity','distributive_equity'),('perceived_safety_privacy','perceived_safety'),('energy_emissions','emissions'),('competence_building','training')])
def test_reviewed_non_fn_bank_covers_declared_facets_without_new_assumptions(cid,facet):
    s,c=initially_scored(Fake(meaning(scores=(cid,),facets={cid:[facet]})))
    s.begin_followups();q=next(q for q in s.questions if q['id'].startswith('u_'))
    spec=contract(q)
    assert spec.context=='original' and spec.modification is None and spec.assumptions==[]
    assert (cid,facet) in [(t.concern_id,t.facet) for t in spec.targets]


def test_citizen_requested_change_is_hypothetical_with_exact_evidence_and_joint_required():
    c=Fake(meaning(scores=('cost_roi_business',),facets={'cost_roi_business':['cost_financing']}))
    s=Session();s.begin();s.submit('I would accept only if residents paid no fees.',c)
    s.draft.concerns[0].conditions=['O.p001'];s.draft.concerns[0].conditional_willingness='willing'
    s.finish_discovery();s.continue_initial(True,c)
    q=s.current_question
    assert q['contract']['context']=='hypothetical' and 'residents paid no fees' in q['contract']['modification']
    s.respond(q['choices'][0],'',c)
    assert s.joint_required and 'residents paid no fees' in s.combined_proposal
    with pytest.raises(ValueError):s.confirm_updated(True)


def test_original_confirmation_without_new_evidence_carries_and_q3_changes_no_cap():
    profile=meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']})
    s,c=initially_scored(Fake(profile));original=s.initial;s.begin_followups(True)
    while s.state==State.FOLLOWUPS:
        q=s.current_question;s.respond(q['choices'][1] if q['id']=='q3' else q['choices'][0],'',c)
    s.record_joint('unsure',[],'',c);before=sum(x[0]=='score' for x in c.calls);s.continue_final(True,c)
    assert s.initial==original and s.final['aggregate']==original['aggregate']
    assert sum(x[0]=='score' for x in c.calls)==before
    assert any(t['question_id']=='q3' and t['transition']=='untested' for t in s.transitions)


def test_mixed_facets_minimum_preserves_remaining_safety_and_blocker():
    profile=meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['personal_privacy','perceived_safety']})
    c=FacetFake(profile,{'personal_privacy':'supported','perceived_safety':'opposed'});s,c=initially_scored(c)
    s.blockers['perceived_safety_privacy']={'status':'yes','evidence_ids':['O.p001'],'confirmed':True}
    s.begin_followups();answer_all(s,c)
    s.record_joint('reject',['perceived_safety_privacy'],'The camera view is acceptable but physical safety still makes this route unacceptable.',c)
    s.continue_final(True,c)
    score=next(c['score'] for c in s.conditional['assessment']['concerns'] if c['concern_id']=='perceived_safety_privacy')
    assert score==2 and sorted(c.reviewed)==['perceived_safety','personal_privacy']
    assert s.conditional['aggregate']['trace']['denominator']==1
    assert blocker_report(s)['modified']['perceived_safety_privacy']['status']=='remaining'
    assert s.initial['assessment']['concerns'][2]['score']==2


def test_resolved_privacy_does_not_erase_untested_safety():
    c=FacetFake(meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['personal_privacy','perceived_safety']}),{'personal_privacy':'supported','perceived_safety':'unassessed'})
    s,c=initially_scored(c);s.blockers['perceived_safety_privacy']={'status':'yes','evidence_ids':['O.p001'],'confirmed':True};s.begin_followups();answer_all(s,c)
    s.record_joint('accept',[],'The camera viewing issue is resolved; I do not know about physical safety.',c);s.continue_final(True,c)
    assert not c.reviewed
    assert next(c['score'] for c in s.conditional['assessment']['concerns'] if c['concern_id']=='perceived_safety_privacy') is None
    assert blocker_report(s)['modified']['perceived_safety_privacy']['status']=='unresolved'


def test_applicability_must_be_explicit_for_unchanged_facets():
    c=FacetFake(meaning(scores=('noise','welfare_equity'),facets={'welfare_equity':['medical_public_benefit']}))
    s,c=initially_scored(c);s.begin_followups();answer_all(s,c)
    s.record_joint('accept',[],'The quieter sound is fine.',c)
    for f in s.facet_meanings:
        if f.concern_id=='welfare_equity':f.applicability_explicit=False
    s.continue_final(True,c)
    assert next(c['score'] for c in s.conditional['assessment']['concerns'] if c['concern_id']=='welfare_equity') is None


def test_skip_stop_leave_unknowns_and_do_not_apply_unpresented_changes():
    s,c=initially_scored(Fake(meaning(scores=('noise','welfare_equity'))));s.begin_followups(True)
    s.skip_followup();s.stop_followups();s.record_joint('unsure',[],'',c);s.continue_final(True,c)
    assert 'curfew' not in s.combined_proposal
    data=s.export();assert len(data['dialogue_and_confirmations']['presented_followups'])==1
    assert data['final_summary']['modified_assessment_attempted']
    assert s.initial['aggregate']==s.final['aggregate']


def test_transactional_confirmation_and_scoring_retry_do_not_duplicate():
    s,c=initially_scored();s.begin_followups();answer_all(s,c);s.record_joint('accept',[],'Modified noise is acceptable.',c)
    count=len(s.confirmations);saved=c.score
    c.score=lambda *args,**kwargs:(_ for _ in ()).throw(AssessmentError('Unavailable',code='transport'))
    with pytest.raises(AssessmentError):s.continue_final(True,c)
    assert s.state==State.UPDATE_CONFIRMED and s.final is None and s.initial is not None
    assert len(s.confirmations)==count+2 and s._pending_final_original is not None
    c.score=saved;s.continue_final(True,c)
    assert len(s.confirmations)==count+2 and s.state==State.FINAL


def test_readable_export_sections_and_headline_context_are_explicit():
    c=FacetFake(meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']}))
    s,c=initially_scored(c);s.begin_followups();answer_all(s,c)
    s.record_joint('accept',[],'The modified noise and private viewing are acceptable; I still support the medical public benefit in this exact modified proposal.',c)
    s.continue_final(True,c);data=s.export()
    assert data['schema_version']=='5.1.0' and len(data['domain_assessments'])==15
    assert data['final_summary']['selected_profile']=='conditional_modified'
    assert data['final_summary']['headline_score']==s.conditional['aggregate']['rounded']
    assert data['aggregation']['conditional_modified']['trace']['denominator']==3
    assert json.loads(s.jsonl())==data and len(s.jsonl().splitlines())==1
    assert 'raw_model_trace' not in json.dumps(data['final_summary'])
    assert data['audit']['legacy_record']['schema_version']=='4.1.0'
    assert [int(t['id'][1:]) for t in data['updates']]==list(range(1,len(data['updates'])+1))


def test_headline_fallback_and_unavailable_qualitative_completion():
    s,c=initially_scored(Fake(meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']})))
    s.begin_followups();answer_all(s,c);s.record_joint('unsure',[],'',c);s.continue_final(True,c)
    summary=final_summary(s);assert summary['selected_profile']=='final_original' and summary['proposal_context']=='original'
    assert summary['modified_assessment_attempted'] and not summary['modified_aggregate_available']
    u,d=initially_scored(Fake(meaning(scores=(),position='uncertain')));u.begin_followups();u.continue_final(True,d)
    summary=final_summary(u);assert summary['headline_score'] is None and summary['explanation']


def test_unknown_original_followup_invalidates_only_target_numeric_value():
    s,c=initially_scored(Fake(meaning(scores=('cost_roi_business',),facets={'cost_roi_business':['cost_financing']})))
    initial=s.initial;s.begin_followups();q=s.current_question;s.respond(q['choices'][-1],'',c,'original');s.continue_final(True,c)
    assert s.initial==initial
    assert s.final['assessment']==initial['assessment']
    assert s.final['aggregate']['trace']['denominator']==1


def test_unrelated_original_clarification_does_not_trigger_score_change():
    s,c=initially_scored(Fake(meaning(scores=('cost_roi_business',),facets={'cost_roi_business':['cost_financing']})))
    initial=s.initial;s.begin_followups();q=s.current_question
    c.next=meaning(q['id']+'.clarification',scores=('noise',))
    s.respond(q['choices'][1],'Noise would bother me.',c,'original')
    s.continue_final(True,c)
    assert s.final['assessment']==initial['assessment']
    assert not any(t['transition']=='corrected_original' and t['proposal_id']=='original' and t['new_score'] is not None for t in s.transitions)


def test_modified_correction_failure_is_atomic_and_keeps_confirmation():
    c=FacetFake();s,c=initially_scored(c);s.begin_followups();answer_all(s,c)
    s.record_joint('accept',[],'The modified noise is acceptable.',c);s.confirm_updated(True)
    draft=s.conditional_draft.model_dump();confirmed=deepcopy(s.conditional_confirmed);evidence=deepcopy(s.evidence)
    c.interpret_facets=lambda *args,**kwargs:(_ for _ in ()).throw(AssessmentError('Transport',code='transport'))
    with pytest.raises(AssessmentError):s.correct_modified('noise','I still object to modified noise.','Correct my view.',c)
    assert s.conditional_draft.model_dump()==draft and s.conditional_confirmed==confirmed and s.evidence==evidence


def test_original_partial_correction_preserves_other_facets_as_unavailable():
    profile=meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['personal_privacy','perceived_safety']})
    s,c=initially_scored(Fake(profile));s.begin_followups();s.stop_followups()
    c.next=meaning('C1.testimony',scores=('perceived_safety_privacy',),position='supported',facets={'perceived_safety_privacy':['personal_privacy']})
    s.correct('perceived_safety_privacy','I accept viewing cameras.','Correct viewing only.',c)
    assert set(s.draft.concerns[0].facets)=={'personal_privacy','perceived_safety'}
    assert s.original_facets['perceived_safety_privacy:perceived_safety'].position=='opposed'
    assert s.original_facets['perceived_safety_privacy:personal_privacy'].position=='supported'
    s.continue_final(True,c)
    assert next(x['score'] for x in s.final['assessment']['concerns'] if x['concern_id']=='perceived_safety_privacy')==2


def test_new_original_conditions_can_add_a_nonrepeating_bounded_hypothetical():
    profile=meaning(scores=('cost_roi_business',),facets={'cost_roi_business':['cost_financing']})
    s,c=initially_scored(Fake(profile));s.begin_followups();q=s.current_question
    patch=meaning(q['id']+'.clarification',scores=('cost_roi_business',),facets={'cost_roi_business':['cost_financing']})
    patch.concerns[0].conditions=[q['id']+'.clarification'];patch.concerns[0].conditional_willingness='willing'
    c.next=patch;s.respond(q['choices'][1],'I would accept only without fees.',c,'original')
    # A contradiction is retained; queued questions still use citizen text, not invented costs.
    assert len({q['id'] for q in s.questions})==len(s.questions)
    assert len(s.questions)<=config('updates')['maximum_questions']


def test_skipped_followup_has_unresolved_typed_transition():
    s,c=initially_scored(Fake(meaning(scores=('cost_roi_business',),facets={'cost_roi_business':['cost_financing']})))
    s.begin_followups();qid=s.current_question['id'];s.skip_followup();s.continue_final(True,c)
    record=next(t for t in s.transitions if t['question_id']==qid)
    assert record['transition']=='unresolved' and record['new_score'] is None
    assert s.evidence[record['evidence_ids'][0]].source=='citizen_control'


def test_modified_medical_dimension_edit_invalidates_previous_facet_applicability():
    c=FacetFake(meaning(scores=('welfare_equity','perceived_safety_privacy'),facets={'welfare_equity':['medical_public_benefit'],'perceived_safety_privacy':['personal_privacy']}))
    s,c=initially_scored(c);s.begin_followups();answer_all(s,c)
    # Explicit modified testimony is required even for otherwise unchanged benefit.
    s.record_joint('accept',[],'I support the medical benefit of the changed proposal.',c)
    s.correct_modified('medical_public_benefit_support','I am now unsure about its medical benefits.','Clarify my position.',c)
    assert all(not f.applicability_explicit for f in s.facet_meanings if f.facet=='medical_public_benefit')


def test_q1_does_not_suppress_separate_security_clarification():
    s,c=initially_scored(Fake(meaning(scores=('technical_safety_security_privacy',),facets={'technical_safety_security_privacy':['data_security']})))
    s.begin_followups()
    assert any(q['id'].startswith('u_') and any(t['facet']=='data_security' for t in q['contract']['targets']) for q in s.questions)
