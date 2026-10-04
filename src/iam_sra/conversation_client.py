"""Explicit score-free interpretation and confirmation-bound numeric review.

The old one-shot client is retained for historical synthetic comparisons only.
This is the sole live client used by the guided application.
"""
import hashlib
import copy
import time
import httpx
from pydantic import Field, ValidationError
from .llm_client import LLMClient, _LOCK, BACKEND, schema_error, STAGE_LIMITS
from .schemas import Strict, MappingAssessment, Concern, Assessment
from .evidence import reference_schema
from .interpretation import check_meaning, verify
from .assessment import AssessmentError
from .settings import ROOT, CONCERNS, SCENARIO, POLICY, config

class NumericReview(Strict):
    score: int | None = Field(ge=1,le=9)
    rationale: str = Field(max_length=400)

class ScopeReview(Strict):
    supported: bool
    rationale: str = Field(max_length=300)

STAGE_LIMITS['scope_review']=300

class ConversationClient(LLMClient):
    def _start(self):
        self.last_diagnostics=[];self.last_trace=[];self.last_raw_scores={}
        self.last_score_decisions=[];self.last_candidate_projections=[]
        self._deadline=time.monotonic()+180
        self.last_settings={'enable_thinking':False,'backend':BACKEND,'context_tokens':4096,
            'temperature':0.2,'top_p':0.8,'stage_deadline_seconds':180,'confirmation_scoring':True,
            'stage_output_limits':dict(STAGE_LIMITS),'maximum_attempts_per_call':2,
            'model':config('model'),'expected_deployment':{'dtype':'half','engine':'V0','attention':'XFORMERS','tensor_parallel_size':1,'max_num_seqs':1}}

    def interpret(self, evidence, context='original', proposal=None, target=None):
        """Exactly one mapping stage (+ bounded retry); no scorer or rubric."""
        with _LOCK:
            self._start()
            sources={k:v.text for k,v in evidence.items() if v.context==context and v.source!='question'}
            if not sources:raise AssessmentError('No citizen testimony for this context.',code='evidence')
            registry='\n'.join(cid+' ['+','.join(c['facets'])+']: '+c['scope']+' EXCLUDE: '+c['exclusion'] for cid,c in CONCERNS.items() if target is None or target==cid or target not in CONCERNS)
            system=(ROOT/'prompts/assessment.txt').read_text()+'\nRegistry:\n'+registry
            system+='\nInterpret ONLY the proposal context '+context+'. Scenario/question wording is background, NOT evidence. Use original-position fields for the position in THIS context. No numeric scoring. Hypothetical responses do not revise the original proposal.'
            system+='\nProposal: '+(proposal or SCENARIO['text'])
            if context=='hypothetical:q1':system+='\nQ1 privacy resolved is ONLY a viewing-privacy interpretation. It does not establish full-route acceptance: current_route_stance stays unassessed unless separate citizen testimony explicitly accepts or rejects the whole hypothetical route. Shielding does not assure cybersecurity.'
            if context=='hypothetical:q2':system+='\nQ2 is a bundled altitude/sound/curfew proposal. Rejecting residential routing or visual clutter alone does not establish acoustic acceptance/rejection; leave noise ambiguous if no noise position is stated.'
            if target:system+='\nThis is user-authored correction for '+target+'. Map that meaning only; omissions in this patch do not delete other concerns.'
            self.last_settings['mapping_prompt_sha256']=hashlib.sha256(system.encode()).hexdigest()
            schema=reference_schema(MappingAssessment.model_json_schema(),sources)
            base=schema['$defs']['MappingConcern']
            mapped=copy.deepcopy(base);ambiguous=copy.deepcopy(base)
            facets=[]
            for definition in CONCERNS.values():
                allowed=definition['facets']
                facets.extend([[f] for f in allowed])
                facets.extend([[a,b] for i,a in enumerate(allowed) for b in allowed[i+1:]])
            mapped['properties']['status']={'type':'string','const':'mapped'}
            mapped['properties']['facets']={'type':'array','enum':facets}
            mapped['properties']['excerpts']={'type':'array','enum':[[ref] for ref in sources]}
            ambiguous['properties']['status']={'type':'string','const':'needs_clarification'}
            ambiguous['properties']['facets']={'type':'array','enum':[[]]+facets}
            ambiguous['properties']['excerpts']={'type':'array','enum':[[]]+[[ref] for ref in sources]}
            schema['$defs']['MappingConcern']={'oneOf':[mapped,ambiguous]}
            def validate(raw):
                result=MappingAssessment.model_validate_json(raw)
                check_meaning(result,evidence,context)
                return result
            try:
                with httpx.Client(timeout=120,trust_env=False) as client:
                    meaning=self._request(client,'mapping',system,{'citizen_passages':[evidence[k].model_dump() for k in sources]},schema,validate)
                    # General FN medical-benefit facet nomination, BEFORE user
                    # confirmation. It assigns no numbers and implies no equity.
                    from .schemas import MappingConcern
                    benefit=meaning.medical_public_benefit_support
                    if target is None and benefit.interpretation in {'supported','opposed','mixed'} and benefit.excerpts and not any(c.concern_id=='welfare_equity' for c in meaning.concerns):
                        meaning.concerns.append(MappingConcern(concern_id='welfare_equity',status='mapped',position=benefit.interpretation,
                            facets=['medical_public_benefit'],excerpts=benefit.excerpts,rationale='Medical public benefit, not distributive equity.',mapping_note='medical_benefit_not_equity'))
                        self.last_candidate_projections.append({'concern_id':'welfare_equity','rule':'FN medical-benefit facet nomination before confirmation','score_assigned':False})
                    # Numeric-free semantic scope review catches broad discovery
                    # overmapping BEFORE asking a citizen to confirm it.
                    for candidate in meaning.concerns:
                        definition=CONCERNS[candidate.concern_id]
                        scope_system=(ROOT/'prompts/scope-review.txt').read_text()+'\nScope: '+definition['scope']+'\nINCLUDE: '+definition['inclusion']+'\nEXCLUDE: '+definition['exclusion']
                        self.last_settings.setdefault('scope_prompt_sha256',{})[candidate.concern_id]=hashlib.sha256(scope_system.encode()).hexdigest()
                        review=self._request(client,'scope_review',scope_system,{'context':context,'candidate':candidate.model_dump(),
                            'citizen_evidence':[evidence[r].model_dump() for r in dict.fromkeys(candidate.excerpts+candidate.conditions)]},ScopeReview.model_json_schema(),ScopeReview.model_validate_json)
                        if not review.supported:
                            candidate.status='needs_clarification';candidate.mapping_note='ambiguous_needs_clarification'
                            candidate.rationale=review.rationale
                    return meaning
            except (httpx.HTTPError,KeyError,IndexError,TypeError,AttributeError) as exc:
                raise AssessmentError('Live interpretation unavailable; no mock fallback.',code='transport') from exc

    def score(self, confirmed, only=None, unavailable=None):
        """Frozen meanings enter scoring; models cannot output semantic changes."""
        meaning,evidence=verify(confirmed)
        with _LOCK:
            self._start()
            conditional=confirmed['context']!='original'
            policy=config('reassessment')
            anchors=policy['conditional_anchors'] if conditional else POLICY['anchors']
            base=(ROOT/'prompts/confirmed-scoring.txt').read_text()
            self.last_settings.update({'rubric':policy['conditional_rubric'] if conditional else POLICY['rubric_version'],
                'confirmed_sha256':confirmed['sha256'],'context':confirmed['context'],
                'prompt_sha256':hashlib.sha256(base.encode()).hexdigest()})
            scored=[]
            try:
                with httpx.Client(timeout=120,trust_env=False) as client:
                    for candidate in meaning.concerns:
                        if only is not None and candidate.concern_id not in only:continue
                        data=candidate.model_dump();data.pop('status')
                        eligible=candidate.concern_id not in (unavailable or set()) and candidate.status=='mapped' and candidate.facets and candidate.excerpts and (
                            candidate.position in {'supported','opposed','mixed'} or candidate.conditional_willingness in {'willing','not_willing'})
                        if not eligible:
                            review=NumericReview(score=None,rationale='Insufficient or ambiguous confirmed evidence; not assessed.')
                        else:
                            cid=candidate.concern_id;definition=CONCERNS[cid]
                            system=base+'\nContext: '+confirmed['context']+'\nAnchors: '+'; '.join(k+'='+v for k,v in anchors.items())
                            system+='\nScope: '+definition['scope']+' EXCLUDE: '+definition['exclusion']
                            if not conditional:system+='\nConcern anchors: '+definition['illustrative_anchors']
                            self.last_settings.setdefault('numeric_prompt_sha256',{})[cid]=hashlib.sha256(system.encode()).hexdigest()
                            refs=list(dict.fromkeys(candidate.excerpts+candidate.conditions))
                            history_refs=set(refs)|set(confirmed.get('supporting_history_by_concern',{}).get(cid,[]))
                            schema=NumericReview.model_json_schema()
                            schema['properties']['score']={'enum':[None]+list(range(1,10))}
                            review=self._request(client,'scoring',system,{'confirmed_meaning':candidate.model_dump(),
                                'proposal':confirmed['proposal'],'citizen_evidence':[evidence[ref].model_dump() for ref in refs],
                                'original_testimony_history':[item.model_dump() for key,item in evidence.items() if key in history_refs and item.source=='citizen_original'] if not conditional else [],
                                'history_note':'Original testimony is retained context. The explicitly confirmed corrected meaning governs this concern; other topics must not change its score.'},schema,NumericReview.model_validate_json)
                            if review.score is None:
                                raise AssessmentError('The numeric reviewer could not score '+cid+' from the confirmed evidence: '+review.rationale+' Review the cited evidence or clarify this meaning.',code='clarification')
                            self.last_raw_scores[cid]=review.score
                        data.update(status='assessed' if review.score is not None else 'unassessed',score=review.score,rationale=review.rationale,
                            excerpts=[evidence[r].text for r in candidate.excerpts],conditions=[evidence[r].text for r in candidate.conditions])
                        scored.append(Concern.model_validate(data))
                    dims={name:{**getattr(meaning,name).model_dump(),'excerpts':[evidence[r].text for r in getattr(meaning,name).excerpts]} for name in ['awareness_understanding','medical_public_benefit_support','current_route_stance']}
                    present={c.concern_id for c in scored}
                    scored.extend(Concern(concern_id=cid,status='unassessed',position='unassessed',score=None,excerpts=[],rationale='No confirmed evidence assessed.') for cid in CONCERNS if cid not in present)
                    return Assessment(scenario_id=meaning.scenario_id,concerns=scored,acceptance_conditions=[evidence[r].text for r in meaning.acceptance_conditions],**dims)
            except ValidationError as exc:
                raise AssessmentError('Confirmed evidence is inconsistent: '+str(schema_error(exc)),code='clarification') from exc
            except (httpx.HTTPError,KeyError,IndexError,TypeError,AttributeError) as exc:
                raise AssessmentError('Live score review unavailable; no mock fallback.',code='transport') from exc
