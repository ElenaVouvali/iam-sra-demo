"""Integrity checks for the synthetic, score-blind 12-persona suite."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def suite():
    return json.loads((ROOT/'eval/fn_generalisation_v1.json').read_text())


def test_generalisation_suite_has_four_distinct_personas_per_profile():
    data=suite();cases=data['cases']
    assert len(cases)==12
    assert len({row['id'] for row in cases})==12
    assert {profile:sum(row['profile']==profile for row in cases)
            for profile in ('citizen','organisational','technical')}=={
                'citizen':4,'organisational':4,'technical':4}
    citizens=[row for row in cases if row['profile']=='citizen']
    assert [sum(row['depth']==depth for row in citizens) for depth in ('short','extended')]==[2,2]
    assert all(row['profile'] in {'citizen','organisational','technical'} for row in cases)


def test_each_persona_declares_facts_unknowns_invariants_and_forbidden_inferences_without_scores():
    cases=suite()['cases']
    for row in cases:
        assert row['ground_truth'] and row['unknowns'] and row['invariants'] and row['forbidden_inferences']
        assert row['protocol']
        assert 'score' not in row and 'target_level' not in row and 'expected_level' not in row
    assert suite()['score_targets'] is None


def test_suite_lineage_is_transparent_and_held_out_cases_are_unchanged():
    cases=suite()['cases'];lineage=[row['lineage'] for row in cases]
    assert sum(value.startswith('adapted from') for value in lineage)==5
    assert sum(value=='new' for value in lineage)==7
    held=set(suite()['held_out'])
    assert held=={'G4_citizen_correction_refusal_extended',
        'G8_organisation_routine_operation','G12_technology_repeated_qualified_operation'}
    assert held <= {row['id'] for row in cases}


def test_scenario_maturity_varies_within_each_non_citizen_profile():
    cases={row['id']:row for row in suite()['cases']}
    assert 'neither is allocated' in ' '.join(cases['G6_organisation_plans_requested_resources']['ground_truth'])
    assert 'completed' in ' '.join(cases['G7_organisation_approved_pilot']['ground_truth'])
    assert 'routine' in ' '.join(cases['G8_organisation_routine_operation']['ground_truth'])
    assert 'not integrated' in ' '.join(cases['G9_technology_lab_subsystem']['ground_truth'])
    assert 'representative' in ' '.join(cases['G11_technology_representative_validation']['ground_truth'])
    assert 'repeated operational use' in ' '.join(cases['G12_technology_repeated_qualified_operation']['ground_truth'])
