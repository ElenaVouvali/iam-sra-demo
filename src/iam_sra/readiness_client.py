"""Two bounded source-first requests: semantic extraction and blind classification."""
import httpx
from .conversation_client import ConversationClient
from .llm_client import _LOCK
from .settings import ROOT, CONCERNS, config
from .readiness import validate_extraction
from .readiness_grounding import (SourceExtraction, SourceReview, validate_source_selection, assemble_reviewed)
from .assessment import AssessmentError


class ReadinessClient(ConversationClient):
    prompt_version = 'readiness-1.3.1'

    def extract_readiness(self, evidence, *, elicitation='initial_answer', context='original', version=1, question=None, existing=()):
        with _LOCK:
            self._start()
            self.last_settings['readiness_protocol_version'] = '3.1.0'
            self.last_settings['readiness_instrument_version'] = config('readiness')['version']
            schema = SourceExtraction.model_json_schema()
            schema['$defs']['SourceClaim']['properties']['evidence_id'] = {'type':'string', 'enum':list(evidence)}
            # The application retrieves exact words by selected ID. Requiring
            # an 8B model to copy them adds failure modes without stronger proof.
            claim_schema = schema['$defs']['SourceClaim']
            for field in ('quotation', 'claim_subject', 'time_scope'):
                del claim_schema['properties'][field]
                claim_schema['required'].remove(field)
            # Optional activity/date scopes remain unknown in live extraction.
            # Free-text paraphrases must never become evidence of a shared scope.
            self.last_settings['scope_policy'] = 'unspecified_live_scopes'
            # Previous model interpretations are deliberately excluded. They
            # contaminated new answers in the exported FN session.
            payload = {'question':question, 'context':context, 'elicitation':elicitation,
                       'citizen_passages':{k:v.text for k,v in evidence.items()},
                       'instrument_version':config('readiness')['version']}
            try:
                with httpx.Client(timeout=180, trust_env=False) as http:
                    source = self._request(http, 'readiness_evidence', (ROOT/'prompts/readiness-evidence.txt').read_text(),
                        payload, schema, lambda raw:validate_source_selection(raw,evidence))
                    decisions = []
                    # Six claims per review keep broad answers within the pinned
                    # context. All batches share _start's deadline and retry cap;
                    # no partial profile is returned if any review fails.
                    for offset in range(0, len(source.claims), 6):
                        batch = source.model_copy(update={'claims':source.claims[offset:offset+6]})
                        review_payload = {'question':question, 'citizen_passages':payload['citizen_passages'],
                            'topics':{k:{'label':v['label'], 'facets':v['facets']} for k,v in CONCERNS.items()},
                            # Hide the extractor's classification and earlier
                            # decisions, preventing approval by label repetition.
                            'candidates':[{'candidate':i, 'evidence_id':c.evidence_id,
                                'quotation':c.quotation, 'interpretation':c.interpretation}
                                for i,c in enumerate(batch.claims)]}
                        def validate_review(raw):
                            value = SourceReview.model_validate_json(raw)
                            assemble_reviewed(batch,value,elicitation,context,version)
                            return value
                        review_schema = SourceReview.model_json_schema()
                        props = review_schema['$defs']['ClaimReview']['properties']
                        props['candidate'] = {'type':'integer', 'enum':list(range(len(batch.claims)))}
                        props['facet_ids']['items'] = {'type':'string',
                            'enum':[f for v in CONCERNS.values() for f in v['facets']]}
                        reviewed = self._request(http, 'readiness_grounding', (ROOT/'prompts/readiness-grounding.txt').read_text(),
                            review_payload, review_schema, validate_review)
                        decisions.extend(d.model_copy(update={'candidate':d.candidate+offset}) for d in reviewed.decisions)
                    review = SourceReview(decisions=decisions)
                    result = assemble_reviewed(source,review,elicitation,context,version)
                    self.last_settings['readiness_grounding'] = {
                        'protocol_version':'3.1.0', 'interaction':source.interaction,
                        'quotation_source':'application_retrieved_citizen_passage',
                        'source_claims':[c.model_dump() for c in source.claims],
                        'decisions':[dict(d.model_dump(), accepted=d.meaning_supported and
                            d.evidence_type == source.claims[d.candidate].kind and
                            d.evidence_type not in {'recognition_only','unsupported'}) for d in review.decisions]}
                    return validate_extraction(result.model_dump(), evidence, elicitation, context, version)
            except httpx.HTTPError as exc:
                self.last_settings['transport_error'] = {'exception_type':type(exc).__name__,
                    'http_status':getattr(getattr(exc,'response',None),'status_code',None), 'detail':str(exc)}
                raise AssessmentError('Readiness evidence could not be extracted. Your draft is retained; retry or skip the question.',code='transport') from exc
