"""Complete retrieved interview; confirmed phase evidence retains its own context."""
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
import json
from uuid import uuid4
from .baseline_session import BaselineSession
from .baseline_routing import adaptive_plan,actual,compatible_context
from .settings import config,ROOT
from .privacy import VERSION,PrivacyError,guarded,export_guard,require_safe_data
from .assessment import AssessmentError
from .conversation_corpus import load_corpus,retrieve_questions,retrieve_scenario,retrieve_scenarios,explanation_collection,runtime_provenance
from .conversation_planner import choose
from .readiness_retrieval import explain


def now():return datetime.now(timezone.utc).isoformat()


def validate_policy(policy):
    if type(policy['general_budget']) is not int or not 1<=policy['general_budget']<=8:
        raise ValueError('General interview budget must be between one and eight.')
    if type(policy['scenario_followup_budget']) is not int or not 0<=policy['scenario_followup_budget']<=4:
        raise ValueError('Scenario follow-up budget must be between zero and four.')
    prerequisites={'actual_exposure_without_contribution':'participation',
        'actual_contribution_without_outcome':'influence','explicit_reflection':'understanding',
        'actual_contribution_for_agency':'participation'}
    rows=policy['scenario_questions']
    if len({q['id'] for q in rows})!=len(rows) or sum(bool(q['initial']) for q in rows)!=1:
        raise ValueError('The registry needs unique questions and one initial scenario question.')
    for q in rows:
        if q['criterion'] not in {'proposal','understanding','information','opportunity','participation','influence'}:
            raise ValueError('Unknown scenario criterion.')
        if q.get('prerequisite') and prerequisites.get(q['prerequisite'])!=q['criterion']:
            raise ValueError('Unknown or mismatched scenario prerequisite.')


def personal_contribution_to_team_activity(exposure,contribution):
    """Answer-specific link, without relabelling individual action as ORL evidence."""
    return bool(exposure.get('subject')=='organisation' and contribution.get('subject')=='respondent'
        and actual(contribution) and contribution['kind']=='contribution'
        and exposure.get('event_id')==contribution.get('event_id')
        and exposure.get('evidence_id')==contribution.get('evidence_id')
        and exposure.get('activity_quote') and exposure['activity_quote'].casefold()==contribution.get('activity_quote','').casefold()
        and not (exposure.get('time_quote') and contribution.get('time_quote') and exposure['time_quote'].casefold()!=contribution['time_quote'].casefold()))


