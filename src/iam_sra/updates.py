"""Application-owned facet contracts/transitions; no invented numeric update formula."""
from copy import deepcopy
from typing import Literal
from pydantic import Field, model_validator
from .schemas import Strict, ConcernID
from .settings import CONCERNS, SCENARIO, config
from .assessment import AssessmentError

TransitionKind=Literal['confirmed_unchanged','corrected_original','resolved_under_modification','partially_resolved','remaining_objection','unresolved','untested']

class FacetTarget(Strict):
    concern_id: ConcernID
    facet: str
    @model_validator(mode='after')
    def canonical(self):
        if self.facet not in CONCERNS[self.concern_id]['facets']:raise ValueError('Noncanonical facet')
        return self

class ChoiceMeaning(Strict):
    label: str
    code: str
    meaning: str

class QuestionContract(Strict):
    question_id: str
    context: Literal['original','hypothetical']
    proposal_id: str
    targets: list[FacetTarget]
    modification: str | None
    assumptions: list[str]
    choices: list[ChoiceMeaning]
    cannot_establish: list[str]
    policy_version: str
    source: str
    selection_reason: str = 'Relevant expressed concern or condition.'

class FacetMeaning(FacetTarget):
    position: Literal['supported','opposed','mixed','uncertain','unassessed']
    evidence_ids: list[str] = Field(default_factory=list,max_length=3)
    condition_ids: list[str] = Field(default_factory=list,max_length=3)
    applicability_explicit: bool
    rationale: str = Field(max_length=400)

class FacetBatch(Strict):
    facets: list[FacetMeaning] = Field(max_length=30)
    @model_validator(mode='after')
    def unique(self):
        keys=[(f.concern_id,f.facet) for f in self.facets]
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate facet meaning')
        return self

class AssessmentTransition(FacetTarget):
    id: str
    question_id: str | None
    context: Literal['original','modified']
    proposal_id: str
    transition: TransitionKind
    evidence_ids: list[str]
    old_score: int | None = Field(ge=1,le=9)
    new_score: int | None = Field(ge=1,le=9)
    facet_review_score: int | None = Field(default=None,ge=1,le=9)
    score_unit: Literal['concern']='concern'
    reason: str
    rubric_version: str
    value_action: Literal['carried','re_reviewed','unavailable']
    confirmed: bool
    policy_version: str
    scoring_policy_version: str | None = None
    anchor_rule_ids: list[str] = Field(default_factory=list)
    condition_ids: list[str] = Field(default_factory=list)
    score_origin: str = 'unavailable'
    reuse_decision: str | None = None


def contract(question):return QuestionContract.model_validate(question['contract'])

def enrich_fn(question,reference=False):
    p=config('updates');q=deepcopy(question);rules=p['fn'][q['id']]
    q['reference_text']=q['text'];q['reference_choices']=deepcopy(q['choices'])
    if not reference:q['text']=rules['citizen_text'];q['choices']=rules['citizen_choices']
    choices=[ChoiceMeaning(label=label,code=code,meaning=code.replace('_',' ')) for label,code in zip(q['choices'],rules['choice_codes'])]
    spec=QuestionContract(question_id=q['id'],context='hypothetical',proposal_id='hypothetical:'+q['id'],
        targets=[FacetTarget(concern_id=cid,facet=f) for cid,facets in rules['targets'].items() for f in facets],
        modification=rules['modification'],assumptions=[rules['modification']],choices=choices,cannot_establish=rules['cannot_establish'],policy_version=p['version'],source='FN PDF pp.'+','.join(map(str,q['source_pages'])),selection_reason='Test a relevant expressed privacy/noise condition.' if q['id']!='q3' else 'Explore the stated rerouting policy trade-off.')
    q.update(contract=spec.model_dump(),policy_version=p['version'],reference_mode=reference,apply_to_joint=q['id'] in {'q1','q2'})
    return q


