"""Screened, bounded request lifecycle shared by the updated model clients."""
import time
import httpx
from .llm_client import LLMTransport, BACKEND, STAGE_LIMITS
from .assessment import AssessmentError
from .settings import config

class ConversationClient(LLMTransport):
    def _start(self):
        self.last_diagnostics=[];self.last_trace=[]
        self.last_anchor_facts={};self.last_metrics={'generation_calls':0,'tokenize_calls':0,'cache_hits':0,'tokenize_cache_hits':0}
        if not hasattr(self,'session_metrics'):self.session_metrics={'generation_calls':0,'tokenize_calls':0,'latency_seconds':0.0}
        self._deadline=min(time.monotonic()+180,getattr(self,'external_deadline',float('inf')))
        self.last_settings={'enable_thinking':False,'backend':BACKEND,'context_tokens':4096,
            'temperature':0.2,'top_p':0.8,'stage_deadline_seconds':180,'screened_requests':True,
            'stage_output_limits':dict(STAGE_LIMITS),'maximum_attempts_per_call':2,
            'model':config('model'),'expected_deployment':{'dtype':'half','engine':'V0','attention':'XFORMERS','tensor_parallel_size':1,'max_num_seqs':1}}

    def bind_session(self,session_id,edit_epoch):
        scope=(session_id,edit_epoch)
        if getattr(self,'_cache_scope',None)!=scope:
            self._request_cache={};self._token_count_cache={};self._cache_scope=scope

    def _request(self,client,stage,system,user,schema,validator):
        from .privacy import require_safe_data
        require_safe_data({'system':system,'user':user,'schema':schema})
        from .interpretation import digest
        started=time.monotonic()
        from uuid import uuid4
        request_id=str(uuid4())
        task=next((k for k in ('coverage_review','requested_passages','subject_grounding','candidate_subjects',
            'relevance_recheck','relevance_check','balance_check','quotations','mapping_batch','position_review') if k in user),
            'facet_evidence' if 'nominated_passages' in user else 'interpretation')
        self.last_request_context={'stage':stage,'task':task,'facet':user.get('facet'),
            'request_id':request_id,'prompt_version':getattr(self,'prompt_version',config('prompts')['version'])}
        self.last_settings['last_request_context']=dict(self.last_request_context)
        key=digest({'stage':stage,'system':system,'user':user,'schema':schema,'endpoint':self.base_url,
            'cache_format':'validated_wire_v2',
            'model':config('model'),'request_settings':{'output_limit':STAGE_LIMITS[stage],'temperature':0.2,'top_p':0.8,'enable_thinking':False,'backend':BACKEND},'policies':{k:config(k) for k in ['concerns','prompts']}})
        cache=getattr(self,'_request_cache',{})
        callback=getattr(self,'progress',None)
        if callback:callback(stage)
        if time.monotonic()>=self._deadline:
            raise AssessmentError("Assessment time limit reached; retry with your saved confirmation.",code="timeout")
        if key in cache:
            try: require_safe_data(cache[key])
            except AssessmentError:
                cache.clear(); self._token_count_cache={}; self._accepted_wire=None
                raise
            result=validator(cache[key])
            self.last_metrics['cache_hits']+=1
            self.last_diagnostics.append({'stage':stage,'attempt':0,'cache_hit':True,'schema_pass':True,'evidence_pass':True,'thinking_detected':False,'latency_seconds':round(time.monotonic()-started,4)})
            self.last_settings.setdefault('request_metrics',[]).append({'request_id':request_id,'stage':stage,'model_calls':0,'retries':0,'cache_hit':True,'latency_seconds':round(time.monotonic()-started,4)})
            return result
        before=self.last_metrics['generation_calls'];offset=len(self.last_diagnostics)
        trace_offset=len(self.last_trace)
        try:
            result=super()._request(client,stage,system,user,schema,validator)
            # Validators may convert passage IDs into source text or otherwise
            # transform the wire format. Cache the accepted response, not the
            # transformed model, so cache hits can run the same validator.
            if hasattr(self,'_cache_scope') and len(self.last_trace)>trace_offset:
                if len(cache)>=128:cache.pop(next(iter(cache)))
                cache[key]=self._accepted_wire
                self._accepted_wire=None
            self._accepted_wire=None
            return result
        except httpx.HTTPError as exc:
            self.last_diagnostics.append({'stage':stage,'failure':'transport','http_status':getattr(getattr(exc,'response',None),'status_code',None),'latency_seconds':round(time.monotonic()-started,4)})
            raise
        finally:
            self.session_metrics['generation_calls']+=self.last_metrics['generation_calls']-before
            self.session_metrics['tokenize_calls']+=self.last_metrics['tokenize_calls']
            self.session_metrics['latency_seconds']+=time.monotonic()-started
            self.last_settings.setdefault('request_metrics',[]).append({'request_id':request_id,'stage':stage,'model_calls':self.last_metrics['generation_calls']-before,
                'retries':sum(d.get('attempt',0)>0 for d in self.last_diagnostics[offset:]),'cache_hit':False,'latency_seconds':round(time.monotonic()-started,4)})
