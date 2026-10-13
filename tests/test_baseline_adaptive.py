"""Synthetic confirmed evidence tests, not evidence of live extraction accuracy."""
from copy import deepcopy
import json
import pytest
from iam_sra.baseline_session import BaselineSession
from iam_sra.baseline_routing import validate_registry, requirement_state
from iam_sra.baseline import selection_plan
from test_baseline import start, familiarity, answer, claim, Extractor, complete


def new(**kw):return start(current=True,**kw)
def until(s,target):
    while s.state=='interview' and s.current_question['id']!=target:s.answer('',Extractor(),'skip')
    assert s.current_question and s.current_question['id']==target

def knowledge():return [claim('concept','concept_explanation',topic_ids=[],interpretation='You describe an aircraft without a pilot.'),claim('delivery','use_knowledge',topic_ids=[],interpretation='You know drones may carry parcels.')]

def full_claims():
    return knowledge()+[claim(),claim('information','information_need',interpretation='You want measurements.'),claim('opportunity','barrier',topic_ids=[],interpretation='You do not know where to comment.')]


def test_registry_rejects_unknown_rules_and_unmapped_roles():
    s=new();validate_registry(s.instrument)
    for path in ['rule','role','prerequisite','budget','wording']:
        c=deepcopy(s.instrument)
        if path=='rule':c['core_questions'][0]['probe_condition']='__import__("os")'
        if path=='role':c['routing']['role_mapping'].pop('authority')
        if path=='prerequisite':c['probes'][0]['prerequisites']=['eval(anything)']
        if path=='budget':c['routing']['maximum_questions']=99
        if path=='wording':c['core_questions'][4]['variants'].pop('organisation_research')
        with pytest.raises(ValueError):validate_registry(c)


@pytest.mark.parametrize('role',['authority','planning','logistics','citizen','researcher','regulator','aviation','technology','other','withheld'])
def test_explicit_role_wording_only_for_organisational_perspective(role):
    personal=new(stakeholder=role);org=new(perspective='organisation',stakeholder=role)
    for s in [personal,org]:familiarity(s);until(s,'experience')
    assert personal.current_question['variant_id']=='personal'
    mapped=org.instrument['routing']['role_mapping'][role]
    assert org.current_question['variant_id']=='organisation_'+mapped
    assert all(v is None for k,v in org.instrument['numerical_policy'].items() if k!='reason')


def test_novice_unknown_is_addressed_not_sufficient_and_never_probed_again():
    s=new();familiarity(s,'no')
    answer(s,'I do not know.',[claim('concept','unknown',topic_ids=[])])
    assert s.current_question['id']=='delivery'
    p=s.current_profile
    assert p['requirements']['concept']['status']=='unknown'
    assert p['interview_dispositions']['concept']['disposition']=='answered'
    assert not p['requirements']['understanding']['status']=='satisfied'
    while s.state=='interview':s.answer('',Extractor(),'unsure')
    assert not any(e['question']['is_probe'] for e in s.events)
    assert s.stop_reason=='completed'


@pytest.mark.parametrize('stance',['I support this.','I oppose this.'])
@pytest.mark.parametrize('role',['citizen','researcher','technology'])
def test_stance_and_profession_do_not_change_sufficiency_or_personal_route(stance,role):
    s=new(stakeholder=role);familiarity(s)
    answer(s,stance+' Aircraft without a pilot carry parcels. Repeated sound could interrupt sleep.',full_claims())
    assert s.current_question['id']=='experience'
    assert s.current_profile['requirements']['understanding']['status']=='satisfied'
    assert s.current_question['variant_id']=='personal'
    assert s.instrument['numerical_policy']['numerical_crl'] is None


@pytest.mark.parametrize('text',['An aircraft without a pilot.','An uncrewed aircraft.'])
def test_concise_equivalent_concept_claims_meet_same_requirement(text):
    s=new();familiarity(s)
    answer(s,text,[claim('concept','concept_explanation',topic_ids=[])])
    assert s.current_profile['requirements']['concept']['status']=='satisfied'
    assert s.current_question['id']=='delivery'


