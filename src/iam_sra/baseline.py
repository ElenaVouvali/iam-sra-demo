"""Phase-1 evidence only: no scenario, acceptance or level assignment."""
from copy import deepcopy
from typing import Literal
from pydantic import Field, model_validator, field_validator, ValidationError
from .schemas import Strict, ConcernID
from .assessment import AssessmentError
from .evidence import original_quote

Dimension = Literal['concept','delivery','understanding','information','exposure','participation','influence','opportunity']
Kind = Literal['concept_explanation','use_knowledge','explained_impact','claim_without_detail','recognition','information_need','learning_exposure',
               'contribution','influence','opportunity','barrier','intention','absence','unknown']
KINDS = {'concept':{'concept_explanation','absence','unknown'},
         'delivery':{'use_knowledge','absence','unknown'},
         'understanding':{'explained_impact','claim_without_detail','recognition','absence','unknown'},
         'information':{'information_need','absence','unknown'},
         'exposure':{'learning_exposure','absence','unknown'},
         'participation':{'contribution','intention','absence','unknown'},
         'influence':{'influence','absence','unknown'},
         'opportunity':{'opportunity','barrier','intention','absence','unknown'}}

class BaselineClaim(Strict):
    evidence_id: str
    dimension: Dimension
    kind: Kind
    interpretation: str = Field(min_length=1,max_length=240)
    # Exact answer span. Required by the 2.3 contract; optional only so frozen
    # 2.0–2.2 exports and validators remain readable.
    span_quote: str = Field(default='',max_length=240)
    topic_ids: list[ConcernID] = Field(default_factory=list,max_length=3)
    subject: Literal['respondent','organisation','other','unknown']
    temporality: Literal['actual','intention','not_applicable','unknown']
    domain: Literal['IAM','transferable','unknown','not_applicable']
    activity_quote: str = Field(default='',max_length=160)
    time_quote: str = Field(default='',max_length=100)
    ambiguities: list[Literal['subject','activity','time','meaning','contradiction']] = Field(default_factory=list,max_length=3)
    outcome_relation: Literal['unknown','reported_link','sequence_only'] = 'unknown'

    @model_validator(mode='after')
    def compatible(self):
        if self.kind not in KINDS[self.dimension]: raise ValueError('Kind outside dimension')
        if self.kind in {'learning_exposure','contribution','influence'} and self.temporality != 'actual':
            raise ValueError('Actual experience must be past/current')
        if self.kind == 'intention' and self.temporality != 'intention':
            raise ValueError('Willingness must remain hypothetical')
        return self

class BaselineExtraction(Strict):
    interaction: Literal['substantive','unsure','declined','confused','already_answered','off_topic']
    claims: list[BaselineClaim] = Field(max_length=6)

class BaselineDecision(Strict):
    candidate: int
    supported: bool
    dimension: Dimension
    kind: Kind
    topic_ids: list[ConcernID] = Field(default_factory=list,max_length=3)
    reason: str = Field(default='',max_length=160)
    interpretation: str | None = Field(default=None,min_length=1,max_length=240)
    ambiguities: list[Literal['subject','activity','time','meaning','contradiction']] | None = Field(default=None,max_length=3)
    outcome_relation: Literal['unknown','reported_link','sequence_only'] | None = None

    subject: Literal['respondent','organisation','other','unknown'] | None = None
    temporality: Literal['actual','intention','not_applicable','unknown'] | None = None
    domain: Literal['IAM','transferable','unknown','not_applicable'] | None = None
    span_quote: str | None = Field(default=None,min_length=1,max_length=240)

class BaselineReview(Strict):
    decisions: list[BaselineDecision] = Field(max_length=6)


