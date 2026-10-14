"""Bounded HTTP transport shared by the confirmed conversation client."""
import json
import hashlib
import threading
import time
import httpx
from pydantic import ValidationError
from .settings import MODEL, BASE_URL, CONTEXT_TOKENS
from .assessment import AssessmentError

_LOCK=threading.Lock()
STAGE_LIMITS = {'readiness_evidence': 1600, 'readiness_grounding': 1400, 'workbook_score': 500}
BACKEND="xgrammar:no-fallback,disable-any-whitespace"

def guided_schema(value):
    # Pinned XGrammar constrains structure/types/enums; local Pydantic enforces
    # all bounds. Unsupported bounds are removed to avoid an Outlines fallback.
    if isinstance(value,dict):
        return {k:guided_schema(v) for k,v in value.items() if k not in {"minimum","maximum","maxItems","minItems","maxLength","minLength"}}
    if isinstance(value,list):return [guided_schema(v) for v in value]
    return value

def schema_error(exc):
    if isinstance(exc,ValidationError):
        fields=", ".join(".".join(map(str,e['loc']))+":"+e['type'] for e in exc.errors()[:3])
        bounds=[".".join(map(str,e['loc']))+" must contain at most "+str(e['ctx']['max_length'])+" items; select the most relevant evidence IDs" for e in exc.errors()[:3] if e['type']=='too_long' and 'max_length' in e.get('ctx',{})]
        if bounds:fields+='; '+ '; '.join(bounds)
        rules=[str(e.get('ctx',{}).get('error','')) for e in exc.errors()[:3] if e['type']=='value_error']
        if rules:fields+='; '+ '; '.join(r for r in rules if r)
        return AssessmentError("Model schema failure at "+fields+"; no assessment saved.",code="schema")
    return AssessmentError("Model JSON/schema checks failed; no assessment saved.",code="schema")

class LLMTransport:
    def __init__(self,base_url=BASE_URL):self.base_url=base_url.rstrip('/')

    def _post_json(self,client,path,payload,stage,phase):
        """Retry a transient connection/status failure once; never expose bodies."""
        for retry in range(2):
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError('Model request timed out.',code='timeout')
            if hasattr(self,'last_metrics'):self.last_metrics['tokenize_calls' if phase=='tokenization' else 'generation_calls']+=1
            try:
                response=client.post(self.base_url+path,json=payload,timeout=min(120,remaining))
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
                try:return response.json()
                except (ValueError,TypeError):
                    code='schema';status=response.status_code;transient=True
            self.last_diagnostics.append({'stage':stage,'phase':phase,'transport_attempt':retry,
                'failure':code,'http_status':status})
            if not transient or retry==1:
                raise AssessmentError('The model service request could not complete.',code=code) from None

    def _request(self,client,stage,system,user,schema,validator):
        from .privacy import require_safe_data, safe_message, PrivacyError
        require_safe_data({'system':system,'user':user,'schema':schema})
        self._accepted_wire = None
        messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(user,ensure_ascii=False,separators=(',',':'))}]
        limit=STAGE_LIMITS[stage]
        for attempt in range(2):
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError("Assessment time limit reached; no result saved.",code="timeout")
            attempt_start=time.monotonic()
            tokenize_payload={"model":MODEL,"messages":messages,"add_generation_prompt":True,"chat_template_kwargs":{"enable_thinking":False}}
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
            if count+limit>CONTEXT_TOKENS:
                if hasattr(self,'last_diagnostics'):self.last_diagnostics.append({'stage':stage,'attempt':attempt,'prompt_tokens':count,'max_output_tokens':limit,'context_tokens':CONTEXT_TOKENS,'failure':'budget'})
                raise AssessmentError("Full "+stage+" request exceeds context budget: "+str(count)+" prompt tokens + "+str(limit)+" reserved output tokens > "+str(CONTEXT_TOKENS)+". Instructions, proposal and evidence all contribute; evidence is never truncated.",code="budget")
            payload={"model":MODEL,"messages":messages,"max_tokens":limit,"temperature":0.2,"top_p":0.8,"chat_template_kwargs":{"enable_thinking":False},"guided_json":guided_schema(schema),"guided_decoding_backend":BACKEND}
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError('Assessment time limit reached; no result saved.',code='timeout')
            body=self._post_json(client,'/v1/chat/completions',payload,stage,'generation')
            # Screen the entire body, including reasoning, before any trace or validator.
            try:
                require_safe_data(body)
            except PrivacyError as exc:
                self.last_diagnostics.append({'stage':stage,'attempt':attempt,'failure':'privacy',
                    'privacy_boundary':'model_output','entity_types':list(exc.entity_types),
                    'privacy_findings':list(exc.findings),
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
            trace={"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"finish_reason":choice['finish_reason'],"retry_feedback":messages[0]['content'][len(system):],"thinking_detected":thinking,"raw_output":None, "output_retention":"structural_metadata_only"}
            self.last_trace.append(trace)
            if choice['finish_reason']!='stop' or thinking:
                error=AssessmentError("Truncated output or visible thinking rejected; no result saved.",code="thinking" if thinking else "truncated")
            else:
                try:
                    result=validator(content)
                    self.last_diagnostics.append({"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"usage":body.get('usage'),"latency_seconds":round(time.monotonic()-attempt_start,4),"schema_pass":True,"evidence_pass":True,"eligibility_pass":True,"thinking_detected":False})
                    self._accepted_wire = content
                    return result
                except ValidationError as exc:
                    error=schema_error(exc)
                    self.last_diagnostics.append({'stage':stage,'attempt':attempt,'validation_fields':[{'location':list(e['loc']),'type':e['type']} for e in exc.errors()[:3]]})
                except PrivacyError: raise
                except AssessmentError as exc:error=AssessmentError(safe_message(exc),code=exc.code)
            self.last_diagnostics.append({"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"failure":error.code,"latency_seconds":round(time.monotonic()-attempt_start,4),"schema_pass":error.code in {'evidence','eligibility'},"evidence_pass":False if error.code=='evidence' else None,"eligibility_pass":False if error.code=='eligibility' else None,"thinking_detected":thinking})
            if attempt==1:raise error
            # No previous citizen/model output is copied into feedback. Recount
            # the whole message before every retry; do not truncate evidence.
            messages[0]['content']=system+'\nRetry: previous output failed '+error.code+' checks: '+safe_message(error)+' Return a fresh object matching the supplied schema and cite only listed passage IDs. Do not add missing facts; use empty optional fields when no detail is supported.'