def select_followups(meaning,evidence,reference=False):
    from .validation import select_questions
    from .settings import QUESTIONS
    p=config('updates');questions=[enrich_fn(q,reference) for q in (QUESTIONS if reference else select_questions(meaning))]
    if not reference:
        def purposeful(q):
            if q['id']=='q2':return any(c.concern_id in {'noise','visual_pollution'} and (c.position!='supported' or c.conditions) for c in meaning.concerns)
            if q['id']=='q3':return any(c.concern_id!='welfare_equity' and (c.position in {'opposed','mixed'} or c.conditions) for c in meaning.concerns)
            return True
        questions=[q for q in questions if purposeful(q)]
    covered={(t.concern_id,t.facet) for q in questions if q['id']!='q3' for t in contract(q).targets if not (q['id']=='q1' and t.facet=='data_security')}
    by={c.concern_id:c for c in meaning.concerns if c.excerpts and c.status in {'mapped','needs_clarification'}}
    for cid in CONCERNS:
        c=by.get(cid)
        if not c:continue
        facets=[f for f in c.facets if (cid,f) not in covered]
        if not facets:continue
        targets=[FacetTarget(concern_id=cid,facet=f) for f in facets]
        conditions=[evidence[r].text for r in c.conditions if r in evidence and evidence[r].context=='original']
        if not conditions and c.status=='mapped' and (c.position=='supported' or c.conditional_willingness!='not_stated'):continue
        modified=bool(conditions);qid=('u_change_' if modified else 'u_original_')+cid;context='hypothetical' if modified else 'original'
        condition='; '.join(conditions)
        text=p['templates']['requested_change' if modified else 'original_check'].format(topic=CONCERNS[cid]['label'],condition=condition,earlier=c.rationale)
        labels=p['hypothetical_choices' if modified else 'original_choices']
        codes=['aspect_accepted','remaining_objection','partial_resolution','unresolved'] if modified else ['confirmed_unchanged','corrected_original','unresolved']
        change='Assume the citizen-described conditions for '+CONCERNS[cid]['label']+' are met: '+condition if modified else None
        spec=QuestionContract(question_id=qid,context=context,proposal_id='hypothetical:'+qid if modified else 'original',targets=targets,
            modification=change,assumptions=[change] if change else [],choices=[ChoiceMeaning(label=a,code=b,meaning=b.replace('_',' ')) for a,b in zip(labels,codes)],
            cannot_establish=['Technical/regulatory/clinical feasibility','Full-route acceptance','Acceptance of a combination','Untargeted facets'],policy_version=p['version'],source='Application-reviewed template1.1; citizen condition evidence',selection_reason='Test a citizen-described acceptable change.' if modified else 'Clarify missing acceptable changes or a specific ambiguous position.')
        questions.append({'id':qid,'text':text,'choices':labels,'contract':spec.model_dump(),'hypothetical':modified,'source_pages':[],
            'relevant_concerns':[cid],'apply_to_joint':modified,'condition_evidence_ids':c.conditions,'policy_version':p['version']})
    return questions[:p['maximum_questions']]


def choice_transition(q,code,cid,facet):
    if (cid,facet) not in {(t.concern_id,t.facet) for t in contract(q).targets}:return 'untested'
    if contract(q).context=='original':return {'confirmed_unchanged':'confirmed_unchanged','corrected_original':'corrected_original'}.get(code,'unresolved')
    if q['id']=='q3':return 'untested'
    if code in {'aspect_accepted'}:return 'resolved_under_modification'
    if code=='privacy_resolved':return 'resolved_under_modification' if facet=='personal_privacy' else 'untested'
    if code=='data_access_remaining':return 'remaining_objection' if facet=='data_security' else 'partially_resolved'
    if code=='camera_presence_remaining':return 'remaining_objection' if facet=='personal_privacy' else 'untested'
    if code=='bundle_accepted':return 'resolved_under_modification' if facet=='acoustic_impact' else 'untested'
    if code=='visual_clutter_remaining':return 'remaining_objection' if cid=='visual_pollution' else 'partially_resolved'
    if code in {'residential_routing_remaining','partial_resolution'}:return 'partially_resolved'
    if code=='remaining_objection':return 'remaining_objection'
    return 'unresolved'


def facet_state(session,cid,facet):
    state='untested';ids=[];qid=None
    for r in session.responses:
        if r.get('skipped'):continue
        q=r['presented_question']
        candidate=choice_transition(q,r['code'],cid,facet)
        if candidate!='untested':state=candidate;ids=[eid for eid in r['evidence_ids'] if session.evidence[eid].source!='question' and session.evidence[eid].context!='original'];qid=q['id']
    return state,ids,qid


def initial_meaning(session):
    from .interpretation import verify
    record=next(r for r in session.confirmations if r['sha256']==session.initial['interpretation_sha256'])
    return verify(record)[0]


