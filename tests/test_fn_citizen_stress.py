import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_citizen_stress_personas_cover_both_depths_without_score_targets():
    bank=json.loads((ROOT/'eval/fn_citizen_stress_v1.json').read_text())
    scenarios=bank['scenarios']
    ids={x['id'] for x in scenarios}
    assert len(ids)==7
    assert {f'S{i}_' for i in range(1,7)}<= {value[:3] for value in ids}
    assert 'S7_multi_concern_evolving_priorities_extended' in ids
    assert {x['depth'] for x in scenarios}=={'short','extended'}
    text=json.dumps(bank).casefold()
    assert 'target_score' not in text and 'target_level' not in text and 'expected_crl' not in text
    for row in scenarios:
        assert row['persona']['perspective']=='citizen'
        assert row['persona']['city'] and row['persona']['unknown_facts']
        assert row['answers']


def test_stress_scenarios_include_unfamiliarity_priority_change_uncertainty_and_no_influence_claims():
    bank=json.loads((ROOT/'eval/fn_citizen_stress_v1.json').read_text())
    rows={x['id']:x for x in bank['scenarios']}
    assert 'birds' in rows['S1_unfamiliar_birds_short']['answers']['open_priorities'].casefold()
    assert 'privacy' in rows['S2_privacy_priority_shift_short']['answers']['open_more'].casefold()
    assert 'not sure' in rows['S3_ambiguous_uncertain_short']['answers']['drone_recognition'].casefold()
    assert 'never had an opportunity' in rows['S4_supportive_inexperienced_extended']['answers']['opportunity'].casefold()
    assert 'do not know' in rows['S5_engaged_influence_uncertain_extended']['answers']['feedback_outcome'].casefold()
    assert 'prefer not to answer' in rows['S6_challenging_correction_refusal_extended']['answers']['opportunity'].casefold()


def test_s7_preserves_distinct_concerns_priority_change_correction_and_no_influence_claim():
    bank=json.loads((ROOT/'eval/fn_citizen_stress_v1.json').read_text())
    row=next(x for x in bank['scenarios'] if x['id']=='S7_multi_concern_evolving_priorities_extended')
    answers=row['answers'];persona=row['persona']
    assert row['depth']=='extended'
    for term in ('nesting birds','noise','bedroom window','not be shared fairly','influence'):
        assert term in answers['open_priorities'].casefold()
    assert 'without choosing' in answers['open_more'].casefold() or 'not chosen' in answers['open_more'].casefold()
    assert 'choose wildlife disturbance and privacy' in answers['priorities'][0].casefold()
    assert 'revise' in answers['priorities'][1].casefold()
    assert 'proposed route, not a confirmed test' in answers['local_basis'].casefold()
    assert 'have not personally influenced' in answers['influence_evidence'].casefold()
    assert not persona['actual_participation'] and not persona['actual_contributions']
    assert 'target_score' not in json.dumps(row).casefold()
