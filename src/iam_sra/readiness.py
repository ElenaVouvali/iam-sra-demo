"""Draft citizen evidence instrument. No level assignment or numerical calculation."""
from copy import deepcopy
from typing import Literal
from pydantic import Field, model_validator
from .schemas import Strict, ConcernID
from .assessment import AssessmentError
from .settings import config, CONCERNS

DEFAULT_MODE = 'acceptance_and_readiness_evidence'
HISTORICAL_MODE = 'legacy_fn_acceptance_demo'
Criterion = Literal['understanding', 'information', 'participation', 'influence', 'opportunity']


def mode_policy(mode=DEFAULT_MODE):
    return deepcopy(config('assessment_modes')['modes'][mode])


class ReadinessRecord(Strict):
    criterion_id: Criterion
    topic_ids: list[ConcernID] = Field(default_factory=list, max_length=4)
    evidence_ids: list[str] = Field(min_length=1, max_length=3)
    interpretation: str = Field(min_length=1, max_length=260)
    kind: Literal['understanding', 'information_need', 'action', 'influence', 'opportunity', 'participation_barrier', 'intention']
    status: Literal['supported', 'explicit_absence', 'unclear', 'conflicting', 'opportunity_barrier']
    temporality: Literal['past_current', 'hypothetical_intention', 'not_applicable']
    experience_domain: Literal['IAM_specific', 'transferable_other_domain', 'not_established']
    proposal_context: Literal['original', 'hypothetical_modification']
    elicitation_context: Literal['initial_answer', 'follow_up', 'scenario_informed', 'after_information_exposure']
    evidence_basis: Literal['self_report', 'answer_demonstrated_reasoning', 'separately_reviewed_external_evidence']
    confirmation_status: Literal['pending', 'confirmed'] = 'pending'
    source: str = 'citizen_answer'
    version: int = 1
    unresolved_contradictions: list[str] = Field(default_factory=list, max_length=3)
    claim_subject: str = ''
    time_scope: str = ''

    @model_validator(mode='after')
    def coherent(self):
        if self.kind == 'intention' and self.temporality != 'hypothetical_intention':
            raise ValueError('Intention is hypothetical, not actual participation.')
        if self.kind in {'action', 'influence'} and self.status == 'supported' and self.temporality != 'past_current':
            raise ValueError('Actual action/influence needs past or current experience.')
        if self.status == 'opportunity_barrier' and self.kind not in {'opportunity', 'participation_barrier'}:
            raise ValueError('Opportunity barriers are separate from capability.')
        if self.criterion_id == 'influence' and self.kind != 'influence':
            raise ValueError('Influence needs its own evidence, not support or willingness.')
        return self


class ProposalView(Strict):
    stance: Literal['supported', 'opposed', 'mixed', 'uncertain', 'not_stated']
    medical_public_benefit_support: Literal['supported', 'opposed', 'uncertain', 'not_stated'] = 'not_stated'
    evidence_ids: list[str] = Field(max_length=3)
    concerns: list[str] = Field(max_length=6)
    conditions: list[str] = Field(max_length=6)
    topic_ids: list[ConcernID] = Field(max_length=15)
    concern_facets: list[str] = Field(default_factory=list, max_length=30)
    policy_preferences: list[str] = Field(max_length=3)


class EvidenceExtraction(Strict):
    acceptance: ProposalView
    records: list[ReadinessRecord] = Field(max_length=10)


