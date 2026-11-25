import importlib.util
import json
from pathlib import Path

from iam_sra.fn_interview import specification
from iam_sra.fn_reference_audit import audit, expected_goals

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=json.loads((ROOT/'eval/fn_golden_paths.json').read_text())


def test_golden_example_expected_conditional_questions_are_independently_derived():
    short=set(expected_goals('citizen_short',FIXTURE,specification()))
    extended=set(expected_goals('citizen_extended',FIXTURE,specification()))
    for expected in ('demonstration_view','tradeoff','local_basis'):
        assert expected in short and expected in extended
    assert 'hypothetical_comparison' not in short


def test_audit_catches_expected_but_unasked_conditional_question():
    data={'conversation':{'fn_interview':{'stages':[]},'messages':[],
        'information_exposures':[],'suggestion':{'status':'abstained'}}}
    result=audit('citizen_short',data,FIXTURE,specification())
    assert {'demonstration_view','tradeoff','local_basis'} <= set(result['expected_but_unasked'])
    assert not result['healthcare_prior_knowledge_not_exposure_id']


def test_audit_checks_question_coverage_separately_from_annotation_coverage():
    expected=expected_goals('citizen_short',FIXTURE,specification())
    stages=[{'id':'reference','status':'explored','goals':[{'id':goal,'status':'explored','evidence_ids':[]} for goal in expected]}]
    data={'conversation':{'fn_interview':{'stages':stages},'messages':[
        {'role':'assistant','objective_id':'drone_recognition','act':'question'}],
        'information_exposures':[],'suggestion':{'status':'abstained'}}}
    result=audit('citizen_short',data,FIXTURE,specification())
    assert 'demonstration_view' in result['expected_but_unasked']
    assert 'demonstration_view' not in result['expected_but_uncovered']


def test_reference_expectations_do_not_reuse_controller_applicability(monkeypatch):
    from iam_sra.fn_interview import FNInterview
    monkeypatch.setattr(FNInterview,'applicable',lambda *args:False)
    expected=set(expected_goals('citizen_short',FIXTURE,specification()))
    assert {'area','demonstration_view','tradeoff','local_basis'}<=expected
