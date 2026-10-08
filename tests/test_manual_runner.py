"""Comparison logic tests; these do not exercise the live model."""
import json
from pathlib import Path
import runpy
import pytest

ROOT=Path(__file__).resolve().parents[1]
compare=runpy.run_path(str(ROOT/'scripts/run-initial-manual-tests.py'))['compare']
CASES=json.loads((ROOT/'manual-tests/initial-assessment-cases.json').read_text())['cases']


def snapshot(case):
    aggregation=case['expected_aggregation'].copy()
    aggregation['trace']={'selected_minimum':aggregation['minimum'],'cap_applied':aggregation['cap_applied']}
    return {'assessment':{'concerns':[{'concern_id':cid,'score':score,'facets':list(case['expected_facets'].get(cid,{}))} for cid,score in case['expected_scores'].items()]},
            'score_decisions':[{'concern_id':cid,'facet':facet,'score':score} for cid,facets in case['expected_facets'].items() for facet,score in facets.items()],
            'aggregate':aggregation}


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_all_manual_targets_compare_without_false_differences(case):
    assert compare(case,snapshot(case))['matches_expected']


def test_manual_comparison_detects_omitted_and_spurious_concerns():
    case=CASES[0];actual=snapshot(case)
    actual['assessment']['concerns']=[c for c in actual['assessment']['concerns'] if c['concern_id']!='noise']
    actual['assessment']['concerns'].append({'concern_id':'public_awareness_trust','score':8})
    result=compare(case,actual)
    assert {r['concern_id'] for r in result['concern_scores']}=={'noise','public_awareness_trust'}
    assert not result['matches_expected']


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_human_target_arithmetic_matches_application(case):
    from types import SimpleNamespace
    from iam_sra.scoring import aggregate
    result=aggregate(SimpleNamespace(concerns=[SimpleNamespace(concern_id=cid,score=v,status='assessed')
        for cid,v in case['expected_scores'].items() if v is not None]))
    for key in ['coverage','mean','cap','adjusted','rounded']:
        assert result[key]==case['expected_aggregation'][key]


def test_mapping_comparison_detects_wrong_position_and_wrong_condition():
    from types import SimpleNamespace
    from iam_sra.interpretation import EvidenceItem
    compare_meaning=runpy.run_path(str(ROOT/'scripts/run-initial-manual-tests.py'))['compare_meaning']
    case={'expected_positions':{'noise':{'acoustic_impact':'opposed'}},
        'expected_conditions':{'noise':{'acoustic_impact':{'required':True,'verbatim_fragment':'quieter'}}}}
    evidence={'p':EvidenceItem(id='p',text='I trust the city.',source='citizen_original',context='original')}
    facets=[SimpleNamespace(concern_id='noise',facet='acoustic_impact',position='supported',condition_ids=['p'])]
    result=compare_meaning(case,facets,evidence)
    assert len(result['positions'])==len(result['conditions'])==1
