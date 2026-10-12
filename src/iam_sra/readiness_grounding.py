"""Source-grounded semantic claims; no numerical or acceptance-based readiness."""
from typing import Literal
import json
from pydantic import Field
from .schemas import Strict, ConcernID
from .readiness import EvidenceExtraction, ProposalView, ReadinessRecord
from .assessment import AssessmentError
from .settings import CONCERNS

ClaimKind = Literal[
    'explained_impact', 'recognition_only', 'information_need', 'information_none',
    'participation_actual', 'participation_none', 'participation_intention',
    'influence_reported', 'influence_unknown', 'influence_none',
    'opportunity_available', 'opportunity_none', 'opportunity_barrier',
    'understanding_unclear', 'information_unclear', 'participation_unclear',
    'opportunity_unclear', 'proposal_stance', 'medical_support',
    'concern', 'condition', 'policy_preference', 'unsupported']


class SourceClaim(Strict):
    kind: ClaimKind
    evidence_id: str
    quotation: str
    interpretation: str = Field(min_length=1, max_length=260)
    claim_subject: str
    time_scope: str


class SourceExtraction(Strict):
    interaction: Literal['substantive', 'confused', 'declined', 'already_answered']
    claims: list[SourceClaim] = Field(max_length=20)


class ClaimReview(Strict):
    candidate: int
    meaning_supported: bool
    evidence_type: ClaimKind
    position: Literal['supported', 'opposed', 'mixed', 'uncertain', 'not_stated']
    experience_domain: Literal['IAM_specific', 'transferable_other_domain', 'not_established']
    topic_ids: list[ConcernID] = Field(max_length=4)
    facet_ids: list[str] = Field(max_length=4)
    reason: str


class SourceReview(Strict):
    decisions: list[ClaimReview] = Field(max_length=20)


def validate_source(raw, evidence):
    result = SourceExtraction.model_validate_json(raw)
    limits = {'concern': 6, 'condition': 6, 'policy_preference': 3}
    for kind, limit in limits.items():
        if sum(c.kind == kind for c in result.claims) > limit:
            raise AssessmentError(f'Combine overlapping {kind} claims into at most {limit} grounded findings.', code='schema')
    if sum(c.kind in RECORD_TYPES for c in result.claims) > 10:
        raise AssessmentError('Combine overlapping readiness claims into at most 10 grounded findings.', code='schema')
    for claim in result.claims:
        if claim.evidence_id not in evidence:
            raise AssessmentError('A claim cites an unavailable passage.', code='evidence')
        quote = ' '.join(claim.quotation.split())
        if not quote or quote not in ' '.join(evidence[claim.evidence_id].text.split()):
            raise AssessmentError('A claim quotation must occur in its cited citizen passage.', code='evidence')
        passage = ' '.join(evidence[claim.evidence_id].text.split()).casefold()
        if any(' '.join(scope.split()).casefold() not in passage for scope in [claim.claim_subject, claim.time_scope] if scope):
            raise AssessmentError('Activity and time scope must be quoted from the citizen passage or left empty.', code='evidence')
    if result.interaction != 'substantive' and result.claims:
        raise AssessmentError('Interview-only confusion or refusal cannot generate semantic claims.', code='schema')
    return result


