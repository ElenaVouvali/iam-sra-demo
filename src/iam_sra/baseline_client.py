"""Bounded baseline extraction/review using the existing screened transport."""
import httpx
from .conversation_client import ConversationClient
from .llm_client import _LOCK
from .baseline import BaselineExtraction, BaselineReview, validate_source, reviewed
from .settings import CONCERNS
from .assessment import AssessmentError
from .privacy import require_safe_data

class BaselineClient(ConversationClient):
    prompt_version='baseline-2.2.0'

    def extract_baseline(self,evidence,*,question,respondent,instrument,prompts):
        require_safe_data({'evidence':evidence,'question':question,'respondent':respondent})
        with _LOCK:
            self._start()
            self.prompt_version=instrument['prompt_version']
            payload={'context':'general_baseline','scenario_id':None,'question':question['question_text'],
                     'respondent_context':respondent,'passages':evidence,'instrument_version':instrument['version'],
                     'information_context':question.get('information_context','before_information'),
                     'displayed_information':question.get('displayed_information',[])}
            if question.get('interpretation_feedback'):
                payload['interpretation_feedback']=question['interpretation_feedback']
            dimensions=[d for d in instrument['dimensions'] if d!='familiarity']
            def scoped_schema(model,definition):
                schema=model.model_json_schema()
                if 'routing' not in instrument:
                    for key in ('ambiguities','outcome_relation'):
                        schema['$defs'][definition]['properties'].pop(key,None)
                schema['$defs'][definition]['properties']['dimension']={'type':'string','enum':dimensions}
                if 'concept' not in dimensions:
                    kinds=schema['$defs'][definition]['properties']['kind']['enum']
                    schema['$defs'][definition]['properties']['kind']['enum']=[k for k in kinds if k not in {'concept_explanation','use_knowledge'}]
                return schema
            schema=scoped_schema(BaselineExtraction,'BaselineClaim')
            schema['$defs']['BaselineClaim']['properties']['evidence_id']={'type':'string','enum':list(evidence)}
            try:
                with httpx.Client(timeout=180,trust_env=False) as http:
                    source=self._request(http,'readiness_evidence',prompts['evidence'],payload,schema,lambda raw:validate_source(raw,evidence))
                    if not source.claims:return source
                    review_payload={'question':question['question_text'],'passages':evidence,
                        'information_context':payload['information_context'],'displayed_information':payload['displayed_information'],
                        'topics':{k:v['label'] for k,v in CONCERNS.items()},
                        'candidates':[{'candidate':i,'evidence_id':c.evidence_id,'interpretation':c.interpretation,
                            'activity_quote':c.activity_quote,'time_quote':c.time_quote} for i,c in enumerate(source.claims)]}
                    def check(raw):
                        result=BaselineReview.model_validate_json(raw);reviewed(source,result);return result
                    review=self._request(http,'readiness_grounding',prompts['grounding'],review_payload,scoped_schema(BaselineReview,'BaselineDecision'),check)
                    self.last_settings['baseline_review']={'decisions':[d.model_dump() for d in review.decisions]}
                    return reviewed(source,review)
            except httpx.HTTPError:
                raise AssessmentError('The local model could not complete this answer. Retry, skip or finish.',code='transport') from None

class MockBaselineClient:
    """Empty test output, never a semantic assessment."""
    def extract_baseline(self,*args,**kwargs):
        return BaselineExtraction(interaction='substantive',claims=[])
