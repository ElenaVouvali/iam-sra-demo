"""Confirmation-gated sessions. No model numeric calls occur during interpretation."""
import json
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from .assessment import AssessmentError, check_input
from .schemas import MappingAssessment, SCHEMA_VERSION
from .evidence import passages
from .interpretation import EvidenceItem, freeze, verify, semantic_key, comparison
from .validation import select_questions, outcome, conclusions
from .scoring import aggregate
from .settings import CONCERNS, SCENARIO, QUESTIONS, POLICY, REGISTRY, config
from .legacy_session import inference_record

class State(str, Enum):
    SCENARIO='scenario'
    ANSWER='citizen_answer'
    INTERPRETATION='interpretation'
    CONFIRMED='confirmed_interpretation'
    INITIAL='initial_scores'
    FOLLOWUPS='follow_ups'
    UPDATED='updated_interpretation'
    UPDATE_CONFIRMED='confirmed_updated_interpretation'
    FINAL='comparison_export'

@dataclass
class Session:
    state: State = State.SCENARIO
    text: str = ''
    evidence: dict = field(default_factory=dict)
    draft: MappingAssessment | None = None
    version: int = 0
    corrections: list = field(default_factory=list)
    interpretations: list = field(default_factory=list)
    confirmations: list = field(default_factory=list)
    responses: list = field(default_factory=list)
    conflicts: dict = field(default_factory=dict)
    include_reference_questions: bool = False
    confirmed: dict | None = None
    updated_confirmed: dict | None = None
    conditional_confirmed: dict | None = None
    conditional_draft: MappingAssessment | None = None
    joint: dict | None = None
    joint_history: list = field(default_factory=list)
    inference: list = field(default_factory=list)
    _initial: dict | None = None
    _final: dict | None = None
    _conditional: dict | None = None
    _questions: list = field(default_factory=list)
    _reasons: dict = field(default_factory=dict)

    def _require(self,*states):
        if self.state not in states:raise ValueError('Invalid session transition')

    def begin(self):
        self._require(State.SCENARIO);self.state=State.ANSWER

    def _record(self,client,stage):
        self.inference.append({'stage':stage,'version':self.version,'diagnostics':deepcopy(getattr(client,'last_diagnostics',[])),
            'settings':deepcopy(getattr(client,'last_settings',{})), 'raw_model_scores':deepcopy(getattr(client,'last_raw_scores',{})),
            'candidate_projections':deepcopy(getattr(client,'last_candidate_projections',[]))})

    def _remember(self,kind):
        self.interpretations.append({'version':self.version,'kind':kind,'model_proposed_meaning':self.draft.model_dump(),
            'conditional_meaning':self.conditional_draft.model_dump() if self.conditional_draft else None})

    def submit(self,text,client):
        self._require(State.ANSWER);check_input(text)
        items={f'O.{k}':EvidenceItem(id=f'O.{k}',text=v,context='original',source='citizen_original') for k,v in passages(text).items()}
        result=client.interpret(items)
        self.text=text;self.evidence=items;self.draft=result.model_copy(deep=True)
        self.version=1;self._remember('initial proposal');self._record(client,'interpretation')
        self.state=State.INTERPRETATION

    def _invalidate(self):
        self.confirmed=None;self.updated_confirmed=None;self.conditional_confirmed=None
        self._final=None;self._conditional=None
        self.version+=1
        self.state=State.UPDATED if self._initial else State.INTERPRETATION

    def correct(self,target,text,reason,client):
        self._require(State.INTERPRETATION,State.CONFIRMED,State.UPDATED,State.UPDATE_CONFIRMED)
        if target not in CONCERNS and target not in ['current_route_stance','medical_public_benefit_support','awareness_understanding']:
            raise ValueError('Unknown interpretation target')
        check_input(text);check_input(reason)
        number=len(self.corrections)+1;key=f'C{number}.testimony'
        item=EvidenceItem(id=key,text=text,context='original',source='citizen_correction')
        patch=client.interpret({key:item},target=target)
        before=self.draft.model_dump()
        if target in CONCERNS:
            old=next((c for c in self.draft.concerns if c.concern_id==target),None)
            match=next((c for c in patch.concerns if c.concern_id==target),None)
            if match is None:raise AssessmentError('Correction has no clear mapping for this concern. State your position or uncertainty explicitly.',code='clarification')
            self.draft.concerns=[c for c in self.draft.concerns if c.concern_id!=target]+[match.model_copy(deep=True)]
            still_used={r for c in self.draft.concerns for r in c.conditions}
            self.draft.acceptance_conditions=list(dict.fromkeys([r for r in self.draft.acceptance_conditions if not old or r not in old.conditions or r in still_used]+match.conditions))
            self._reasons[target]='Reassessed from confirmed user-authored original-proposal clarification.'
            self.conflicts.pop('original:'+target,None)
        else:
            setattr(self.draft,target,getattr(patch,target).model_copy(deep=True))
            if target=='current_route_stance':self.draft.acceptance_conditions=list(patch.acceptance_conditions)
            self.conflicts.pop('original:'+target,None)
        self.evidence[key]=item
        self.corrections.append({'id':f'C{number}','target':target,'evidence_id':key,'citizen_text':text,'reason':reason,
            'provenance':'user_authored_testimony; model proposes interpretation; confirmation required',
            'before':before,'after':self.draft.model_dump()})
        self._invalidate();self._remember('correction');self._record(client,'correction interpretation')

    def confirm(self,agreed):
        self._require(State.INTERPRETATION)
        if agreed is not True:raise ValueError('Explicit confirmation is required before scoring.')
        if self.conflicts:raise ValueError('Resolve the targeted clarification questions before confirmation.')
        self.confirmed=freeze(self.draft,self.evidence,self.version,'original',SCENARIO['text'],supporting_history=self._supporting_history())
        self.confirmations.append(deepcopy(self.confirmed));self.state=State.CONFIRMED

    def _supporting_history(self):
        history={}
        for version in self.interpretations:
            for c in version['model_proposed_meaning']['concerns']:
                refs=[r for r in c['excerpts']+c.get('conditions',[]) if r in self.evidence and self.evidence[r].source=='citizen_original']
                history[c['concern_id']]=list(dict.fromkeys(history.get(c['concern_id'],[])+refs))
        return history

    def correct_modified(self,target,text,reason,client):
        self._require(State.UPDATED,State.UPDATE_CONFIRMED)
        if self.conditional_draft is None or target not in list(CONCERNS)+['current_route_stance','medical_public_benefit_support','awareness_understanding']:raise ValueError('Select an existing modified-context meaning.')
        check_input(text);check_input(reason)
        key=f'M{len(self.corrections)+1}.testimony'
        item=EvidenceItem(id=key,text=text,context='modified',source='citizen_correction')
        patch=client.interpret({key:item},'modified',self.combined_proposal,target)
        before=self.conditional_draft.model_dump()
        if target in CONCERNS:
            match=next((c for c in patch.concerns if c.concern_id==target),None)
            if match is None:raise ValueError('State the concern-specific position or uncertainty explicitly.')
            self.conditional_draft.concerns=[c for c in self.conditional_draft.concerns if c.concern_id!=target]+[match.model_copy(deep=True)]
        else:
            setattr(self.conditional_draft,target,getattr(patch,target).model_copy(deep=True))
            self.conflicts.pop('joint:'+target,None)
        self.evidence[key]=item
        self.corrections.append({'id':key,'target':target,'context':'modified','citizen_text':text,'reason':reason,
            'before':before,'after':self.conditional_draft.model_dump(),'provenance':'user_authored_testimony'})
        self._invalidate();self._remember('modified correction');self._record(client,'modified correction interpretation')

    def _snapshot(self,assessment,record,kind,client,reasons=None):
        inference=inference_record(assessment,client)
        inference['score_policy']='Numeric-only review of confirmed meanings; carry-forward and exclusions are recorded separately. Python aggregates per profile.'
        return {'kind':kind,'interpretation_sha256':record['sha256'],'interpretation_version':record['version'],
            'context':record['context'],'proposal':record['proposal'],'assessment':assessment.model_dump(),
            'aggregate':aggregate(assessment),'update_reasons':deepcopy(reasons or {}),
            'rubric':config('reassessment')['conditional_rubric'] if kind=='conditional' else POLICY['rubric_version'],
            'rubric_anchors':deepcopy(config('reassessment')['conditional_anchors'] if kind=='conditional' else POLICY['anchors']),
            'policy':config('reassessment')['version'],'inference':inference}

    def score_initial(self,client):
        self._require(State.CONFIRMED);verify(self.confirmed)
        try:result=client.score(deepcopy(self.confirmed))
        except AssessmentError as exc:
            self._record(client,'initial scoring failure')
            if exc.code=='clarification':self.confirmed=None;self.state=State.INTERPRETATION
            raise
        self._initial=self._snapshot(result,self.confirmed,'initial',client)
        self._record(client,'initial scoring');self.state=State.INITIAL

    @property
    def initial(self):return deepcopy(self._initial)
    @property
    def final(self):return deepcopy(self._final)
    @property
    def conditional(self):return deepcopy(self._conditional)
    @property
    def questions(self):return deepcopy(self._questions)

    def begin_followups(self,include_reference_questions=False):
        self._require(State.INITIAL)
        self.include_reference_questions=bool(include_reference_questions)
        # Use confirmed semantics/facets, not whether numeric review succeeded.
        meaning,_=verify(self.confirmed)
        self._questions=deepcopy(list(QUESTIONS) if include_reference_questions else select_questions(meaning))
        self.state=State.FOLLOWUPS if self._questions else State.UPDATED

    def _merge_original(self,patch):
        by={c.concern_id:c for c in self.draft.concerns}
        for new in patch.concerns:
            old=by.get(new.concern_id)
            if old and (old.position!=new.position or old.conditional_willingness!=new.conditional_willingness or set(old.facets)-set(new.facets)):
                self.conflicts['original:'+new.concern_id]={'target':new.concern_id,'before':old.model_dump(),'proposed':new.model_dump(),
                    'question':'For the unchanged original proposal, which position do you mean? Clarify this concern in your own words.'}
                continue
            by[new.concern_id]=new.model_copy(deep=True)
            self._reasons[new.concern_id]='Reassessed from confirmed original-context follow-up evidence.'
        self.draft.concerns=list(by.values())
        for name in ['current_route_stance','medical_public_benefit_support','awareness_understanding']:
            new=getattr(patch,name);old=getattr(self.draft,name)
            if new.interpretation=='unassessed':continue
            if old.interpretation!='unassessed' and old.interpretation!=new.interpretation:
                self.conflicts['original:'+name]={'target':name,'before':old.model_dump(),'proposed':new.model_dump(),
                    'question':'Clarify what you mean about '+name.replace('_',' ')+' in the original proposal.'}
            else:setattr(self.draft,name,new.model_copy(deep=True))

    def respond(self,choice,clarification,client,clarification_context='hypothetical'):
        self._require(State.FOLLOWUPS)
        if clarification_context not in {'original','hypothetical'}:raise ValueError('Choose a clarification context')
        q=self._questions[len(self.responses)];qid=q['id'];r=outcome(q,choice,clarification)
        ctx='hypothetical:'+qid
        items={f'{qid}.question':EvidenceItem(id=f'{qid}.question',text=q['text'],context=ctx,source='question',question_id=qid),
            f'{qid}.choice':EvidenceItem(id=f'{qid}.choice',text=choice,context=ctx,source='citizen_choice',question_id=qid)}
        if clarification:
            key=f'{qid}.clarification';items[key]=EvidenceItem(id=key,text=clarification,
                context='original' if clarification_context=='original' else ctx,source='citizen_correction',question_id=qid)
        # Separate selection and clarification interpretation makes contradictions
        # reviewable instead of silently treating the last sentence as decisive.
        meaning=client.interpret({k:v for k,v in items.items() if v.source!='question' and v.context==ctx and v.source=='citizen_choice'},ctx,q['text']) if qid!='q3' else None
        traces=[{'stage':'choice interpretation','diagnostics':deepcopy(getattr(client,'last_diagnostics',[]))}] if meaning else []
        patch=None
        if clarification:
            key=f'{qid}.clarification';patch=client.interpret({key:items[key]},items[key].context,SCENARIO['text'] if clarification_context=='original' else q['text'])
            traces.append({'stage':'clarification interpretation','diagnostics':deepcopy(getattr(client,'last_diagnostics',[]))})
        self.evidence.update(items)
        if patch and clarification_context=='original':self._merge_original(patch)
        elif patch and meaning:
            for new in patch.concerns:
                old=next((c for c in meaning.concerns if c.concern_id==new.concern_id),None)
                if old and (old.position!=new.position or old.conditional_willingness!=new.conditional_willingness or set(old.facets)-set(new.facets)):
                    self.conflicts[qid+':'+new.concern_id]={'target':new.concern_id,'question_id':qid,
                        'before':old.model_dump(),'proposed':new.model_dump(),
                        'question':'Your choice and clarification differ on '+CONCERNS[new.concern_id]['label']+'. For this hypothetical, which do you mean?'}
            for name in ['current_route_stance','medical_public_benefit_support','awareness_understanding']:
                old=getattr(meaning,name);new=getattr(patch,name)
                if old.interpretation!='unassessed' and new.interpretation!='unassessed' and old.interpretation!=new.interpretation:
                    self.conflicts[qid+':'+name]={'target':name,'question_id':qid,'before':old.model_dump(),'proposed':new.model_dump(),
                        'question':'Your selected choice and clarification differ on '+name.replace('_',' ')+'. Clarify what you mean in this hypothetical.'}
        r.update(evidence_ids=list(items),clarification_context=clarification_context,
            choice_meaning=meaning.model_dump() if meaning else None,clarification_meaning=patch.model_dump() if patch else None,
            interpretation_diagnostics=traces)
        self.responses.append(r);self.version+=1;self._remember('follow-up interpretation')
        if len(self.responses)==len(self._questions):self.state=State.UPDATED

    @property
    def joint_required(self):return any(q['id'] in {'q1','q2'} for q in self._questions)
    @property
    def combined_proposal(self):
        changes=[config('reassessment')['combined_changes'][q['id']] for q in self._questions if q['id'] in {'q1','q2'}]
        return SCENARIO['text']+'\n\nApply ALL these hypothetical changes together (all other scenario details stay as stated):\n'+'\n'.join(changes)

    def resolve_conflict(self,key,text,client):
        self._require(State.UPDATED)
        if key not in self.conflicts:raise ValueError('Unknown clarification request')
        problem=self.conflicts[key]
        if key.startswith('joint:'):
            self.correct_modified(problem['target'],text,'Explicit resolution of combined-proposal choice/text conflict',client)
            return
        if key.startswith('original:'):
            self.correct(problem['target'],text,'Explicit resolution of conflicting original-proposal interpretations',client)
            return
        check_input(text);qid=problem['question_id'];ctx='hypothetical:'+qid
        eid=f'R{len(self.corrections)+1}.testimony'
        item=EvidenceItem(id=eid,text=text,context=ctx,source='citizen_correction',question_id=qid)
        q=next(q for q in self._questions if q['id']==qid)
        patch=client.interpret({eid:item},ctx,q['text'],problem['target'])
        supported=any(c.concern_id==problem['target'] for c in patch.concerns) if problem['target'] in CONCERNS else getattr(patch,problem['target']).interpretation!='unassessed'
        if not supported:raise ValueError('Clarify the requested meaning explicitly, including unsure if appropriate.')
        self.evidence[eid]=item
        self.corrections.append({'id':eid,'target':problem['target'],'citizen_text':text,'reason':'Explicit hypothetical conflict resolution',
            'context':ctx,'resolved_conflict':deepcopy(problem),'meaning':patch.model_dump()})
        response=next(r for r in self.responses if r['question_id']==qid)
        response['evidence_ids'].append(eid)
        response.setdefault('resolutions',[]).append({'target':problem['target'],'evidence_id':eid,'confirmed_proposed_meaning':patch.model_dump()})
        self.conflicts.pop(key);self._invalidate();self.joint=None;self.conditional_draft=None

    def record_joint(self,choice,remaining,text,client):
        self._require(State.UPDATED,State.UPDATE_CONFIRMED)
        if not self.joint_required:raise ValueError('No modified proposal has been presented')
        if choice not in {'accept','reject','unsure'}:raise ValueError('Unknown joint response')
        if any(cid not in CONCERNS for cid in remaining):raise ValueError('Unknown remaining concern')
        if text:check_input(text)
        items={};prefix='J'+str(len(self.joint_history)+1)
        # Retain individual gates as explicitly contextualized testimony, never
        # infer combined acceptance from them. The new joint response is required.
        for r in self.responses:
            if r['question_id'] not in {'q1','q2'}:continue
            q=r['presented_question']
            for old_id in r['evidence_ids']:
                old=self.evidence[old_id]
                if old.context=='original' or old.source=='question':continue
                eid=prefix+'.background.'+old_id
                resolved=old_id in {entry['evidence_id'] for entry in r.get('resolutions',[])}
                items[eid]=EvidenceItem(id=eid,text=old.text,context='modified',source='citizen_resolved_prior_gate' if resolved else 'citizen_prior_gate',question_id=q['id'])
        statement={'accept':'I accept this exact combined proposal.','reject':'I reject this exact combined proposal.','unsure':'I am unsure about this exact combined proposal.'}[choice]
        items[prefix+'.choice']=EvidenceItem(id=prefix+'.choice',text=statement,context='modified',source='citizen_choice')
        if remaining:
            items[prefix+'.remaining']=EvidenceItem(id=prefix+'.remaining',text='My remaining concerns are: '+', '.join(CONCERNS[c]['label'] for c in remaining),context='modified',source='citizen_choice')
        if text:items[prefix+'.clarification']=EvidenceItem(id=prefix+'.clarification',text=text,context='modified',source='citizen_correction')
        proposal=self.combined_proposal
        meaning=client.interpret(items,'modified',proposal+'\nSeparate-gate answers are contextual history, not proof of joint acceptance. Interpret the explicit joint answer and remaining concerns; preserve untested facets.')
        self.evidence.update(items)
        self.conditional_draft=meaning.model_copy(deep=True)
        self.joint={'choice':choice,'remaining_concern_ids':list(remaining),'clarification':text,'proposal':proposal,
            'evidence_ids':list(items),'history_links':{eid:eid.removeprefix(prefix+'.background.') for eid in items if eid.startswith(prefix+'.background.')},
            'provenance':'explicit user choice; question context supplied separately by application'}
        self.joint_history.append({**deepcopy(self.joint),'version':self.version+1,'evidence_records':{k:v.model_dump() for k,v in items.items()}})
        self.conflicts.pop('joint:current_route_stance',None)
        actual=meaning.current_route_stance.interpretation
        expected={'accept':'supported','reject':'opposed','unsure':'uncertain'}[choice]
        if actual in {'supported','opposed'} and expected in {'supported','opposed'} and actual!=expected:
            self.conflicts['joint:current_route_stance']={'target':'current_route_stance','choice':choice,'proposed':meaning.current_route_stance.model_dump(),
                'question':'Your combined-proposal choice and interpreted testimony conflict. Do you accept or reject this exact proposal? Clarify in your own words.'}
        self._invalidate();self._remember('joint modified interpretation');self._record(client,'joint interpretation')

    def confirm_updated(self,agreed):
        self._require(State.UPDATED)
        if agreed is not True:raise ValueError('Explicit updated-meaning confirmation is required.')
        if self.conflicts:raise ValueError('Resolve conflicting answers before confirming.')
        if self.joint_required and self.joint is None:raise ValueError('Respond to the exact combined proposal first, including unsure.')
        self.updated_confirmed=freeze(self.draft,self.evidence,self.version,'original',SCENARIO['text'],supporting_history=self._supporting_history())
        if self.joint and self.joint['choice']!='unsure':
            self.conditional_confirmed=freeze(self.conditional_draft,self.evidence,self.version,'modified',self.joint['proposal'])
        self.confirmations.extend(deepcopy([c for c in [self.updated_confirmed,self.conditional_confirmed] if c]))
        self.state=State.UPDATE_CONFIRMED

    def score_final(self,client):
        try:return self._score_final(client)
        except AssessmentError as exc:
            self._record(client,'final scoring failure')
            if exc.code=='clarification':
                self.updated_confirmed=None;self.conditional_confirmed=None;self.state=State.UPDATED
            raise

    def _score_final(self,client):
        self._require(State.UPDATE_CONFIRMED)
        original,_=verify(self.updated_confirmed)
        initial_record=next(r for r in self.confirmations if r['sha256']==self._initial['interpretation_sha256'])
        initial_meaning,_=verify(initial_record)
        old={c.concern_id:c for c in initial_meaning.concerns}
        changed={c.concern_id for c in original.concerns if c.concern_id not in old or semantic_key(c)!=semantic_key(old[c.concern_id])}
        from .schemas import Assessment, Concern
        result=Assessment.model_validate(self._initial['assessment'])
        # Refresh nonnumeric dimensions from confirmed data without a model call.
        if changed:
            revised=client.score(deepcopy(self.updated_confirmed),only=changed)
            replacements={c.concern_id:c for c in revised.concerns if c.concern_id in changed}
            result.concerns=[replacements.get(c.concern_id,c) for c in result.concerns]
            for cid in changed:self._reasons.setdefault(cid,'Reassessed from relevant confirmed original-proposal evidence.')
            self._record(client,'final original scoring')
        evidence=self.updated_confirmed['evidence']
        for name in ['awareness_understanding','medical_public_benefit_support','current_route_stance']:
            dim=getattr(original,name).model_copy(deep=True);dim.excerpts=[evidence[r]['text'] for r in dim.excerpts];setattr(result,name,dim)
        result.acceptance_conditions=[evidence[r]['text'] for r in original.acceptance_conditions]
        reasons={cid:self._reasons.get(cid,'No relevant new original-proposal evidence; score carried forward unchanged.') for cid in CONCERNS}
        final=self._snapshot(result,self.updated_confirmed,'final_original',client,reasons)
        final['carried_scores']={c.concern_id:{'score':c.score,'from_snapshot':'initial','reason':reasons[c.concern_id]} for c in result.concerns if c.concern_id not in changed}
        if not changed:
            final['inference'].update(raw_model_scores={},attempts=[],raw_model_trace=[],settings={'model_call':False,'reason':'All concern scores carried from immutable initial snapshot.'})
        conditional=None
        if self.conditional_confirmed:
            profile,_=verify(self.conditional_confirmed)
            # Unknown facets cannot be erased by a successful privacy/noise gate.
            tested={'perceived_safety_privacy':{'personal_privacy'},'noise':set(CONCERNS['noise']['facets']),
                'visual_pollution':set(CONCERNS['visual_pollution']['facets'])}
            unavailable=set()
            for c in profile.concerns:
                previous=old.get(c.concern_id)
                untested=set(previous.facets)-tested.get(c.concern_id,set()) if previous else set()
                explicit_joint=any(self.evidence[r].source=='citizen_correction' and self.evidence[r].context=='modified' for r in c.excerpts) and untested.issubset(set(c.facets))
                if untested and not explicit_joint:unavailable.add(c.concern_id)
            # Exclusions are separate from the intact confirmed semantic record.
            cond_result=client.score(deepcopy(self.conditional_confirmed),unavailable=unavailable)
            conditional=self._snapshot(cond_result,self.conditional_confirmed,'conditional',client,
                {c.concern_id:('Reassessed in explicit combined hypothetical context.' if c.score is not None else c.rationale) for c in cond_result.concerns})
            conditional['scoring_exclusions']={cid:'Untested original facets remain; conditional concern score unavailable.' for cid in unavailable}
            self._record(client,'conditional scoring')
        self._final=final;self._conditional=conditional;self.state=State.FINAL

    def export(self):
        self._require(State.FINAL)
        return deepcopy({'experimental':True,'schema_version':'4.0.0','versions':{'assessment_schema':SCHEMA_VERSION,'registry':REGISTRY['version'],
            'scenario':SCENARIO['version'],'rubric':POLICY['rubric_version'],'scoring':POLICY['version'],
            'reassessment':config('reassessment'),'model':config('model'),'prompts':config('prompts')},
            'citizen_text':self.text,'evidence':{k:v.model_dump() for k,v in self.evidence.items()},
            'interpretations':self.interpretations,'confirmations':self.confirmations,'corrections':self.corrections,
            'initial':self._initial,'final_original':self._final,'conditional':self._conditional,
            'presented_questions':self._questions,'responses':self.responses,'joint_proposal_response':self.joint,
            'joint_proposal_history':self.joint_history,
            'update_reasons':self._final['update_reasons'],'comparison':comparison(self._initial,self._final,self._conditional,self._final['update_reasons']),
            'inference':self.inference,'confirmation_limit':'Agreement about meaning, not scientific validity.'})

    def json(self):return json.dumps(self.export(),ensure_ascii=False,indent=2)
    def jsonl(self):return json.dumps(self.export(),ensure_ascii=False,separators=(',',':'))+'\n'