class InterviewPhase(BaselineSession):
    def __init__(self,stage,prior=None,scenario=None,policy=None,template=None):
        self.stage=stage;self.prior=prior or {'claims':[]};self.scenario=scenario
        self.conversation_policy=deepcopy(policy or config('conversation'))
        self._planned=None;self.eligible=[]
        super().__init__()
        self.instrument['conversational_context']=True
        if template is not None:
            self.instrument=deepcopy(template.instrument);self.prompts=deepcopy(template.prompts)
            self.model_provenance=deepcopy(template.model_provenance);self.source_provenance=deepcopy(template.source_provenance)
            self.mode_version=template.mode_version
        else:
            extra=(ROOT/'prompts/conversation-context.txt').read_text()
            self.prompts={k:v+'\n'+extra for k,v in self.prompts.items()}
        self.prompt_hashes={k:sha256(v.encode()).hexdigest() for k,v in self.prompts.items()}
        self.prompt_version='conversation-evidence-1.0.0'
        self.instrument['prompt_version']=self.prompt_version
        if stage=='general':self.instrument['routing']['maximum_questions']=self.conversation_policy['general_budget']
        if stage=='scenario':
            self.evidence_prefix='R'
            self.instrument['dimensions']['proposal']='Your views of this example'
            self.instrument['routing']['maximum_questions']=1+self.conversation_policy['scenario_followup_budget']
            self.instrument['core_questions']=[self._scenario_question(q) for q in self.conversation_policy['scenario_questions']]
            self.instrument['probes']=[]

    def _scenario_question(self,item):
        dimension=item['criterion'];variant='organisation' if self.respondent and self.respondent['perspective']=='organisation' else 'personal'
        req={'proposal':'proposal_view','understanding':'effect_reasoning','information':'information_need',
             'opportunity':'participation_access','participation':'actual_contribution','influence':'reported_outcome'}[dimension]
        return {'id':item['id'],'dimension':dimension,'covers':[dimension],'question_text':item[variant],
            'text':item[variant],'variant_id':variant,'is_probe':False,'format':'text',
            'applicable_perspectives':list(self.instrument['perspectives']),
            'applicable_roles':list(self.instrument['stakeholders']),
            'target_requirement':req,'rule_id':'contextual_missing_evidence','selection_reason':'Explore a relevant gap in the illustrative example.',
            'triggering_evidence_ids':[],'routing_version':self.conversation_policy['planner_version'],
            'topic_ids':item.get('topic_ids',[]),
            'assessment_context':'illustrative_scenario','scenario_id':self.scenario['id'],
            'elicitation_context':'post_information_reflection' if item['id']=='scenario_reflection' else 'scenario_initial' if item['initial'] else 'scenario_followup',
            'scenario_card':{'id':self.scenario['id'],'text':self.scenario['text'],'unknowns':self.scenario['unknowns']},
            'initial':item['initial'],'prerequisite':item.get('prerequisite')}

    @property
    def current_question(self):
        if self.state!='interview':return None
        if self._editing:
            old=next((e for e in self.events if e['id']==self._editing),None)
            if old:return deepcopy(old['question'])
        return deepcopy(self._planned)

    def _select(self):
        if self._editing:
            self._planned=self.current_question;self.eligible=[deepcopy(self._planned)];return
        if self.stage=='general':
            self.eligible,omitted=adaptive_plan(self.events,self.instrument,self.respondent,shortlist=True)
            claims=self.current_profile['claims'];filtered=[]
            for q in self.eligible:
                if q['id']=='contribution':
                    pending=[c for c in claims if actual(c) and c['kind']=='learning_exposure' and c['evidence_id'] in q['triggering_evidence_ids']]
                    remaining=[a for a in pending if not any(personal_contribution_to_team_activity(a,c) for c in claims)]
                    if pending and not remaining:
                        omitted.append({'question_id':q['id'],'rule_id':'personal_contribution_to_team_activity_already_reported',
                            'reason':'The same answer explicitly links the personal contribution to the team activity; subjects remain separate.'})
                        continue
                    if pending:q['triggering_evidence_ids']=sorted({a['evidence_id'] for a in remaining})
                filtered.append(q)
            self.eligible=filtered
            self.skipped_by_design.extend({**r,'version':self.version} for r in omitted)
        else:self.eligible=self._scenario_eligible()
        if self.eligible:self._planned=deepcopy(self.eligible[0])
        else:
            self._planned=None
            self.finish('question_budget' if sum(e['active'] and e['confirmed'] for e in self.events)>=self.maximum_questions else 'completed')

    def _scenario_eligible(self):
        active=[e for e in self.events if e['active'] and e['confirmed']]
        if len(active)>=self.maximum_questions:return []
        items=[self._scenario_question(q) for q in self.conversation_policy['scenario_questions']]
        if not active:return [q for q in items if q['initial']]
        own=self.current_profile['claims'];combined=self.prior['claims']+own
        suppressed={e['question']['dimension'] for e in active if e['control'] in {'skip','decline','unsure'} or e['interaction'] in {'declined','unsure','confused'}}
        suppressed|={c['dimension'] for c in own if c['kind']=='unknown'}
        suppressed|=set(self.prior.get('declined_dimensions',[]))
        done={e['question']['id'] for e in active};result=[]
        topics=set(self.scenario.get('topic_ids',[]))|{t for c in combined for t in c.get('topic_ids',[])}
        for q in items:
            dim=q['dimension']
            if q['initial'] or q['id'] in done or dim in suppressed or q['prerequisite']=='explicit_reflection':continue
            if q['topic_ids'] and not topics.intersection(q['topic_ids']):continue
            # Previously stated needs/barriers remain useful; asking them again
            # is not a new evidence achievement. Applying understanding to this
            # new example is distinct from a general conceptual explanation.
            relevant=combined if dim in {'information','opportunity'} else own
            if q['topic_ids']:relevant=[c for c in relevant if set(c.get('topic_ids',[])).intersection(q['topic_ids'])]
            if dim not in {'participation','influence'} and any(c['dimension']==dim and c['subject'] in {'respondent','organisation'} for c in relevant):continue
            if q['prerequisite']:
                source_kind='learning_exposure' if q['prerequisite']=='actual_exposure_without_contribution' else 'contribution'
                candidates=[c for c in combined if actual(c) and c['kind']==source_kind]
                if q['prerequisite']=='actual_exposure_without_contribution':candidates=[a for a in candidates if not any(c['dimension']=='participation' and c['kind']!='intention' and
                    (compatible_context(a,c) or personal_contribution_to_team_activity(a,c)) for c in combined)]
                elif dim=='influence':
                    candidates=[a for a in candidates if not any(c['dimension']=='influence' and compatible_context(a,c) for c in combined)]
                if not candidates:continue
                q['triggering_evidence_ids']=[c['evidence_id'] for c in candidates]
            result.append(q)
        return result