def validate_extraction(raw, evidence, elicitation, context, version):
    import json
    try:
        wire = json.loads(raw) if isinstance(raw, str) else deepcopy(raw)
    except json.JSONDecodeError as exc:
        raise AssessmentError('Readiness response is not valid JSON.', code='schema') from exc
    if not isinstance(wire, dict):
        raise AssessmentError('Readiness response must be an object.', code='schema')
    rows = wire.get('records', [])
    for item in rows if isinstance(rows, list) else []:
        if isinstance(item, dict):
            citations = item.get('evidence_ids')
            if isinstance(citations, dict):
                primary = citations.get('primary')
                additional = citations.get('additional', [])
                if set(citations) != {'primary', 'additional'} or not isinstance(primary, str) or not isinstance(additional, list) or len(additional) > 2 or not all(isinstance(ref, str) for ref in additional):
                    raise AssessmentError('A readiness record needs its primary citizen citation.', code='schema')
                item['evidence_ids'] = list(dict.fromkeys([primary] + additional))
            item.update(proposal_context=context, elicitation_context=elicitation,
                        confirmation_status='pending', source='citizen_answer', version=version)
    result = EvidenceExtraction.model_validate(wire)
    allowed_facets = {f for topic in result.acceptance.topic_ids for f in CONCERNS[topic]['facets']}
    if not set(result.acceptance.concern_facets) <= allowed_facets:
        raise AssessmentError('A concern facet needs its explicitly supported topic.', code='evidence')
    refs = result.acceptance.evidence_ids + [r for item in result.records for r in item.evidence_ids + item.unresolved_contradictions]
    for ref in refs:
        if ref not in evidence or evidence[ref].source in {'question', 'citizen_control', 'application_control'}:
            raise AssessmentError('Evidence extraction cites a missing or non-answer passage.', code='evidence')
    if (result.acceptance.stance != 'not_stated' or result.acceptance.medical_public_benefit_support != 'not_stated' or result.acceptance.concerns or result.acceptance.conditions or result.acceptance.policy_preferences) and not result.acceptance.evidence_ids:
        raise AssessmentError('Proposal findings require citizen evidence.', code='evidence')
    for item in result.records:
        if item.evidence_basis == 'separately_reviewed_external_evidence':
            raise AssessmentError('Citizen testimony cannot establish external verification.', code='evidence')
        item.confirmation_status = 'pending'
        item.elicitation_context = elicitation
        item.proposal_context = context
        item.version = version
        item.source = 'citizen_answer'
    return result


def build_profile(records, asked=(), registry=None):
    """Descriptive coverage, with explicit uncertainty and no ordinal ordering."""
    confirmed = [r.model_dump() if hasattr(r, 'model_dump') else deepcopy(r) for r in records
                 if (r.confirmation_status if hasattr(r, 'confirmation_status') else r['confirmation_status']) == 'confirmed']
    coverage = {}
    for indicator in (registry or config('readiness'))['indicators']:
        cid = indicator['criterion_id']; rows = [r for r in confirmed if r['criterion_id'] == cid]
        states = {r['status'] for r in rows}
        conflict = any(r['unresolved_contradictions'] for r in rows) or 'conflicting' in states
        # Claims of current experience/opportunity and explicit absence coexist as
        # unresolved evidence; never select the more positive assertion by default.
        scopes = {(r['experience_domain'], r['proposal_context'], r['kind'],
                   r.get('claim_subject','').casefold().strip(), r.get('time_scope','').casefold().strip()) for r in rows}
        for scope in scopes:
            # Missing scope is not permission to assume that two statements
            # describe the same activity or period. Intention and action differ.
            if not scope[3] or not scope[4]: continue
            scoped = [r for r in rows if (r['experience_domain'], r['proposal_context'], r['kind'],
                r.get('claim_subject','').casefold().strip(), r.get('time_scope','').casefold().strip()) == scope]
            if {'supported', 'explicit_absence'} <= {r['status'] for r in scoped}: conflict = True
            if any(r['kind'] == 'opportunity' and r['status'] == 'supported' for r in scoped) and any(r['kind'] == 'opportunity' and r['status'] == 'opportunity_barrier' for r in scoped): conflict = True
        if conflict: status = 'conflicting'
        elif 'unclear' in states: status = 'unclear'
        elif 'opportunity_barrier' in states: status = 'opportunity_barrier'
        elif rows and cid == 'participation' and all(r['kind'] == 'intention' for r in rows): status = 'unclear'
        elif rows: status = 'evidence_recorded'
        else: status = 'unsupported' if cid in asked else 'not_asked'
        coverage[cid] = {'status': status, 'asked': cid in asked, 'evidence_ids': list(dict.fromkeys(e for r in rows for e in r['evidence_ids']))}
    topics = {}
    for topic_id in CONCERNS:
        rows = [r for r in confirmed if topic_id in r['topic_ids']]
        criteria = sorted({r['criterion_id'] for r in rows})
        states = {coverage[c]['status'] for c in criteria}
        status = ('conflicting' if 'conflicting' in states else 'unclear' if 'unclear' in states
                  else 'opportunity_barrier' if 'opportunity_barrier' in states
                  else 'evidence_recorded' if rows else 'not_asked')
        topics[topic_id] = {'status': status, 'criterion_ids': criteria,
            'evidence_ids': list(dict.fromkeys(e for r in rows for e in r['evidence_ids'])),
            'asked': False, 'note': 'Questions are cross-cutting; no topic-specific interview or capability is assumed.'}
    return {'records': confirmed, 'criterion_coverage': coverage, 'topic_coverage': topics,
            'numerical_crl': None, 'numerical_srl': None,
            'unavailable_reason': mode_policy()['unavailable_reason']}