def test_assertion_does_not_cover_effect_reasoning_and_probe_is_interleaved():
    s=new();familiarity(s)
    answer(s,'Drones are uncrewed and carry parcels. They could make a difference.',knowledge()+[claim(kind='claim_without_detail')])
    assert s.current_question['id']=='reasoning'  # before effects/experience/needs
    assert s.current_profile['requirements']['understanding']['status']=='missing'
    q=s.current_question;assert q['triggering_evidence_ids'] and q['target_requirement']=='effect_reasoning'
    answer(s,'Repeated sound could wake people because flights occur during rest.',[claim()])
    assert s.current_question['id']=='experience'
    assert 'understanding' in {r['question_id'] for r in s.skipped_by_design}


def test_unknown_reasoning_probe_does_not_repeat_core_effects():
    s=new();familiarity(s)
    answer(s,'Aircraft carry goods. There may be effects.',knowledge()+[claim(kind='claim_without_detail')])
    assert s.current_question['id']=='reasoning';s.answer('',Extractor(),'unsure')
    assert s.current_question['id']=='experience'


def test_material_subject_ambiguity_has_priority_without_claiming_contradiction():
    s=new();familiarity(s)
    answer(s,'A drone is uncrewed. We evaluated delivery drones.',knowledge()+[claim('exposure','learning_exposure',subject='unknown',temporality='actual',domain='IAM',ambiguities=['subject'],topic_ids=[])])
    assert s.current_question['id']=='scope'
    assert s.current_question['variant_id']=='subject'
    assert s.current_profile['coverage']['exposure']['status']=='scope_unclear'
    assert 'proven_contradiction' not in json.dumps(s.current_profile)
    s.answer('',Extractor(),'unsure')
    assert s.current_question['id']=='understanding'
    assert len([e for e in s.events if e['question']['is_probe']])==1


@pytest.mark.parametrize('actual',[True,False])
def test_authority_actual_activity_vs_plan(actual):
    s=new(perspective='organisation',stakeholder='authority');familiarity(s);until(s,'experience')
    rows=[claim('participation','contribution' if actual else 'intention',subject='organisation',temporality='actual' if actual else 'intention',domain='IAM',topic_ids=[])]
    answer(s,'Our team submitted a delivery consultation response.' if actual else 'Our team plans to respond to a consultation.',rows)
    if actual:
        assert s.current_question['id']=='influence'
        answer(s,'We do not know whether anything changed.',[claim('influence','unknown',subject='organisation',topic_ids=[])])
    else:assert s.current_question['id']=='needs'
    complete(s)
    assert not any(c['kind']=='influence' for c in s.current_profile['claims'])
    assert s.current_profile['requirements']['experience']['status']==('satisfied' if actual else 'missing')


def test_seminar_contribution_probe_immediate_then_shared_objectives():
    s=new();familiarity(s);until(s,'experience')
    answer(s,'I attended a drone seminar.',[claim('exposure','learning_exposure',temporality='actual',domain='IAM',topic_ids=[])])
    assert s.current_question['id']=='contribution'
    answer(s,'I only listened.',[claim('participation','absence',domain='IAM',topic_ids=[])])
    assert s.current_question['id']=='needs'
    complete(s)
    assert 'influence' not in [e['question']['id'] for e in s.events]


def test_unknown_outcome_and_sequence_only_are_not_demonstrated_influence():
    for kind,relation in [('unknown','unknown'),('influence','sequence_only'),('influence','reported_link')]:
        s=new();familiarity(s);until(s,'experience')
        answer(s,'I submitted a proposal.',[claim('participation','contribution',temporality='actual',domain='IAM',topic_ids=[])])
        assert s.current_question['id']=='influence'
        answer(s,'Something changed afterwards.' if kind=='influence' else 'I do not know.',[
            claim('influence',kind,temporality='actual' if kind=='influence' else 'not_applicable',outcome_relation=relation,topic_ids=[])])
        item=next(q for q in s.instrument['probes'] if q['id']=='influence')
        state,_=requirement_state(item,s.current_profile['claims'])
        assert state==('satisfied' if relation=='reported_link' else 'unknown' if kind=='unknown' else 'missing')
        assert all(c['external_verification'] is False for c in s.current_profile['claims'])


