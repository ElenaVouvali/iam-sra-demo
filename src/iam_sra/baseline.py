"""Phase-1 evidence only: no scenario, acceptance or level assignment."""
from copy import deepcopy
from typing import Literal
from pydantic import Field, model_validator, ValidationError
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

class BaselineReview(Strict):
    decisions: list[BaselineDecision] = Field(max_length=6)


def validate_source(raw, evidence):
    value = BaselineExtraction.model_validate_json(raw) if isinstance(raw,str) else BaselineExtraction.model_validate(raw)
    for c in value.claims:
        if c.evidence_id not in evidence: raise AssessmentError('Unknown baseline passage ID.',code='evidence')
        for scope in (c.activity_quote,c.time_quote):
            if scope and original_quote(evidence[c.evidence_id],scope) is None:
                raise AssessmentError('Activity and time scope must use exact supporting words or be empty.',code='evidence')
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
        for field in ('subject','temporality','domain'):
            if getattr(d,field) is not None:data[field]=getattr(d,field)
        if d.ambiguities is not None:data['ambiguities']=d.ambiguities
        if d.outcome_relation is not None:data['outcome_relation']=d.outcome_relation
        try: accepted.append(BaselineClaim.model_validate(data))
        except ValidationError: continue  # Never turn reasoning into actual experience.

    unique={}
    for c in accepted:
        key=(c.evidence_id,c.dimension,c.kind,c.subject,c.temporality,c.domain)
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