def next_question(profile, answers, budget=None, registry=None):
    registry = registry or config('readiness')
    budget = registry['maximum_questions'] if budget is None else budget
    if len(answers) >= budget: return None
    # Cover missing dimensions before spending the small budget on a repeat.
    definitions = sorted(registry['indicators'], key=lambda d: any(a['criterion_id'] == d['criterion_id'] for a in answers))
    for definition in definitions:
        cid = definition['criterion_id']; previous = [a for a in answers if a['criterion_id'] == cid]
        status = profile['criterion_coverage'][cid]['status']
        if status == 'evidence_recorded' or status == 'opportunity_barrier': continue
        # Unsure/skip is a valid endpoint; a clarification never becomes a loop.
        if previous and (previous[-1]['control'] in {'skip', 'unsure', 'decline'} or len(previous) >= 2): continue
        if cid == 'influence':
            participation = [r for r in profile['records'] if r['criterion_id'] == 'participation'
                             and r['kind'] == 'action' and r['status'] == 'supported' and r['temporality'] == 'past_current']
            if not participation: continue
        question = deepcopy(definition)
        clarification = bool(previous)
        question['question_text'] = definition['clarification_text'] if clarification else definition['question_text']
        question['clarification'] = clarification
        question['id'] = definition['question_id'] + ('_clarify' if previous else '')
        return question
    return None


def profile_changes(initial, final):
    a = initial['records'] if initial else []; b = final['records']
    signature = lambda r: (r['criterion_id'], tuple(r['evidence_ids']), r['interpretation'], r['status'])
    old = {signature(r) for r in a}; new = {signature(r) for r in b}
    return {'newly_supported_evidence': [r for r in b if signature(r) not in old and r['status'] == 'supported'],
            'newly_recorded_evidence': [r for r in b if signature(r) not in old],
            'newly_recorded_absence': [r for r in b if signature(r) not in old and r['status'] == 'explicit_absence'],
            'after_information_evidence': [r for r in b if signature(r) not in old and r['elicitation_context'] == 'after_information_exposure'],
            'clarified_or_corrected_interpretations': [r for r in a if signature(r) not in new],
            'unresolved_contradictions': [cid for cid, c in final['criterion_coverage'].items() if c['status'] == 'conflicting'],
            'remaining_gaps': [cid for cid, c in final['criterion_coverage'].items() if c['status'] in {'not_asked', 'unsupported', 'unclear'}],
            'opportunity_barriers': [r for r in b if r['status'] == 'opportunity_barrier'],
            'interpretation': 'Assessment refinement from elicited evidence; no personal improvement or change over time is inferred.'}


def citizen_result(session):
    profile = session.final_readiness or session.current_profile
    return {'acceptance': deepcopy(session.acceptance),
            'readiness': [{'criterion_id': cid, 'status': coverage['status'],
                           'interpretations': list(dict.fromkeys(r['interpretation'] for r in profile['records'] if r['criterion_id'] == cid))[-2:]}
                          for cid, coverage in profile['criterion_coverage'].items()],
            'note': session.numerical_policy['unavailable_reason']}