class ConversationSession:
    assessment_mode='retrieval_grounded_conversation'
    def __init__(self,collection=None):
        self.privacy_contract=VERSION;self.session_id=str(uuid4());self.instrument=deepcopy(config('conversation'))
        validate_policy(self.instrument)
        self.collection=deepcopy(collection or load_corpus());self.stage='general';self.general=InterviewPhase('general')
        self.provenance=runtime_provenance(self.collection)
        self.scenario=None;self.card=None;self.plans=[];self.failed_attempt=None;self.failure_history=[]
        self.information_exposures=[];self.pre_information_snapshots=[];self.baseline_snapshot=None
        self.final_snapshots=[];self.superseded_scenarios=[];self.stop_reason=None;self.edit_epoch=0
        self.baseline_snapshots=[];self.model_provenance=deepcopy(config('model'))
        self.explanation_collection=explanation_collection(self.collection)
        self.corpus_sha256=sha256(json.dumps(self.collection,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        self.planner_prompt=(ROOT/'prompts/conversation-planner.txt').read_text()
        self._provisional=None
        self.rubric=deepcopy(config('readiness_levels'))

    @property
    def phase(self):return self.scenario if self.stage=='scenario' else self.general
    @property
    def respondent(self):return self.general.respondent
    @property
    def current_question(self):return self.phase.current_question if self.stage in {'general','scenario'} else None
    @property
    def pending(self):return self.phase.pending if self.stage in {'general','scenario'} else None
    @property
    def version(self):return self.general.version+(self.scenario.version if self.scenario else 0)+self.edit_epoch
    @property
    def state(self):
        if self.stage in {'offer','final_review','final'}:return self.stage
        return self.stage+'_'+self.phase.state

    def profile(self):
        claims=deepcopy(self.general.current_profile['claims'])
        if self.scenario:claims+=deepcopy(self.scenario.current_profile['claims'])
        unresolved=sorted(set(self.general.current_profile['unresolved_scope']+(self.scenario.current_profile['unresolved_scope'] if self.scenario else [])))
        coverage={}
        for d in self.general.instrument['dimensions']:
            rows=[c for c in claims if c['dimension']==d]
            contexts={'general_baseline':self.general.current_profile['coverage'][d]['status']}
            if self.scenario:contexts['illustrative_scenario']=self.scenario.current_profile['coverage'][d]['status']
            statuses=list(contexts.values())
            status=('scope_unclear' if d in unresolved else 'evidence_recorded' if any(c['status']=='supported' for c in rows) else
                'explicit_absence' if any(c['kind']=='absence' for c in rows) else
                next((v for v in ('unknown','declined','skipped','unclear') if v in statuses),'not_asked'))
            coverage[d]={'status':status,'by_context':contexts,'evidence_ids':[c['evidence_id'] for c in rows]}
        return {'claims':claims,'coverage':coverage,'unresolved_scope':unresolved}

    @guarded('place','function')
    def set_context(self,perspective,role,city,place='',function=''):
        self.general.set_context(perspective,role,city,place,function);self.stage='general'

    def _plan(self,client=None):
        phase=self.phase
        if phase.state!='interview':return
        if phase.current_question.get('format')=='selection':return
        p=self.profile();query=' '.join(c['interpretation'] for c in p['claims'][-4:]) or 'understanding experience information participation'
        p['planning_context']={'respondent':self.respondent,
            'recent_questions':[e['question']['question_text'] for e in phase.events if e['active'] and e['confirmed']][-4:],
            'scenario':{'text':self.card['text'],'unknowns':self.card['unknowns']} if self.stage=='scenario' else None}
        retrieved=retrieve_questions(self.collection,phase.eligible,self.respondent['perspective'],self.respondent['stakeholder_category'],query,self.stage,self.instrument['shortlist_size'])
        for r in retrieved:
            r['allowed_wording']=list(dict.fromkeys([r['question']['question_text']]+r['wording_options']))
            if r['question']['id'] in {'reasoning','scope'}:r['allowed_wording']=[r['question']['question_text']]
        if not retrieved:
            phase.finish('completed');self.stop_reason='no_suitable_retrieved_question';return
        question,audit=choose(self.stage,retrieved,p,client)
        phase._planned=question
        self.plans.append({**audit,'sequence':len(self.plans)+1,'selected_at':now(),'session_version':self.version,
            'corpus_version':self.collection['version']})

    def scenario_options(self):
        return retrieve_scenarios(self.collection,self.respondent,self.profile())

    @guarded('scenario_id')
    def select_scenario(self,scenario_id):
        if self.stage!='offer':raise ValueError('Choose an example before starting its discussion.')
        card=next((c for c in self.scenario_options() if c['id']==scenario_id),None)
        if card is None:raise ValueError('This example is not applicable to the selected perspective.')
        self.card=card;self._provisional=None
        self.plans.append({'action':'respondent_selected_scenario','source_ids':[card['id']],'recorded_at':now()})

    @guarded('text')
    def answer(self,text,client,planner=None,control='answer'):
        if self.stage not in {'general','scenario'} or self.phase.state!='interview':raise ValueError('No answer is requested at this step.')
        q=self.current_question
        if hasattr(client,'bind_session'):client.bind_session(self.session_id,self.edit_epoch)
        try:self.phase.answer(text,client,control)
        except AssessmentError as exc:
            if not isinstance(exc,PrivacyError) or exc.code!='privacy_unavailable':
                failed={'stage':self.stage,'question':q,'text':text,'status':'unresolved_interpretation',
                    'error_code':exc.code,'recorded_at':now()}
                require_safe_data(failed);self.failed_attempt=failed
            raise
        if self.failed_attempt:
            same=self.failed_attempt['stage']==self.stage and self.failed_attempt['question']['id']==q['id']
            self.failure_history.append({**self.failed_attempt,'resolution':'retried' if same and control=='answer' else 'unresolved_'+control})
            self.failed_attempt=None
        self._provisional=None
        if self.phase.state=='interview':self._plan(planner)

    @guarded()
    def confirm_answer(self,planner=None,actor='respondent'):
        self.phase.confirm(True,actor=actor);self._plan(planner);self._provisional=None

    @guarded('text')
    def correct_interpretation(self,text,client):
        self.phase.correct_interpretation(text,client);self._provisional=None

    @guarded()
    def finish(self):
        if self.phase.pending:raise ValueError('Confirm or correct this answer before finishing.')
        self.phase.finish('user_finish')
        self.stop_reason='user_finish_with_unresolved_interpretation' if self.failed_attempt else 'user_finish'

    @guarded()
    def confirm_general(self,actor='respondent'):
        self.general.complete(actor=actor);self.baseline_snapshot={**deepcopy(self.general.current_profile),
            'respondent_context':deepcopy(self.respondent),'version':self.general.version}
        self.baseline_snapshots.append(deepcopy(self.baseline_snapshot))
        if self.failed_attempt:
            self.failure_history.append({**self.failed_attempt,'resolution':'unresolved_at_stage_boundary'});self.failed_attempt=None
        self.card=retrieve_scenario(self.collection,self.respondent,self.profile());self.stage='offer' if self.card else 'final_review'
        if not self.card:self.stop_reason='no_suitable_scenario'

    @guarded()
    def decline_scenario(self):
        if self.stage!='offer':raise ValueError('No scenario is being offered.')
        self.stop_reason='scenario_declined';self.stage='final_review'

    def _expose(self,entry):
        require_safe_data(entry)
        self.pre_information_snapshots.append({'sequence':len(self.information_exposures)+1,'profile':deepcopy(self.profile()),'recorded_at':now()})
        self.information_exposures.append(entry)
        self.general.information_exposures=deepcopy(self.information_exposures)
        if self.scenario:self.scenario.information_exposures=deepcopy(self.information_exposures)

    @guarded()
    def accept_scenario(self,planner=None):
        if self.stage!='offer':raise ValueError('No scenario is being offered.')
        prior=deepcopy(self.baseline_snapshot)
        prior['declined_dimensions']=[e['question']['dimension'] for e in self.general.events if e['active'] and
            (e['control']=='decline' or e['interaction']=='declined')]
        self.scenario=InterviewPhase('scenario',prior,self.card,self.instrument,template=self.general)
        self.scenario.set_context(self.respondent['perspective'],self.respondent['stakeholder_category'],self.respondent['city'],
            self.respondent['broad_place'] or '',self.respondent['function'] or '')
        self.stage='scenario'
        self.explanation_collection=explanation_collection(self.collection,self.card['id'])
        self._expose({'id':'scenario_display_'+str(len(self.information_exposures)+1),'version':self.card['version'],'text':self.card['text'],
            'source_ids':[self.card['id']],'content':deepcopy(self.card),'sequence':len(self.information_exposures)+1,
            'displayed_at':now(),'acknowledged':False,'kind':'illustrative_scenario'})
        self._plan(planner)

    @guarded('question')
    def ask_information(self,question,client=None):
        if self.stage!='scenario':raise ValueError('Optional information is available during the illustrative discussion.')
        if self.pending:raise ValueError('Confirm this answer before requesting information.')
        if sum(e['kind']=='explanation' for e in self.information_exposures)>=self.instrument['information_budget']:
            raise ValueError('The optional information limit has been reached.')
        result=explain(question,client,collection=self.explanation_collection)
        require_safe_data(result)
        text='\n\n'.join(e['quotation'] for e in result['excerpts']) or result['notice']
        self._expose({'id':'explanation_'+str(len(self.information_exposures)+1),'version':result['corpus_version'],
            'text':text,'content':result,'source_ids':[e['passage_id'] for e in result['excerpts']],
            'sequence':len(self.information_exposures)+1,'displayed_at':now(),'acknowledged':False,'kind':'explanation'})
        self._provisional=None

    @guarded()
    def start_reflection(self):
        if self.stage!='scenario' or self.pending or not any(e['kind']=='explanation' for e in self.information_exposures):
            raise ValueError('Read an optional sourced explanation and confirm your answer first.')
        if any(e['active'] and e['question']['id']=='scenario_reflection' for e in self.scenario.events):raise ValueError('This optional reflection was already answered.')
        if len([e for e in self.scenario.events if e['active']])>=self.scenario.maximum_questions:raise ValueError('No follow-up slots remain.')
        item=next(q for q in self.instrument['scenario_questions'] if q['id']=='scenario_reflection')
        question=self.scenario._scenario_question(item)
        record=next((r for r in self.collection['questions'] if r['stage']=='scenario' and r['question_id']==item['id']
                     and r['variant_id']==question['variant_id']),None)
        if not record:raise ValueError('No suitable sourced reflection question is available.')
        self.scenario.state='interview';self.scenario._planned=question
        self.scenario.eligible=[deepcopy(self.scenario._planned)]
        self.plans.append({'action':'user_requested_reflection','stage':'scenario','question_id':item['id'],
            'source_ids':[record['id']],'exposure_source_ids':self.information_exposures[-1]['source_ids'],
            'displayed_question':self.scenario._planned['question_text'],'recorded_at':now()})

    @guarded()
    def acknowledge(self,exposure_id):
        event=next(e for e in self.information_exposures if e['id']==exposure_id)
        event['acknowledged']=True;event['acknowledged_at']=now()

    @guarded()
    def confirm_final(self,actor='respondent'):
        if self.stage=='scenario':
            self.scenario.complete(actor=actor);self.stage='final_review'
            self.stop_reason=self.stop_reason or self.scenario.stop_reason
        if self.stage!='final_review':raise ValueError('Check the final summary before confirming.')
        self.final_snapshots.append({'profile':deepcopy(self.profile()),'confirmed_at':now(),'actor':actor,
            'respondent_context':deepcopy(self.respondent),
            'interpretation':'Additional elicited evidence/corrections; no change in personal maturity is inferred.'})
        self.stage='final'

    @guarded()
    def back(self):
        self.edit_epoch+=1;self._provisional=None;self.stop_reason=None
        if self.stage in {'offer','final','final_review'}:
            if self.scenario:self.stage='scenario';return self.scenario.back()
            self.stage='general';return self.general.back()
        return self.phase.back()

    @guarded()
    def edit_answer(self,stage,event_id):
        if stage not in {'general','scenario'}:raise ValueError('Select an answer from this interview.')
        self.edit_epoch+=1;self._provisional=None;self.failed_attempt=None;self.stop_reason=None
        if stage=='general' and self.scenario:
            self.superseded_scenarios.append({'reason':'Baseline answer corrected','session':self.scenario.export()})
            self.scenario=None;self.card=None;self.baseline_snapshot=None
        self.stage=stage
        self.plans.append({'action':'invalidate_future_route','stage':stage,'event_id':event_id,'recorded_at':now()})
        return self.phase.edit_answer(event_id)

    @guarded()
    def edit_context(self):
        self.edit_epoch+=1;self._provisional=None;self.stop_reason=None
        if self.scenario:
            self.superseded_scenarios.append({'reason':'Respondent context corrected','session':self.scenario.export(),'scenario_card':deepcopy(self.card)})
        self.scenario=None;self.card=None;self.baseline_snapshot=None;self.stage='general'
        self.general.edit_context()

    def proposal_view(self):
        rows=[c for c in self.profile()['claims'] if c['dimension']=='proposal']
        states={'view_support':'supported','view_opposition':'opposed','view_uncertainty':'uncertain','view_mixed':'mixed'}
        stances=list(dict.fromkeys(states[c['kind']] for c in rows if c['kind'] in states))
        return {'stance':stances[-1] if len(stances)==1 else 'mixed' if stances else 'not_stated',
            'unresolved_stance_conflict':len(stances)>1,'concerns':[c for c in rows if c['kind']=='view_concern'],
            'conditions':[c for c in rows if c['kind']=='view_condition'],
            'medical_purpose_support':[c for c in rows if c['kind']=='view_purpose_support'],
            'evidence_ids':[c['evidence_id'] for c in rows]}

    @guarded()
    def provisional_estimate(self,client):
        if self.stage!='final':raise ValueError('Confirm the final summary first.')
        if self.respondent['perspective']!='personal':raise ValueError('This demonstration does not estimate organisational or technical readiness.')
        phases=[self.general]+([self.scenario] if self.scenario else [])
        def own_evidence(c):return c['dimension']!='proposal' and c['subject']=='respondent'
        answers=[{'id':e['id'],'text':'\n'.join(dict.fromkeys(c.get('span_quote','') for c in e['claims'] if own_evidence(c))),
            'text_kind':'exact_supporting_quotations','question':e['question']['question_text'],
            'context':e['context'],'information_context':e['information_context'],
            'record_evidence_ids':[c['evidence_id'] for c in e['claims'] if own_evidence(c)]} for phase in phases
            for e in phase.events if e['active'] and e['confirmed'] and any(own_evidence(c) for c in e['claims'])]
        fields=('evidence_id','event_id','dimension','kind','interpretation','span_quote','subject','temporality','domain',
            'information_context','independent_prior_knowledge','outcome_relation','ambiguities','status','topic_ids',
            'activity_quote','time_quote','evidence_basis','external_verification')
        claims=[{k:c[k] for k in fields if k in c} for c in self.profile()['claims'] if own_evidence(c)]
        # Several distinct claims may cite the same passage. Score references
        # identify claims separately instead of silently overwriting a passage.
        for n,c in enumerate(claims,1):c['claim_id']='C'+str(n)
        # Keep every relevant claim, without duplicating its full audit metadata
        # under both answer and profile. The complete audit stays in the export.
        rubric={k:deepcopy(self.rubric[k]) for k in ('version','document','sha256','sheet','crl')}
        payload={'rubric':rubric,'answers':answers,'profile':{'claims':claims},
            'assessment_scope_version':'conversation-citizen-estimate-1.1.0',
            'assessment_scope':'Versioned conversational citizen demonstration; distinguish baseline from supplied-scenario reasoning.'}
        require_safe_data(payload)
        meaningful=[c for c in payload['profile']['claims'] if c['dimension']!='familiarity' and c['status']=='supported']
        from .citizen_score import validate_citizen_score,empty_assessment
        result=validate_citizen_score(client.assign(payload),payload).model_dump() if meaningful else empty_assessment('There is insufficient substantive evidence for a provisional estimate.')
        if set(result['evidence_ids'])-{a['id'] for a in answers}:raise AssessmentError('Unknown estimate evidence.',code='evidence')
        anchor=next((a for a in self.rubric['crl'] if a['level']==result['crl']),None)
        indexed={c['claim_id']:c for c in claims}
        for row in result['criteria']:
            row['supporting_evidence']=[deepcopy(indexed[i]) for i in row['evidence_ids']]
        result.update(status='draft_provisional_model_judgement',approved_by=None,criterion=deepcopy(anchor),
            source={'document':self.rubric['document'],'locator':'Read me worksheet','sha256':self.rubric['sha256']},
            assessment_scope_version=payload['assessment_scope_version'],prompt_version=getattr(client,'prompt_version',None),
            anchor_review=deepcopy(getattr(client,'last_anchor_review',None)),
            validation_status='model_assessed_and_reviewed_not_external_verification' if getattr(client,'last_anchor_review',None) else 'no_positive_anchor_review',
            source_locators=deepcopy(self.instrument.get('scoring_source_locators',[])),
            numerical_srl=None,uncertainty='Self-reports are unverified; coverage is partial and no approved evidence-to-level rule exists.',
            model_provenance=deepcopy(self.model_provenance),session_version=self.version)
        require_safe_data(result);self._provisional=result

    @export_guard
    def export(self):
        baseline=self.general.export();scenario=self.scenario.export() if self.scenario else None
        if scenario:scenario.update(assessment_mode='conversational_scenario_component',context='illustrative_scenario',scenario_id=self.card['id'])
        initial=deepcopy(self.baseline_snapshots[0]) if self.baseline_snapshots else None;final=self.profile()
        before={c['evidence_id'] for c in initial['claims']} if initial else set()
        return {'schema_version':self.instrument['schema_version'],'assessment_mode':self.assessment_mode,
            'instrument':deepcopy(self.instrument),'session_id':self.session_id,'state':self.state,
            'privacy_contract':self.privacy_contract,'respondent_context':deepcopy(self.respondent),
            'selected_scenario':deepcopy(self.card) if self.scenario else None,'suggested_scenario':deepcopy(self.card),
            'scenario_decision':'accepted' if self.scenario else 'declined' if self.stop_reason=='scenario_declined' else 'pending',
            'baseline':baseline,'scenario':scenario,'confirmed_baseline_history':deepcopy(self.baseline_snapshots),
            'initial_confirmed_profile':initial,'final_profile':final,'confirmed_final_snapshots':deepcopy(self.final_snapshots),
            'changes':{'new_evidence_ids':sorted({c['evidence_id'] for c in final['claims'] if c['evidence_id'] not in before}),
                'corrections':deepcopy(self.general.corrections+(self.scenario.corrections if self.scenario else [])),
                'meaning':'Assessment refinement or post-information reasoning; not proof of personal development.'},
            'proposal_views':self.proposal_view(),'planning_actions':deepcopy(self.plans),
            'information_exposures':deepcopy(self.information_exposures),'pre_information_snapshots':deepcopy(self.pre_information_snapshots),
            'unresolved_attempt':deepcopy(self.failed_attempt),'failure_history':deepcopy(self.failure_history),
            'superseded_scenarios':deepcopy(self.superseded_scenarios),'stop_reason':self.stop_reason,
            'numerical_crl':None,'numerical_srl':None,'numerical_orl':None,'numerical_trl':None,
            'numerical_reason':self.instrument['numerical_reason'],'provisional_citizen_estimate':deepcopy(self._provisional),
            'corpus_provenance':{'version':self.collection['version'],'sources':deepcopy(self.collection['sources']),
                'coverage':deepcopy(self.collection['coverage'])},
            'provenance':deepcopy(self.provenance),
            'model_provenance':deepcopy(self.model_provenance),'planner_prompt_hash':sha256(self.planner_prompt.encode()).hexdigest()}

    def json(self):return json.dumps(self.export(),ensure_ascii=False,indent=2)
    def jsonl(self):return json.dumps(self.export(),ensure_ascii=False,separators=(',',':'))+'\n'