# The live 2.3 model contract uses one tagged value for the three labels that
# previously caused cross-field failures (dimension, kind and temporality).
# The server maps this finite vocabulary to the established internal record.
CLAIM_TYPES = (
    'concept_explanation','concept_absence','concept_unknown',
    'delivery_use_knowledge','delivery_absence','delivery_unknown',
    'understanding_explained_impact','understanding_claim_without_detail','understanding_recognition','understanding_absence','understanding_unknown',
    'information_need','information_absence','information_unknown',
    'exposure_learning','exposure_absence','exposure_unknown',
    'participation_contribution','participation_intention','participation_absence','participation_unknown',
    'influence_reported','influence_absence','influence_unknown',
    'opportunity_access','opportunity_barrier','opportunity_intention','opportunity_absence','opportunity_unknown',
)
CLAIM_TYPE_MAP = {
    'concept_explanation':('concept','concept_explanation','not_applicable'), 'concept_absence':('concept','absence','not_applicable'), 'concept_unknown':('concept','unknown','unknown'),
    'delivery_use_knowledge':('delivery','use_knowledge','not_applicable'), 'delivery_absence':('delivery','absence','not_applicable'), 'delivery_unknown':('delivery','unknown','unknown'),
    'understanding_explained_impact':('understanding','explained_impact','not_applicable'), 'understanding_claim_without_detail':('understanding','claim_without_detail','not_applicable'), 'understanding_recognition':('understanding','recognition','not_applicable'), 'understanding_absence':('understanding','absence','not_applicable'), 'understanding_unknown':('understanding','unknown','unknown'),
    'information_need':('information','information_need','not_applicable'), 'information_absence':('information','absence','not_applicable'), 'information_unknown':('information','unknown','unknown'),
    'exposure_learning':('exposure','learning_exposure','actual'), 'exposure_absence':('exposure','absence','not_applicable'), 'exposure_unknown':('exposure','unknown','unknown'),
    'participation_contribution':('participation','contribution','actual'), 'participation_intention':('participation','intention','intention'), 'participation_absence':('participation','absence','not_applicable'), 'participation_unknown':('participation','unknown','unknown'),
    'influence_reported':('influence','influence','actual'), 'influence_absence':('influence','absence','not_applicable'), 'influence_unknown':('influence','unknown','unknown'),
    'opportunity_access':('opportunity','opportunity','not_applicable'), 'opportunity_barrier':('opportunity','barrier','not_applicable'), 'opportunity_intention':('opportunity','intention','intention'), 'opportunity_absence':('opportunity','absence','not_applicable'), 'opportunity_unknown':('opportunity','unknown','unknown'),
}

class CanonicalClaim(Strict):
    evidence_id: str
    claim_type: str
    span_quote: str = Field(min_length=1,max_length=240)
    interpretation: str = Field(min_length=1,max_length=240)
    topic_ids: list[ConcernID] = Field(default_factory=list,max_length=3)
    subject: Literal['respondent','organisation','other','unknown']
    domain: Literal['IAM','transferable','unknown','not_applicable']
    activity_quote: str = Field(default='',max_length=160)
    time_quote: str = Field(default='',max_length=100)
    ambiguities: list[Literal['subject','activity','time','meaning','contradiction']] = Field(default_factory=list,max_length=3)
    outcome_relation: Literal['unknown','reported_link','sequence_only'] = 'unknown'

    @field_validator('claim_type')
    @classmethod
    def known_claim_type(cls,value):
        if value not in CLAIM_TYPE_MAP: raise ValueError('Unknown canonical claim type.')
        return value

class CanonicalExtraction(Strict):
    interaction: Literal['substantive','unsure','declined','confused','already_answered','off_topic']
    claims: list[CanonicalClaim] = Field(max_length=6)

class CanonicalDecision(Strict):
    candidate: int
    supported: bool
    claim_type: str
    topic_ids: list[ConcernID] = Field(default_factory=list,max_length=3)
    reason: str = Field(default='',max_length=100)
    span_quote: str | None = Field(default=None,min_length=1,max_length=240)
    interpretation: str | None = Field(default=None,min_length=1,max_length=240)
    ambiguities: list[Literal['subject','activity','time','meaning','contradiction']] | None = Field(default=None,max_length=3)
    outcome_relation: Literal['unknown','reported_link','sequence_only'] | None = None
    subject: Literal['respondent','organisation','other','unknown'] | None = None
    domain: Literal['IAM','transferable','unknown','not_applicable'] | None = None

    @field_validator('claim_type')
    @classmethod
    def known_claim_type(cls,value):
        if value not in CLAIM_TYPE_MAP: raise ValueError('Unknown canonical claim type.')
        return value

class CanonicalReview(Strict):
    decisions: list[CanonicalDecision] = Field(max_length=6)
    additional_claims: list[CanonicalClaim] = Field(default_factory=list,max_length=3)


