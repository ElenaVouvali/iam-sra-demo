"""Assemble independently reviewed facet evidence into concern summaries."""
from typing import Literal
from pydantic import Field, model_validator
from .schemas import Strict, MappingAssessment, MappingConcern, Dimension, Awareness
from .updates import FacetMeaning
from .settings import CONCERNS, SCENARIO


class Entry(Strict):
    position: Literal['supported', 'opposed', 'mixed', 'uncertain']
    evidence_ids: list[str] = Field(min_length=1, max_length=3)
    condition_ids: list[str] = Field(max_length=3)
    conditional_willingness: Literal['willing', 'not_willing', 'uncertain', 'not_stated']
    rationale: str = Field(max_length=200)

    @model_validator(mode='after')
    def coherent_conditions(self):
        if self.condition_ids and self.conditional_willingness=='not_stated':
            raise ValueError('Conditions require explicit willingness interpretation; ordinary support is not a condition.')
        return self


def assemble(records, route):
    facets = []
    concerns = []
    for cid, definition in CONCERNS.items():
        entries = [(facet, records.get(cid + ':' + facet)) for facet in definition['facets']]
        entries = [(facet, entry) for facet, entry in entries if entry is not None]
        if not entries:
            continue
        positions = {e.position for _, e in entries}
        willingness = {e.conditional_willingness for _, e in entries}
        concerns.append(MappingConcern(concern_id=cid, status='mapped',
            position=next(iter(positions)) if len(positions)==1 else 'mixed',
            facets=[f for f, _ in entries],
            excerpts=list(dict.fromkeys(r for _, e in entries for r in e.evidence_ids))[:3],
            conditions=list(dict.fromkeys(r for _, e in entries for r in e.condition_ids))[:3],
            conditional_willingness=next(iter(willingness)) if len(willingness)==1 else 'uncertain',
            rationale='; '.join(e.rationale for _, e in entries)[:400], mapping_note='distinct_shared_evidence'))
        facets.extend(FacetMeaning(concern_id=cid, facet=f, position=e.position,
            evidence_ids=e.evidence_ids, condition_ids=e.condition_ids,
            applicability_explicit=True, rationale=e.rationale,
            conditional_willingness=e.conditional_willingness) for f, e in entries)
    medical = records.get('welfare_equity:medical_public_benefit')
    benefit = Dimension(interpretation=medical.position, excerpts=medical.evidence_ids,
        rationale=medical.rationale) if medical else Dimension(interpretation='unassessed', excerpts=[], rationale='Not expressed.')
    return MappingAssessment(scenario_id=SCENARIO['id'], concerns=concerns,
        awareness_understanding=Awareness(interpretation='unassessed', excerpts=[], rationale='Not assessed by facet extraction.'),
        current_route_stance=route, medical_public_benefit_support=benefit, acceptance_conditions=[]), facets
