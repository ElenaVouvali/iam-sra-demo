"""Confirmation-gated sessions. No model numeric calls occur during interpretation."""
import json
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from .assessment import AssessmentError, check_input
from .schemas import MappingAssessment, SCHEMA_VERSION
from .evidence import passages
from .interpretation import EvidenceItem, freeze, verify, semantic_key, comparison, reconcile_original
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
    session_id: str = field(default_factory=lambda:str(uuid4()))
    state: State = State.SCENARIO
    text: str = ''
    initial_text: str = ''
    evidence: dict = field(default_factory=dict)
    draft: MappingAssessment | None = None
    version: int = 0
    discovery_finished: bool = False
    discovery_stop_reason: str | None = None
    discovery_questions: list = field(default_factory=list)
    discovery_responses: list = field(default_factory=list)
    discovery_topics: list = field(default_factory=list)
    discovery_events: list = field(default_factory=list)
    blockers: dict = field(default_factory=dict)
    acceptable_changes: dict = field(default_factory=dict)
    unmapped_issues: list = field(default_factory=list)
    no_reservations: bool = False
    reasons_explicit: bool | None = None
    discovery_candidate_exclusions: list = field(default_factory=list)
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
    presented_followups: list = field(default_factory=list)
    followup_stop_reason: str | None = None
    facet_meanings: list = field(default_factory=list)
    facet_scores: dict = field(default_factory=dict)
    transitions: list = field(default_factory=list)
    update_observations: list = field(default_factory=list)
    _pending_final_original: dict | None = None
    _reasons: dict = field(default_factory=dict)
    original_facets: dict = field(default_factory=dict)
    revision_history: list = field(default_factory=list)
    _checkpoints: dict = field(default_factory=dict)

    def _require(self,*states):
        if self.state not in states:raise ValueError('Invalid session transition')

    def _checkpoint(self,key):
        if key not in self._checkpoints:
            omitted={'_checkpoints','revision_history','inference','evidence','confirmations','interpretations','_initial','initial_text'}
            self._checkpoints[key]=deepcopy({k:v for k,v in vars(self).items() if k not in omitted})

    def _answer_prefix(self,key):
        if not any(k.startswith(key+'.') and k!=key+'.question' for k in self.evidence):return key
        n=2
        while any(k.startswith(key+f'.v{n}.') for k in self.evidence):n+=1
        return key+f'.v{n}'

    def rewind(self,question_id):
        """Restore before an answer; preserve initial snapshot and all superseded evidence."""
        if question_id not in self._checkpoints:raise ValueError('This answer is not editable.')
        history={'edited_question_id':question_id,'revision':len(self.revision_history)+1,'answers':deepcopy(self.responses),
            'discovery_answers':deepcopy(self.discovery_responses),'joint':deepcopy(self.joint),'original_text':self.text,
            'meaning':self.draft.model_dump() if self.draft else None,'snapshots':{'final_original':self.final,'conditional_modified':self.conditional},
            'presented_questions':deepcopy(self.presented_followups),'presented_discovery_questions':deepcopy(self.discovery_questions),
            'original_facet_meanings':[f.model_dump() for f in self.original_facets.values()],'updates':deepcopy(self.transitions)}
        self.revision_history.append(history)
        checkpoint=deepcopy(self._checkpoints[question_id]);keys=list(self._checkpoints);index=keys.index(question_id)
        self._checkpoints={k:v for k,v in self._checkpoints.items() if k in keys[:index+1]}
        for key,value in checkpoint.items():setattr(self,key,value)
        self.confirmed=None;self.updated_confirmed=None;self.conditional_confirmed=None
        self._final=None;self._conditional=None;self._pending_final_original=None;self.transitions=[];self.facet_scores={}
        self.version=max(self.version,max((r['version'] for r in self.interpretations),default=0))+1
        if question_id=='initial_answer':self.state=State.ANSWER
        elif any(q['id']==question_id for q in self.discovery_questions):self.state=State.INTERPRETATION;self.discovery_finished=False
        elif question_id=='combined_proposal':self.state=State.UPDATED
        else:self.state=State.FOLLOWUPS
        self.presented_followups=[q for q in self.presented_followups if any(r['question_id']==q['id'] for r in self.responses)]
        self.joint=None;self.conditional_draft=None;self.facet_meanings=[]

    def begin(self):
        self._require(State.SCENARIO);self.state=State.ANSWER

    def _record(self,client,stage):
        self.inference.append({'stage':stage,'version':self.version,'diagnostics':deepcopy(getattr(client,'last_diagnostics',[])),
            'raw_model_trace':deepcopy(getattr(client,'last_trace',[])),
            'settings':deepcopy(getattr(client,'last_settings',{})), 'raw_model_scores':deepcopy(getattr(client,'last_raw_scores',{})),
            'candidate_projections':deepcopy(getattr(client,'last_candidate_projections',[]))})

    def _remember(self,kind):
        self.interpretations.append({'version':self.version,'kind':kind,'model_proposed_meaning':self.draft.model_dump(),
            'conditional_meaning':self.conditional_draft.model_dump() if self.conditional_draft else None,
            'original_facet_meanings':[f.model_dump() for f in self.original_facets.values()]})

    def submit(self,text,client):
        self._require(State.ANSWER);check_input(text)
        self._checkpoint('initial_answer')
        prefix='O' if 'O.p001' not in self.evidence else 'O'+str(len(self.revision_history)+1)
        items={f'{prefix}.{k}':EvidenceItem(id=f'{prefix}.{k}',text=v,context='original',source='citizen_original') for k,v in passages(text).items()}
        result=client.interpret(items)
        self._record(client,'interpretation attempt')
        facts=client.discovery_facts(items) if hasattr(client,'discovery_facts') else None
        self.text=text;self.evidence.update(items);self.draft,self.original_facets=reconcile_original(None,result,{})
        self.version=1;self._remember('initial proposal')
        self.state=State.INTERPRETATION
        if facts is not None:
            self._apply_discovery_facts(facts,items)
            self._record(client,'discovery metadata')

    def _apply_discovery_facts(self,facts,items):
        self.reasons_explicit=facts.reasons_explicit
        # Global sufficiency metadata must never veto independently scoped evidence.
        if facts.no_reservations and self.draft.current_route_stance.interpretation=='supported' and not any(c.status=='mapped' and (c.position in {'opposed','mixed'} or c.conditions) for c in self.draft.concerns):
            self.no_reservations=True
        for boundary in facts.blockers:
            self.blockers[boundary.concern_id]={'status':boundary.status,'evidence_ids':boundary.excerpts,'provenance':'model_proposed_explicit_boundary','confirmed':False}
        for wording in facts.unmapped_issues:
            self._add_unmapped(wording,[k for k,v in items.items() if wording in v.text])

    def _add_unmapped(self,wording,refs):
        if any(i['wording']==wording for i in self.unmapped_issues):return
        self.unmapped_issues.append({'id':'U'+str(len(self.unmapped_issues)+1),'wording':wording,'status':'unmapped','evidence_ids':refs,'context':'original'})

    @property
    def discovery_question(self):
        from .discovery import next_question
        self._require(State.INTERPRETATION)
        question=next_question(self)
        if question and not any(q['id']==question['id'] for q in self.discovery_questions):
            self.discovery_questions.append(deepcopy(question))
            key=question['id']+'.question'
            self.evidence[key]=EvidenceItem(id=key,text=question['text'],context='original',source='question',question_id=question['id'])
        elif question:
            # Reuse the already presented question, so a retry cannot change its context.
            question=next(q for q in self.discovery_questions if q['id']==question['id'])
        return deepcopy(question)

    def finish_discovery(self,reason='user_finish'):
        self._require(State.INTERPRETATION)
        self.discovery_finished=True;self.discovery_stop_reason=reason
        key='DE'+str(len(self.discovery_events)+1)+'.finish'
        self.evidence[key]=EvidenceItem(id=key,text='Discovery ended: '+reason+'. Unanswered topics remain unknown.',context='original',source='citizen_control' if reason=='user_finish' else 'application_control')
        self.discovery_events.append({'id':key,'evidence_id':key,'action':'finish','reason':reason,'context':'original','policy_version':config('discovery')['version'],'after_answers':len(self.discovery_responses),'citizen_control':reason=='user_finish'})

    def respond_discovery(self,selections,text,client,facets=None,skip=False):
        self._require(State.INTERPRETATION)
        q=self.discovery_question
        if q is None:raise ValueError('No discovery question is pending.')
        selections=list(selections);facets=list(facets or [])
        if len(selections)!=len(set(selections)) or any(x not in q['choices'] for x in selections):raise ValueError('Select an offered answer.')
        if not q['multiple'] and len(selections)>1:raise ValueError('Select one answer for this question.')
        if any(f not in q['facets'] for f in facets):raise ValueError('Select a facet for this topic.')
        if skip:selections=[];text='';facets=[]
        if text:check_input(text)
        if not skip and not selections and not text.strip() and not facets:raise ValueError('Choose an answer, add your own words, or Skip.')
        if 'no_reservations' in selections and (len(selections)>1 or text.strip()):raise ValueError('Confirm no reservations on its own, or describe your reservations instead.')
        prefix=self._answer_prefix(q['id'])
        items={};labels=config('discovery')['choice_labels'];cid=q['concern_id']
        if skip:
            key=prefix+'.skip';items[key]=EvidenceItem(id=key,text='I skip this question; no position is inferred.',context='original',source='citizen_control',question_id=q['id'])
        for index,choice in enumerate(selections):
            key=prefix+f'.selection{index+1}'
            if choice in CONCERNS or choice in {'other','cannot_specify'}:
                wording='Topic to explore (no position or severity stated): '+(CONCERNS[choice]['label'] if choice in CONCERNS else labels[choice])
            else:
                wording=labels[choice]
                if cid:wording='My position on the '+CONCERNS[cid]['label']+' aspect of the unchanged original proposal: '+{'supported':'I accept this aspect','opposed':'I reject this aspect','mixed':'I accept some parts of this aspect; others need changes','uncertain':'I am unsure about this aspect'}.get(choice,wording)
                if q['kind']=='blocker':wording=q['text']+' My answer: '+labels[choice]+'.'
                if q['kind']=='changes':wording='Could a change make '+CONCERNS[cid]['label']+' acceptable in the original proposal? My answer: '+labels[choice]+'.'
            items[key]=EvidenceItem(id=key,text=wording,context='original',source='citizen_choice',question_id=q['id'])
        if facets:
            key=prefix+'.facets';items[key]=EvidenceItem(id=key,text='Aspects to explore (no severity stated): '+', '.join(facets),context='original',source='citizen_choice',question_id=q['id'])
        if text.strip():
            key=prefix+'.text';items[key]=EvidenceItem(id=key,text=text,context='original',source='citizen_discovery',question_id=q['id'])
        # Selection-only topic nominations and boundaries cannot cause mapping/scoring.
        patch=None
        semantic_items={k:v for k,v in items.items() if k.endswith('.text') or (q['kind'] in {'stance','topic'} and '.selection' in k and not any(token in v.text for token in ['Topic to explore','Cannot specify'])) or (q['kind']=='reasons' and 'no_reservations' in selections)}
        if semantic_items and facets:semantic_items[prefix+'.facets']=items[prefix+'.facets']
        self._checkpoint(q['id'])
        previous=self.draft.model_copy(deep=True)
        if semantic_items:
            patch=client.interpret(semantic_items,context='original',proposal=SCENARIO['text']+'\nClarification question (background only): '+q['text'],target=cid if cid else None)
        # Commit only after successful inference. Retries reuse IDs/drafts without losing evidence.
        self.evidence.update(items)
        if patch:
            for new in patch.concerns:
                if cid and new.concern_id!=cid:continue
                old=next((c for c in self.draft.concerns if c.concern_id==new.concern_id),None)
                if old and new.concern_id in self.discovery_candidate_exclusions:
                    # No topic evidence existed in the original bare stance. Replace that
                    # unconfirmed candidate; retain its history, never inherit its inferred stance.
                    old=None;self.discovery_candidate_exclusions.remove(new.concern_id)
                if old and set(old.facets)&set(new.facets) and old.position in {'supported','opposed'} and new.position in {'supported','opposed'} and old.position!=new.position:
                    self.conflicts['original:'+new.concern_id]={'target':new.concern_id,'before':old.model_dump(),'proposed':new.model_dump(),
                        'question':'Your statements differ about '+CONCERNS[new.concern_id]['label']+'. Correct this meaning in your own words before confirmation.'}
                    continue
                if old:
                    combined=new.model_dump()
                    combined['facets']=list(dict.fromkeys(old.facets+new.facets))
                    combined['excerpts']=list(dict.fromkeys(old.excerpts+new.excerpts))
                    combined['conditions']=list(dict.fromkeys(old.conditions+new.conditions))
                    if new.conditional_willingness=='not_stated':combined['conditional_willingness']=old.conditional_willingness
                    if new.position=='unassessed':combined['position']=old.position
                    from .schemas import MappingConcern
                    try:new=MappingConcern.model_validate(combined)
                    except ValueError:
                        self.conflicts['original:'+new.concern_id]={'target':new.concern_id,'question':'Several meanings need consolidation. Correct this topic in your own words before confirming.'}
                        continue
                self.draft.concerns=[c for c in self.draft.concerns if c.concern_id!=new.concern_id]+[new.model_copy(deep=True)]
            for name in ['current_route_stance','medical_public_benefit_support','awareness_understanding']:
                if cid:continue
                new=getattr(patch,name);old=getattr(self.draft,name)
                if new.interpretation=='unassessed':continue
                if old.interpretation in {'supported','opposed'} and new.interpretation in {'supported','opposed'} and old.interpretation!=new.interpretation:
                    self.conflicts['original:'+name]={'target':name,'question':'Your statements differ about '+name.replace('_',' ')+'. Correct this meaning before confirmation.'}
                else:setattr(self.draft,name,new.model_copy(deep=True))
            condition_refs=list(dict.fromkeys(r for c in self.draft.concerns for r in c.conditions))
            # All conditions remain per concern/evidence; a root summary is bounded by its existing schema.
            self.draft.acceptance_conditions=condition_refs if len(condition_refs)<=5 else []
            dimensions={name:getattr(self.draft,name).model_copy(deep=True) for name in ['current_route_stance','medical_public_benefit_support','awareness_understanding']}
            self.draft,self.original_facets=reconcile_original(previous,patch,self.original_facets)
            for name,value in dimensions.items():setattr(self.draft,name,value)
            self._record(client,'discovery interpretation')
        for choice in selections:
            if choice in CONCERNS and choice not in self.discovery_topics:self.discovery_topics.append(choice)
        if 'no_reservations' in selections:self.no_reservations=True
        if 'other' in selections and not (patch and patch.concerns):
            self._add_unmapped(text.strip() or 'Other',[k for k in items if k.endswith('.text') or '.selection' in k])
        if q['kind']=='blocker' and selections:
            self.blockers[cid]={'status':selections[0],'evidence_ids':list(items),'provenance':'citizen_choice','confirmed':False}
        if q['kind']=='changes':
            self.acceptable_changes[cid]={'status':selections[0] if selections else 'unsure','text':text,'evidence_ids':list(items)}
        if q['kind']=='unmapped':
            issue=next(i for i in self.unmapped_issues if i['id']==q['issue_id'])
            issue['clarification']=text;issue['clarification_evidence_ids']=list(items)
        self.discovery_responses.append({'question_id':q['id'],'selection_key':q['selection_key'],'selections':selections,'free_text':text,'selected_facets':facets,
            'skipped':skip,'context':'original','concern_id':cid,'issue_id':q['issue_id'],'evidence_ids':list(items),'selection_reason':q['selection_reason'],'policy_version':q['policy_version']})
        self._invalidate();self._remember('discovery')
        from .discovery import next_question
        if len(self.discovery_responses)>=config('discovery')['maximum_questions']:self.finish_discovery('question_limit')
        elif next_question(self) is None:self.finish_discovery('sufficient_or_unknown_after_skips')

    def _invalidate(self):
        self.confirmed=None;self.updated_confirmed=None;self.conditional_confirmed=None
        for boundary in self.blockers.values():boundary['confirmed']=False
        if any(c.status=='mapped' and (c.position in {'opposed','mixed'} or c.conditions) for c in self.draft.concerns) or self.draft.current_route_stance.interpretation!='supported':self.no_reservations=False
        self._final=None;self._conditional=None;self._pending_final_original=None
        self.transitions=[];self.facet_scores={}
        self.version+=1
        self.state=State.UPDATED if self._initial else State.INTERPRETATION

    def correct(self,target,text,reason,client):
        self._require(State.INTERPRETATION,State.CONFIRMED,State.UPDATED,State.UPDATE_CONFIRMED,State.FINAL)
        if target not in CONCERNS and target not in ['current_route_stance','medical_public_benefit_support','awareness_understanding']:
            raise ValueError('Unknown interpretation target')
        check_input(text);check_input(reason)
        number=len(self.corrections)+1;key=f'C{number}.testimony'
        item=EvidenceItem(id=key,text=text,context='original',source='citizen_correction')
        patch=client.interpret({key:item},target=target)
        before=self.draft.model_dump()
        previous=self.draft.model_copy(deep=True)
        if target in CONCERNS:
            old=next((c for c in self.draft.concerns if c.concern_id==target),None)
            match=next((c for c in patch.concerns if c.concern_id==target),None)
            if match is None:raise AssessmentError('Correction has no clear mapping for this concern. State your position or uncertainty explicitly.',code='clarification')
            self.draft.concerns=[c for c in self.draft.concerns if c.concern_id!=target]+[match.model_copy(deep=True)]
            still_used={r for c in self.draft.concerns for r in c.conditions}
            self.draft.acceptance_conditions=list(dict.fromkeys([r for r in self.draft.acceptance_conditions if not old or r not in old.conditions or r in still_used]+match.conditions))
            self._reasons[target]='Reassessed from confirmed user-authored original-proposal clarification.'
            self.conflicts.pop('original:'+target,None)
            if match.position in {'uncertain','unassessed'} and len(match.facets)>1:
                self.conflicts['original:'+target]={'target':target,'question':'Which specific aspect are you unsure about? Please explain each aspect separately; your earlier clear views have been retained.'}
        else:
            setattr(self.draft,target,getattr(patch,target).model_copy(deep=True))
            if target=='current_route_stance':self.draft.acceptance_conditions=list(patch.acceptance_conditions)
            self.conflicts.pop('original:'+target,None)
        self.evidence[key]=item
        self.draft,self.original_facets=reconcile_original(previous,patch,self.original_facets,explicit=True)
        if target not in CONCERNS:setattr(self.draft,target,getattr(patch,target).model_copy(deep=True))
        if target=='current_route_stance':self.draft.acceptance_conditions=list(patch.acceptance_conditions)
        self.corrections.append({'id':f'C{number}','target':target,'evidence_id':key,'citizen_text':text,'reason':reason,
            'provenance':'user_authored_testimony; model proposes interpretation; confirmation required',
            'before':before,'after':self.draft.model_dump()})
        self._invalidate();self._remember('correction');self._record(client,'correction interpretation')

    def correct_blocker(self,cid,status,text=''):
        self._require(State.INTERPRETATION,State.CONFIRMED,State.UPDATED,State.UPDATE_CONFIRMED,State.FINAL)
        if cid not in self.blockers or status not in {'yes','no','unsure'}:raise ValueError('Select an existing boundary and Yes, No or Unsure.')
        if text:check_input(text)
        prefix='B'+str(len(self.corrections)+1)
        before=deepcopy(self.blockers[cid])
        key=prefix+'.choice'
        self.evidence[key]=EvidenceItem(id=key,text='Would '+CONCERNS[cid]['label']+' alone make the ORIGINAL proposal unacceptable even if other concerns were addressed? My answer: '+status,context='original',source='citizen_choice')
        refs=[key]
        if text:
            ref=prefix+'.text';self.evidence[ref]=EvidenceItem(id=ref,text=text,context='original',source='citizen_correction');refs.append(ref)
        self.blockers[cid]={'status':status,'evidence_ids':refs,'provenance':'citizen_corrected_boundary','confirmed':False}
        self.corrections.append({'id':prefix,'target':'blocker:'+cid,'citizen_text':text,'before':before,'after':deepcopy(self.blockers[cid]),'evidence_ids':refs,'context':'original'})
        self._invalidate();self._remember('boundary correction')

    def confirm(self,agreed):
        self._require(State.INTERPRETATION)
        if agreed is not True:raise ValueError('Explicit confirmation is required before scoring.')
        if self.conflicts:raise ValueError('Resolve the targeted clarification questions before confirmation.')
        from .discovery import next_question
        if not self.discovery_finished and next_question(self) is not None:raise ValueError('Answer the next discovery question, Skip it, or Finish discovery before confirming.')
        if not self.discovery_finished:self.finish_discovery('sufficient')
        for boundary in self.blockers.values():boundary['confirmed']=True
        self.confirmed=freeze(self.draft,self.evidence,self.version,'original',SCENARIO['text'],supporting_history=self._supporting_history(),acceptance_boundaries=self._discovery_boundaries(),facet_meanings=[f.model_dump() for f in self.original_facets.values()])
        self.confirmations.append(deepcopy(self.confirmed));self.state=State.CONFIRMED

    def _discovery_boundaries(self):
        return {'policy_version':config('discovery')['version'],'blockers':deepcopy(self.blockers),
            'acceptable_changes':deepcopy(self.acceptable_changes),'no_reservations':self.no_reservations,
            'unmapped_issues':deepcopy(self.unmapped_issues),
            'conditions_from_confirmed_meaning':{c.concern_id:{'conditional_willingness':c.conditional_willingness,'evidence_ids':c.conditions} for c in self.draft.concerns if c.conditions or c.conditional_willingness!='not_stated'}}

    def _supporting_history(self):
        # A bare overall stance is not concern-specific historical support.
        history={}
        for version in self.interpretations:
            for c in version['model_proposed_meaning']['concerns']:
                refs=[r for r in c['excerpts']+c.get('conditions',[]) if r in self.evidence and self.evidence[r].source=='citizen_original']
                history[c['concern_id']]=list(dict.fromkeys(history.get(c['concern_id'],[])+refs))
        return {cid:refs for cid,refs in history.items() if refs}

    def correct_modified(self,target,text,reason,client):
        self._require(State.UPDATED,State.UPDATE_CONFIRMED,State.FINAL)
        if self.conditional_draft is None or target not in list(CONCERNS)+['current_route_stance','medical_public_benefit_support','awareness_understanding']:raise ValueError('Select a meaning for the modified proposal.')
        check_input(text);check_input(reason)
        key=f'M{len(self.corrections)+1}.testimony'
        item=EvidenceItem(id=key,text=text,context='modified',source='citizen_correction')
        patch=client.interpret({key:item},'modified',self.combined_proposal,target)
        before=self.conditional_draft.model_dump();draft=self.conditional_draft.model_copy(deep=True)
        facts=deepcopy(self.facet_meanings)
        if target in CONCERNS:
            match=next((c for c in patch.concerns if c.concern_id==target),None)
            if match is None:raise ValueError('State this topic position or uncertainty explicitly.')
            draft.concerns=[c for c in draft.concerns if c.concern_id!=target]+[match.model_copy(deep=True)]
            from .updates import FacetMeaning, modified_facets
            required=sorted(set(pair for pair in modified_facets(self) if pair[0]==target)|{(target,f) for f in match.facets})
            reviewed=[(target,f) for f in match.facets]
            if hasattr(client,'interpret_facets'):updated=client.interpret_facets({key:item},self.joint['proposal'],reviewed)
            else:updated=[FacetMeaning(concern_id=target,facet=f,position=match.position if f in match.facets else 'unassessed',evidence_ids=[key] if f in match.facets else [],condition_ids=match.conditions if f in match.facets else [],applicability_explicit=f in match.facets,rationale=match.rationale) for cid,f in required]
            changed={(f.concern_id,f.facet) for f in updated}
            facts=[f for f in facts if (f.concern_id,f.facet) not in changed]+updated
        else:
            setattr(draft,target,getattr(patch,target).model_copy(deep=True))
            if target=='medical_public_benefit_support':
                for f in facts:
                    if f.concern_id=='welfare_equity' and f.facet=='medical_public_benefit':f.applicability_explicit=False
            if target=='current_route_stance':
                # A revised joint decision cannot silently keep route-only facet applicability.
                for f in facts:
                    if not any(self.evidence[r].source=='citizen_correction' for r in f.evidence_ids):f.applicability_explicit=False
        # Commit only once both mapping and aspect review have succeeded.
        self.conditional_draft=draft;self.facet_meanings=facts;self.evidence[key]=item
        self.conflicts.pop('joint:'+target,None)
        if target=='current_route_stance' and self.joint:
            decision={'supported':'accept','opposed':'reject','uncertain':'unsure'}.get(draft.current_route_stance.interpretation)
            if decision:
                self.joint['choice']=decision
                self.joint_history.append({**deepcopy(self.joint),'revision_evidence_id':key,'version':self.version+1})
        self.corrections.append({'id':key,'target':target,'context':'modified','citizen_text':text,'reason':reason,
            'before':before,'after':draft.model_dump(),'provenance':'user_authored_testimony'})
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
        if self._initial is not None:
            self.state=State.INITIAL;return
        try:result=client.score(deepcopy(self.confirmed))
        except AssessmentError as exc:
            self._record(client,'initial scoring failure')
            raise
        self.initial_text=self.text
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
        meaning,evidence=verify(self.confirmed)
        from .updates import select_followups
        self._questions=select_followups(meaning,evidence,include_reference_questions)
        self.state=State.FOLLOWUPS if self._questions else State.UPDATED

    @property
    def current_question(self):
        self._require(State.FOLLOWUPS)
        q=self._questions[len(self.responses)]
        if not any(old['id']==q['id'] for old in self.presented_followups):self.presented_followups.append(deepcopy(q))
        return deepcopy(q)

    def skip_followup(self):
        self._require(State.FOLLOWUPS)
        q=self.current_question;self._checkpoint(q['id']);prefix=self._answer_prefix(q['id']);ctx='original' if q['contract']['context']=='original' else 'hypothetical:'+q['id']
        key=prefix+'.skip';self.evidence[key]=EvidenceItem(id=key,text='I skip this question; my position remains unknown.',context=ctx,source='citizen_control',question_id=q['id'])
        self.responses.append({'question_id':q['id'],'presented_question':q,'choice':None,'code':'unresolved','clarification':'','clarification_context':ctx,
            'evidence_ids':[key],'skipped':True,'outcome':'Skipped; unknowns retained.','numerical_update':None})
        from .updates import contract
        for target in contract(q).targets:
            self.update_observations.append({'question_id':q['id'],'context':'original' if ctx=='original' else 'modified','proposal_id':q['contract']['proposal_id'],'concern_id':target.concern_id,'facet':target.facet,'transition':'unresolved','evidence_ids':[key],'reason':'Citizen skipped; unknowns retained.'})
        if len(self.responses)==len(self._questions):self.state=State.UPDATED

    def stop_followups(self):
        self._require(State.FOLLOWUPS)
        self.followup_stop_reason='user_stop';self.state=State.UPDATED

    def continue_initial(self,agreed,client,reference_mode=False):
        self._require(State.INTERPRETATION,State.CONFIRMED,State.INITIAL)
        if self.state==State.INTERPRETATION:self.confirm(agreed)
        if self.state==State.CONFIRMED:self.score_initial(client)
        if self.state==State.INITIAL:self.begin_followups(reference_mode)

    def continue_final(self,agreed,client):
        self._require(State.UPDATED,State.UPDATE_CONFIRMED)
        if self.state==State.UPDATED:self.confirm_updated(agreed)
        self.score_final(client)

    def _merge_original(self,patch):
        by={c.concern_id:c for c in self.draft.concerns}
        for new in patch.concerns:
            old=by.get(new.concern_id)
            if old and set(old.facets)&set(new.facets) and new.position in {'supported','opposed','mixed'} and old.position!=new.position:
                self.conflicts['original:'+new.concern_id]={'target':new.concern_id,'before':old.model_dump(),'proposed':new.model_dump(),
                    'question':'For the unchanged original proposal, which position do you mean? Clarify this concern in your own words.'}
                continue
            by[new.concern_id]=new.model_copy(deep=True)
            self._reasons[new.concern_id]='Reassessed from confirmed original-context follow-up evidence.'
        safe_patch=patch.model_copy(deep=True);safe_patch.concerns=[c for c in patch.concerns if 'original:'+c.concern_id not in self.conflicts]
        self.draft,self.original_facets=reconcile_original(self.draft,safe_patch,self.original_facets)
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
        q=self.current_question;qid=q['id']
        from .updates import contract
        spec=contract(q)
        if choice not in q['choices']:raise ValueError('Choose an offered answer.')
        self._checkpoint(qid)
        prefix=self._answer_prefix(qid)
        selected=spec.choices[q['choices'].index(choice)]
        if selected.code=='corrected_original' and not clarification.strip():raise AssessmentError('Please explain what should be corrected.',code='clarification')
        r=outcome(q,choice,clarification) if qid in {'q1','q2','q3'} else {'question_id':qid,'choice':choice,'code':selected.code,'clarification':clarification,'outcome':selected.meaning,'numerical_update':None,'presented_question':deepcopy(q)}
        ctx='original' if spec.context=='original' else 'hypothetical:'+qid
        items={f'{prefix}.question':EvidenceItem(id=f'{prefix}.question',text=q['text'],context=ctx,source='question',question_id=qid),
            f'{prefix}.choice':EvidenceItem(id=f'{prefix}.choice',text=choice,context=ctx,source='citizen_choice',question_id=qid)}
        if clarification:
            key=f'{prefix}.clarification';items[key]=EvidenceItem(id=key,text=clarification,
                context='original' if clarification_context=='original' else ctx,source='citizen_correction',question_id=qid)
        # Separate selection and clarification interpretation makes contradictions
        # reviewable instead of silently treating the last sentence as decisive.
        from .updates import declared_choice_meaning
        meaning=declared_choice_meaning(q,selected.code,prefix+'.choice') if qid!='q3' and spec.context!='original' else None
        traces=[{'stage':'choice interpretation','diagnostics':[],'source':'reviewed choice contract'}] if meaning else []
        patch=None
        if clarification:
            key=f'{prefix}.clarification'
            if spec.context=='original':
                items[key]=items[key].model_copy(update={'context':'original'})
            patch=client.interpret({key:items[key]},items[key].context,SCENARIO['text'] if items[key].context=='original' else q['text'])
            traces.append({'stage':'clarification interpretation','diagnostics':deepcopy(getattr(client,'last_diagnostics',[]))})
        # A broad unsure choice records an unknown response, not a replacement of prior aspects.
        allowed={t.concern_id for t in spec.targets}
        if meaning:meaning.concerns=[c for c in meaning.concerns if c.concern_id in allowed]
        if patch:patch.concerns=[c for c in patch.concerns if c.concern_id in allowed]
        self.evidence.update(items)
        if patch and patch.concerns and (clarification_context=='original' or spec.context=='original'):self._merge_original(patch)
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
        from .updates import choice_transition
        for t in spec.targets:
            self.update_observations.append({'question_id':qid,'proposal_id':spec.proposal_id,'context':'original' if spec.context=='original' else 'modified',
                'concern_id':t.concern_id,'facet':t.facet,'transition':choice_transition(q,r['code'],t.concern_id,t.facet),
                'evidence_ids':[eid for eid in r['evidence_ids'] if self.evidence[eid].source!='question'],'reason':selected.meaning+'; this choice does not calculate a numeric update.'})
        self.responses.append(r);self.version+=1;self._remember('follow-up interpretation')
        from .updates import select_followups
        existing={q['id'] for q in self._questions}
        for candidate in select_followups(self.draft,self.evidence,self.include_reference_questions):
            if candidate['id'] not in existing and len(self._questions)<config('updates')['maximum_questions']:
                self._questions.append(candidate);existing.add(candidate['id'])
        if len(self.responses)==len(self._questions):self.state=State.UPDATED

    @property
    def joint_required(self):return any(q.get('apply_to_joint') for q in self.presented_followups)
    @property
    def combined_proposal(self):
        changes=[config('reassessment')['combined_changes'].get(q['id'],q['contract']['modification']) for q in self.presented_followups if q.get('apply_to_joint')]
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

    def record_joint(self,choice,remaining,text,client,unchanged_confirmed=None):
        self._require(State.UPDATED,State.UPDATE_CONFIRMED)
        if not self.joint_required:raise ValueError('No modified proposal has been presented')
        if choice not in {'accept','reject','unsure'}:raise ValueError('Unknown joint response')
        if any(cid not in CONCERNS for cid in remaining):raise ValueError('Unknown remaining concern')
        if text:check_input(text)
        self._checkpoint('combined_proposal')
        items={};prefix='J'+str(len(self.joint_history)+1)
        # Retain individual gates as explicitly contextualized testimony, never
        # infer combined acceptance from them. The new joint response is required.
        for r in self.responses:
            if r.get('skipped') or not r['presented_question'].get('apply_to_joint'):continue
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
        from .updates import FacetMeaning, facet_state
        unchanged_confirmed=list(unchanged_confirmed or [])
        available={(f.concern_id+':'+f.facet):f for f in self.original_facets.values() if f.position in {'supported','opposed','mixed'} and facet_state(self,f.concern_id,f.facet)[0]=='untested'}
        if any(key not in available for key in unchanged_confirmed):raise ValueError('Choose an established unchanged aspect.')
        for key in unchanged_confirmed:
            fact=available[key];eid=prefix+'.applies.'+key
            testimony='For this exact combined proposal, my earlier view still applies: '+fact.rationale
            items[eid]=EvidenceItem(id=eid,text=testimony,context='modified',source='citizen_applicability_confirmation')
        proposal=self.combined_proposal
        meaning=client.interpret(items,'modified',proposal+'\nSeparate-gate answers are contextual history, not proof of joint acceptance. Interpret the explicit joint answer and remaining concerns; preserve untested facets.')
        from .updates import FacetMeaning
        established={(c.concern_id,f) for c in self.draft.concerns if c.status=='mapped' for f in c.facets}|{(f.concern_id,f.facet) for f in self.original_facets.values()}
        declared={(c['concern_id'],f) for response in self.responses for c in (response.get('choice_meaning') or {}).get('concerns',[]) for f in c['facets']}
        for candidate in meaning.concerns:
            direct=any(items[r].source=='citizen_correction' for r in candidate.excerpts)
            candidate.facets=[f for f in candidate.facets if direct or (candidate.concern_id,f) in established|declared]
        meaning.concerns=[c for c in meaning.concerns if c.facets]
        required=sorted(established|{(c.concern_id,f) for c in meaning.concerns if c.status=='mapped' for f in c.facets})
        self._record(client,'combined-proposal interpretation attempt')
        facts=[]
        if choice!='unsure' and required:
            if hasattr(client,'interpret_facets'):
                facts=client.interpret_facets(items,proposal,required)
            else:
                # Explicit test doubles/legacy adapters: single-facet meaning only;
                # multiple facets are conservative unknowns without a facet interpreter.
                for cid,f in required:
                    c=next((c for c in meaning.concerns if c.concern_id==cid),None)
                    usable=c and len(c.facets)==1 and f in c.facets and c.status=='mapped'
                    facts.append(FacetMeaning(concern_id=cid,facet=f,position=c.position if usable else 'unassessed',evidence_ids=c.excerpts if usable else [],condition_ids=c.conditions if usable else [],applicability_explicit=bool(usable),rationale=c.rationale if usable else 'Independent aspect evidence unavailable.'))
        # Link declared, actually answered gates to explicit acceptance of the combination.
        # Assumptions alone cannot create a facet, nor can global acceptance create new approval.
        from .updates import facet_state
        by={(f.concern_id,f.facet):f for f in facts}
        for cid,aspect in required:
            state,refs,qid=facet_state(self,cid,aspect)
            current=by.get((cid,aspect))
            accepted=choice=='accept' and state=='resolved_under_modification' and cid not in remaining
            direct_conflict=current and current.applicability_explicit and current.position in {'opposed','mixed'} and any(items[r].source=='citizen_correction' for r in current.evidence_ids)
            if accepted and direct_conflict:
                self.conflicts['joint:'+cid]={'target':cid,'question':'Your earlier answer accepts this change, but your added words retain an objection. Which meaning applies to these changes together?'}
            elif accepted:
                linked=[prefix+'.background.'+r for r in refs if prefix+'.background.'+r in items]
                if linked:by[(cid,aspect)]=FacetMeaning(concern_id=cid,facet=aspect,position='supported',evidence_ids=[linked[-1],prefix+'.choice'],
                    applicability_explicit=True,rationale='Citizen accepted this tested change and explicitly accepts the combination.')
            key=cid+':'+aspect
            if key in unchanged_confirmed:
                old=available[key];eid=prefix+'.applies.'+key
                by[(cid,aspect)]=FacetMeaning(concern_id=cid,facet=aspect,position=old.position,evidence_ids=[eid],condition_ids=[],applicability_explicit=True,rationale=old.rationale)
        facts=list(by.values())
        self.evidence.update(items)
        self.facet_meanings=facts
        # The facet ledger is authoritative; project its meanings into the existing parent schema.
        from .schemas import MappingConcern, Dimension
        meaning.concerns=[]
        for cid in sorted({f.concern_id for f in facts}):
            group=[f for f in facts if f.concern_id==cid]
            clear=all(f.applicability_explicit and f.position in {'supported','opposed','mixed'} for f in group)
            positions={f.position for f in group}
            position='mixed' if len(positions)>1 else next(iter(positions))
            meaning.concerns.append(MappingConcern(concern_id=cid,status='mapped' if clear else 'needs_clarification',position=position,
                facets=[f.facet for f in group],excerpts=list(dict.fromkeys(f.evidence_ids[0] for f in group if f.evidence_ids)),
                conditions=list(dict.fromkeys(f.condition_ids[0] for f in group if f.condition_ids)),rationale='Confirmed aspect meanings; see each aspect and its exact evidence.'))
        medical=next((f for f in facts if f.facet=='medical_public_benefit' and f.applicability_explicit),None)
        if medical:meaning.medical_public_benefit_support=Dimension(interpretation=medical.position,excerpts=medical.evidence_ids,rationale=medical.rationale)
        self.conditional_draft=meaning.model_copy(deep=True)
        self.joint={'choice':choice,'remaining_concern_ids':list(remaining),'clarification':text,'proposal':proposal,
            'evidence_ids':list(items),'history_links':{eid:eid.removeprefix(prefix+'.background.') for eid in items if eid.startswith(prefix+'.background.')},
            'unchanged_aspects_confirmed':unchanged_confirmed,'provenance':'explicit user choice; question context supplied separately by application'}
        self.joint_history.append({**deepcopy(self.joint),'version':self.version+1,'evidence_records':{k:v.model_dump() for k,v in items.items()}})
        self.conflicts.pop('joint:current_route_stance',None)
        actual=meaning.current_route_stance.interpretation
        expected={'accept':'supported','reject':'opposed','unsure':'uncertain'}[choice]
        if actual!='unassessed' and actual!=expected:
            self.conflicts['joint:current_route_stance']={'target':'current_route_stance','choice':choice,'proposed':meaning.current_route_stance.model_dump(),
                'question':'Your combined-proposal choice and interpreted testimony conflict. Do you accept or reject this exact proposal? Clarify in your own words.'}
        if 'joint:current_route_stance' not in self.conflicts:
            from .schemas import Dimension
            self.conditional_draft.current_route_stance=Dimension(interpretation=expected,excerpts=[prefix+'.choice'],rationale='Explicit citizen answer to the exact combined proposal.')
        self._invalidate();self._remember('joint modified interpretation');self._record(client,'joint interpretation')

    def confirm_updated(self,agreed):
        self._require(State.UPDATED)
        if agreed is not True:raise ValueError('Explicit updated-meaning confirmation is required.')
        if self.conflicts:raise ValueError('Resolve conflicting answers before confirming.')
        if self.joint_required and self.joint is None:raise ValueError('Respond to the exact combined proposal first, including unsure.')
        for boundary in self.blockers.values():boundary['confirmed']=True
        self.updated_confirmed=freeze(self.draft,self.evidence,self.version,'original',SCENARIO['text'],supporting_history=self._supporting_history(),acceptance_boundaries=self._discovery_boundaries(),facet_meanings=[f.model_dump() for f in self.original_facets.values()])
        if self.joint and self.joint['choice']!='unsure':
            self.conditional_confirmed=freeze(self.conditional_draft,self.evidence,self.version,'modified',self.joint['proposal'],facet_meanings=[f.model_dump() for f in self.facet_meanings])
        self.confirmations.extend(deepcopy([c for c in [self.updated_confirmed,self.conditional_confirmed] if c]))
        self.state=State.UPDATE_CONFIRMED

    def score_final(self,client):
        try:return self._score_final(client)
        except AssessmentError as exc:
            self._record(client,'final scoring failure')
            raise

    def _score_final(self,client):
        self._require(State.UPDATE_CONFIRMED)
        if self._pending_final_original and self._pending_final_original['interpretation_sha256']==self.updated_confirmed['sha256']:
            final=deepcopy(self._pending_final_original)
        else:
            original,_=verify(self.updated_confirmed)
            initial_record=next(r for r in self.confirmations if r['sha256']==self._initial['interpretation_sha256'])
            initial_meaning,_=verify(initial_record)
            old={c.concern_id:c for c in initial_meaning.concerns}
            changed={c.concern_id for c in original.concerns if c.concern_id not in old or semantic_key(c)!=semantic_key(old[c.concern_id])}|(set(old)-{c.concern_id for c in original.concerns})
            for cid in set(old)-{c.concern_id for c in original.concerns}:self._reasons[cid]='Earlier answer superseded; this topic has no current confirmed original-proposal evidence.'
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
        self._pending_final_original=deepcopy(final)
        conditional=None
        if self.conditional_confirmed:
            conditional=self._score_conditional(client)
        self._final=final;self._conditional=conditional;self.state=State.FINAL
        from .updates import build_transitions
        self.transitions=build_transitions(self)

    def _score_conditional(self,client):
        import time
        client.external_deadline=time.monotonic()+180
        try:return self._conditional_reviews(client)
        finally:del client.external_deadline

    def _conditional_reviews(self,client):
        from .updates import modified_facets, facet_availability
        from .schemas import Assessment, Concern, MappingConcern
        from .interpretation import digest
        profile,evidence=verify(self.conditional_confirmed)
        required=modified_facets(self);by={c.concern_id:c for c in profile.concerns}
        exclusions={};scores={};reasons={};items=[];traces=[]
        for cid in CONCERNS:
            facets=[f for c,f in required if c==cid]
            facts=[next((x for x in self.facet_meanings if x.concern_id==cid and x.facet==f),None) for f in facets]
            c=by.get(cid)
            eligible=bool(facets) and all(f and facet_availability(self,f) for f in facts)
            if eligible:
                values=[]
                for f in facts:
                    # Slice only the already-confirmed per-facet meaning; never remap it.
                    record=deepcopy(self.conditional_confirmed)
                    facet=MappingConcern(concern_id=cid,status='mapped',position=f.position,facets=[f.facet],excerpts=f.evidence_ids,conditions=f.condition_ids,
                        conditional_willingness='willing' if f.condition_ids else 'not_stated',rationale=f.rationale)
                    record['meaning']['concerns']=[facet.model_dump()]
                    record['facet_slice']={'concern_id':cid,'facet':f.facet,'confirmed_parent_sha256':self.conditional_confirmed['sha256']}
                    record.pop('sha256');record['sha256']=digest(record)
                    assessed=client.score(record,only={cid})
                    value=next(x.score for x in assessed.concerns if x.concern_id==cid)
                    values.append(value);scores[cid+':'+f.facet]=value
                    traces.append({'facet':f.model_dump(),'inference':inference_record(assessed,client)})
                eligible=all(v is not None for v in values)
            score=min(values) if eligible else None
            refs=list(dict.fromkeys(r for f in facts if f for r in f.evidence_ids))
            conditions=list(dict.fromkeys(r for f in facts if f for r in f.condition_ids))
            missing=[f for f in facets if not any(x and x.facet==f and facet_availability(self,x) for x in facts)]
            rationale='Minimum of independently reviewed applicable aspects in this modified proposal.' if eligible else 'Clarify these aspects in the combined proposal: '+', '.join(missing) if missing else 'An independent numerical review returned unavailable; see facet review reasons.'
            if not eligible:exclusions[cid]=rationale
            # Parent evidence remains bounded; all exact aspect refs are in confirmed facets/export.
            items.append(Concern(concern_id=cid,status='assessed' if score is not None else 'unassessed',score=score,position='mixed' if len({f.position for f in facts if f})>1 else facts[0].position if facts and facts[0] else 'unassessed',
                facets=facets,excerpts=[evidence[r].text for r in refs],conditions=[evidence[r].text for r in conditions],conditional_willingness='willing' if conditions else 'not_stated',rationale=rationale))
            reasons[cid]=rationale
        dims={name:{**getattr(profile,name).model_dump(),'excerpts':[evidence[r].text for r in getattr(profile,name).excerpts]} for name in ['awareness_understanding','medical_public_benefit_support','current_route_stance']}
        result=Assessment(scenario_id=profile.scenario_id,concerns=items,acceptance_conditions=[evidence[r].text for r in profile.acceptance_conditions],**dims)
        snapshot=self._snapshot(result,self.conditional_confirmed,'conditional',client,reasons)
        snapshot.update(scoring_exclusions=exclusions,facet_reviews=traces,facet_scores=scores,facet_combination=config('updates')['facet_combination'])
        snapshot['inference']['raw_model_scores']=deepcopy(scores)
        self.facet_scores=scores;self._record(client,'conditional aspect scoring')
        return snapshot

    def legacy_export(self):
        self._require(State.FINAL)
        from .discovery import report
        return deepcopy({'experimental':True,'schema_version':'4.1.0','discovery':report(self),'versions':{'assessment_schema':SCHEMA_VERSION,'registry':REGISTRY['version'],
            'scenario':SCENARIO['version'],'rubric':POLICY['rubric_version'],'scoring':POLICY['version'],
            'discovery':config('discovery'),'reassessment':config('reassessment'),'model':config('model'),'prompts':config('prompts')},
            'citizen_text':self.text,'evidence':{k:v.model_dump() for k,v in self.evidence.items()},
            'interpretations':self.interpretations,'confirmations':self.confirmations,'corrections':self.corrections,
            'initial':self._initial,'final_original':self._final,'conditional':self._conditional,
            'presented_questions':self._questions,'responses':self.responses,'joint_proposal_response':self.joint,
            'joint_proposal_history':self.joint_history,
            'update_reasons':self._final['update_reasons'],'comparison':comparison(self._initial,self._final,self._conditional,self._final['update_reasons']),
            'inference':self.inference,'confirmation_limit':'Agreement about meaning, not scientific validity.'})

    def export(self):
        self._require(State.FINAL)
        from .reporting import export_session
        return export_session(self)

    def json(self):return json.dumps(self.export(),ensure_ascii=False,indent=2)
    def jsonl(self):return json.dumps(self.export(),ensure_ascii=False,separators=(',',':'))+'\n'