def canonical_claim(value, evidence):
    c=CanonicalClaim.model_validate(value) if not isinstance(value,CanonicalClaim) else value
    if c.evidence_id not in evidence: raise AssessmentError('Unknown baseline passage ID.',code='evidence')
    for quote in (c.span_quote,c.activity_quote,c.time_quote):
        if quote and original_quote(evidence[c.evidence_id],quote) is None:
            raise AssessmentError('Claim support must be an exact span from the cited answer passage.',code='evidence')
    dimension,kind,temporality=CLAIM_TYPE_MAP[c.claim_type]
    return BaselineClaim(evidence_id=c.evidence_id,dimension=dimension,kind=kind,interpretation=c.interpretation,
        span_quote=c.span_quote,topic_ids=c.topic_ids,subject=c.subject,temporality=temporality,domain=c.domain,
        activity_quote=c.activity_quote,time_quote=c.time_quote,ambiguities=c.ambiguities,outcome_relation=c.outcome_relation)


def validate_canonical_source(raw, evidence):
    value=CanonicalExtraction.model_validate_json(raw) if isinstance(raw,str) else CanonicalExtraction.model_validate(raw)
    claims=[canonical_claim(c,evidence) for c in value.claims]
    return BaselineExtraction(interaction=value.interaction,claims=claims)


def reviewed_canonical(source, review, evidence):
    if sorted(d.candidate for d in review.decisions) != list(range(len(source.claims))):
        raise AssessmentError('Every baseline claim requires one review.',code='evidence')
    decisions=[]
    for d in review.decisions:
        dim,kind,temp=CLAIM_TYPE_MAP[d.claim_type]
        old=source.claims[d.candidate]
        if d.span_quote and original_quote(evidence[old.evidence_id],d.span_quote) is None:
            raise AssessmentError('Reviewer support must be an exact span from the cited answer passage.',code='evidence')
        old_is_actual=old.temporality=='actual';new_is_actual=temp=='actual'
        old_is_intention=old.temporality=='intention';new_is_intention=temp=='intention'
        if d.supported and ((old_is_intention and new_is_actual) or (old_is_actual and new_is_intention)):
            if not d.span_quote or d.span_quote.strip().casefold()==old.span_quote.strip().casefold():
                raise AssessmentError('A reviewed change between intention and actual activity needs a distinct supporting answer span.',code='evidence')
        decisions.append(BaselineDecision(candidate=d.candidate,supported=d.supported,dimension=dim,kind=kind,
            topic_ids=d.topic_ids,reason=d.reason,interpretation=d.interpretation,ambiguities=d.ambiguities,
            outcome_relation=d.outcome_relation,subject=d.subject,temporality=temp,domain=d.domain,span_quote=d.span_quote))
    accepted=reviewed(source,BaselineReview(decisions=decisions))
    # Invalid reclassifications raise in reviewed(); they cannot disappear
    # silently from an otherwise complete interpretation.
    additions=[]
    for c in review.additional_claims:
        additions.append(canonical_claim(c,evidence))
    claims=list(accepted.claims)+additions
    unique={}
    for c in claims:
        key=(c.evidence_id,c.dimension,c.kind,c.subject,c.temporality,c.domain,c.span_quote.casefold())
        unique.setdefault(key,c)
    return BaselineExtraction(interaction='substantive' if unique else source.interaction,claims=list(unique.values()))


def validate_source(raw, evidence):
    value = BaselineExtraction.model_validate_json(raw) if isinstance(raw,str) else BaselineExtraction.model_validate(raw)
    for c in value.claims:
        if c.evidence_id not in evidence: raise AssessmentError('Unknown baseline passage ID.',code='evidence')
        for scope in (c.span_quote,c.activity_quote,c.time_quote):
            if scope and original_quote(evidence[c.evidence_id],scope) is None:
                raise AssessmentError('Claim support and activity/time scope must use exact words from the cited answer or be empty.',code='evidence')
    return value