def test_personal_route_does_not_use_organisation_or_third_party_activity_as_own():
    for subject in ['organisation','other']:
        s=new(stakeholder='researcher');familiarity(s)
        answer(s,'The research team evaluated deliveries.',[claim('exposure','learning_exposure',subject=subject,temporality='actual',domain='IAM',topic_ids=[])])
        assert s.current_profile['requirements']['experience']['status']=='missing'
        until(s,'experience');assert s.current_question['variant_id']=='personal'


def test_budget_reserves_every_remaining_core_and_never_repeats_probes():
    s=new();familiarity(s);until(s,'understanding')
    answer(s,'There may be effects.',[claim(kind='claim_without_detail')])
    # One spare slot permits immediate clarification, but not a second that
    # would displace a remaining shared objective.
    assert s.current_question['id']=='reasoning';s.answer('',Extractor(),'unsure')
    until(s,'experience')
    answer(s,'I attended an activity.',[claim('exposure','learning_exposure',temporality='actual',domain='unknown',topic_ids=[])])
    assert s.current_question['id']=='needs'
    while s.state=='interview':s.answer('',Extractor(),'skip')
    active=[e for e in s.events if e['active']]
    assert len(active)==8 and sum(e['question']['is_probe'] for e in active)==1
    assert {q['id'] for q in s.instrument['core_questions']}<={e['question']['id'] for e in active}
    assert s.stop_reason=='question_budget'


def test_determinism_and_only_confirmed_evidence_routes():
    s=new();familiarity(s);before=deepcopy(s.current_question)
    s.answer('I know about effects.',Extractor(full_claims()))
    assert selection_plan(s.events,s.instrument,s.respondent)[0]==before
    s.confirm(True);events=deepcopy(s.events)
    a=selection_plan(events,s.instrument,s.respondent)
    assert a==selection_plan(events,s.instrument,s.respondent) and events==s.events
    assert s.selection_decisions[-1]['variant_id']=='personal'


def test_different_subject_domain_time_and_activity_not_assumed_conflicting():
    for field,pos,neg in [('domain','transferable','IAM'),('subject','respondent','organisation'),('time_quote','last year','this year'),('activity_quote','a seminar','a consultation')]:
        s=new();familiarity(s)
        a=claim('exposure','learning_exposure',temporality='actual',domain='IAM',topic_ids=[],**({field:pos} if field!='domain' else {}))
        b=claim('exposure','absence',domain='IAM',topic_ids=[],**({field:neg} if field!='domain' else {}))
        if field=='domain':a['domain']=pos;b['domain']=neg
        answer(s,'I attended a seminar last year but have not attended a consultation this year.',[a,b])
        assert not s.current_profile['unresolved_scope']


def test_opportunity_barrier_does_not_imply_inability_or_experience():
    s=new();familiarity(s)
    answer(s,'I have never been invited.',[claim('opportunity','barrier',topic_ids=[])])
    assert s.current_profile['requirements']['opportunity']['status']=='satisfied'
    assert s.current_profile['requirements']['experience']['status']=='missing'
    assert not any(c['kind']=='contribution' for c in s.current_profile['claims'])


def test_correction_and_context_change_preserve_exposure_and_archive_pending():
    s=new(stakeholder='researcher');familiarity(s);s.show_definition();pre=deepcopy(s.pre_information_snapshots)
    answer(s,'An aircraft without a pilot.',knowledge())
    s.answer('There may be effects.',Extractor([claim(kind='claim_without_detail')]))
    pending=s.pending['id'];s.edit_context()
    assert s.superseded_pending[-1]['id']==pending
    assert s.pending is None and s.current_profile['claims']==[]
    s.set_context('organisation','authority','milan')
    assert s.current_question['id']=='familiarity' and s.information_exposures
    assert s.pre_information_snapshots==pre
    familiarity(s);answer(s,'An aircraft without a pilot.',knowledge())
    assert all(c['information_context']=='after_information' for c in s.events[-1]['claims'])
    assert all(e['relevance_status']=='superseded' for e in s.events[:2])


