"""Model selects passage IDs; application retrieves untouched citizen text."""
import copy
import json
import re
from .assessment import AssessmentError, check_input
from .schemas import Assessment

def passages(text):
    check_input(text)
    # Formatting inside a passage is retained. This is segmentation, not normalization.
    chunks=[part.strip() for part in re.split(r'(?<=[.!?])\s+|\n\s*\n',text) if part.strip()]
    return {f"p{i:03d}":part for i,part in enumerate(chunks,1)}

def reference_schema(schema, sources):
    result=copy.deepcopy(schema)
    item={"type":"string","enum":list(sources)}
    for definition in result.get("$defs",{}).values():
        props=definition.get("properties",{})
        if "excerpts" in props:
            props["excerpts"]["items"]=copy.deepcopy(item)
            props["excerpts"]["description"]="IDs of relevant citizen passages, not quotations or paraphrases."
    result["properties"]["acceptance_conditions"]["items"]=copy.deepcopy(item)
    result["properties"]["acceptance_conditions"]["description"]="Passage IDs explicitly stating conditions; otherwise empty."
    return result

def resolve(raw, sources):
    try:
        result=Assessment.model_validate_json(raw)
    except ValueError as exc:
        raise AssessmentError("Model output failed JSON/schema checks; no assessment was saved.",code="schema") from exc
    groups=list(result.concerns)+[result.awareness_understanding,result.medical_public_benefit_support,result.current_route_stance]
    try:
        for group in groups:
            group.excerpts=[sources[ref] for ref in group.excerpts]
        result.acceptance_conditions=[sources[ref] for ref in result.acceptance_conditions]
    except KeyError as exc:
        raise AssessmentError("Model selected an unknown evidence passage; no assessment was saved.",code="evidence") from exc
    return result.model_dump_json()
