"""Version-frozen Phase 1; screened, confirmed evidence and append-only history."""
import json
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4
from .privacy import VERSION, guarded, export_guard, require_clean, require_safe_data
from .settings import ROOT, config
from .baseline import profile, select_question, selection_plan, validate_source
from .evidence import passages
from .assessment import AssessmentError

MODE='general_baseline'

class BaselineSession:
    assessment_mode=MODE
    def __init__(self):
        self.privacy_contract=VERSION
        self.session_id=str(uuid4());self.state='welcome';self.version=0
        self.instrument=deepcopy(config('baseline'));self.mode_version=self.instrument['version'].removeprefix('baseline-')
        if 'routing' in self.instrument:
            from .baseline_routing import validate_registry
            validate_registry(self.instrument)
        self.prompts={k:(ROOT/f'prompts/baseline-{k}.txt').read_text() for k in ['evidence','grounding']}
        self.prompt_version=self.instrument['prompt_version']
        self.prompt_hashes={k:sha256(v.encode()).hexdigest() for k,v in self.prompts.items()}
        self.respondent=None;self.context_history=[];self.events=[];self.evidence={};self.pending=None
        self.confirmations=[];self.corrections=[];self.inference=[];self.selection_decisions=[]
        self.information_exposures=[];self.initial_snapshots=[];self._completed=None;self.completed_snapshots=[]
        self.stop_reason=None;self.handoff_record=None;self._editing=None
        self.skipped_by_design=[];self.pre_information_snapshots=[]
        self.superseded_pending=[]
        self.interpretation_reviews=[]
        self.model_provenance=deepcopy(config('model'))
        self.source_provenance=[{k:r[k] for k in ('document','sha256','reviewed_sections') if k in r} for r in json.loads((ROOT/'references/source-register.json').read_text())['sources']]

    @property
    def current_profile(self):return profile(self.events,self.instrument,self.respondent)
    @property
    def initial_baseline(self):return deepcopy(self.initial_snapshots[0]) if self.initial_snapshots else None
    @property
    def completed_baseline(self):return deepcopy(self._completed)
    @property
    def maximum_questions(self):return self.instrument.get('routing',{}).get('maximum_questions',self.instrument.get('maximum_questions',self.instrument['maximum_core_items']+self.instrument['maximum_adaptive_probes']))
    @property
    def current_question(self):
        if self.state!='interview':return None
        if self._editing:
            previous=next((e for e in self.events if e['id']==self._editing),None)
            if previous:return deepcopy(previous['question'])
        return select_question(self.events,self.instrument,self.respondent)

    def _require(self,*states):
        if self.state not in states:raise ValueError('This action is unavailable at this step.')

    @guarded('place','function')
    def set_context(self,perspective,stakeholder,city,place='',function='',sector='none'):
        self._require('welcome','context')
        for key,val in [('perspectives',perspective),('stakeholders',stakeholder),('cities',city)]:
            if val not in self.instrument[key]:raise ValueError('Select a listed context option.')
        if len(place)>80 or len(function)>240:raise ValueError('Use a short, broad description.')
        if city!='other' and place:raise ValueError('Broad place is only available for another city or region.')
        if perspective!='organisation' and function:raise ValueError('Function is optional only when representing an organisation.')
        value={'perspective':perspective,'stakeholder_category':stakeholder,'city':city,
               'broad_place':place.strip() or None,'function':function.strip() or None,'language':self.instrument['locale']}
        if 'stakeholder_taxonomy' in self.instrument:
            if sector not in self.instrument['sectors']:raise ValueError('Select a listed sector.')
            taxonomy=self.instrument['stakeholder_taxonomy']
            category=next((r for r in taxonomy['categories'] if r['id']==stakeholder),None)
            value.update(stakeholder_taxonomy_version=taxonomy['version'],
                         stakeholder_record=deepcopy(category),stakeholder_display_label=self.instrument['stakeholders'][stakeholder],sector=sector)
        require_safe_data(value)
        self.version+=1;self.respondent=value
        self.context_history.append({'version':self.version,'context':deepcopy(value),'confirmed':True})
        self.state='interview';self._completed=None;self.handoff_record=None;self.stop_reason=None
        self._select()

    def _select(self):
        q,omitted=selection_plan(self.events,self.instrument,self.respondent)
        if self._editing:q=self.current_question
        if not hasattr(self,'skipped_by_design'):self.skipped_by_design=[]
        for row in omitted:
            record={**row,'version':self.version,'based_on_event_ids':[e['id'] for e in self.events if e['active'] and e['confirmed']]}
            if record not in self.skipped_by_design:self.skipped_by_design.append(record)
        if q:
            self.selection_decisions.append({'version':self.version,'question_id':q['id'],'rule_id':q['rule_id'],
                'reason':q['selection_reason'],'is_probe':q['is_probe'],'based_on_event_ids':[e['id'] for e in self.events if e['active'] and e['confirmed']],
                **({k:deepcopy(q[k]) for k in ('variant_id','target_requirement','triggering_evidence_ids','routing_version')} if 'routing' in self.instrument else {})})
        else:
            reason='question_budget' if sum(e['active'] and e['confirmed'] for e in self.events)>=self.maximum_questions else 'completed'
            if 'routing' in self.instrument:
                dispositions=self.current_profile['interview_dispositions']
                self.routing_stop_reason='objectives_addressed' if all(v['disposition'] not in {'not_asked','budget_limited'} for v in dispositions.values()) else 'no_eligible_useful_item'
            self.finish(reason)

    def _archive_pending(self,reason):
        if self.pending and 'routing' in self.instrument:
            previous=deepcopy(self.pending)
            previous.update(active=False,relevance_status='superseded_pending',invalidation_reason=reason)
            self.superseded_pending.append(previous)

    @guarded('text')
    def answer(self,text,client,control='answer'):
        self._require('interview')
        if control not in {'answer','skip','unsure','decline'}:raise ValueError('Unknown answer control.')
        q=self.current_question
        if q is None:raise ValueError('No question is pending.')
        if q.get('format')=='selection':
            if control=='answer' and text not in self.instrument['familiarity']:raise ValueError('Choose a listed familiarity answer.')
        if control=='answer' and not text.strip():raise ValueError('Write an answer, or choose Unsure or Skip.')
        if len(text)>6000:raise ValueError('Please shorten the answer to 6,000 characters.')
        version=self.version+1;event_id='B'+str(version)+'_'+str(len(self.events)+1)
        evidence={event_id+'.'+key:value for key,value in passages(text).items()} if text.strip() else {}
        claims=[];interaction='substantive'
        information_context='after_information' if self.information_exposures else 'before_information'
        if q['id']=='familiarity' and control=='answer':
            selection=text
            claims=[{'evidence_id':next(iter(evidence)),'dimension':'familiarity','kind':'self_report',
                     'interpretation':'You described your earlier familiarity as: '+self.instrument['familiarity'][selection]+'.',
                     'topic_ids':[],'subject':'respondent','temporality':'before_session','domain':'IAM',
                     'activity_quote':'','time_quote':'','status':'explicit_absence' if selection=='no' else 'unknown' if selection in {'unsure','withheld'} else 'supported'}]
            if selection in {'unsure','withheld'}:control='unsure' if selection=='unsure' else 'decline'
        elif control=='answer':
            model_question=deepcopy(q)
            model_question['information_context']=information_context
            if self.information_exposures:
                model_question['displayed_information']=[{'id':e['id'],'version':e['version'],'text':e['text']} for e in self.information_exposures]
            result=client.extract_baseline(evidence,question=model_question,respondent=deepcopy(self.respondent),
                    instrument=deepcopy(self.instrument),prompts=deepcopy(self.prompts))
            claims,interaction=self._claims(result,evidence,q,event_id,version,information_context)
        event={'id':event_id,'version':version,'question':deepcopy(q),'text':text if control=='answer' or q['id']=='familiarity' else '',
               'control':control,'interaction':interaction,'claims':claims,'confirmed':False,'active':True,
               'context':'general_baseline','scenario_id':None,'information_context':information_context,
               'created_at':datetime.now(timezone.utc).isoformat(),'replaces':self._editing}
        if 'routing' in self.instrument:
            event.update(relevance_status='current',answering_perspective=self.respondent['perspective'])
            from .baseline_routing import evidence_status
            for c in claims:c['evidence_status']=evidence_status(c)
        else:
            for c in claims:
                c.pop('ambiguities',None);c.pop('outcome_relation',None)
        for c in claims:
            c.update(question_id=q['id'],event_id=event_id,evidence_basis='self_report' if c['dimension']!='understanding' or c['kind']!='explained_impact' else 'answer_demonstrated_reasoning',
                confirmation_status='pending',version=version,context='general_baseline',scenario_id=None,
                source='respondent_answer',elicitation_context='baseline_core' if not q['is_probe'] else 'baseline_probe',
                information_context=information_context,external_verification=False)
        for c in claims:
            c['independent_prior_knowledge']=False if information_context=='after_information' else None
        require_safe_data(event)
        audit=None
        if control=='answer' and q['id']!='familiarity':
            audit={'event_id':event_id,'instrument_version':self.instrument['version'],'prompt_version':self.prompt_version,
                'prompt_hashes':deepcopy(self.prompt_hashes),'diagnostics':deepcopy(getattr(client,'last_diagnostics',[])),
                'settings':deepcopy(getattr(client,'last_settings',{}))}
            require_safe_data(audit)
        self.version=version;self.pending=event;self.evidence.update(evidence)
        if audit is not None:
            self.inference.append(audit)
            self.state='review'
        else:self.confirm(True,actor='structured_selection')

    def _claims(self,result,evidence,q,event_id,version,information_context):
        result=validate_source(result.model_dump(),evidence)
        require_safe_data(result.model_dump());claims=[]
        for c in result.claims:
            if c.dimension not in self.instrument['dimensions']:
                raise AssessmentError('The interpretation used a category outside this session version.',code='evidence')
            row=c.model_dump()
            row['status']='explicit_absence' if c.kind=='absence' else 'unknown' if c.kind=='unknown' else 'supported'
            if 'routing' in self.instrument:
                from .baseline_routing import evidence_status
                row['evidence_status']=evidence_status(row)
            else:
                row.pop('ambiguities',None);row.pop('outcome_relation',None)
            row.update(question_id=q['id'],event_id=event_id,
                evidence_basis='answer_demonstrated_reasoning' if c.kind=='explained_impact' else 'self_report',
                confirmation_status='pending',version=version,context='general_baseline',scenario_id=None,
                source='respondent_answer',elicitation_context='baseline_probe' if q['is_probe'] else 'baseline_core',
                information_context=information_context,external_verification=False,
                independent_prior_knowledge=False if information_context=='after_information' else None)
            claims.append(row)
        return claims,result.interaction

    @guarded('text')
    def correct_interpretation(self,text,client):
        """Revise the reading, with original answer/evidence and question unchanged."""
        self._require('review')
        if not text.strip() or len(text)>1500:raise ValueError('Describe the interpretation to change, in at most 1,500 characters.')
        pending=deepcopy(self.pending)
        evidence={k:v for k,v in self.evidence.items() if k.startswith(pending['id']+'.')}
        question=deepcopy(pending['question']);question.update(
            interpretation_feedback=text,information_context=pending['information_context'])
        if self.information_exposures:
            question['displayed_information']=[{'id':e['id'],'version':e['version'],'text':e['text']} for e in self.information_exposures]
        result=client.extract_baseline(evidence,question=question,respondent=deepcopy(self.respondent),
                    instrument=deepcopy(self.instrument),prompts=deepcopy(self.prompts))
        claims,interaction=self._claims(result,evidence,question,pending['id'],pending['version'],pending['information_context'])
        revised={**pending,'claims':claims,'interaction':interaction,
                 'interpretation_revision':pending.get('interpretation_revision',0)+1}
        audit={'event_id':pending['id'],'version':self.version,'feedback':text,
               'previous_claims':deepcopy(pending['claims']),'revised_claims':deepcopy(claims),
               'original_answer_unchanged':True,'confirmed':False,'revision':revised['interpretation_revision'],
               'diagnostics':deepcopy(getattr(client,'last_diagnostics',[])),
               'settings':deepcopy(getattr(client,'last_settings',{}))}
        require_safe_data({'pending':revised,'audit':audit})
        if not hasattr(self,'interpretation_reviews'):self.interpretation_reviews=[]
        self.interpretation_reviews.append(audit);self.pending=revised

    @guarded()
    def review_interpretation(self,event_id):
        """Reopen an existing interpretation without replacing the respondent's text."""
        self._require('baseline_review')
        original=next((deepcopy(e) for e in self.events if e['id']==event_id and e['active'] and e['claims'] and e['question']['id']!='familiarity'),None)
        if original is None:raise ValueError('Choose an interpretation from this summary.')
        self.edit_answer(event_id)
        version=self.version+1;new_id='B'+str(version)+'_'+str(len(self.events)+1)
        evidence={new_id+'.'+k:v for k,v in passages(original['text']).items()}
        mapping={old:new_id+old[len(original['id']):] for old in self.evidence if old.startswith(original['id']+'.')}
        pending={**original,'id':new_id,'version':version,'confirmed':False,'active':True,
                 'replaces':event_id,'relevance_status':'current'}
        for claim in pending['claims']:
            claim.update(evidence_id=mapping[claim['evidence_id']],event_id=new_id,version=version,confirmation_status='pending')
        require_safe_data({'pending':pending,'evidence':evidence})
        self.evidence.update(evidence);self.pending=pending;self.version=version;self.state='review'

    @guarded()
    def show_definition(self):
        """Explicit display action; never a citizen answer or interview item."""
        self._require('interview','review')
        if 'definition' not in self.instrument:raise ValueError('No definition is available in this version.')
        if self.pending:raise ValueError('Confirm or correct your answer before requesting an explanation.')
        definition=deepcopy(self.instrument['definition'])
        require_safe_data(definition)
        snapshot={'version':self.version,'profile':deepcopy(self.current_profile),
                  'event_ids':[e['id'] for e in self.events if e['active'] and e['confirmed']]}
        entry={**definition,'sequence':len(self.information_exposures)+1,
               'displayed_at':datetime.now(timezone.utc).isoformat(),'session_version':self.version,
               'action':'explicit_definition_request','acknowledged':False}
        require_safe_data(entry)
        if not hasattr(self,'pre_information_snapshots'):self.pre_information_snapshots=[]
        self.pre_information_snapshots.append(snapshot)
        self.information_exposures.append(entry)
        return definition['text']

    @guarded()
    def confirm(self,accepted,actor='respondent'):
        self._require('review','interview')
        if not self.pending:raise ValueError('No answer to confirm.')
        if accepted is not True:raise ValueError('Correct the answer or choose an explicit confirmation.')
        if actor not in {'respondent','automation','structured_selection'}:raise ValueError('Invalid confirmation actor.')
        event=deepcopy(self.pending);event['confirmed']=True
        for c in event['claims']:c['confirmation_status']='confirmed'
        self.events.append(event)
        for review in getattr(self,'interpretation_reviews',[]):
            if review['event_id']==event['id']:review['confirmed']=review.get('revision')==event.get('interpretation_revision')
        self.confirmations.append({'event_id':event['id'],'version':self.version,'actor':actor,
            'meaning':'Confirmation of intended meaning, not independent verification.'})
        if self._editing:self.corrections.append({'replaced_event_id':self._editing,'replacement_event_id':event['id'],'version':self.version})
        self.pending=None;self._editing=None;self.state='interview';self._completed=None;self.handoff_record=None
        if not self.initial_snapshots:self.initial_snapshots.append({**deepcopy(self.current_profile),'respondent_context':deepcopy(self.respondent),'version':self.version})
        self._select()

    @guarded('text')
    def correct_pending(self,text,client):
        self._require('review')
        previous=deepcopy(self.pending);self.pending=None;self.state='interview'
        try:
            self.answer(text,client)
        except Exception:
            self.pending=previous;self.state='review'
            raise
        self.corrections.append({'pending_event_id':previous['id'],'replacement_event_id':self.pending['id'],'version':self.version})
        if 'routing' in self.instrument:
            previous.update(active=False,relevance_status='superseded_pending',superseded_by=self.pending['id'])
            self.superseded_pending.append(previous)

    @guarded()
    def edit_answer(self,event_id):
        self._require('interview','review','baseline_review','complete')
        event=next((e for e in self.events if e['id']==event_id and e['active']),None)
        if event is None:raise ValueError('Select an active answer.')
        self._archive_pending('Earlier answer reopened')
        for e in self.events:
            if e['active'] and e['version']>=event['version']:
                e['active']=False
                if 'routing' in self.instrument:e.update(relevance_status='superseded',invalidation_reason='Earlier answer reopened')
        self.version+=1;self._editing=event_id;self.pending=None;self._completed=None;self.handoff_record=None
        self.stop_reason=None;self.state='interview';self._select()
        return event['text']

    @guarded()
    def back(self):
        """Return to the preceding entry/review without retaining dependent results."""
        self._require('interview','review','baseline_review','complete')
        if self.state=='complete':
            self._completed=None;self.handoff_record=None;self.state='baseline_review'
            return ''
        if self.state=='review':
            previous=deepcopy(self.pending)
            self.corrections.append({'pending_event_id':previous['id'],'version':self.version,'reason':'Returned to answer entry'})
            if 'routing' in self.instrument:
                previous.update(active=False,relevance_status='superseded_pending')
                self.superseded_pending.append(previous)
            self.pending=None;self.state='interview'
            return previous['text']
        active=[e for e in self.events if e['active'] and e['confirmed']]
        if active:return self.edit_answer(active[-1]['id'])
        self.edit_context()
        return ''

    @guarded()
    def edit_context(self):
        self._require('interview','review','baseline_review','complete')
        self._archive_pending('Respondent context reopened')
        for e in self.events:
            e['active']=False
            if 'routing' in self.instrument:e.update(relevance_status='superseded',invalidation_reason='Respondent context reopened')
        self.context_history.append({'version':self.version+1,'invalidated':True,'reason':'Respondent context correction'})
        self.version+=1;self.pending=None;self._completed=None;self.handoff_record=None;self.stop_reason=None
        self.state='context';self._editing=None

    @guarded()
    def finish(self,reason='user_finish'):
        self._require('interview','review')
        if reason not in {'completed','user_finish','question_budget'}:raise ValueError('Invalid stop reason.')
        if self.pending:raise ValueError('Confirm or correct the pending answer before finishing.')
        self.stop_reason=reason;self.state='baseline_review';self._completed=None;self.handoff_record=None
        if 'routing' in self.instrument and reason!='completed':self.routing_stop_reason=reason

    @guarded()
    def complete(self,actor='respondent'):
        self._require('baseline_review')
        if actor not in {'respondent','automation'}:raise ValueError('Invalid confirmation actor.')
        self._completed={**deepcopy(self.current_profile),'respondent_context':deepcopy(self.respondent),'version':self.version}
        self.completed_snapshots.append({'version':self.version,'profile':deepcopy(self._completed),'actor':actor})
        self.state='complete'

    @guarded()
    def handoff(self):
        self._require('complete')
        if self.handoff_record is not None:return deepcopy(self.handoff_record)
        p=self.completed_baseline
        result={'version':'baseline-handoff-1.0.0','baseline_session_id':self.session_id,'baseline_version':self.version,
                'respondent_context':deepcopy(self.respondent),'language':self.respondent['language'],
                'selected_scenario_id':None,'confirmed_topic_ids':sorted({t for c in p['claims'] for t in c['topic_ids']}),
                'gaps':{d:v['status'] for d,v in p['coverage'].items() if v['status']!='evidence_recorded'},
                'experience_context':[c for c in p['claims'] if c['dimension'] in {'exposure','participation','influence'}],
                'claims':p['claims'],'interpretation_limit':'General baseline evidence; not a response to any scenario.'}
        require_safe_data(result);self.handoff_record=deepcopy(result);return result

    @guarded()
    def continue_scenario(self):
        self._require('complete')
        if self.respondent['perspective']!='personal':raise ValueError('The specialised next stage for this perspective is pending.')
        from .readiness_session import ReadinessSession
        next_session=ReadinessSession()
        # Kept separately; excluded from scenario evidence/profile/scoring inputs.
        handoff=self.handoff()
        handoff['selected_scenario_id']=next_session.scenario['id']
        require_safe_data(handoff);self.handoff_record=deepcopy(handoff)
        next_session.baseline_handoff=deepcopy(handoff)
        next_session.baseline_provenance=self.export()
        return next_session

    @export_guard
    def export(self):
        return {'schema_version':self.instrument.get('schema_version','iam-baseline-1.0.0'),'assessment_mode':MODE,'mode_version':self.mode_version,
                'session_id':self.session_id,'state':self.state,'context':'general_baseline','scenario_id':None,
                'privacy_contract':self.privacy_contract,'respondent_context':deepcopy(self.respondent),
                'context_history':deepcopy(self.context_history),'instrument':deepcopy(self.instrument),
                'prompt_version':self.prompt_version,'prompt_hashes':deepcopy(self.prompt_hashes),
                'source_provenance':deepcopy(self.source_provenance),
                **{k:None for k in ('numerical_crl','numerical_orl','numerical_trl','numerical_srl')},
                'model_provenance':deepcopy(self.model_provenance),'events':deepcopy(self.events),
                'evidence':deepcopy(self.evidence),'confirmations':deepcopy(self.confirmations),'corrections':deepcopy(self.corrections),
                'initial_baseline_snapshot':self.initial_baseline,'completed_baseline_snapshot':self.completed_baseline,
                'completed_snapshot_history':deepcopy(self.completed_snapshots),'current_profile':deepcopy(self.current_profile),
                'selection_decisions':deepcopy(self.selection_decisions),
                **({'pending_answer':deepcopy(self.pending),
                    'skipped_by_design':deepcopy(getattr(self,'skipped_by_design',[])),
                    'pre_information_snapshots':deepcopy(getattr(self,'pre_information_snapshots',[]))}
                   if 'maximum_questions' in self.instrument else {}),
                **({'routing_version':self.instrument['routing']['version'],
                    'routing_stop_reason':getattr(self,'routing_stop_reason',None) if self.stop_reason else None,
                    'role_mapping':{'category':self.respondent['stakeholder_category'],
                        'mapped_role':self.instrument['routing']['role_mapping'][self.respondent['stakeholder_category']],
                        'answering_perspective':self.respondent['perspective']} if self.respondent else None,
                    'superseded_pending':deepcopy(self.superseded_pending)} if 'routing' in self.instrument else {}),
                'information_exposures':deepcopy(self.information_exposures),
                **({'interpretation_reviews':deepcopy(getattr(self,'interpretation_reviews',[]))} if 'interpretation_review_policy' in self.instrument or getattr(self,'interpretation_reviews',[]) else {}),
                'inference':deepcopy(self.inference),'stop_reason':self.stop_reason,'handoff':deepcopy(self.handoff_record),
                'numerical_results':deepcopy(self.instrument['numerical_policy'])}

    def json(self):return json.dumps(self.export(),ensure_ascii=False,indent=2)
    def jsonl(self):return json.dumps(self.export(),ensure_ascii=False,separators=(',',':'))+'\n'
