"""Current numeric score schema and compatibility checks for archived ordinal audits."""
from typing import Literal
from pydantic import Field
from .schemas import Strict
from .settings import config

class AnchorFacts(Strict):
    acceptance: Literal['rejects','conditional','balanced','cautious','qualified','clear','endorsement','unknown']
    objection: Literal['categorical','strong_personal_boundary','strong_disruption','meaningful_reservation','limited_reservation','none','unknown']
    further_requirement: bool
    evidence_ids: list[str] = Field(min_length=1,max_length=3)
    endorsement_evidence_ids: list[str] = Field(default_factory=list,max_length=3)
    rationale: str = Field(max_length=400)


def decide(facts,position,endorsement_verified=False):
    """No keywords, arithmetic or hidden neutral fallback."""
    a,o=facts.acceptance,facts.objection
    rule=None;reason=facts.rationale
    if a=='unknown':reason='Your position on this aspect needs clarification.'
    elif position=='opposed' and a in {'cautious','qualified','clear','endorsement'} or position=='supported' and a in {'rejects','conditional'}:
        reason='The scoring description conflicts with your confirmed position; clarify this aspect.'
    elif a=='conditional' and not facts.further_requirement:
        reason='Conditional willingness needs the relevant further requirement; clarify this aspect.'
    elif a in {'rejects','conditional'}:
        if a=='rejects' and o=='categorical':rule='categorical_refusal'
        elif o=='strong_personal_boundary':rule='strong_personal_boundary'
        elif o=='strong_disruption':rule='strong_disruption'
        elif o in {'meaningful_reservation','limited_reservation'} and facts.further_requirement:rule='further_change_required'
        else:reason='What would need to change, or whether you refuse despite the stated changes, is unclear.'
    elif a in {'balanced','cautious','qualified'} and o in {'categorical','strong_personal_boundary','strong_disruption','unknown'}:
        reason='The acceptance description and objection are inconsistent or incomplete; clarification is needed.'
    elif a=='balanced':rule='balanced_position'
    elif a=='cautious':rule='cautious_acceptance'
    elif a=='qualified':rule='qualified_acceptance'
    elif a in {'clear','endorsement'}:
        if o not in {'none','limited_reservation'}:reason='Acceptance and the remaining objection conflict; clarification is needed.'
        elif facts.further_requirement or o=='limited_reservation':rule='qualified_acceptance'
        elif a=='endorsement' and endorsement_verified and facts.endorsement_evidence_ids:rule='explicit_unqualified_endorsement'
        else:rule='clear_acceptance'
    policy=config('ordinal')
    return {'score':policy['rules'][rule] if rule else None,'anchor_rule_id':rule,'scoring_policy_version':policy['version'],
        'construct':policy['construct'],'descriptive_facts':facts.model_dump(),'evidence_ids':facts.evidence_ids,
        'highest_criterion_verified':bool(rule=='explicit_unqualified_endorsement'),
        'origin':'python_anchor_predicate','reuse_decision':'not_reused','reason':reason}


class NumericScore(Strict):
    """The LLM supplies the number; Python checks shape and evidence only."""
    score: int | None = Field(ge=1,le=9)
    evidence_ids: list[str] = Field(min_length=1,max_length=3)
    endorsement_evidence_ids: list[str] = Field(default_factory=list,max_length=3)
    rationale: str = Field(min_length=1,max_length=400)
