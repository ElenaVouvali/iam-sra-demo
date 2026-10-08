"""Bounded HTTP transport shared by the confirmed conversation client."""
import json
import hashlib
import threading
import time
from pydantic import ValidationError
from .settings import MODEL, BASE_URL, CONTEXT_TOKENS
from .assessment import AssessmentError

_LOCK=threading.Lock()
STAGE_LIMITS={"initial_interpretation":1400,"mapping":1400,"coverage_review":700,"scope_review":300,"discovery":500,"facets":1200,"scoring":500}
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

    def _request(self,client,stage,system,user,schema,validator):
        messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(user,ensure_ascii=False,separators=(',',':'))}]
        limit=STAGE_LIMITS[stage]
        for attempt in range(2):
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError("Assessment time limit reached; no result saved.",code="timeout")
            attempt_start=time.monotonic()
            timeout=min(120,remaining)
            tokenize_payload={"model":MODEL,"messages":messages,"add_generation_prompt":True,"chat_template_kwargs":{"enable_thinking":False}}
            token_key=hashlib.sha256(json.dumps({'endpoint':self.base_url,
                'model_revision':getattr(self,'last_settings',{}).get('model'),
                'payload':tokenize_payload},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            token_cache=getattr(self,'_token_count_cache',{})
            if token_key in token_cache:
                count=token_cache[token_key]
                if hasattr(self,'last_metrics'):self.last_metrics['tokenize_cache_hits']+=1
            else:
                if hasattr(self,'last_metrics'):self.last_metrics['tokenize_calls']+=1
                tokenized=client.post(self.base_url+'/tokenize',json=tokenize_payload,timeout=timeout)
                tokenized.raise_for_status();count=tokenized.json()['count']
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
            if hasattr(self,'last_metrics'):self.last_metrics['generation_calls']+=1
            response=client.post(self.base_url+'/v1/chat/completions',json=payload,timeout=min(120,remaining))
            response.raise_for_status();body=response.json();choice=body['choices'][0];message=choice['message'];content=message.get('content') or ''
            thinking=bool(message.get('reasoning_content')) or '<think>' in content or '</think>' in content
            trace={"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"finish_reason":choice['finish_reason'],"retry_feedback":messages[0]['content'][len(system):],"thinking_detected":thinking,"raw_output":None if thinking else content}
            self.last_trace.append(trace)
            if choice['finish_reason']!='stop' or thinking:
                error=AssessmentError("Truncated output or visible thinking rejected; no result saved.",code="thinking" if thinking else "truncated")
            else:
                try:
                    result=validator(content)
                    self.last_diagnostics.append({"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"usage":body.get('usage'),"latency_seconds":round(time.monotonic()-attempt_start,4),"schema_pass":True,"evidence_pass":True,"eligibility_pass":True,"thinking_detected":False})
                    return result
                except ValidationError as exc:error=schema_error(exc)
                except AssessmentError as exc:error=exc
            self.last_diagnostics.append({"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"failure":error.code,"latency_seconds":round(time.monotonic()-attempt_start,4),"schema_pass":error.code in {'evidence','eligibility'},"evidence_pass":False if error.code=='evidence' else None,"eligibility_pass":False if error.code=='eligibility' else None,"thinking_detected":thinking})
            if attempt==1:raise error
            # No previous citizen/model output is copied into feedback. Recount
            # the whole message before every retry; do not truncate evidence.
            messages[0]['content']=system+'\nRetry: previous output failed '+error.code+' checks: '+str(error)+' Use every required field, allowed facet and listed passage ID. Unassessed dimensions need empty excerpts. Keep rationales short. Return fresh JSON.'