def reviewed(source, review):
    if sorted(d.candidate for d in review.decisions) != list(range(len(source.claims))):
        raise AssessmentError('Every baseline claim requires one review.',code='evidence')
    accepted=[]
    for d in review.decisions:
        c=source.claims[d.candidate]
        if not d.supported: continue
        same = d.dimension == c.dimension and d.kind == c.kind and all(getattr(d,f) is None or getattr(d,f)==getattr(c,f) for f in ('subject','temporality','domain'))
        # A reviewer may correct classification only with an explicit reviewed meaning.
        if not same and not d.interpretation: continue
        data=c.model_dump()
        data.update(dimension=d.dimension,kind=d.kind,
                    interpretation=d.interpretation or c.interpretation,
                    topic_ids=sorted(set(c.topic_ids)&set(d.topic_ids)))
        if d.span_quote is not None:data['span_quote']=d.span_quote
        for field in ('subject','temporality','domain'):
            if getattr(d,field) is not None:data[field]=getattr(d,field)
        if d.ambiguities is not None:data['ambiguities']=d.ambiguities
        if d.outcome_relation is not None:data['outcome_relation']=d.outcome_relation
        try: accepted.append(BaselineClaim.model_validate(data))
        except ValidationError:
            raise AssessmentError('A reviewed interpretation remained inconsistent. Correct it, retry, skip or finish.',code='evidence') from None

    unique={}
    for c in accepted:
        key=(c.evidence_id,c.dimension,c.kind,c.subject,c.temporality,c.domain,c.span_quote.casefold())
        unique.setdefault(key,c)
    return BaselineExtraction(interaction='substantive' if unique else source.interaction,claims=list(unique.values()))


def profile(events, instrument, respondent=None):
    claims=[deepcopy(c) for e in events if e['active'] and e['confirmed'] for c in e['claims']]
    coverage={}
    for dim in instrument['dimensions']:
        rows=[c for c in claims if c['dimension']==dim]
        asked=any(e['active'] and dim in e['question'].get('covers',[e['question']['dimension']]) for e in events)
        controls=[('unsure' if e.get('interaction')=='unsure' else 'decline' if e.get('interaction')=='declined' else e['control']) for e in events if e['active'] and dim in e['question'].get('covers',[e['question']['dimension']])]
        pos=[c for c in rows if c['status']=='supported'];neg=[c for c in rows if c['status']=='explicit_absence']
        # Opposite reports are not a proven contradiction unless scopes are known.
        scope_unclear=any(not (a['domain'] in {'IAM','transferable'} and b['domain'] in {'IAM','transferable'} and a['domain']!=b['domain']) for a in pos for b in neg)
        status=('scope_unclear' if scope_unclear else 'evidence_recorded' if pos else
                'explicit_absence' if neg else 'unknown' if any(c['status']=='unknown' for c in rows) or 'unsure' in controls else
                'declined' if 'decline' in controls else 'skipped' if 'skip' in controls else 'unclear' if asked else 'not_asked')
        coverage[dim]={'status':status,'asked':asked,'evidence_ids':[c['evidence_id'] for c in rows]}
    result={'claims':claims,'coverage':coverage,'unresolved_scope':[d for d,v in coverage.items() if v['status']=='scope_unclear']}
    if 'routing' in instrument:
        from .baseline_routing import enrich_profile
        enrich_profile(result,events,instrument,respondent)
    return result