def modified_facets(session):
    """Required facets are union of original and new meanings, with no inheritance."""
    required={(c.concern_id,f) for c in session.draft.concerns if c.status=='mapped' for f in c.facets}
    required.update((f.concern_id,f.facet) for f in session.original_facets.values())
    # Only independently mapped modified testimony may introduce a required aspect.
    required.update((c.concern_id,f) for c in (session.conditional_draft.concerns if session.conditional_draft else []) if c.status=='mapped' for f in c.facets)
    return sorted(required)


def facet_availability(session,facet):
    if not facet.applicability_explicit or facet.position in {'uncertain','unassessed'} or not facet.evidence_ids:return False
    sources=[session.evidence[r] for r in facet.evidence_ids]
    if all(e.id.endswith('.remaining') for e in sources):return False
    if any(e.context!='modified' or e.source in {'question','application_control','citizen_control'} for e in sources):return False
    state,_,_=facet_state(session,facet.concern_id,facet.facet)
    direct=any(e.source in {'citizen_correction','citizen_applicability_confirmation'} for e in sources)
    # A separate gate plus explicit joint acceptance supports that tested facet;
    # route acceptance alone cannot establish applicability of unrelated facets.
    if not direct and not (state in {'resolved_under_modification','remaining_objection'} and session.joint and session.joint['choice'] in {'accept','reject'}):return False
    return True


def build_transitions(session):
    from .interpretation import verify, semantic_key
    from .settings import POLICY
    p=config('updates');initial=initial_meaning(session);original,_=verify(session.updated_confirmed)
    old={c.concern_id:c for c in initial.concerns};now={c.concern_id:c for c in original.concerns}
    score=lambda snapshot,cid:next((c['score'] for c in snapshot['assessment']['concerns'] if c['concern_id']==cid),None) if snapshot else None
    records=[]
    for observed in session.update_observations:
        records.append(AssessmentTransition(id='T'+str(len(records)+1),**observed,old_score=score(session.initial,observed['concern_id']),new_score=None,
            rubric_version=POLICY['rubric_version'] if observed['context']=='original' else config('reassessment')['conditional_rubric'],value_action='unavailable',confirmed=True,policy_version=p['version']))
    for cid in CONCERNS:
        facets=set(old[cid].facets if cid in old else [])|set(now[cid].facets if cid in now else [])
        changed=cid in now and (cid not in old or semantic_key(now[cid])!=semantic_key(old[cid]))
        for f in sorted(facets):
            refs=now[cid].excerpts+now[cid].conditions if cid in now else []
            records.append(AssessmentTransition(id='T'+str(len(records)+1),question_id=next((session.evidence[r].question_id for r in refs if session.evidence[r].question_id),None),context='original',proposal_id='original',concern_id=cid,facet=f,
                transition='corrected_original' if changed else 'confirmed_unchanged',evidence_ids=list(dict.fromkeys(refs)),old_score=score(session.initial,cid),new_score=score(session.final,cid),reason=session.final['update_reasons'][cid],rubric_version=POLICY['rubric_version'],value_action='re_reviewed' if changed and score(session.final,cid) is not None else 'unavailable' if score(session.final,cid) is None else 'carried',confirmed=True,policy_version=p['version']))
    for cid,f in modified_facets(session) if session.joint else []:
        state,refs,qid=facet_state(session,cid,f)
        item=next((x for x in session.facet_meanings if x.concern_id==cid and x.facet==f),None)
        if item:
            refs=list(dict.fromkeys(item.evidence_ids+item.condition_ids))
            if not facet_availability(session,item):state='unresolved' if item.position in {'uncertain','unassessed'} else state
            elif item.position in {'opposed','mixed'}:state='remaining_objection' if item.position=='opposed' else 'partially_resolved'
            elif item.position=='supported':state='resolved_under_modification' if state!='untested' else 'confirmed_unchanged'
        value=score(session.conditional,cid)
        records.append(AssessmentTransition(id='T'+str(len(records)+1),question_id=qid,context='modified',proposal_id='combined_modified',concern_id=cid,facet=f,transition=state,evidence_ids=refs,old_score=score(session.initial,cid),new_score=value,
            facet_review_score=session.facet_scores.get(cid+':'+f),reason='All required facets must have applicable confirmed modified evidence; parent uses their minimum.' if value is not None else 'Modified parent unavailable: missing, uncertain or untested facet evidence.',rubric_version=config('reassessment')['conditional_rubric'],value_action='re_reviewed' if value is not None else 'unavailable',confirmed=session.updated_confirmed is not None,policy_version=p['version']))
    output=[]
    for r in records:
        row=r.model_dump()
        snapshot=session.final if r.context=='original' else session.conditional if r.proposal_id=='combined_modified' else None
        decisions=[d for d in (snapshot.get('score_decisions',[]) if snapshot else []) if d['concern_id']==r.concern_id and d['facet']==r.facet]
        row.update(scoring_policy_version=config('ordinal')['version'],anchor_rule_ids=[d.get('anchor_rule_id') for d in decisions],
            condition_ids=list(dict.fromkeys(e for d in decisions for e in d.get('condition_ids',[]))),
            score_origin='unavailable' if r.new_score is None else decisions[0].get('origin','unavailable') if decisions else 'test_or_legacy_client',
            reuse_decision=decisions[0].get('reuse_decision') if decisions else None)
        if decisions and all(d.get('origin')=='equivalent_meaning_reuse' for d in decisions) and r.new_score is not None:row['value_action']='carried'
        output.append(row)
    return output