def validate_source_selection(raw, evidence):
    """Retrieve quotations by ID instead of requiring the model to copy prose.

    Existing explicit quotations are still validated, never silently repaired.
    The live wire schema omits quotation; the internal audit retains source text.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssessmentError('Source selection must be valid JSON.', code='schema') from exc
    if isinstance(data, dict) and isinstance(data.get('claims'), list):
        for claim in data['claims']:
            if isinstance(claim, dict):
                claim.setdefault('claim_subject', '')
                claim.setdefault('time_scope', '')
            if isinstance(claim, dict) and 'quotation' not in claim:
                eid = claim.get('evidence_id')
                if not isinstance(eid, str) or eid not in evidence:
                    raise AssessmentError('A claim must select one of the supplied passage IDs.', code='evidence')
                claim['quotation'] = evidence[eid].text
    return validate_source(json.dumps(data, ensure_ascii=False), evidence)


# Kind assigns criterion and status, so the model cannot quietly relabel support
# for a proposal as an action and pass a syntactic coherence check.
RECORD_TYPES = {
    'explained_impact': ('understanding', 'understanding', 'supported'),
    'information_need': ('information', 'information_need', 'supported'),
    'information_none': ('information', 'information_need', 'explicit_absence'),
    'participation_actual': ('participation', 'action', 'supported'),
    'participation_none': ('participation', 'action', 'explicit_absence'),
    'participation_intention': ('participation', 'intention', 'supported'),
    'influence_reported': ('influence', 'influence', 'supported'),
    'influence_unknown': ('influence', 'influence', 'unclear'),
    'influence_none': ('influence', 'influence', 'explicit_absence'),
    'opportunity_available': ('opportunity', 'opportunity', 'supported'),
    'opportunity_none': ('opportunity', 'opportunity', 'explicit_absence'),
    'opportunity_barrier': ('opportunity', 'participation_barrier', 'opportunity_barrier'),
    **{cid + '_unclear': (cid, {'understanding':'understanding', 'information':'information_need',
        'participation':'action', 'opportunity':'opportunity'}[cid], 'unclear')
        for cid in ['understanding', 'information', 'participation', 'opportunity']}}


def assemble_reviewed(source, review, elicitation, context, version):
    """Keep only independently classified claims; audit rejected claims upstream."""
    if sorted(d.candidate for d in review.decisions) != list(range(len(source.claims))):
        raise AssessmentError('Grounding review must check each claim once.', code='schema')
    view = ProposalView(stance='not_stated', evidence_ids=[], concerns=[], conditions=[], topic_ids=[], policy_preferences=[])
    records = []
    for decision in review.decisions:
        if not set(decision.facet_ids) <= {f for topic in decision.topic_ids for f in CONCERNS[topic]['facets']}:
            raise AssessmentError('Reviewed facets must belong to the reviewed topics.', code='evidence')
        claim = source.claims[decision.candidate]
        if not decision.meaning_supported or decision.evidence_type != claim.kind or claim.kind in {'recognition_only', 'unsupported'}:
            continue
        if claim.kind in RECORD_TYPES:
            cid, kind, status = RECORD_TYPES[claim.kind]
            records.append(ReadinessRecord(criterion_id=cid, kind=kind, status=status,
                evidence_ids=[claim.evidence_id], interpretation=claim.interpretation,
                topic_ids=decision.topic_ids,
                temporality='hypothetical_intention' if kind == 'intention' else 'past_current'
                    if kind in {'action', 'influence'} else 'not_applicable',
                experience_domain=decision.experience_domain, proposal_context=context,
                elicitation_context=elicitation, evidence_basis='answer_demonstrated_reasoning'
                    if claim.kind == 'explained_impact' else 'self_report',
                claim_subject=claim.claim_subject, time_scope=claim.time_scope, version=version))
        else:
            if claim.kind == 'proposal_stance': view.stance = decision.position
            elif claim.kind == 'medical_support':
                if decision.position == 'mixed': continue
                view.medical_public_benefit_support = decision.position
            else:
                field = {'concern':'concerns', 'condition':'conditions', 'policy_preference':'policy_preferences'}[claim.kind]
                values = getattr(view, field)
                if claim.interpretation not in values: values.append(claim.interpretation)
            if claim.evidence_id not in view.evidence_ids: view.evidence_ids.append(claim.evidence_id)
            # Only evidenced concerns nominate optional mitigation topics.
            if claim.kind == 'concern':
                view.topic_ids = list(dict.fromkeys(view.topic_ids + decision.topic_ids))
                view.concern_facets = list(dict.fromkeys(view.concern_facets + decision.facet_ids))
    # Keep all per-claim citations in the audit; this public view has a compact
    # citation allowance. Do not lose independently supported semantic findings.
    view.evidence_ids = view.evidence_ids[:3]
    return EvidenceExtraction(acceptance=view, records=records)
