import json
import pytest
from iam_sra.evidence import passages, reference_schema, resolve
from iam_sra.schemas import Assessment
from iam_sra.assessment import parse_assessment, AssessmentError
from test_core import payload

def test_passages_keep_pdf_linebreaks_and_punctuation():
    text='Look, that electric hum\nis annoying. Cameras aren’t welcome!'
    sources=passages(text)
    assert sources=={'p001':'Look, that electric hum\nis annoying.','p002':'Cameras aren’t welcome!'}
    assert all(s in text for s in sources.values())
    raw=payload({'noise':3},'p001')
    result=parse_assessment(resolve(json.dumps(raw),sources),text)
    assert result.concerns[0].excerpts==[sources['p001']]

def test_guided_schema_only_allows_existing_references():
    schema=reference_schema(Assessment.model_json_schema(),{'p001':'Noise matters.'})
    for d in schema['$defs'].values():
        if 'excerpts' in d.get('properties',{}):assert d['properties']['excerpts']['items']['enum']==['p001']
    assert schema['properties']['acceptance_conditions']['items']['enum']==['p001']

@pytest.mark.parametrize('ref',['p999','noise','a paraphrase'])
def test_unknown_reference_is_rejected(ref):
    with pytest.raises(AssessmentError):resolve(json.dumps(payload({'noise':3},ref)),{'p001':'Noise matters.'})

def test_conditions_are_retrieved_from_actual_passages():
    text='Noise bothers me. Only if flights are quiet would I accept.'
    raw=payload({'noise':3},'p001');raw['acceptance_conditions']=['p002']
    result=parse_assessment(resolve(json.dumps(raw),passages(text)),text)
    assert result.acceptance_conditions==['Only if flights are quiet would I accept.']


def test_live_wire_requires_condition_and_facet_fields():
    schema=reference_schema(Assessment.model_json_schema(),{'p001':'Noise matters.'})
    definition=schema['$defs']['Concern']
    assert {'conditional_willingness','conditions','facets','mapping_note'}<=set(definition['required'])
    assert definition['properties']['conditions']['items']['enum']==['p001']


def test_dimension_transport_prevents_empty_evidence_for_assessed_interpretation():
    schema=reference_schema(Assessment.model_json_schema(),{'p001':'One sentence.'})
    for name in ['Dimension','Awareness']:
        absent,present=schema['$defs'][name]['oneOf']
        assert absent['properties']['excerpts']['const']==[]
        assert present['properties']['excerpts']['enum']==[['p001']]
        assert 'unassessed' not in present['properties']['interpretation']['enum']
