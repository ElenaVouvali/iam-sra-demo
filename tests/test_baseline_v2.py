"""Synthetic evidence fixtures; assertions check contracts, not Qwen accuracy."""
from copy import deepcopy
import json
import pytest
from iam_sra.baseline import BaselineClaim, BaselineExtraction, BaselineReview, reviewed
from iam_sra.baseline_session import BaselineSession
from iam_sra.privacy import PrivacyError, require_clean
from test_baseline import Extractor, claim, answer, familiarity, complete, start


def new(**kw):return start(current=True,**kw)


def until(s,target):
    while s.state=='interview' and s.current_question['id']!=target:
        s.answer('',Extractor(),'skip')
    assert s.current_question and s.current_question['id']==target


def test_new_registry_canonical_source_and_historical_ambiguity_preserved():
    s=new();t=s.instrument['stakeholder_taxonomy']
    assert len(t['categories'])==8
    assert s.respondent['stakeholder_record']['canonical_wording']=='General Public and Civil Society Organisations'
    assert s.respondent['stakeholder_taxonomy_version']==t['version']
    assert 'healthcare' not in s.instrument['stakeholders'] and 'healthcare' in s.instrument['sectors']
    old=start(stakeholder='healthcare');old_label=old.instrument['stakeholders']['healthcare']
    assert old.export()['respondent_context']['stakeholder_category']=='healthcare'
    assert old.instrument['stakeholders']['healthcare']==old_label
    assert 'stakeholder_taxonomy_version' not in old.respondent
    assert not {'pending_answer','skipped_by_design','pre_information_snapshots'} & old.export().keys()
    for row in t['categories']:
        assert row['source_section']=='GA Part B §2.2.1, p.30'
    assert t['interface_responses']==['other','withheld']


def test_sector_not_perspective_or_capability():
    s=BaselineSession();s.set_context('personal','citizen','madrid',sector='healthcare')
    assert s.respondent['perspective']=='personal'
    assert s.respondent['sector']=='healthcare' and not s.current_profile['claims']
    assert all(v is None for k,v in s.instrument['numerical_policy'].items() if k!='reason')


def test_novice_unknown_skip_decline_and_early_finish():
    s=new();familiarity(s,'no')
    assert s.current_question['id']=='concept'
    answer(s,'I do not know.',[claim('concept','unknown',topic_ids=[],interpretation='You are unsure what a drone is.')])
    assert s.current_question['id']=='delivery'
    s.answer('',Extractor(),'skip');s.answer('',Extractor(),'decline')
    s.finish();s.complete(actor='automation');d=s.export()
    assert d['stop_reason']=='user_finish'
    assert d['current_profile']['coverage']['concept']['status']=='unknown'
    assert d['current_profile']['coverage']['delivery']['status']=='skipped'
    assert d['current_profile']['coverage']['understanding']['status']=='declined'
    assert d['current_profile']['coverage']['influence']['status']=='not_asked'
    assert not d['information_exposures']


def test_drone_familiarity_not_delivery_or_reasoning():
    s=new();familiarity(s,'lot')
    assert len(s.current_profile['claims'])==1
    answer(s,'It is an aircraft without a pilot on board.',[claim('concept','concept_explanation',topic_ids=[],interpretation='You describe an aircraft without a pilot on board.')])
    assert s.current_question['id']=='delivery'
    answer(s,'I have not heard of delivery uses.',[claim('delivery','absence',topic_ids=[],interpretation='You have not heard of delivery uses.')])
    assert s.current_profile['coverage']['concept']['status']=='evidence_recorded'
    assert s.current_profile['coverage']['delivery']['status']=='explicit_absence'
    assert not any(c['dimension']=='understanding' for c in s.current_profile['claims'])


