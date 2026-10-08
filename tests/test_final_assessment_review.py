from iam_sra.settings import config
"""FN-led bounded progression is an explicit pilot index, not a conditional rating."""
from copy import deepcopy
import pytest
from iam_sra.session import State
from iam_sra.assessment_review import final_review, progression
from iam_sra.reporting import final_summary
from test_confirmation import Fake,meaning,initially_scored
from test_ui import fresh,click


def started():
    m=meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']})
    m.concerns[-1].position='supported'
    s,c=initially_scored(Fake(m));s.begin_followups()
    assert s.initial['aggregate']['rounded']==4
    return s,c


def finish(s,c,choices=None,priority=0):
    choices=choices or {}
    while s.state==State.FOLLOWUPS:
        q=s.current_question
        index=priority if q['id']=='macro_policy' else choices.get(q['id'],0)
        s.respond(q['choices'][index],'',c)
    assert not s.joint_confirmation_required
    s.continue_final(True,c)
    return final_review(s)


@pytest.mark.parametrize('index,expected',[(0,6),(1,5),(2,3),(3,4)])
def test_full_partial_rejected_and_unknown_outcomes(index,expected):
    s,c=started();initial=deepcopy(s.initial)
    review=finish(s,c,{'u_change_noise':index,'u_change_perceived_safety_privacy':index})
    assert review['final_headline']==expected
    assert s.initial==initial and s.final['assessment']==initial['assessment']
    assert review['final_profile']=='bounded_followup'
    assert s.joint is None and s.conditional is None
    gains={r['concern_id']:r['gain'] for r in review['progression']['decisions']}
    for cid in ['noise','perceived_safety_privacy']:
        old=next(r['score'] for r in initial['assessment']['concerns'] if r['concern_id']==cid)
        assert gains[cid]==max(1,min(9,old+{0:2,1:1,2:-2,3:0}[index]))-old
    assert gains['welfare_equity']==0


@pytest.mark.parametrize('priority',range(3))
def test_policy_priority_adjusts_overall_score_without_changing_medical_support(priority):
    s,c=started();review=finish(s,c,priority=priority)
    assert review['final_headline']==[6,4,6][priority]
    medical=next(r for r in review['concerns'] if r['concern_id']=='welfare_equity')
    assert medical['initial_score']==medical['final_score']==8
    assert review['policy_priority_answers'][0]['numerical_change']==[2,-2,0][priority]
    assert s.export()['final_assessment_review']==review


def test_only_noise_resolved_retains_privacy_bottleneck():
    s,c=started();review=finish(s,c,{'u_change_perceived_safety_privacy':2})
    assert review['final_headline']==3
    assert review['final_aggregate']['cap']==3
    assert review['final_aggregate']['mean']==14/3


def test_only_privacy_resolved_with_noise_rejected_gives_three():
    s,c=started();review=finish(s,c,{'u_change_noise':2})
    assert review['final_headline']==3


def test_unknown_required_aspect_prevents_whole_concern_gain():
    m=meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['personal_privacy','perceived_safety']})
    s,c=initially_scored(Fake(m));s.begin_followups()
    # Test just viewing: do not pretend the untested safety aspect is resolved.
    s._questions[0]['contract']['targets']=[{'concern_id':'perceived_safety_privacy','facet':'personal_privacy'}]
    review=finish(s,c,priority=2)
    assert review['progression']['decisions'][2]['gain']==0
    assert review['final_headline']==s.initial['aggregate']['rounded']


def test_positive_update_is_once_per_concern_and_clamped_to_nine():
    s,c=started();finish(s,c)
    responses=deepcopy(s.responses);s.responses+=responses
    assert progression(s)['aggregate']['rounded']==6
    assert all(r['gain']<=2 for r in progression(s)['decisions'])
    s._final['assessment']['concerns']=deepcopy(s._final['assessment']['concerns'])
    next(x for x in s._final['assessment']['concerns'] if x['concern_id']=='noise')['score']=8
    row=next(r for r in progression(s)['decisions'] if r['concern_id']=='noise')
    assert row['progression_score']==9 and row['gain']==1


def test_clarification_reservation_prevents_full_resolution_gain():
    s,c=started();finish(s,c)
    r=next(r for r in s.responses if r['question_id']=='u_change_noise')
    r['clarification_meaning']=meaning('extra',scores=('noise',),position='mixed').model_dump()
    row=next(r for r in progression(s)['decisions'] if r['concern_id']=='noise')
    assert row['gain']==0 and 'reservation' in row['reason']


def test_unknown_emissions_receives_no_question_and_accepted_energy_is_retained():
    from test_followup_manual_pack import CASES,session
    case=next(c for c in CASES if c['id']=='T18')
    s,c=session(case);s.begin_followups()
    assert not s.questions and s.state==State.UPDATED
    s.continue_final(True,c)
    assert final_summary(s)['selected_profile']=='final_original'


