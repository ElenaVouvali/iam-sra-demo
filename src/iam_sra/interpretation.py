"""Score-free, versioned meanings and evidence provenance."""
import hashlib
import json
from copy import deepcopy
from pydantic import BaseModel, ConfigDict
from .schemas import MappingAssessment
from .assessment import AssessmentError

INTERPRETATION_VERSION = '1.1.0'

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

def freeze(meaning, evidence, version, context, proposal, actor='user', supporting_history=None):
    check_meaning(meaning,evidence,context)
    payload={'schema':INTERPRETATION_VERSION,'version':version,'context':context,'proposal':proposal,
        'meaning':meaning.model_dump(),'evidence':{k:v.model_dump() for k,v in evidence.items() if v.context==context},
        'confirmation':{'actor':actor,'meaning_only':True},'supporting_history_by_concern':deepcopy(supporting_history or {})}
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
