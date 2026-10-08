"""Model selects passage IDs; application retrieves untouched citizen text."""
import copy
import re
from .assessment import AssessmentError, check_input
from .schemas import Assessment
from .settings import CONCERNS

def passages(text):
    check_input(text)
    # Formatting inside a passage is retained. This is segmentation, not normalization.
    chunks=[part.strip() for part in re.split(r'(?<=[.!?])\s+|\n\s*\n',text) if part.strip()]
    return {f"p{i:03d}":part for i,part in enumerate(chunks,1)}


def original_quote(text,quotation):
    """Match whitespace-only formatting differences and return untouched source text.

    PDF line wrapping may be rendered as spaces by the model. Words, spelling,
    case, punctuation and passage boundaries must still match the citizen.
    """
    if not isinstance(quotation,str) or not quotation.strip():return None
    if quotation in text:return quotation
    pattern=r'\s+'.join(re.escape(word) for word in quotation.split())
    match=re.search(pattern,text)
    return match.group(0) if match else None

def reference_schema(schema, sources):
    result=copy.deepcopy(schema)
    item={"type":"string","enum":list(sources)}
    for definition in result.get("$defs",{}).values():
        props=definition.get("properties",{})
        if "interpretation" in props:
            definition["properties"]={key:props[key] for key in ["interpretation","excerpts","rationale"]}
        if "conditions" in props:
            props["conditions"]["items"]=copy.deepcopy(item)
        if "excerpts" in props:
            props["excerpts"]["items"]=copy.deepcopy(item)
            props["excerpts"]["description"]="IDs of relevant citizen passages, not quotations or paraphrases."
    result["properties"]["acceptance_conditions"]["items"]=copy.deepcopy(item)
    result["properties"]["acceptance_conditions"]["description"]="Passage IDs explicitly stating conditions; otherwise empty."
    # Pinned XGrammar cannot enforce minItems without backend fallback. For
    # global dimensions, use small literal array enums to enforce the evidence
    # invariant at generation time: unassessed => [], otherwise one source ID.
    # Concern evidence remains up to three passages, checked with Pydantic.
    for name in ["Dimension","Awareness"]:
        definition=result["$defs"][name]
        absent=copy.deepcopy(definition);present=copy.deepcopy(definition)
        absent["properties"]["interpretation"]={"type":"string","const":"unassessed"}
        absent["properties"]["excerpts"]={"type":"array","const":[]}
        allowed=[value for value in definition["properties"]["interpretation"]["enum"] if value!="unassessed"]
        present["properties"]["interpretation"]={"type":"string","enum":allowed}
        present["properties"]["excerpts"]={"type":"array","enum":[[ref] for ref in sources]}
        result["$defs"][name]={"oneOf":[absent,present]}
    order=["scenario_id","awareness_understanding","medical_public_benefit_support","current_route_stance","acceptance_conditions","concerns"]
    result["properties"]={key:result["properties"][key] for key in order}
    base=result["$defs"]["Concern"] if "Concern" in result["$defs"] else result["$defs"].get("MappingConcern",result["$defs"].get("ConcernMapping"))
    order=["concern_id","status","position","facets","conditional_willingness","conditions","excerpts","score","rationale","mapping_note"]
    base["properties"]={key:base["properties"][key] for key in order if key in base["properties"]}
    base["required"]=list(base["properties"])
    base["properties"]["facets"]["items"]={"type":"string","enum":sorted({f for c in CONCERNS.values() for f in c["facets"]})}
    return result

def resolve(raw, sources, model=Assessment):
    try:
        result=model.model_validate_json(raw)
    except ValueError as exc:
        raise AssessmentError("Model output failed JSON/schema checks; no assessment was saved.",code="schema") from exc
    groups=list(result.concerns)+[result.awareness_understanding,result.medical_public_benefit_support,result.current_route_stance]
    try:
        for group in groups:
            group.excerpts=[sources[ref] for ref in group.excerpts]
            if hasattr(group, "conditions"):
                group.conditions=[sources[ref] for ref in group.conditions]
        result.acceptance_conditions=[sources[ref] for ref in result.acceptance_conditions]
    except KeyError as exc:
        raise AssessmentError("Model selected an unknown evidence passage; no assessment was saved.",code="evidence") from exc
    return result.model_dump_json()