def test_edit_reuses_exact_question_not_another_now_eligible_probe():
    s=new();familiarity(s);until(s,'experience')
    answer(s,'I attended a drone seminar.',[claim('exposure','learning_exposure',temporality='actual',domain='IAM',topic_ids=[])])
    target=s.events[-1];assert s.current_question['id']=='contribution'
    s.edit_answer(target['id'])
    assert s.current_question==target['question']
    answer(s,'I did not attend.',[claim('exposure','absence',topic_ids=[])])
    assert s.current_question['id']=='needs'
    assert s.events[-2]['relevance_status']=='superseded'


def test_frozen_20_and_1x_keep_original_selector_and_export_shape():
    from iam_sra.settings import ROOT
    for name in ['baseline_sample.json','baseline_v2_sample.json']:
        s=BaselineSession();s.instrument=deepcopy(json.loads((ROOT/'eval'/name).read_text())['instrument'])
        s.set_context('personal','citizen','madrid');familiarity(s)
        answer(s,'There may be effects.',[claim(kind='claim_without_detail')])
        assert s.current_question['id']!='reasoning'
        data=s.export();assert 'routing_version' not in data
        assert 'ambiguities' not in s.events[-1]['claims'][0]


def test_completed_export_has_dispositions_requirements_provenance_no_scores():
    s=new();familiarity(s);s.finish();s.complete(actor='automation');d=s.export()
    assert d['schema_version']=='iam-baseline-2.2.0'
    assert d['routing_version']=='baseline-routing-1.0.0'
    assert d['routing_stop_reason']=='user_finish'
    assert d['role_mapping']['answering_perspective']=='personal'
    assert d['current_profile']['interview_dispositions']['concept']['disposition']=='not_asked'
    assert d['numerical_crl'] is None and d['scenario_id'] is None


def test_two_probe_ceiling_when_broad_answer_frees_slots():
    s=new();familiarity(s)
    answer(s,'Uncrewed aircraft carry goods. They may have effects.',knowledge()+[claim(kind='claim_without_detail')])
    assert s.current_question['id']=='reasoning'
    answer(s,'Repeated sound could interrupt rest.',[claim()])
    assert s.current_question['id']=='experience'
    answer(s,'I contributed at an activity.',[claim('participation','contribution',temporality='actual',domain='unknown',topic_ids=[])])
    assert s.current_question['id']=='domain'
    answer(s,'It was a bus activity.',[claim('participation','contribution',temporality='actual',domain='transferable',topic_ids=[])])
    while s.state=='interview':s.answer('',Extractor(),'skip')
    assert sum(e['question']['is_probe'] for e in s.events)==2
    assert len(s.events)<=8
    assert 'influence' not in [e['question']['id'] for e in s.events]


def test_unknown_scope_and_flagged_conflict_preserve_both_passages():
    s=new();familiarity(s)
    answer(s,'I attended an activity but have no experience.',[
        claim('exposure','learning_exposure',temporality='actual',domain='unknown',topic_ids=[]),
        claim('exposure','absence',domain='unknown',topic_ids=[],ambiguities=['contradiction'])])
    assert len(s.current_profile['claims'])==3
    assert s.current_question['id']=='scope'
    assert s.current_profile['coverage']['exposure']['status']=='scope_unclear'
    assert 'unresolved_contradiction' in s.current_profile['coverage']['exposure']['evidence_statuses']
    s.answer('',Extractor(),'unsure')
    assert s.current_question['id']=='delivery'
    assert s.current_profile['unresolved_scope']==['exposure']


