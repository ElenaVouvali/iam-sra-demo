"""Bounded HTTP transport shared by the confirmed conversation client."""
import json
import hashlib
import os
from copy import deepcopy
import threading
import time
import httpx
from pydantic import ValidationError
from .settings import MODEL, BASE_URL
from .assessment import AssessmentError
from .model_spec import thinking_enabled, context_tokens, reasoning_tokens

_LOCK=threading.Lock()
STAGE_LIMITS = {'readiness_evidence': 1600, 'readiness_grounding': 1400, 'workbook_score': 500}
BACKEND="xgrammar:no-fallback,disable-any-whitespace"

def _screen_generation_body(body, user, stage):
    """Screen model output while treating exact echoes of screened evidence as references.

    The response content stays untouched for validation. Only the temporary
    screening copy omits an information-request quote that is an exact substring
    of the participant answer already screened in the request. Arbitrary text,
    non-matching quotes and every other model field remain screened normally.
    """
    from .privacy import require_safe_data
    screening_copy=deepcopy(body)
    answer=user.get('answer') if isinstance(user,dict) else None
    if stage=='chat_turn' and isinstance(answer,str) and answer:
        for choice in screening_copy.get('choices',[]) if isinstance(screening_copy,dict) else []:
            message=choice.get('message') if isinstance(choice,dict) else None
            content=message.get('content') if isinstance(message,dict) else None
            if not isinstance(content,str):continue
            try:decoded=json.loads(content)
            except (ValueError,TypeError):continue
            interpretation=decoded.get('interpretation') if isinstance(decoded,dict) else None
            quote=interpretation.get('information_request_quote') if isinstance(interpretation,dict) else None
            if isinstance(quote,str) and quote and quote in answer:
                interpretation['information_request_quote']=''
                message['content']=json.dumps(decoded,ensure_ascii=False,separators=(',',':'))
    require_safe_data(screening_copy)

def guided_schema(value):
    # Pinned XGrammar constrains structure/types/enums; local Pydantic enforces
    # all bounds. Unsupported bounds are removed to avoid an Outlines fallback.
    if isinstance(value,dict):
        return {k:guided_schema(v) for k,v in value.items() if k not in {"minimum","maximum","maxItems","minItems","maxLength","minLength"}}
    if isinstance(value,list):return [guided_schema(v) for v in value]
    return value

def schema_error(exc):
    if isinstance(exc,ValidationError):
        field='.'.join(str(v) for v in exc.errors()[0]['loc']) or 'response'
        return AssessmentError("The model response did not match its expected structure.",code="schema",field=field)
    return AssessmentError("Model JSON/schema checks failed; no assessment saved.",code="schema")

