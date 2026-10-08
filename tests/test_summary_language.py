"""Citizen wording must remain a presentation of the existing mapped positions."""
from copy import deepcopy
from types import SimpleNamespace

from iam_sra.reporting import ASPECT_LABELS, citizen_summary
from iam_sra.settings import CONCERNS


def test_all_registered_aspects_have_citizen_labels():
    assert {facet for concern in CONCERNS.values() for facet in concern['facets']} <= ASPECT_LABELS.keys()


def test_supported_information_and_trust_use_natural_wording_without_remapping():
    facts={facet:SimpleNamespace(facet=facet, position='supported')
           for facet in ['awareness','institutional_trust','acoustic_impact']}
    session=SimpleNamespace(
        draft=SimpleNamespace(
            current_route_stance=SimpleNamespace(interpretation='uncertain'),
            medical_public_benefit_support=SimpleNamespace(interpretation='unassessed')),
        original_facets=facts, joint=None, final=None, conditional=None)
    before=deepcopy(session)
    lines=citizen_summary(session)['lines']
    assert 'You consider the public information about the proposal adequate.' in lines
    assert 'You express trust in the institutions responsible for the proposal.' in lines
    assert 'You find noise acceptable in the original proposal.' in lines
    assert not any('medical purpose' in line for line in lines)
    assert session==before
