import itertools
import pytest
from iam_sra.settings import QUESTIONS
from iam_sra.validation import outcome, conclusions
from test_core import assessment

def responses(indices):return [outcome(q,q['choices'][i]) for q,i in zip(QUESTIONS,indices)]
def rules(summary):return {m['rule_id'] for m in summary['matched_rules']}
@pytest.mark.parametrize('indices',list(itertools.product(range(4),range(4),range(3))))
def test_fn_combination_rules(indices):
    summary=conclusions(responses(indices))
    assert ('physical_adjustments_accepted' in rules(summary))==(indices[0]==0 and indices[1]==0)
    assert ('remaining_objection' in rules(summary))==(indices[0] in [1,2] or indices[1] in [1,2])
    assert ('local_rights_priority' in rules(summary))==(indices[2]==1)
    assert summary['numerical_update'] is None
    assert summary['unresolved_questions']==[q['id'] for q,i in zip(QUESTIONS,indices) if i==len(q['choices'])-1]

def test_acceptance_and_local_rights_priority_coexist():
    summary=conclusions(responses([0,0,1]))
    assert rules(summary)=={'physical_adjustments_accepted','local_rights_priority'}
    assert summary['overlapping_source_outcomes']
    assert not summary['remaining_concerns']

def test_multiple_remaining_concerns_and_policy_are_preserved():
    summary=conclusions(responses([1,1,1]))
    assert summary['remaining_concerns']==['Telemetry/cybersecurity data access','Visual clutter']
    assert rules(summary)=={'remaining_objection','local_rights_priority'}

def test_original_unasked_concerns_remain_untested():
    a=assessment({'noise':3,'cost_roi_business':3})
    before=a.model_dump()
    summary=conclusions(responses([0,0,0]),a)
    assert summary['untested_original_concerns']==['cost_roi_business']
    assert a.model_dump()==before

def test_previous_session_records_are_compatible():
    old=responses([0,1,1])
    for r in old:r.pop('code')
    assert conclusions(old)['remaining_concerns']==['Visual clutter']

def test_all_reference_questions_do_not_assess_missing_concerns():
    from iam_sra.session import Session
    a=assessment({'perceived_safety_privacy':2})
    s=Session();s.begin();s.submit('noise privacy visual welfare',lambda text:a)
    original=s.original.model_dump()
    s.validate(True,include_reference_questions=True)
    assert [q['id'] for q in s.questions]==['q1','q2','q3']
    for q in s.questions:s.respond(q['choices'][0])
    assert s.export()['include_reference_questions'] is True
    assert s.original.model_dump()==original