class LLMTransport:
    def __init__(self,base_url=BASE_URL):
        self.base_url=base_url.rstrip('/')
        # CPU weight offloading may require longer bounded generation requests.
        timeout=os.getenv('IAM_MODEL_TIMEOUT_SECONDS')
        if timeout is not None:
            timeout=int(timeout)
            if not 15<=timeout<=1800:
                raise ValueError('IAM_MODEL_TIMEOUT_SECONDS must be between 15 and 1800')
        self.request_timeout=120 if timeout is None else timeout
        self.stage_timeout=180 if timeout is None else timeout

    def _post_json(self,client,path,payload,stage,phase):
        from .model_lifecycle import inference_lease
        waiting=time.monotonic()
        with inference_lease(self.base_url, self._deadline):
            if hasattr(self,'last_metrics'):
                self.last_metrics['model_wait_seconds']=round(self.last_metrics.get('model_wait_seconds',0)+time.monotonic()-waiting,6)
            return self._post_json_active(client,path,payload,stage,phase)

    def _post_json_active(self,client,path,payload,stage,phase):
        """Retry a transient connection/status failure once; never expose bodies."""
        for retry in range(2):
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError('Model request timed out.',code='timeout')
            if hasattr(self,'last_metrics'):self.last_metrics['tokenize_calls' if phase=='tokenization' else 'generation_calls']+=1
            request_started=time.monotonic()
            try:
                response=client.post(self.base_url+path,json=payload,timeout=min(self.request_timeout,remaining))
                response.raise_for_status()
            except httpx.TimeoutException:
                code='timeout';status=None;transient=False
            except httpx.HTTPStatusError as exc:
                status=exc.response.status_code
                transient=status in {502,503,504}
                code='service_busy' if status==429 else 'service_request' if status<500 else 'transport'
            except httpx.RequestError:
                code='transport';status=None;transient=True
            else:
                try:
                    body=response.json()
                except (ValueError,TypeError):
                    code='schema';status=response.status_code;transient=True
                else:
                    usage=body.get('usage',{}) if isinstance(body,dict) else {}
                    tokens=usage.get('completion_tokens') if isinstance(usage,dict) else None
                    if phase=='generation' and hasattr(self,'last_metrics') and type(tokens) is int and 0<=tokens<=65536:
                        self.last_metrics['generated_tokens']=self.last_metrics.get('generated_tokens',0)+tokens
                        self.last_metrics['generation_http_seconds']=round(self.last_metrics.get('generation_http_seconds',0)+time.monotonic()-request_started,6)
                    return body
            self.last_diagnostics.append({'stage':stage,'phase':phase,'transport_attempt':retry,
                'failure':code,'http_status':status})
            if not transient or retry==1:
                raise AssessmentError('The model service request could not complete.',code=code) from None

    def _request(self,client,stage,system,user,schema,validator,retry_hint=None):
        from .privacy import require_safe_data, safe_message, PrivacyError
        require_safe_data({'system':system,'user':user,'schema':schema})
        self._accepted_wire = None
        enabled=thinking_enabled()
        context_limit=context_tokens()
        messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(user,ensure_ascii=False,separators=(',',':'))}]
        limit=STAGE_LIMITS[stage]+reasoning_tokens()
        for attempt in range(2):
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError("Assessment time limit reached; no result saved.",code="timeout")
            attempt_start=time.monotonic()
            tokenize_payload={"model":MODEL,"messages":messages,"add_generation_prompt":True,"chat_template_kwargs":{"enable_thinking":enabled}}
            token_key=hashlib.sha256(json.dumps({'endpoint':self.base_url,
                'model_revision':getattr(self,'last_settings',{}).get('model'),
                'payload':tokenize_payload},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            token_cache=getattr(self,'_token_count_cache',{})
            if token_key in token_cache:
                count=token_cache[token_key]
                if hasattr(self,'last_metrics'):self.last_metrics['tokenize_cache_hits']+=1
            else:
                tokenized=self._post_json(client,'/tokenize',tokenize_payload,stage,'tokenization')
                if not isinstance(tokenized,dict) or type(tokenized.get('count')) is not int:
                    raise AssessmentError('The model service returned an invalid token count.',code='service_request')
                count=tokenized['count']
                if type(count) is not int or count<0:raise AssessmentError("Invalid token count; no assessment saved.",code="transport")
                if hasattr(self,'_cache_scope'):
                    if len(token_cache)>=128:token_cache.pop(next(iter(token_cache)))
                    token_cache[token_key]=count
            if count+limit>context_limit:
                if hasattr(self,'last_diagnostics'):self.last_diagnostics.append({'stage':stage,'attempt':attempt,'prompt_tokens':count,'max_output_tokens':limit,'context_tokens':context_limit,'failure':'budget'})
                raise AssessmentError("Full "+stage+" request exceeds context budget: "+str(count)+" prompt tokens + "+str(limit)+" reserved output tokens > "+str(context_limit)+". Instructions, proposal and evidence all contribute; evidence is never truncated.",code="budget")
            payload={"model":MODEL,"messages":messages,"max_tokens":limit,"temperature":0.6 if enabled else 0.2,"top_p":0.95 if enabled else 0.8,"chat_template_kwargs":{"enable_thinking":enabled},"guided_json":guided_schema(schema),"guided_decoding_backend":BACKEND}
            if enabled:payload['top_k']=20
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError('Assessment time limit reached; no result saved.',code='timeout')
            body=self._post_json(client,'/v1/chat/completions',payload,stage,'generation')
            # In the explicitly enabled profile, the server separates internal
            # work from deliverable JSON. Discard that untrusted private channel
            # before any retention, logging, downstream prompting or assessment.
            # Every deliverable field still passes the existing privacy gate.
            reasoning_chars=0
            if enabled and isinstance(body,dict):
                for row in body.get('choices',[]) if isinstance(body.get('choices'),list) else []:
                    message=row.get('message') if isinstance(row,dict) else None
                    if isinstance(message,dict):
                        discarded=message.pop('reasoning_content',None)
                        if isinstance(discarded,str):reasoning_chars+=len(discarded)
                        elif discarded is not None:
                            raise AssessmentError('The reasoning parser returned an invalid channel.',code='schema',field='reasoning_content')
                        discarded=None
                if hasattr(self,'last_metrics'):
                    self.last_metrics['reasoning_characters']=self.last_metrics.get('reasoning_characters',0)+reasoning_chars
            # With thinking disabled, unexpected reasoning is screened/rejected
            # exactly as before. Never strip think tags out of final JSON.
            try:
                _screen_generation_body(body,user,stage)
            except PrivacyError as exc:
                self.last_diagnostics.append({'stage':stage,'attempt':attempt,'failure':'privacy',
                    'privacy_boundary':'model_output','entity_types':list(exc.entity_types),
                    'field_paths':[row.get('field_path','root') for row in exc.findings],
                    'latency_seconds':round(time.monotonic()-attempt_start,4)})
                body=None  # Rejected content must never enter traces or retry feedback.
                if attempt==0 and exc.code!='privacy_unavailable':
                    messages[0]['content']=system+'\nRetry: generated content failed local privacy screening. Return a fresh grounded object without introducing private details. Use only the supplied passage IDs; do not add facts.'
                    continue
                raise PrivacyError('The generated interpretation could not be displayed safely. Retry this step with the same answer; rejected output was not saved.',
                    unavailable=exc.code=='privacy_unavailable', entity_types=exc.entity_types,findings=exc.findings,
                    boundary='model_output') from None
            try:
                choice=body['choices'][0];message=choice['message'];content=message.get('content') or ''
                if not isinstance(content,str) or not isinstance(choice['finish_reason'],str):raise TypeError()
            except (KeyError,TypeError,IndexError,AttributeError):
                self.last_diagnostics.append({'stage':stage,'attempt':attempt,'failure':'schema','boundary':'response_envelope'})
                if attempt==1:raise AssessmentError('The model returned an incomplete response envelope.',code='schema') from None
                continue
            thinking=bool(message.get('reasoning_content')) or '<think>' in content or '</think>' in content
            trace={"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"finish_reason":choice['finish_reason'],"retry_feedback":messages[0]['content'][len(system):],"thinking_detected":thinking or reasoning_chars>0,"reasoning_enabled":enabled,"reasoning_characters":reasoning_chars,"raw_output":None, "output_retention":"structural_metadata_only"}
            self.last_trace.append(trace)
            if choice['finish_reason']!='stop' or thinking:
                error=AssessmentError("Truncated output or visible thinking rejected; no result saved.",code="thinking" if thinking else "truncated")
                completion_status=choice['finish_reason']
            else:
                completion_status='stop'
                try:
                    result=validator(content)
                    self.last_diagnostics.append({"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"usage":body.get('usage'),"latency_seconds":round(time.monotonic()-attempt_start,4),"schema_pass":True,"evidence_pass":True,"eligibility_pass":True,"completion_status":completion_status,"thinking_detected":reasoning_chars>0,"reasoning_enabled":enabled,"reasoning_characters":reasoning_chars})
                    self._accepted_wire = content
                    return result
                except ValidationError as exc:
                    error=schema_error(exc)
                    self.last_diagnostics.append({'stage':stage,'attempt':attempt,'validation_fields':[{'location':list(e['loc']),'type':e['type']} for e in exc.errors()[:3]],'validation_field':error.field})
                except PrivacyError: raise
                except AssessmentError as exc:
                    error=AssessmentError(safe_message(exc),code=exc.code,field=exc.field)
                    if getattr(exc,'validation_fields',None):
                        self.last_diagnostics.append({'stage':stage,'attempt':attempt,'validation_fields':exc.validation_fields})
            self.last_diagnostics.append({"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"failure":error.code,"validation_field":error.field,"completion_status":completion_status,"latency_seconds":round(time.monotonic()-attempt_start,4),"schema_pass":error.code in {'evidence','eligibility'},"evidence_pass":False if error.code=='evidence' else None,"eligibility_pass":False if error.code=='eligibility' else None,"thinking_detected":thinking})
            if attempt==1:raise error
            # No previous citizen/model output is copied into feedback. Recount
            # the whole message before every retry; do not truncate evidence.
            feedback=('Retry: previous output failed '+error.code+' checks at '+str(error.field or 'response')+': '+safe_message(error)+
                      ' Return a fresh object matching the supplied schema and cite only listed passage IDs. Do not add missing facts.')
            if retry_hint:
                feedback+=' '+retry_hint
            else:
                feedback+=' Use empty optional fields only when the schema permits them and no detail is supported.'
            messages[0]['content']=system+'\n'+feedback
