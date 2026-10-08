"""One score-free relevance check; rejected nominations never reach scoring."""
from .assessment import AssessmentError
from .schemas import Strict
from .settings import ROOT,config


class ScopeVerdicts(Strict):
    supported: dict[str,bool]


def review(client,http,result,sources,registry):
    nominated=[f.facet for f in result.facets]
    schema=ScopeVerdicts.model_json_schema()
    schema['properties']['supported']={
        'type':'object','properties':{key:{'type':'boolean'} for key in nominated},
        'required':nominated,'additionalProperties':False}
    def validate(raw):
        verdicts=ScopeVerdicts.model_validate_json(raw)
        if set(verdicts.supported)!=set(nominated):
            raise AssessmentError('Review each nominated facet exactly once; no unrelated verdicts.',code='schema')
        return verdicts
    verdicts=client._request(http,'coverage_review',
        (ROOT/config('prompts')['initial_relevance_prompt']).read_text(),
        {'relevance_check':True,'facet_definitions':{key:registry[key] for key in nominated},
         'citizen_passages':{r:v.text for r,v in sources.items()}},schema,validate)
    retained=[f for f in result.facets if verdicts.supported[f.facet]]
    client.last_settings['initial_relevance_review']={
        'nominated_facets':nominated,'verdicts':verdicts.supported,
        'discarded_facets':[key for key in nominated if not verdicts.supported[key]],
        'score_assigned':False}
    return result.model_copy(update={'facets':retained})