def test_concept_and_time_saving_use_survive_grounding_without_impact_reasoning():
    for dimension,kind,text in [('concept','concept_explanation','You describe an aircraft without a pilot on board.'),
                                ('delivery','use_knowledge','You know drones can carry medical materials to save time.')]:
        c=BaselineClaim.model_validate(claim(dimension,kind,evidence_id='B2_1.p001',topic_ids=[],interpretation=text))
        source=BaselineExtraction(interaction='substantive',claims=[c])
        decision=dict(candidate=0,supported=True,dimension=dimension,kind=kind,topic_ids=[],interpretation=text,reason='Everyday knowledge is supported.')
        assert reviewed(source,BaselineReview.model_validate({'decisions':[decision]})).claims[0].kind==kind


def test_confirmed_earlier_evidence_avoids_later_questions_and_logs_design_skips():
    s=new();familiarity(s)
    answer(s,'Aircraft without a pilot can carry goods. Noise can disturb sleep because flights repeat. I need sound data.',[
        claim('concept','concept_explanation',topic_ids=[],interpretation='You describe an aircraft without a pilot.'),
        claim('delivery','use_knowledge',topic_ids=[],interpretation='You know they can carry goods.'),claim(),
        claim('information','information_need',interpretation='You want sound data.')])
    assert s.current_question['id']=='experience'
    assert {'delivery','understanding','needs'} <= {r['question_id'] for r in s.skipped_by_design}
    assert all(r['rule_id']=='confirmed_evidence_covers_item' for r in s.skipped_by_design)


@pytest.mark.parametrize('stance',['I support deliveries.','I oppose deliveries.'])
def test_equally_reasoned_support_opposition_do_not_score_or_change_route(stance):
    s=new();familiarity(s)
    answer(s,stance+' Repeated noise could interrupt sleep because flights occur during rest.',[claim()])
    assert s.current_profile['coverage']['understanding']['status']=='evidence_recorded'
    assert s.current_question['id']=='delivery'  # concept answered but not demonstrated; no repeat
    assert not any(c['dimension']=='participation' for c in s.current_profile['claims'])
    assert s.instrument['numerical_policy']['numerical_crl'] is None


def test_max_eight_total_at_most_two_probes_and_budget_stop():
    s=new();familiarity(s)
    until(s,'experience')
    answer(s,'I attended a seminar.',[claim('exposure','learning_exposure',temporality='actual',domain='unknown',topic_ids=[],interpretation='You attended a seminar.')])
    until(s,'opportunity');s.answer('',Extractor(),'skip')
    assert s.current_question['id']=='contribution'
    answer(s,'I suggested a change.',[claim('participation','contribution',temporality='actual',domain='unknown',topic_ids=[],interpretation='You suggested a change.')])
    assert s.state=='baseline_review' and s.stop_reason=='question_budget'
    active=[e for e in s.events if e['active']]
    assert len(active)==8 and sum(e['question']['is_probe'] for e in active)==1


def test_two_probes_when_earlier_answer_frees_core_budget():
    s=new();familiarity(s)
    answer(s,'I know they carry goods. They can make noise.',[
        claim('concept','concept_explanation',topic_ids=[],interpretation='You describe unmanned aircraft.'),
        claim('delivery','use_knowledge',topic_ids=[],interpretation='You describe carrying goods.'),
        claim(kind='claim_without_detail',interpretation='You mention possible noise.')])
    until(s,'experience')
    answer(s,'I attended a drone seminar.',[claim('exposure','learning_exposure',temporality='actual',domain='IAM',topic_ids=[],interpretation='You attended a drone seminar.')])
    until(s,'opportunity');s.answer('',Extractor(),'skip')
    assert s.current_question['id']=='reasoning'
    answer(s,'Repeated flights could interrupt rest.',[claim()])
    assert s.current_question['id']=='contribution'
    s.answer('',Extractor(),'unsure')
    assert s.state=='baseline_review'
    assert sum(e['question']['is_probe'] for e in s.events)==2 and len(s.events)<=8


