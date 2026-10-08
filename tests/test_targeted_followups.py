"""Concern-specific hypothetical gates preserve original scores and evidence."""
from copy import deepcopy
from test_confirmation import Fake, meaning, initially_scored
from iam_sra.settings import CONCERNS, config
from iam_sra.updates import select_followups, contract, choice_transition
from iam_sra.session import State


def test_all_expressed_objections_receive_distinct_questions_without_six_question_cutoff():
    s,c=initially_scored(Fake(meaning(scores=tuple(CONCERNS))))
    initial=deepcopy(s.initial);s.begin_followups()
    assert len(s.questions)==len(CONCERNS)+1
    assert len({q['id'] for q in s.questions})==len(CONCERNS)+1
    for q in [q for q in s.questions if q['id']!='macro_policy']:
        spec=contract(q)
        assert spec.context=='hypothetical' and spec.modification and spec.assumptions
        assert len(set(t.concern_id for t in spec.targets))==1
        assert q['choices']==['Fully addresses this concern','Partly addresses this concern','Does not address this concern','Unsure']
        assert q['apply_to_joint']
    assert s.initial==initial


def test_positive_support_does_not_receive_mitigation_question():
    s,c=initially_scored(Fake(meaning(position='supported')))
    s.begin_followups();assert not s.questions and s.state==State.UPDATED


def test_unclear_position_receives_no_followup():
    s,c=initially_scored(Fake(meaning(position='uncertain')))
    s.begin_followups();assert not s.questions and s.state==State.UPDATED


def test_only_expressed_facets_are_targeted_and_partial_resolution_stays_partial():
    s,c=initially_scored(Fake(meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['personal_privacy']})))
    s.begin_followups();q=s.current_question
    assert [t.facet for t in contract(q).targets]==['personal_privacy']
    assert choice_transition(q,'partial_resolution','perceived_safety_privacy','personal_privacy')=='partially_resolved'
    assert choice_transition(q,'aspect_accepted','perceived_safety_privacy','perceived_safety')=='untested'
    initial=deepcopy(s.initial);s.respond(q['choices'][0],'',c)
    assert s.joint_required and s.initial==initial
    s.stop_followups();s.record_joint('unsure',[],'',c);s.continue_final(True,c)
    assert s.initial==initial and s.final['assessment']==initial['assessment'] and s.conditional is None


def test_reviewed_bank_covers_every_registered_facet():
    assert {f for c in CONCERNS.values() for f in c['facets']}==set(config('updates')['mitigations'])


def test_supported_position_with_conditions_still_tests_the_stated_conditions():
    s,c=initially_scored(Fake(meaning(position='supported')))
    profile=s.draft.model_copy(deep=True)
    profile.concerns[0].conditions=['O.p001']
    q=select_followups(profile,s.evidence,assessed_scores={r['concern_id']:r['score'] for r in s.initial['assessment']['concerns']})[0]
    assert contract(q).context=='hypothetical'
    assert q['condition_evidence_ids']==['O.p001']
    assert contract(q).modification==config('updates')['mitigations']['acoustic_impact']
    assert 'You previously asked for:' not in q['text']
    assert 'may not meet all of those conditions' not in q['text']


def test_partial_answer_records_no_full_resolution_or_route_acceptance():
    s,c=initially_scored();initial=deepcopy(s.initial);s.begin_followups();q=s.current_question
    s.respond(q['choices'][1],'',c)
    assert s.responses[0]['code']=='partial_resolution'
    assert s.update_observations[-1]['transition']=='partially_resolved'
    assert not s.responses[0]['choice_meaning']['concerns']
    assert s.responses[0]['choice_meaning']['current_route_stance']['interpretation']=='unassessed'
    assert s.initial==initial


def test_question_names_the_target_and_retains_condition_references_without_model_rationale():
    s,c=initially_scored(Fake(meaning(scores=('noise',))))
    profile=s.draft.model_copy(deep=True)
    profile.concerns[0].rationale='Model-interpreted citizen position; see supporting passages.'
    profile.concerns[0].conditions=['O.p001']
    q=select_followups(profile,s.evidence,assessed_scores={r['concern_id']:r['score'] for r in s.initial['assessment']['concerns']})[0]
    assert q['text'].startswith('About noise\n')
    assert profile.concerns[0].rationale not in q['text']
    assert q['condition_evidence_ids']==['O.p001']
    assert 'concern about noise?' in q['text']


def test_physical_safety_question_does_not_introduce_camera_viewing():
    s,c=initially_scored(Fake(meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['perceived_safety']})))
    q=select_followups(s.draft,s.evidence,assessed_scores={r['concern_id']:r['score'] for r in s.initial['assessment']['concerns']})[0]
    assert q['text'].startswith('About physical safety\n')
    assert 'camera' not in q['text'].lower()


def test_confirmed_opposition_without_a_numeric_score_receives_no_followup():
    s,c=initially_scored(Fake(meaning(scores=('noise',))))
    row=next(r for r in s._initial['assessment']['concerns'] if r['concern_id']=='noise')
    row['score']=None;row['status']='unassessed'
    s.begin_followups()
    assert not s.questions


def test_unknown_airspace_is_excluded_from_questions_and_policy_topics():
    m=meaning(scores=('noise','airspace_capacity'))
    m.concerns[1].position='uncertain'
    s,c=initially_scored(Fake(m));s.begin_followups()
    assert [q['id'] for q in s.questions]==['u_change_noise','macro_policy']
    assert 'aircraft' not in s.questions[-1]['text']
    assert 'noise' in s.questions[-1]['text']