def blocker_report(session):
    result={'original':deepcopy(session.blockers),'modified':{}}
    for cid,b in session.blockers.items():
        original=next((c for c in session.draft.concerns if c.concern_id==cid),None)
        facets=original.facets if original else []
        assessed=[r for r in session.transitions if r['context']=='modified' and r['proposal_id']=='combined_modified' and r['concern_id']==cid]
        statuses={r['transition'] for r in assessed}
        facts=[f for f in session.facet_meanings if f.concern_id==cid and f.facet in facets]
        status='unresolved'
        if facets and len(facts)==len(facets) and all(facet_availability(session,f) for f in facts):
            status='remaining' if any(f.position in {'opposed','mixed'} for f in facts) else 'addressed_under_modification'
        if 'remaining_objection' in statuses:status='remaining'
        elif facets and len(assessed)>=len(facets) and statuses.issubset({'resolved_under_modification','confirmed_unchanged'}) and all(any(f.concern_id==cid and f.facet==r['facet'] and facet_availability(session,f) for f in session.facet_meanings) for r in assessed):status='addressed_under_modification'
        result['modified'][cid]={'original_status':b['status'],'status':status,'confirmed':session.updated_confirmed is not None,'independently_decisive':None,'independently_decisive_reason':'An original acceptance condition does not establish independent decisiveness in the modified proposal.','evidence_ids':list(dict.fromkeys(r for t in assessed for r in t['evidence_ids'])),'reason':'Original boundary retained; only relevant confirmed modified evidence can address it. Numerical cap is independent.'}
    return result


def declared_choice_meaning(question, code, evidence_id):
    """Interpret reviewed choices, never invent positions for question-only topics."""
    from .schemas import MappingAssessment, MappingConcern
    dim={'interpretation':'unassessed','excerpts':[],'rationale':'Not stated by this answer.'}
    concerns=[]
    for target in contract(question).targets:
        status=choice_transition(question,code,target.concern_id,target.facet)
        if status not in {'resolved_under_modification','remaining_objection'}:continue
        # Each emitted position is expressed by the selected choice itself.
        concerns.append(MappingConcern(concern_id=target.concern_id,status='mapped',position='supported' if status=='resolved_under_modification' else 'opposed',
            facets=[target.facet],excerpts=[evidence_id],rationale='The selected answer explicitly '+('accepts this aspect under the stated change.' if status=='resolved_under_modification' else 'retains this objection under the stated change.')))
    grouped={}
    for c in concerns:
        if c.concern_id in grouped:grouped[c.concern_id].facets+=c.facets
        else:grouped[c.concern_id]=c
    route=dim if code!='bundle_accepted' else {'interpretation':'supported','excerpts':[evidence_id],'rationale':'Accepted this separate operating-condition proposal.'}
    from .settings import SCENARIO
    return MappingAssessment(scenario_id=SCENARIO['id'],concerns=list(grouped.values()),current_route_stance=route,
        medical_public_benefit_support=dim,awareness_understanding=dim,acceptance_conditions=[])
