"""Policy/flow regressions using explicit extraction doubles, not semantic claims."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from iam_sra.session import Session
from iam_sra.readiness import (ReadinessRecord, ProposalView, EvidenceExtraction, build_profile,
    validate_extraction, next_question, mode_policy, citizen_result)
from iam_sra.assessment import AssessmentError
from iam_sra.interpretation import EvidenceItem


def record(cid='understanding', **changes):
    values = dict(criterion_id=cid, topic_ids=['noise'], evidence_ids=['x'], interpretation='Repeated sound may interrupt rest.',
        kind={'understanding':'understanding','participation':'action','influence':'influence','information':'information_need','opportunity':'opportunity'}[cid],
        status='supported', temporality='past_current' if cid in {'participation','influence','opportunity'} else 'not_applicable',
        experience_domain='IAM_specific', proposal_context='original', elicitation_context='initial_answer',
        evidence_basis='self_report' if cid != 'understanding' else 'answer_demonstrated_reasoning')
    return ReadinessRecord(**(values | changes))


class Extractor:
    def __init__(self, records=(), stance='opposed', concerns=(), conditions=(), policy=(), facets=()):
        self.rows=records; self.stance=stance; self.concerns=concerns; self.conditions=conditions; self.policy=policy; self.calls=0;self.facets=facets
    def extract_readiness(self, evidence, **kwargs):
        self.calls+=1; ref=next(iter(evidence))
        rows=[r.model_copy(update={'evidence_ids':[ref]}) for r in self.rows]
        return EvidenceExtraction(acceptance=ProposalView(stance=self.stance,evidence_ids=[ref] if self.stance!='not_stated' else [],
            concerns=list(self.concerns),conditions=list(self.conditions),topic_ids=list(dict.fromkeys(['noise'] if self.concerns else [])) + (['perceived_safety_privacy'] if 'personal_privacy' in self.facets else []),concern_facets=list(self.facets),policy_preferences=list(self.policy)),records=rows)
    def score(self,*args,**kwargs): raise AssertionError('Default mode must never score acceptance.')


def confirmed(client=None, text='I oppose the route because repeated flights may interrupt rest.', **kwargs):
    s=Session(assessment_mode="acceptance_and_readiness_evidence",**kwargs); s.submit(text,client or Extractor([record()])); s.confirm(True); return s


def test_default_and_historical_modes_are_explicit_and_fixed():
    s=Session(assessment_mode="acceptance_and_readiness_evidence"); assert s.assessment_mode=='acceptance_and_readiness_evidence'
    with pytest.raises(ValueError): Session(assessment_mode='legacy_fn_acceptance_demo')
    with pytest.raises(AttributeError): s.assessment_mode='legacy_fn_acceptance_demo'
    with pytest.raises(ValueError): Session(assessment_mode='invalid')


@pytest.mark.parametrize('stance,text', [('opposed','No, never.'),('supported','Yes, unconditionally!'),('uncertain','I cannot decide.'),('not_stated','I have no view.')])
def test_every_stance_without_concern_gets_interview_not_number(stance,text):
    s=confirmed(Extractor(stance=stance),text)
    assert s.current_question['criterion_id']=='understanding'
    s.finish(); result=s.export()
    assert result['numerical_crl'] is None and result['numerical_srl'] is None
    assert result['readiness_score_status']['reason']==mode_policy()['unavailable_reason']
    assert 'aggregate' not in result and 'aggregation' not in result


def test_informed_opposition_records_reasoning_without_support():
    s=confirmed(); assert s.current_profile['records'][0]['evidence_basis']=='answer_demonstrated_reasoning'
    assert s.acceptance['original_proposal']['stance']=='opposed'
    assert s.current_question['criterion_id']=='information'


def test_uninformed_support_does_not_establish_understanding():
    s=confirmed(Extractor(stance='supported'), 'I love drones, I accept everything!')
    assert s.initial_readiness['records']==[]
    assert s.initial_readiness['criterion_coverage']['understanding']['status']=='not_asked'


@pytest.mark.parametrize('stance,policy', [('supported',['Prioritise speed']),('opposed',['Prioritise privacy']),('uncertain',[])])
def test_stance_and_policy_invariance(stance,policy):
    a=confirmed(Extractor([record()],stance=stance,policy=policy)); b=confirmed(Extractor([record()],stance='mixed'))
    assert a.initial_readiness==b.initial_readiness


def test_intention_does_not_answer_actual_participation_question_or_enable_influence():
    intent=record('participation',kind='intention',temporality='hypothetical_intention',interpretation='Would attend a workshop.')
    profile=build_profile([intent.model_copy(update={'confirmation_status':'confirmed'})])
    assert profile['criterion_coverage']['participation']['status']=='unclear'
    answers=[{'criterion_id':'understanding','control':'skip'},{'criterion_id':'information','control':'skip'}]
    assert next_question(profile,answers)['criterion_id']=='participation'
    answers.append({'criterion_id':'participation','control':'skip'})
    assert next_question(profile,answers)['criterion_id']=='opportunity'


def test_actual_transferable_participation_enables_influence_question():
    s=confirmed(Extractor([record('participation',experience_domain='transferable_other_domain',interpretation='Reported a bus consultation contribution.')]))
    s.skip();s.skip()
    assert s.current_question['criterion_id']=='influence'
    s.skip(unsure=True)
    assert s.current_profile['criterion_coverage']['influence']['status']=='unclear'
    assert s.initial_readiness['records'][0]['experience_domain']=='transferable_other_domain'


def test_no_experience_is_explicit_absence_not_incapability():
    s=confirmed(Extractor([record('participation',status='explicit_absence',interpretation='Reports no prior participation.')]))
    s.skip();s.skip()
    assert s.current_question['criterion_id']=='opportunity'
    assert s.initial_readiness['records'][0]['status']=='explicit_absence'


def test_barrier_and_lack_of_interest_are_different_records():
    barrier=record('opportunity',status='opportunity_barrier',kind='participation_barrier',interpretation='Meeting access prevents participation.')
    interest=record('participation',kind='intention',status='explicit_absence',temporality='hypothetical_intention',interpretation='Does not want to attend.')
    assert barrier.status!=interest.status and barrier.criterion_id!=interest.criterion_id
    s=confirmed(Extractor([barrier]));s.finish()
    assert s.export()['readiness_changes']['opportunity_barriers']


def test_claimed_external_verification_is_not_accepted_from_citizen_text():
    r=record('influence',evidence_basis='separately_reviewed_external_evidence')
    payload=Extractor([r]).extract_readiness({'x':EvidenceItem(id='x',text='I have proof the city listened.',context='original',source='citizen_original')})
    with pytest.raises(AssessmentError,match='external verification'):
        validate_extraction(payload.model_dump(),{'x':EvidenceItem(id='x',text='Claimed proof',context='original',source='citizen_original')},'initial_answer','original',1)


def test_reported_influence_is_self_report_not_verified():
    s=confirmed(Extractor([record('influence',interpretation='Reports that a schedule changed after their comment.')]))
    s.finish(); assert s.final_readiness['records'][0]['evidence_basis']=='self_report'
    assert not s.confirmations[0]['external_truth_verified']


def test_missing_and_invalid_citations_fail_without_historical_fallback():
    class Bad(Extractor):
        def extract_readiness(self,evidence,**kwargs):
            result=super().extract_readiness(evidence,**kwargs);result.records[0].evidence_ids=['invented'];return result
    s=Session(assessment_mode="acceptance_and_readiness_evidence")
    with pytest.raises(AssessmentError):s.submit('An arbitrary answer about an unseen impact.',Bad([record()]))
    assert s.state=='answer' and s.draft_text and s.initial_readiness is None
    assert s.export()['numerical_srl'] is None


def test_model_failure_retains_draft_and_does_not_confirm_or_score():
    class Broken:
        def extract_readiness(self,*args,**kwargs):raise AssessmentError('unavailable',code='transport')
    s=Session(assessment_mode="acceptance_and_readiness_evidence")
    with pytest.raises(AssessmentError):s.submit('Unexpected response, still valid text.',Broken())
    assert s.draft_text=='Unexpected response, still valid text.' and not s.confirmations
    assert s.initial_readiness is None and s.final_readiness is None


def test_empty_answer_is_retryable_skip_is_not_an_answer_or_capability():
    s=Session(assessment_mode="acceptance_and_readiness_evidence")
    with pytest.raises(AssessmentError):s.submit('',Extractor())
    s=confirmed(Extractor());s.skip()
    assert s.current_profile['criterion_coverage']['understanding']['status']=='skipped'
    assert not s.current_profile['records']


def test_clarification_counts_toward_question_budget_and_skip_stops_loop():
    s=confirmed(Extractor(),question_budget=2)
    s.respond('I cannot explain this.',Extractor([record(status='unclear')],stance='not_stated'));s.confirm(True)
    assert not s.current_question['clarification']  # Missing dimensions precede repeats.
    s.skip()
    assert s.state=='final' and s.stop_reason=='question_budget' and len(s.answers)==2


def test_explicit_unsure_does_not_repeat_question():
    s=confirmed(Extractor()); first=s.current_question['id'];s.skip(unsure=True)
    assert s.current_question['id']!=first


def test_initial_intention_does_not_trigger_a_presupposed_activity_clarification():
    s=confirmed(Extractor([record('participation',kind='intention',temporality='hypothetical_intention')]))
    assert not s.current_question['clarification']
    assert 'Was this' not in s.current_question['question_text']


def test_declining_to_repeat_moves_to_another_dimension():
    s=confirmed(Extractor())
    first=s.current_question['criterion_id']
    s.respond('I already answered; please move on.',Extractor([],stance='not_stated'))
    s.pending['control']='decline';s.pending['interaction']='already_answered';s.confirm(True)
    assert s.current_question['criterion_id']!=first
    assert not s.current_profile['records']


def test_information_exposure_is_tracked_without_awarding_readiness():
    s=confirmed(Extractor());initial=s.initial_readiness
    s.record_information_exposure()
    s.respond('I still have no further information.',Extractor([],stance='not_stated'));s.confirm(True)
    assert s.initial_readiness==initial and not s.current_profile['records']
    assert s.export()['information_exposures'][0]['understanding_verified'] is False


def test_initial_snapshot_immutable_and_final_recomputed_after_followup():
    s=confirmed(Extractor()); before=s.initial_readiness
    s.respond('I spoke at a local drone consultation and proposed a quieter schedule.',Extractor([record('participation')],stance='not_stated'));s.confirm(True);s.finish()
    assert s.initial_readiness==before and s.final_readiness['records']
    changes=s.export()['readiness_changes'];assert changes['newly_supported_evidence'][0]['criterion_id']=='participation'
    assert 'influence' in changes['remaining_gaps']
    x=s.initial_readiness;x['records'].append({});assert s.initial_readiness==before


def test_edit_initial_preserves_snapshot_and_supersedes_dependent_confirmations():
    s=confirmed(); initial=s.initial_readiness;s.finish(); old=s.events[0]['id']
    s.edit_answer(old)
    assert s.initial_readiness==initial and s.final_readiness is None
    assert not s.events[0]['active'] and s.corrections[0]['superseded_confirmations']
    with pytest.raises(ValueError):s.finish()
    s.submit('I correct that earlier answer.',Extractor(stance='uncertain'));s.confirm(True);s.finish()
    assert s.initial_readiness==initial and s.final_readiness['records']==[]
    assert len(s.export()['initial_readiness_snapshots'])==2


def test_edit_followup_invalidates_later_answers_and_keeps_initial():
    s=confirmed(Extractor());initial=s.initial_readiness
    s.respond('I attended a meeting.',Extractor([record('participation')],stance='not_stated'));s.confirm(True);s.skip();s.finish()
    event=s.answers[0]['id'];s.edit_answer(event)
    assert s.final_readiness is None and s.initial_readiness==initial and not s.answers
    s.correct('I meant I would attend.',Extractor([record('participation',kind='intention',temporality='hypothetical_intention')],stance='not_stated'))
    s.confirm(True)
    assert s.current_profile['records'][0]['kind']=='intention'


def test_conflicts_remain_visible_until_citizen_correction():
    a=record('opportunity',confirmation_status='confirmed',claim_subject='public consultation access',time_scope='current')
    b=record('opportunity',status='explicit_absence',confirmation_status='confirmed',interpretation='No route to take part.',claim_subject='public consultation access',time_scope='current')
    profile=build_profile([a,b]);assert profile['criterion_coverage']['opportunity']['status']=='conflicting'


def test_intention_and_no_past_participation_are_not_a_contradiction():
    a=record('participation',kind='intention',temporality='hypothetical_intention',confirmation_status='confirmed',claim_subject='consultation',time_scope='current')
    b=record('participation',kind='action',status='explicit_absence',temporality='past_current',confirmation_status='confirmed',claim_subject='consultation',time_scope='current')
    assert build_profile([a,b])['criterion_coverage']['participation']['status']=='evidence_recorded'


def test_unknown_scope_does_not_create_automatic_conflict():
    a=record('participation',confirmation_status='confirmed')
    b=record('participation',status='explicit_absence',confirmation_status='confirmed')
    assert build_profile([a,b])['criterion_coverage']['participation']['status']!='conflicting'


def test_explicit_absence_is_reported_as_new_evidence():
    from iam_sra.readiness import profile_changes
    a=record('participation',kind='action',status='explicit_absence',temporality='past_current',confirmation_status='confirmed')
    change=profile_changes(build_profile([]),build_profile([a]))
    assert change['newly_recorded_absence'] and change['newly_recorded_evidence']


def test_learning_check_is_optional_bounded_and_preserves_initial_snapshot():
    s=confirmed(Extractor([record()]),question_budget=2);initial=s.initial_readiness
    s.start_learning()
    assert s.current_question['elicitation_context']=='after_information_exposure'
    s.respond('It could affect daytime rest; actual sound exposure remains unknown.',Extractor([record()],stance='not_stated'))
    assert s.pending['records'][0]['elicitation_context']=='after_information_exposure'
    s.confirm(True)
    assert len(s.answers)==1 and s.initial_readiness==initial
    assert not s.information_exposures[0]['understanding_verified']
    s.skip();assert s.state=='final' and len(s.answers)==2
    s.start_learning();assert s.state=='final'  # Budget cannot be bypassed.


def test_reading_explanation_alone_creates_no_understanding_record():
    s=confirmed(Extractor());initial=s.initial_readiness
    s.start_learning();s.skip()
    assert not s.current_profile['records'] and s.initial_readiness==initial


def test_unmentioned_facet_cannot_be_explored_from_a_parent_topic():
    s=confirmed(Extractor(concerns=['private-space viewing'],facets=['personal_privacy']))
    s.finish()
    with pytest.raises(ValueError,match='explicitly evidenced'):
        s.explore_acceptance('perceived_safety','Would address my concern','',Extractor())


def test_hypothetical_context_and_exposure_are_tracked_not_prior_experience():
    s=confirmed(Extractor(concerns=['noise','privacy'],facets=['acoustic_impact','personal_privacy']));s.finish();before=s.final_readiness
    s.explore_acceptance('acoustic_impact','Would address my concern','',Extractor())
    assert s.final_readiness==before
    assert s.acceptance['optional_hypothetical_findings'][0]['context']=='hypothetical_modification'
    assert s.export()['numerical_crl'] is None
    s.explore_acceptance('personal_privacy','Would partly address my concern','I would attend a demonstration to learn.',
        Extractor([record('participation',kind='intention',temporality='hypothetical_intention')],stance='not_stated'))
    s.confirm(True)
    assert s.final_readiness['records'][0]['proposal_context']=='hypothetical_modification'
    assert s.final_readiness['records'][0]['temporality']=='hypothetical_intention'


def test_hypothetical_intention_cannot_be_actual_action():
    with pytest.raises(ValueError):record('participation',temporality='hypothetical_intention')


def test_same_policy_source_for_ui_export_and_null_reason():
    s=confirmed();s.finish();e=s.export()
    assert e['citizen_result']==citizen_result(s)
    assert e['citizen_result']['note']==e['readiness_score_status']['reason']
    assert json.loads(s.json())==json.loads(s.jsonl())
    assert e['assessment_participation']['engagement_or_codesign_awarded'] is False
    assert not any('phase' in r for r in e['final_readiness_profile']['records'])


def test_confirmation_required_and_pending_cannot_be_final():
    s=Session(assessment_mode="acceptance_and_readiness_evidence");s.submit('I support the service.',Extractor(stance='supported'))
    with pytest.raises(ValueError):s.confirm(False)
    with pytest.raises(ValueError):s.finish()
    assert not s.current_profile['records']


def test_initial_clarity_prevents_repeated_question_and_total_budget_bounded():
    s=confirmed(Extractor([record(),record('information'),record('participation',status='explicit_absence'),record('opportunity')]))
    assert s.state=='final' and s.answers==[]


def test_arbitrary_unseen_reasoning_not_fixture_dependent():
    text='I oppose this because night-shift carers sleep at noon. A daytime curfew could redistribute the burden; I need shift-work data.'
    s=confirmed(Extractor([record(interpretation='Explains how work schedules could alter who experiences noise.'),record('information')]),text)
    assert len(s.initial_readiness['records'])==2
    assert s.current_question['criterion_id']=='participation'


def test_registry_draft_sources_and_candidate_revision_separation():
    from iam_sra.settings import config
    r=config('readiness')
    assert r['approved_by'] is None and r['review_status']=='draft_pending_FN'
    assert len(r['indicators'])==5 and len(r['original_candidates'])==5
    assert all(q['source_reference'] and q['approved_by'] is None for q in r['indicators'])




def test_transferable_experience_and_no_iam_experience_do_not_conflict():
    a=record('participation',experience_domain='transferable_other_domain',confirmation_status='confirmed')
    b=record('participation',experience_domain='IAM_specific',status='explicit_absence',confirmation_status='confirmed')
    assert build_profile([a,b])['criterion_coverage']['participation']['status']=='evidence_recorded'


def test_available_contact_and_access_barrier_can_coexist():
    a=record('opportunity',confirmation_status='confirmed')
    b=record('opportunity',kind='participation_barrier',status='opportunity_barrier',confirmation_status='confirmed')
    assert build_profile([a,b])['criterion_coverage']['opportunity']['status']=='opportunity_barrier'


def test_edits_mark_dependent_confirmations_inactive():
    s=confirmed();s.finish();s.edit_answer(s.events[0]['id'])
    assert all(not c['active'] for c in s.confirmations)


def test_topic_coverage_preserves_uncertainty_and_unasked_topics():
    r=record(status='unclear',confirmation_status='confirmed')
    p=build_profile([r])
    assert p['topic_coverage']['noise']['status']=='unclear'
    assert p['topic_coverage']['energy_emissions']['status']=='not_asked'


def test_confirmed_interpretation_mutation_cannot_silently_change_final_profile():
    s=confirmed();s.events[0]['records'][0]['interpretation']='Altered after confirmation'
    with pytest.raises(ValueError,match='confirm'):s.finish()


def test_unknown_scope_retains_passages_and_requests_neutral_clarification():
    a=record('participation',kind='action',temporality='past_current',status='supported',confirmation_status='confirmed',evidence_ids=['a'])
    b=record('participation',kind='action',temporality='past_current',status='explicit_absence',confirmation_status='confirmed',evidence_ids=['b'])
    profile=build_profile([a,b])
    assert profile['criterion_coverage']['participation']['status']=='scope_clarification_required'
    assert profile['criterion_coverage']['participation']['evidence_ids']==['a','b']
    from iam_sra.settings import config
    registry=deepcopy(config('readiness'))
    registry['indicators']=[i for i in registry['indicators'] if i['criterion_id']=='participation']
    question=next_question(profile,[],registry=registry)
    assert 'different activities or times' in question['question_text']
    assert profile['numerical_crl'] is None


def test_distinct_known_events_or_times_do_not_request_scope_clarification():
    a=record('participation',kind='action',temporality='past_current',status='supported',confirmation_status='confirmed',claim_subject='bus consultation',time_scope='last year')
    b=record('participation',kind='action',temporality='past_current',status='explicit_absence',confirmation_status='confirmed',claim_subject='drone consultation',time_scope='this year')
    assert build_profile([a,b])['criterion_coverage']['participation']['status']=='evidence_recorded'