def test_intention_no_influence_and_actual_contribution_unknown_outcome():
    for actual in (False,True):
        s=new();familiarity(s);until(s,'experience')
        answer(s,'I suggested a clinic stop.' if actual else 'I would attend.',[
            claim('participation','contribution' if actual else 'intention',temporality='actual' if actual else 'intention',domain='transferable',topic_ids=[],interpretation='You report a contribution.' if actual else 'You would attend a future discussion.')])
        until(s,'opportunity')
        answer(s,'I have never been invited.',[claim('opportunity','barrier',topic_ids=[],interpretation='You have not been invited.')])
        if actual:
            assert s.current_question['id']=='influence'
            answer(s,'I do not know what changed.',[claim('influence','unknown',topic_ids=[],interpretation='You do not know what changed.')])
        else:assert s.state=='baseline_review'
        assert not any(c['kind']=='influence' for c in s.current_profile['claims'])
        assert s.current_profile['coverage']['opportunity']['status']=='evidence_recorded'


def test_requested_definition_preserves_pre_answer_and_marks_all_later_evidence():
    s=new();familiarity(s,'no')
    answer(s,'I do not know what a drone is.',[claim('concept','unknown',topic_ids=[],interpretation='You do not know what a drone is.')])
    before=deepcopy(s.current_profile);initial=s.initial_baseline;n=len(s.events)
    text=s.show_definition()
    assert len(s.events)==n and s.pre_information_snapshots[0]['profile']==before
    assert s.information_exposures[0]['text']==text
    assert s.information_exposures[0]['displayed_at'] and not s.information_exposures[0]['acknowledged']
    client=answer(s,'They can carry parcels.',[claim('delivery','use_knowledge',topic_ids=[],interpretation='You describe parcel delivery.')])
    assert client.calls[0]['question']['information_context']=='after_information'
    assert client.calls[0]['question']['displayed_information'][0]['text']==text
    c=s.events[-1]['claims'][0]
    assert c['information_context']=='after_information' and c['independent_prior_knowledge'] is False
    assert s.initial_baseline==initial
    complete(s);s.handoff();s.edit_answer(s.events[-1]['id'])
    assert s.completed_baseline is None and s.handoff_record is None
    assert s.information_exposures[0]['text']==text  # Cannot undo a real display by editing.
    assert s.export()['schema_version']=='iam-baseline-2.0.0'


def test_explanation_cannot_be_displayed_before_pending_answer_confirmation():
    s=new();familiarity(s,'no');s.answer('I do not know.',Extractor())
    with pytest.raises(ValueError):s.show_definition()
    assert not s.information_exposures


def test_all_new_free_text_paths_block_before_mutation_or_model():
    s=new();familiarity(s);client=Extractor();before=deepcopy(s.__dict__)
    with pytest.raises(PrivacyError):s.answer('My password is synthetic-secret-xyz.',client)
    assert not client.calls and s.__dict__==before
    with pytest.raises(PrivacyError):s.set_context('personal','citizen','other','my address is 42 example street')
    assert s.__dict__==before
    s.answer('A drone is an aircraft.',client);before=deepcopy(s.__dict__)
    with pytest.raises(PrivacyError):s.correct_pending('My PIN is 1846.',client)
    assert s.__dict__==before
    s.pending['text']='My PIN is 1846.'
    with pytest.raises(PrivacyError):s.export()


@pytest.mark.presidio_live
def test_real_detector_current_registry_definition_and_export():
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    for row in BaselineSession().instrument['stakeholder_taxonomy']['categories']:
        s=new(stakeholder=row['id']);familiarity(s,'no')
        s.show_definition()
        answer(s,'A drone is an aircraft without a pilot on board.',[
            claim('concept','concept_explanation',topic_ids=[],interpretation='You describe an aircraft without a pilot on board.')])
        assert s.events[-1]['information_context']=='after_information'
        complete(s)
        assert s.export()['schema_version']=='iam-baseline-2.0.0'


def test_frozen_old_session_rejects_new_dimensions_without_mutation():
    s=start();familiarity(s);before=deepcopy(s.__dict__)
    with pytest.raises(Exception,match='outside this session version'):
        s.answer('An aircraft without a pilot.',Extractor([claim('concept','concept_explanation',topic_ids=[])]))
    assert s.__dict__==before
