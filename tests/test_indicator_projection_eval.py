import json
from pathlib import Path

from iam_sra.readiness_bank import load_bank

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'eval/iam_indicator_concern_cases_v1.json').read_text())['cases']


def test_indicator_benchmark_uses_exact_registered_v4_ids_and_spans_all_15():
    bank=load_bank();known={row['id'] for row in bank['indicators']}
    assert len(known)==15
    expected={item for case in CASES for item in case['expected_indicator_ids']}
    assert expected==known


def test_benchmark_preserves_wildlife_as_unmapped_and_includes_multi_indicator_evidence():
    wildlife=next(row for row in CASES if row['id']=='wildlife_nesting')
    assert wildlife['expected_unmapped'] and wildlife['expected_indicator_ids']==[]
    assert 'nesting birds' in wildlife['evidence']
    multi=[row for row in CASES if len(row['expected_indicator_ids'])>1]
    assert {row['id'] for row in multi}>={'urban_plan_participation','staff_and_public_learning','transport_chain_tradeoff'}
    assert all(row['evidence'] and row['rationale'] for row in multi)


def test_indicator_cases_are_fictional_and_do_not_encode_readiness_targets():
    assert all('level' not in case and 'score' not in case for case in CASES)
    assert len(CASES)>=15
