"""Bounded semantic mapping followed by independent per-concern review."""
import hashlib
import copy
import json
import threading
import time
import httpx
from pydantic import ValidationError
from .settings import ROOT, CONCERNS, SCENARIO, POLICY, MODEL, BASE_URL, CONTEXT_TOKENS
from .schemas import Assessment, Concern, MappingAssessment, ScoreBatch
from .evidence import passages, reference_schema, resolve
from .assessment import parse_assessment, check_input, AssessmentError

_LOCK=threading.Lock()
STAGE_LIMITS={"mapping":1400,"scoring":300}
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

class LLMClient:
    def __init__(self,base_url=BASE_URL):self.base_url=base_url.rstrip('/')

    def _request(self,client,stage,system,user,schema,validator):
        messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(user,ensure_ascii=False,separators=(',',':'))}]
        limit=STAGE_LIMITS[stage]
        for attempt in range(2):
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError("Assessment time limit reached; no result saved.",code="timeout")
            timeout=min(120,remaining)
            tokenized=client.post(self.base_url+'/tokenize',json={"model":MODEL,"messages":messages,"add_generation_prompt":True,"chat_template_kwargs":{"enable_thinking":False}},timeout=timeout)
            tokenized.raise_for_status();count=tokenized.json()['count']
            if type(count) is not int or count<0:raise AssessmentError("Invalid token count; no assessment saved.",code="transport")
            if count+limit>CONTEXT_TOKENS:raise AssessmentError("Full "+stage+" prompt plus output exceeds 4096 tokens; shorten your answer. Evidence is never truncated.",code="budget")
            payload={"model":MODEL,"messages":messages,"max_tokens":limit,"temperature":0.2,"top_p":0.8,"chat_template_kwargs":{"enable_thinking":False},"guided_json":guided_schema(schema),"guided_decoding_backend":BACKEND}
            remaining=self._deadline-time.monotonic()
            if remaining<=0:raise AssessmentError('Assessment time limit reached; no result saved.',code='timeout')
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
                    self.last_diagnostics.append({"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"usage":body.get('usage'),"schema_pass":True,"evidence_pass":True,"eligibility_pass":True,"thinking_detected":False})
                    return result
                except ValidationError as exc:error=schema_error(exc)
                except AssessmentError as exc:error=exc
            self.last_diagnostics.append({"stage":stage,"attempt":attempt,"prompt_tokens":count,"max_output_tokens":limit,"failure":error.code,"schema_pass":error.code in {'evidence','eligibility'},"evidence_pass":False if error.code=='evidence' else None,"eligibility_pass":False if error.code=='eligibility' else None,"thinking_detected":thinking})
            if attempt==1:raise error
            # No previous citizen/model output is copied into feedback. Recount
            # the whole message before every retry; do not truncate evidence.
            messages[0]['content']=system+'\nRetry: previous output failed '+error.code+' checks: '+str(error)+' Use every required field, allowed facet and listed passage ID. Unassessed dimensions need empty excerpts. Keep rationales short. Return fresh JSON.'

    def __call__(self,text):
        with _LOCK:
            self.last_diagnostics=[];self.last_trace=[];self.last_raw_scores={};self.last_score_decisions=[];self.last_candidate_projections=[];self.last_settings={}
            self._deadline=time.monotonic()+180
            check_input(text);sources=passages(text)
            citizen=[{"id":i,"text":t} for i,t in sources.items()]
            registry='\n'.join(i+' ['+','.join(c['facets'])+']: '+c['scope']+' EXCLUDE: '+c['exclusion'] for i,c in CONCERNS.items())
            mapping_system=(ROOT/'prompts/assessment.txt').read_text()+'\nRegistry:\n'+registry+'\nHypothetical scenario: '+SCENARIO['text']
            scoring_base=(ROOT/'prompts/scoring.txt').read_text()
            self.last_settings={"temperature":0.2,"top_p":0.8,"seed":None,"enable_thinking":False,"guided_backend":BACKEND,"stage_output_limits":STAGE_LIMITS,"context_tokens":CONTEXT_TOKENS,"timeout_seconds":120,"maximum_attempts_per_stage":2,"maximum_calls":32,"assessment_deadline_seconds":180,"mapping_prompt_sha256":hashlib.sha256(mapping_system.encode()).hexdigest(),"scoring_prompt_sha256":hashlib.sha256(scoring_base.encode()).hexdigest(),"deployment":{"dtype":"half","engine":"V0","attention":"XFORMERS","tensor_parallel_size":1,"max_num_seqs":1}}
            try:
                with httpx.Client(timeout=120,trust_env=False) as client:
                    mapping_schema=reference_schema(MappingAssessment.model_json_schema(),sources)
                    def validate_mapping(raw):
                        wire=MappingAssessment.model_validate_json(raw)
                        # Resolve and check every reference; both representations
                        # are retained only in memory for this explicit session.
                        resolved=MappingAssessment.model_validate_json(resolve(raw,sources,MappingAssessment))
                        return wire,resolved
                    wire,mapped=self._request(client,'mapping',mapping_system,{"citizen_passages":citizen},mapping_schema,validate_mapping)
                    # FN explicitly maps medical public-service support to one
                    # welfare facet. A positive/negative/mixed support dimension
                    # can therefore nominate a missing facet for independent
                    # review. This never assigns a score or implies equity.
                    benefit=wire.medical_public_benefit_support
                    present={c.concern_id for c in wire.concerns}
                    if benefit.interpretation in {'supported','opposed','mixed'} and benefit.excerpts and 'welfare_equity' not in present:
                        candidate={"concern_id":"welfare_equity","status":"mapped","position":benefit.interpretation,"facets":["medical_public_benefit"],"conditional_willingness":"not_stated","conditions":[],"excerpts":benefit.excerpts,"rationale":"Medical-support interpretation nominates a welfare facet for independent evidence review.","mapping_note":"medical_benefit_not_equity"}
                        wire_data=wire.model_dump();wire_data['concerns'].append(candidate)
                        wire=MappingAssessment.model_validate(wire_data)
                        mapped=MappingAssessment.model_validate_json(resolve(wire.model_dump_json(),sources,MappingAssessment))
                        self.last_candidate_projections.append({"rule":"medical_support_facet_review","concern_id":"welfare_equity","facet":"medical_public_benefit","source_interpretation":benefit.interpretation,"evidence_passages":benefit.excerpts,"score_assigned":False})
                    if not mapped.concerns:
                        result=Assessment.model_validate({**mapped.model_dump(),"concerns":[]})
                        return parse_assessment(result.model_dump_json(),text)
                    data=mapped.model_dump();decisions=[]
                    anchors='; '.join(k+'='+v for k,v in POLICY['anchors'].items())
                    for candidate in data['concerns']:
                        if candidate['status']=='needs_clarification' and not (candidate['excerpts'] or candidate['conditions']):
                            candidate['status']='unassessed';candidate['score']=None
                            continue
                        cid=candidate['concern_id'];definition=CONCERNS[cid]
                        guidance=cid+': '+definition['inclusion']+' EXCLUDE: '+definition['exclusion']+' ANCHOR GUIDE: '+definition['illustrative_anchors']
                        scoring_system=scoring_base+'\nOnly review this concern: '+guidance+'\nGeneral anchors: '+anchors
                        self.last_settings.setdefault('scoring_prompt_hashes',{})[cid]=hashlib.sha256(scoring_system.encode()).hexdigest()
                        score_schema=ScoreBatch.model_json_schema();score_def=score_schema['$defs']['ScoreDecision']
                        # Classify scope before choosing a status or anchor. The
                        # review cannot presume the candidate is a valid mapping.
                        order=['concern_id','scope_supported','status','decision','position','facets','excerpts','conditional_willingness','conditions','score','rationale']
                        score_def['properties']={key:score_def['properties'][key] for key in order}
                        score_def['required']=list(score_def['properties'])
                        score_def['properties']['concern_id']={"type":"string","const":cid}
                        score_def['properties']['conditions']['items']={"type":"string","enum":list(sources)}
                        # This pinned backend drops maxItems. Literal array enums
                        # enforce a bounded evidence selection during generation.
                        # Every passage remains eligible; conditions are separate.
                        score_def['properties']['excerpts']={"type":"array","enum":[[]]+[[ref] for ref in sources]}
                        allowed=definition['facets']
                        score_def['properties']['facets']={"type":"array","enum":[[]]+[[f] for f in allowed]+[[a,b] for i,a in enumerate(allowed) for b in allowed[i+1:]]}
                        retained=copy.deepcopy(score_def)
                        excluded=copy.deepcopy(score_def)
                        rp=retained['properties'];ep=excluded['properties']
                        rp['status']={'type':'string','const':'assessed'}
                        rp['decision']={'type':'string','const':'retained'}
                        rp['scope_supported']={'type':'boolean','const':True}
                        rp['score']={'type':'integer','enum':list(range(1,10))}
                        for field in ['excerpts','facets']:
                            rp[field]['enum']=[items for items in rp[field]['enum'] if items]
                        ep['status']={'type':'string','const':'unassessed'}
                        ep['decision']={'type':'string','enum':['excluded','needs_clarification']}
                        ep['score']={'type':'null','const':None}
                        score_schema['$defs']['ScoreDecision']={'oneOf':[retained,excluded]}
                        def validate_score(raw):
                            batch=ScoreBatch.model_validate_json(raw)
                            if len(batch.concern_scores)!=1 or batch.concern_scores[0].concern_id!=cid:
                                raise AssessmentError('Review exactly the requested concern once; no result saved.',code='schema')
                            decision=batch.concern_scores[0]
                            if any(ref not in sources for ref in decision.conditions+decision.excerpts):raise AssessmentError('Review selected an unknown condition passage.',code='evidence')
                            check={**candidate,'status':decision.status,'score':decision.score,'rationale':decision.rationale,'conditional_willingness':decision.conditional_willingness,'conditions':[sources[ref] for ref in decision.conditions],'position':decision.position,'facets':decision.facets,'excerpts':[sources[ref] for ref in decision.excerpts]}
                            Concern.model_validate(check)
                            return decision
                        # The original text is authoritative. Do not pass the
                        # first model's stance/score/willingness as trusted facts.
                        decision=self._request(client,'scoring',scoring_system,{"citizen_passages":citizen,"requested_concern_id":cid},score_schema,validate_score)
                        decisions.append(decision)
                        candidate.update(status=decision.status,score=decision.score,rationale=decision.rationale,conditional_willingness=decision.conditional_willingness,conditions=[sources[ref] for ref in decision.conditions],position=decision.position,facets=decision.facets,excerpts=[sources[ref] for ref in decision.excerpts])
                        if decision.status=='unassessed':
                            candidate['mapping_note']='ambiguous_needs_clarification'
                    result=parse_assessment(json.dumps(data),text)
                    self.last_raw_scores={c.concern_id:c.score for c in decisions}
                    self.last_score_decisions=[c.model_dump() for c in decisions]
                    return result
            except (httpx.HTTPError,KeyError,IndexError,TypeError,AttributeError,ValueError) as exc:
                if isinstance(exc,AssessmentError):raise
                raise AssessmentError("Live model unavailable or response invalid; no mock fallback or result saved.",code="transport") from exc