def test_configurable_smaller_budget_and_early_finish():
    s=new();s.instrument['routing']['maximum_questions']=3;s.instrument['routing']['maximum_probes']=0
    familiarity(s)
    s.answer('',Extractor(),'skip');s.answer('',Extractor(),'skip')
    assert s.maximum_questions==3 and s.state=='baseline_review'
    assert s.stop_reason=='question_budget'
    assert s.current_profile['interview_dispositions']['experience']['disposition']=='budget_limited'


def test_decline_suppresses_later_probe_without_becoming_negative_evidence():
    s=new();familiarity(s);until(s,'experience')
    s.answer('',Extractor(),'decline');complete(s)
    assert not any(e['question']['id'] in {'contribution','domain','influence'} for e in s.events)
    assert s.current_profile['interview_dispositions']['experience']['disposition']=='declined'
    assert s.current_profile['requirements']['experience']['status']=='missing'


def test_probe_applicability_and_not_applicable_disposition():
    s=new();q=next(q for q in s.instrument['core_questions'] if q['id']=='opportunity')
    q['applicable_perspectives']=['organisation']
    familiarity(s);complete(s)
    assert s.current_profile['interview_dispositions']['opportunity']['disposition']=='not_applicable'
    assert any(row['rule_id']=='not_applicable' for row in s.skipped_by_design)


@pytest.mark.presidio_live
def test_real_detector_adaptive_registry_request_and_export(monkeypatch):
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    from iam_sra.llm_client import LLMTransport
    from iam_sra.baseline_client import BaselineClient
    calls=[]
    def transport(self,http,stage,system,user,schema,validator):
        calls.append(stage)
        if stage=='readiness_evidence':
            raw={'interaction':'substantive','claims':[claim('concept','concept_explanation',evidence_id=next(iter(user['passages'])),topic_ids=[],interpretation='You describe an aircraft without a pilot on board.')]}
        else:
            raw={'decisions':[dict(candidate=0,supported=True,dimension='concept',kind='concept_explanation',topic_ids=[],reason='A supplied definition.') ]}
        return validator(json.dumps(raw))
    monkeypatch.setattr(LLMTransport,'_request',transport)
    s=new(stakeholder='researcher');familiarity(s);s.answer('An aircraft without a pilot on board.',BaselineClient());s.confirm(True)
    complete(s)
    assert calls==['readiness_evidence','readiness_grounding']
    assert s.export()['schema_version']=='iam-baseline-2.2.0'
    assert s.export()['privacy_screening_enabled'] is True


def test_confirmed_subject_clarification_resolves_scope_without_rewriting_original():
    s=new(perspective='organisation',stakeholder='researcher');familiarity(s)
    answer(s,'We researched delivery options.',[claim('exposure','learning_exposure',subject='unknown',temporality='actual',domain='IAM',ambiguities=['subject'],topic_ids=[])])
    old=deepcopy(s.events[-1]);assert s.current_question['variant_id']=='subject'
    s.answer('I mean our research team evaluated delivery options.',Extractor([claim('exposure','learning_exposure',subject='organisation',temporality='actual',domain='IAM',topic_ids=[])]))
    assert s.current_profile['unresolved_scope']==['exposure']  # not confirmed yet
    s.confirm(True)
    assert not s.current_profile['unresolved_scope']
    assert s.current_profile['scope_clarifications'][0]['original_evidence_id']==old['claims'][0]['evidence_id']
    assert s.events[-2]==old
    assert s.current_profile['requirements']['experience']['status']=='satisfied'


def test_absent_drone_participation_does_not_close_transferable_outcome_gap():
    s=new();familiarity(s);until(s,'experience')
    answer(s,'I proposed a bus stop at a consultation. I have never attended a drone consultation.',[
        claim('participation','contribution',temporality='actual',domain='transferable',topic_ids=[]),
        claim('participation','absence',domain='IAM',topic_ids=[])])
    assert s.current_question['id']=='influence'
    assert s.current_question['triggering_evidence_ids']
    answer(s,'I do not know if the bus stop changed.',[claim('influence','unknown',domain='transferable',topic_ids=[])])
    assert s.current_question['id']=='needs'