def test_completed_screen_shows_only_updated_srl_and_keeps_initial_in_export(monkeypatch):
    m=meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']})
    m.concerns[-1].position='supported'
    app=fresh(monkeypatch,Fake(m));click(app)
    app.text_area(key='citizen_answer').set_value('I support medical deliveries but oppose noise and viewing.');click(app)
    app.checkbox(key='confirm_1').check().run();click(app)
    assert app.metric[0].value=='4/9'
    click(app,'Continue to follow-up questions')
    s=app.session_state.session;initial=deepcopy(s.initial)
    while s.state==State.FOLLOWUPS:
        q=s.current_question;app.radio(key='choice_'+q['id']).set_value(q['choices'][0]);click(app)
    assert not any(x.key=='joint_choice' for x in app.radio)
    assert not any(x.label=='This reflects what I meant' for x in app.checkbox)
    assert s.state==State.FINAL and s.initial==initial
    assert [(m.label,m.value) for m in app.metric]==[('Updated SRL after follow-ups','6/9')]
    assert not app.dataframe and not app.json and not app.exception
    text=' '.join(x.value for x in app.markdown)
    assert 'How the update policy works' not in text
    assert not any(e.label=='Aggregation and bottleneck calculations' for e in app.expander)
    assert s.export()['final_assessment_review']['initial_aggregate']['rounded']==4
    assert s.export()['final_assessment_review']['policy_priority_answers'][0]['numerical_change']==2


def test_parent_support_does_not_hide_an_unknown_companion_aspect():
    from test_followup_manual_pack import CASES,session
    case=next(c for c in CASES if c['id']=='T18')
    s,c=session(case)
    # Real parent projection can describe the clear accepted aspect as supported
    # while retaining uncertainty in the independent ledger.
    s.draft.concerns[0].position='supported'
    from iam_sra.interpretation import freeze
    s.confirmed=freeze(s.draft,s.evidence,s.version,'original','Original proposal')
    s.begin_followups()
    assert not s.questions and s.state==State.UPDATED
    assert s.original_facets['energy_emissions:emissions'].position=='uncertain'


def test_unconfirmed_gates_do_not_produce_progression_gains():
    s,c=started()
    while s.state==State.FOLLOWUPS:
        q=s.current_question;s.respond(q['choices'][0],'',c)
    assert s.updated_confirmed is None
    assert all(d['gain']==0 for d in progression(s)['decisions'])


def test_export_has_traceable_progression_without_fabricated_combined_acceptance():
    s,c=started();finish(s,c);data=s.export()
    assert data['schema_version']=='5.4.0'
    assert data['aggregation']['bounded_followup']['rounded']==data['final_summary']['headline_score']==6
    assert data['aggregation']['initial_original']['rounded']==4
    assert data['proposals']['combined_modified'] is None
    assert len(data['proposals']['independent_hypotheses'])==2
    noise=next(d for d in data['domain_assessments'] if d['concern_id']=='noise')
    assert noise['profiles']['initial_original']['score']==noise['profiles']['final_original']['score']==3
    assert noise['progression_decision']['progression_score']==5


def test_original_uncertainty_does_not_create_mitigation_or_policy_questions():
    s,c=initially_scored(Fake(meaning(scores=('energy_emissions',),position='uncertain',facets={'energy_emissions':['emissions']})))
    s.begin_followups()
    assert not s.questions and s.state==State.UPDATED
    s.continue_final(True,c)
    assert s.final['aggregate']['coverage']=='0/15'


def test_partial_resolution_with_remaining_requirements_still_adds_one():
    s,c=started();finish(s,c,{'u_change_noise':1})
    r=next(r for r in s.responses if r['question_id']=='u_change_noise')
    r['clarification_meaning']=meaning('extra',scores=('noise',),position='mixed').model_dump()
    row=next(r for r in progression(s)['decisions'] if r['concern_id']=='noise')
    assert row['gain']==1


def test_policy_adjustment_applies_once_and_exposes_bottleneck_clipping():
    s,c=started();review=finish(s,c)
    adjustment=review['progression']['aggregate']['policy_adjustment']
    assert adjustment=={'before':6,'requested':2,'applied':0,'after':6,'ceiling':6,'question_id':'macro_policy'}
    last=deepcopy(next(r for r in s.responses if r['question_id']=='macro_policy'))
    last['code']='concern_priority';s.responses.extend([last,last])
    adjustment=progression(s)['aggregate']['policy_adjustment']
    assert adjustment['requested']==-2 and adjustment['after']==4


def test_policy_penalty_never_reduces_overall_score_below_one():
    s,c=started();finish(s,c,{'u_change_noise':2,'u_change_perceived_safety_privacy':2},priority=1)
    adjustment=progression(s)['aggregate']['policy_adjustment']
    assert adjustment['before']==3 and adjustment['after']==1


def test_policy_bonus_requests_two_and_respects_remaining_bottleneck_room():
    s,c=started();finish(s,c)
    for row in s._final['assessment']['concerns']:
        if row['score'] is not None:row['score']=6
    adjustment=progression(s)['aggregate']['policy_adjustment']
    assert adjustment['before']==7 and adjustment['after']==8
    assert adjustment['requested']==2 and adjustment['applied']==1
    for row in s._final['assessment']['concerns']:
        if row['score'] is not None:row['score']=5 if row['concern_id']=='welfare_equity' else 3
    adjustment=progression(s)['aggregate']['policy_adjustment']
    assert adjustment['before']==5 and adjustment['after']==7
    assert adjustment['requested']==adjustment['applied']==2
