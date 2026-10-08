"""One score-free model interpretation; Python checks structure and provenance."""
import json
import hashlib
from typing import Literal
from pydantic import Field
from .assessment import AssessmentError
from .facet_mapping import Entry,assemble
from .interpretation import check_meaning
from .schemas import Strict,Dimension
from .settings import CONCERNS,SCENARIO,ROOT,config


class RouteInterpretation(Strict):
    interpretation: Literal['supported','opposed','mixed','uncertain','unassessed']
    excerpts: list[str]=Field(max_length=1)


class EvidenceReferences(Strict):
    # A required scalar survives the decoder's removal of minItems.
    primary: str
    additional: list[str]=Field(max_length=2)

    def ids(self):
        return list(dict.fromkeys([self.primary]+self.additional))


class FacetInterpretation(Strict):
    facet: str
    position: Literal['supported','opposed','mixed','uncertain']
    evidence_ids: EvidenceReferences
    condition_ids: list[str]=Field(max_length=3)
    conditional_willingness: Literal['willing','not_willing','uncertain','not_stated']


class Interpretation(Strict):
    route: RouteInterpretation
    facets: list[FacetInterpretation]=Field(max_length=26)


def assemble_interpretation(result):
    records={f.facet:Entry(**f.model_dump(exclude={'facet','evidence_ids'}),evidence_ids=f.evidence_ids.ids(),
        rationale='Model-interpreted citizen position; see supporting passages.') for f in result.facets}
    route=Dimension(**result.route.model_dump(),rationale='Model-interpreted whole-route position; see supporting passage.')
    return assemble(records,route)




def interpret(client,http,evidence,proposal=None):
    system=(ROOT/config('prompts')['initial_interpretation']).read_text()
    client.last_settings['mapping_prompt_sha256']=hashlib.sha256(system.encode()).hexdigest()
    sources={r:v for r,v in evidence.items() if v.context=='original' and v.source!='question'}
    if not sources:raise AssessmentError('No citizen evidence.',code='evidence')
    registry={cid+':'+f:d.get('facet_scopes',{}).get(f,d['scope'])
        for cid,d in CONCERNS.items() for f in d['facets']}
    schema=Interpretation.model_json_schema()
    entry=schema['$defs']['FacetInterpretation']
    entry['properties']['facet']={'type':'string','enum':list(registry)}
    refs_schema=schema['$defs']['EvidenceReferences']['properties']
    refs_schema['primary']={'type':'string','enum':list(sources)}
    refs_schema['additional']['items']={'type':'string','enum':list(sources)}
    entry['properties']['condition_ids']['items']={'type':'string','enum':list(sources)}
    route=schema['$defs']['RouteInterpretation']
    route['properties']['excerpts']={'type':'array','enum':[[]]+[[r] for r in sources]}
    # Encode cross-field invariants in guided decoding, not just validation.
    # No semantic value is repaired or guessed after generation.
    import copy
    positioned_route=copy.deepcopy(route)
    positioned_route['properties']['interpretation']={'type':'string','enum':['supported','opposed','mixed','uncertain']}
    positioned_route['properties']['excerpts']={'type':'array','enum':[[r] for r in sources]}
    absent_route=copy.deepcopy(route)
    absent_route['properties']['interpretation']={'type':'string','const':'unassessed'}
    absent_route['properties']['excerpts']={'type':'array','enum':[[]]}
    schema['$defs']['RouteInterpretation']={'oneOf':[positioned_route,absent_route]}
    no_willingness=copy.deepcopy(entry)
    no_willingness['properties']['conditional_willingness']={'type':'string','const':'not_stated'}
    no_willingness['properties']['condition_ids']={'type':'array','enum':[[]]}
    stated_willingness=copy.deepcopy(entry)
    stated_willingness['properties']['conditional_willingness']={'type':'string','enum':['willing','not_willing','uncertain']}
    schema['$defs']['FacetInterpretation']={'oneOf':[no_willingness,stated_willingness]}
    def validate(raw):
        def unique_object(pairs):
            values={}
            for key,value in pairs:
                if key in values:raise AssessmentError('Duplicate interpretation field.',code='schema')
                values[key]=value
            return values
        try:values=json.loads(raw,object_pairs_hook=unique_object)
        except (ValueError,TypeError) as exc:
            if isinstance(exc,AssessmentError):raise
            raise AssessmentError('Invalid interpretation JSON.',code='schema') from exc
        result=Interpretation.model_validate(values)
        if any(f.facet not in registry for f in result.facets):
            raise AssessmentError('Unknown interpreted facet.',code='schema')
        if len({f.facet for f in result.facets})!=len(result.facets):
            raise AssessmentError('Duplicate interpreted facet.',code='schema')
        refs=result.route.excerpts+[r for f in result.facets for r in f.evidence_ids.ids()+f.condition_ids]
        if any(r not in sources for r in refs):
            raise AssessmentError('Interpretation cites an unknown citizen passage.',code='evidence')
        # Check the existing downstream representation too, before caching.
        meaning,_=assemble_interpretation(result)
        check_meaning(meaning,evidence,'original')
        return result
    result=client._request(http,'initial_interpretation',system,
        {'proposal':proposal or SCENARIO['text'],'facet_definitions':registry,
         'citizen_passages':{r:v.text for r,v in sources.items()}},schema,validate)
    if result.route.interpretation=='unassessed' and result.facets:
        # A focused reread may confirm the route really is unstated. It never
        # derives whole-route rejection automatically from individual objections.
        first=result.model_dump()
        first_facets=list(result.facets)
        parents={f.facet.split(':',1)[0] for f in result.facets}
        requested={k:v for k,v in registry.items() if k.split(':',1)[0] in parents}
        review_schema=copy.deepcopy(schema)
        for variant in review_schema['$defs']['FacetInterpretation']['oneOf']:
            variant['properties']['facet']['enum']=list(requested)
        def validate_review(raw):
            reviewed=validate(raw)
            if any(f.facet not in requested for f in reviewed.facets):
                raise AssessmentError('Position review introduced an unrelated concern.',code='schema')
            return reviewed
        review_system=(ROOT/config('prompts')['initial_position_review']).read_text()
        result=client._request(http,'initial_interpretation',review_system,
            {'position_review':True,'proposal':proposal or SCENARIO['text'],
             'facet_definitions':requested,'citizen_passages':{r:v.text for r,v in sources.items()}},
            review_schema,validate_review)
        reviewed=result.model_dump()
        # A focused reread is not new citizen testimony. Omission alone must
        # not delete an earlier cited facet; explicit revised entries win.
        # The following independent relevance check still rejects unsupported ones.
        reviewed_keys={f.facet for f in result.facets}
        preserved=[f for f in first_facets if f.facet not in reviewed_keys]
        if preserved:
            result=validate(result.model_copy(update={'facets':result.facets+preserved}).model_dump_json())
        client.last_settings['initial_position_review']={'reason':'Facets expressed but route stance not identified',
            'first_interpretation':first,'reviewed_interpretation':reviewed,
            'preserved_omitted_facets':[f.facet for f in preserved]}
    if result.facets and config('prompts').get('initial_relevance_review',False):
        from .initial_relevance import review
        result=review(client,http,result,sources,registry)
    meaning,facets=assemble_interpretation(result)
    client.last_original_facets=facets
    client.last_settings.update(initial_mapping='direct_interpretation',
        direct_interpretation=result.model_dump(),unresolved_facet_reviews={})
    return meaning
