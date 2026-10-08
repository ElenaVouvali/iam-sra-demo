"""Score-free, versioned meanings and evidence provenance."""
import hashlib
import json
from copy import deepcopy
from pydantic import BaseModel, ConfigDict
from .schemas import MappingAssessment
from .assessment import AssessmentError

INTERPRETATION_VERSION = '1.4.0'

class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    id: str
    text: str
    context: str
    source: str  # citizen_original, citizen_correction, citizen_choice, question
    question_id: str | None = None

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def references(meaning):
    groups=[meaning.awareness_understanding,meaning.medical_public_benefit_support,meaning.current_route_stance]+list(meaning.concerns)
    return {ref for group in groups for ref in group.excerpts+getattr(group,'conditions',[])}|set(meaning.acceptance_conditions)

def check_meaning(meaning, evidence, context):
    for ref in references(meaning):
        item=evidence.get(ref)
        if item is None or item.source=='question' or item.context!=context:
            raise AssessmentError('Interpretation cites missing, non-citizen or wrong-context evidence; clarify before scoring.',code='evidence')
    return meaning

def freeze(meaning, evidence, version, context, proposal, actor='user', supporting_history=None, acceptance_boundaries=None, facet_meanings=None):
    check_meaning(meaning,evidence,context)
    payload={'schema':INTERPRETATION_VERSION,'version':version,'context':context,'proposal':proposal,
        'meaning':meaning.model_dump(),'facet_meanings':deepcopy(facet_meanings or []),'evidence':{k:v.model_dump() for k,v in evidence.items() if v.context==context},
        'confirmation':{'actor':actor,'meaning_only':True},'acceptance_boundaries':deepcopy(acceptance_boundaries or {}),'supporting_history_by_concern':deepcopy(supporting_history or {})}
    return {**deepcopy(payload),'sha256':digest(payload)}

def verify(record):
    payload={k:v for k,v in record.items() if k!='sha256'}
    if record.get('sha256')!=digest(payload):
        raise AssessmentError('Confirmed interpretation changed; confirm again before scoring.',code='confirmation')
    meaning=MappingAssessment.model_validate(record['meaning'])
    evidence={k:EvidenceItem.model_validate(v) for k,v in record['evidence'].items()}
    check_meaning(meaning,evidence,record['context'])
    for refs in record.get('supporting_history_by_concern',{}).values():
        for ref in refs:
            if ref not in evidence or evidence[ref].source=='question' or evidence[ref].context!=record['context']:
                raise AssessmentError('Invalid supporting history citation; clarify before scoring.',code='evidence')
    if record.get('facet_meanings'):
        from .updates import FacetMeaning
        for item in record['facet_meanings']:
            facet=FacetMeaning.model_validate(item)
            for ref in facet.evidence_ids+facet.condition_ids:
                if ref not in evidence or evidence[ref].context!=record['context'] or evidence[ref].source in {'question','application_control','citizen_control'}:
                    raise AssessmentError('Aspect cites missing or wrong-context citizen evidence.',code='evidence')
    return meaning,evidence

def semantic_key(concern):
    # Evidence changes are relevant too; do not re-score just for model wording.
    d=concern.model_dump();d.pop('rationale',None);d.pop('mapping_note',None)
    return digest(d)

def comparison(initial, final, conditional, reasons):
    from .settings import CONCERNS
    def by_id(snapshot):return {c['concern_id']:c for c in snapshot['assessment']['concerns']} if snapshot else {}
    a,b,c=by_id(initial),by_id(final),by_id(conditional)
    return [{'concern_id':cid,'concern':definition['label'],'initial_score':a.get(cid,{}).get('score'),
        'final_original_score':b.get(cid,{}).get('score'),'conditional_score':c.get(cid,{}).get('score'),
        'reason':reasons.get(cid,'No relevant new evidence; carried forward.'),
        'conditional_reason':conditional.get('scoring_exclusions',{}).get(cid,conditional.get('update_reasons',{}).get(cid,'Not assessed in this modified context.')) if conditional else 'No sufficiently evidenced conditional profile.',
        'evidence':{'initial':a.get(cid,{}).get('excerpts',[]),'final_original':b.get(cid,{}).get('excerpts',[]),'conditional':c.get(cid,{}).get('excerpts',[])}}
        for cid,definition in CONCERNS.items()]