def _legacy_select_question(events, instrument, respondent):
    active=[e for e in events if e['active'] and e['confirmed']]
    current=profile(active,instrument);claims=current['claims']
    done={e['question']['id'] for e in active}
    for q in instrument['core_questions']:
        if q['id'] in done: continue
        # Later core items are omitted only when the needed evidence is already clear.
        covered={d for d in q['covers'] if any(c['dimension']==d for c in claims)}
        actual_contribution=any(c['kind']=='contribution' and c['temporality']=='actual' for c in claims)
        exposure_rows=[c for c in claims if c['dimension']=='exposure']
        absent_exposure=exposure_rows and all(c['status'] in {'explicit_absence','unknown'} for c in exposure_rows)
        supplied=q['id'] in {'experience','needs'} and (covered==set(q['covers']) or q['id']=='experience' and (actual_contribution or absent_exposure))
        if supplied:continue
        result=deepcopy(q);result['selection_reason']='Core item; relevant evidence not yet clearly supplied.';result['is_probe']=False
        result['question_text']=q['organisation_text'] if respondent['perspective']=='organisation' else q['text']
        if q['id']=='experience' and 'exposure' in covered:
            result['question_text']=q['when_exposure_already_reported']
            result['selection_reason']='Earlier exposure reported; contribution remains unestablished.'
        if q['id']=='needs' and len(covered)==1:
            result['question_text']=q['when_information_already_reported' if 'information' in covered else 'when_opportunity_already_reported']
            result['selection_reason']='Ask only the remaining needs/opportunities dimension.'
        return result
    if sum(e['question']['is_probe'] for e in active)>=instrument['maximum_adaptive_probes']:return None
    suppressed={d for e in active if e['control'] in {'skip','unsure','decline'} or e.get('interaction') in {'unsure','declined','confused','already_answered'} for d in e['question'].get('covers',[e['question']['dimension']])}
    def actual(kind):return [c for c in claims if c['kind']==kind and c['status']=='supported' and c['temporality']=='actual']
    conditions={
      'positive_and_absence_scope_unresolved':bool(current['unresolved_scope']),
      'understanding_claim_without_reason':any(c['kind']=='claim_without_detail' for c in claims) and not any(c['kind']=='explained_impact' for c in claims),
      'actual_exposure_without_contribution_evidence':bool(actual('learning_exposure')) and not any(c['dimension']=='participation' and c['kind']!='intention' for c in claims),
      'actual_experience_unknown_domain':any(c['domain']=='unknown' for c in actual('learning_exposure')+actual('contribution')),
      'actual_contribution_without_outcome':bool(actual('contribution')) and not any(c['dimension']=='influence' for c in claims)}
    for q in sorted(instrument['probes'],key=lambda q:q['priority']):
        if q['id'] in done or q['dimension'] in suppressed or not conditions[q['eligibility']]:continue
        result=deepcopy(q)
        if q['id']=='scope':
            dims=[d for d in current['unresolved_scope'] if d not in suppressed]
            if not dims:continue
            result['dimension']=dims[0]
        result.update(question_text=q['text'],is_probe=True,covers=[result['dimension']],selection_reason=q['eligibility'])
        return result
    return None


def selection_plan(events, instrument, respondent):
    """Pure deterministic routing, including auditable omissions; no score or stance."""
    if 'routing' in instrument:
        from .baseline_routing import adaptive_plan
        return adaptive_plan(events,instrument,respondent)
    if 'maximum_questions' not in instrument:
        return _legacy_select_question(events,instrument,respondent), []
    active=[e for e in events if e['active'] and e['confirmed']]
    done={e['question']['id'] for e in active}
    claims=profile(active,instrument)['claims']
    omitted=[];available=[]
    for q in instrument['core_questions']:
        if q['id'] in done: continue
        covered={d for d in q['covers'] if any(c['dimension']==d for c in claims)}
        contribution=any(c['kind']=='contribution' and c['temporality']=='actual' for c in claims)
        absent=any(c['dimension']=='exposure' and c['kind']=='absence' for c in claims)
        supplied=covered==set(q['covers']) or q['id']=='experience' and (contribution or absent)
        if supplied:
            omitted.append({'question_id':q['id'],'rule_id':'confirmed_evidence_covers_item',
                'reason':'Earlier confirmed evidence already addresses this item.'})
            continue
        r=deepcopy(q);r.update(question_text=q['organisation_text'] if respondent['perspective']=='organisation' else q['text'],
            is_probe=False,selection_reason='Relevant evidence has not yet been discussed.')
        if q['id']=='experience' and 'exposure' in covered:
            r['question_text']=q['when_exposure_already_reported']
            r['selection_reason']='Exposure reported; ask only about contribution.'
        available.append(r)
    if len(active)>=instrument['maximum_questions']:
        remaining=available
        probe=_legacy_select_question(events,{**instrument,'core_questions':[]},respondent)
        if probe:remaining=remaining+[probe]
        omitted += [{'question_id':q['id'],'rule_id':'total_question_budget',
                     'reason':'Total interview question budget reached.'} for q in remaining]
        return None,omitted
    if available:return available[0],omitted
    # Reuse the established probe eligibility with no core items. This preserves
    # actual/intention, unknown scope and skip suppression rules.
    probe_instrument={**instrument,'core_questions':[]}
    return _legacy_select_question(events,probe_instrument,respondent),omitted


def select_question(events, instrument, respondent):
    return selection_plan(events,instrument,respondent)[0]
