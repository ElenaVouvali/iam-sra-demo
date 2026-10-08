"""Structural regressions; these tests do not measure live model accuracy."""
from iam_sra.facet_mapping import Entry, assemble
from iam_sra.schemas import Dimension
from iam_sra.interpretation import reconcile_original


def entry(position, ref, condition=None):
    return Entry(position=position,evidence_ids=[ref],condition_ids=[condition] if condition else [],
        conditional_willingness='willing' if condition else 'not_stated',rationale='Independent citizen position.')


def route():
    return Dimension(interpretation='unassessed',excerpts=[],rationale='No overall stance.')


def test_opposing_safety_and_accepted_privacy_keep_separate_evidence():
    records={'perceived_safety_privacy:perceived_safety':entry('opposed','O.p001','O.p002'),
        'perceived_safety_privacy:personal_privacy':entry('supported','O.p003'),
        'welfare_equity:medical_public_benefit':entry('supported','O.p004'),
        'welfare_equity:distributive_equity':entry('opposed','O.p005','O.p006')}
    meaning,facets=assemble(records,route())
    result,ledger=reconcile_original(None,meaning,{},reviewed_facets=facets)
    assert len(result.concerns)==2
    assert ledger['perceived_safety_privacy:personal_privacy'].position=='supported'
    assert ledger['perceived_safety_privacy:perceived_safety'].condition_ids==['O.p002']
    assert ledger['welfare_equity:medical_public_benefit'].evidence_ids==['O.p004']
    assert result.medical_public_benefit_support.interpretation=='supported'


def test_explicit_unknown_remains_required_alongside_accepted_energy():
    meaning,facets=assemble({'energy_emissions:energy_demand':entry('supported','O.p001'),
        'energy_emissions:emissions':entry('uncertain','O.p002')},route())
    result,ledger=reconcile_original(None,meaning,{},reviewed_facets=facets)
    assert set(result.concerns[0].facets)=={'energy_demand','emissions'}
    assert ledger['energy_emissions:emissions'].position=='uncertain'