def reconcile_original(previous, patch, facets, explicit=False, reviewed_facets=None):
    """Preserve independently evidenced aspects; unknowns do not erase other meanings.

    Independent initial extraction retains every explicitly evidenced facet,
    including uncertainty. Legacy correction projections preserve their prior policy.
    """
    from .updates import FacetMeaning
    from .schemas import MappingConcern
    result=previous.model_copy(deep=True) if previous else patch.model_copy(deep=True)
    ledger=deepcopy(facets)
    by={c.concern_id:c for c in result.concerns}
    for c in patch.concerns:
        if c.status=='needs_clarification' and not c.facets:continue
        for aspect in c.facets:
            key=c.concern_id+':'+aspect;old=ledger.get(key)
            # Broad uncertainty is not a correction of each previously clear aspect.
            if old and c.position in {'uncertain','unassessed'} and len(c.facets)>1:continue
            ledger[key]=FacetMeaning(concern_id=c.concern_id,facet=aspect,position=c.position,evidence_ids=c.excerpts,
                condition_ids=c.conditions,applicability_explicit=c.status=='mapped',rationale=c.rationale,
                conditional_willingness=c.conditional_willingness)
        if c.concern_id not in by:by[c.concern_id]=c.model_copy(deep=True)
        elif c.conditional_willingness!='not_stated' or explicit and set(by[c.concern_id].facets)<=set(c.facets):by[c.concern_id].conditional_willingness=c.conditional_willingness
    if reviewed_facets is not None:
        ledger={f.concern_id+':'+f.facet:f.model_copy(deep=True) for f in reviewed_facets}
    benefit=patch.medical_public_benefit_support
    medical_named=not patch.concerns or any(c.concern_id=='welfare_equity' and 'medical_public_benefit' in c.facets for c in patch.concerns)
    broad_uncertainty=any(c.concern_id=='welfare_equity' and len(c.facets)>1 and c.position in {'uncertain','unassessed'} for c in patch.concerns)
    if reviewed_facets is None and medical_named and not (broad_uncertainty and benefit.interpretation=='uncertain' and 'welfare_equity:medical_public_benefit' in ledger) and benefit.interpretation!='unassessed' and benefit.excerpts:
        ledger['welfare_equity:medical_public_benefit']=FacetMeaning(concern_id='welfare_equity',facet='medical_public_benefit',
            position=benefit.interpretation,evidence_ids=benefit.excerpts,applicability_explicit=True,rationale=benefit.rationale)
    for cid in {f.concern_id for f in ledger.values()}:
        all_facts=[f for f in ledger.values() if f.concern_id==cid]
        clear=[f for f in all_facts if f.applicability_explicit and f.position in {'supported','opposed','mixed'}]
        chosen=all_facts if reviewed_facets is not None else clear or all_facts
        old=by.get(cid);template=old.model_dump() if old else {'concern_id':cid,'mapping_note':'direct','conditional_willingness':'not_stated'}
        positions={f.position for f in clear}
        position='mixed' if len(positions)>1 or 'mixed' in positions else next(iter(positions)) if positions else 'uncertain'
        template.update(status='mapped' if clear else 'needs_clarification',position=position,facets=[f.facet for f in chosen],
            excerpts=list(dict.fromkeys(r for f in chosen for r in f.evidence_ids))[:3],conditions=list(dict.fromkeys(r for f in chosen for r in f.condition_ids))[:3],
            rationale='; '.join(f.rationale for f in chosen)[:400])
        try:by[cid]=MappingConcern.model_validate(template)
        except ValueError as exc:raise AssessmentError('Please clarify these aspects together; your earlier testimony is retained.',code='clarification') from exc
    result.concerns=list(by.values())
    previous_condition_ids={r for c in previous.concerns for r in c.conditions} if previous else set()
    extra=[r for r in result.acceptance_conditions if r not in previous_condition_ids]
    conditions=list(dict.fromkeys([r for c in result.concerns for r in c.conditions]+extra))
    # Every condition remains in its concern and facet ledger. The bounded
    # global summary must not reject a valid many-concern response.
    result.acceptance_conditions=conditions if len(conditions)<=5 else []
    medical=ledger.get('welfare_equity:medical_public_benefit')
    if medical and medical.position!='unassessed' and medical.evidence_ids:
        from .schemas import Dimension
        result.medical_public_benefit_support=Dimension(interpretation=medical.position,excerpts=medical.evidence_ids,rationale=medical.rationale)
    return result,ledger
