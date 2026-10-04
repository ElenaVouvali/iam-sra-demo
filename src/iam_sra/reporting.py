"""Readable, versioned exports and a deterministic single headline."""
from copy import deepcopy
from .settings import SCENARIO, CONCERNS, REGISTRY, POLICY, config
from .updates import blocker_report, initial_meaning

EXPORT_VERSION='5.3.0'
PROFILES={'initial_original':'initial','final_original':'final','conditional_modified':'conditional'}

def final_summary(session):
    selected=None;snapshot=None
    for key,attribute in [('conditional_modified','conditional'),('final_original','final')]:
        candidate=getattr(session,attribute)
        if candidate and candidate['aggregate']['rounded'] is not None:selected=key;snapshot=candidate;break
    attempted=bool(session.joint)
    conditional_available=bool(session.conditional and session.conditional['aggregate']['rounded'] is not None)
    original_position=session.draft.current_route_stance.interpretation
    modified_position=session.conditional_draft.current_route_stance.interpretation if session.conditional_draft else None
    context='modified' if selected=='conditional_modified' else 'original' if selected else None
    explanation='An illustrative index of the topics you discussed, for the '+('combined hypothetical proposal.' if context=='modified' else 'unchanged original proposal.') if selected else 'Your views and conditions were recorded, but too few topics had clear assessable evidence for a numerical result.'
    needs=clarification_needs(session)
    if not selected:
        explanation=(' '.join(n['reason'] for n in needs) if needs else 'A numerical result requires three independently assessable topics. Unmentioned topics remain unknown; you can add another aspect that matters to you.')
    limitations=['Experimental scenario assessment; no psychometric or population validity.','Coverage changes across proposals are not personal improvement or decline.']
    if attempted and not conditional_available:limitations.append('The modified proposal was considered, but its numerical assessment is unavailable. Any displayed score describes the original proposal.')
    return {'headline_score':snapshot['aggregate']['rounded'] if snapshot else None,'selected_profile':selected,'proposal_context':context,
        'proposal_id':'combined_modified' if context=='modified' else 'original' if context else None,
        'proposal':session.combined_proposal if context=='modified' else SCENARIO['text'] if context else None,
        'explanation':explanation,'clarification_needs':needs,'citizen_summary':citizen_summary(session),'coverage':snapshot['aggregate']['coverage'] if snapshot else session.final['aggregate']['coverage'] if session.final else '0/15',
        'modified_assessment_attempted':attempted,'modified_aggregate_available':conditional_available,
        'original_route_position':original_position,'modified_route_position':modified_position,
        'medical_public_benefit_support':session.draft.medical_public_benefit_support.interpretation,
        'remaining_conditions':[{'evidence_id':r,'citizen_quote':session.evidence[r].text,'context':session.evidence[r].context} for r in dict.fromkeys(
            ([r for f in session.facet_meanings if f.position!='supported' or not f.applicability_explicit for r in f.condition_ids] if context=='modified' else [r for c in session.draft.concerns for r in c.conditions]))],
        'decisive_remaining_boundaries':{cid:b for cid,b in (blocker_report(session)['modified'] if context=='modified' else blocker_report(session)['original']).items() if (b.get('independently_decisive') is True if context=='modified' else b.get('status')=='yes' and b.get('confirmed') is True)},
        'remaining_modified_topics':deepcopy(session.joint['remaining_concern_ids']) if session.joint else [],
        'limitations':limitations,'selection_rule':'conditional aggregate available → conditional; else final-original available → original; else unavailable. Never select an initial score.'}


def export_session(session):
    snapshots={key:getattr(session,attribute) for key,attribute in PROFILES.items()}
    initial=initial_meaning(session);profiles={'initial_original':initial,'final_original':session.draft,'conditional_modified':session.conditional_draft}
    domains=[]
    for cid,definition in CONCERNS.items():
        rows={}
        for name,snapshot in snapshots.items():
            item=next((c for c in snapshot['assessment']['concerns'] if c['concern_id']==cid),None) if snapshot else None
            meaning=next((c for c in profiles[name].concerns if c.concern_id==cid),None) if profiles[name] else None
            refs=meaning.excerpts if meaning else []
            if name=='conditional_modified':refs=list(dict.fromkeys(r for f in session.facet_meanings if f.concern_id==cid for r in f.evidence_ids))
            rows[name]={'score':item['score'] if item else None,'status':item['status'] if item else 'unavailable',
                'reason':item['rationale'] if item else 'No confirmed assessable proposal-context evidence.',
                'citizen_passages':[{'answer_id':r,'quotation':session.evidence[r].text,'context':session.evidence[r].context,'source':session.evidence[r].source} for r in refs],
                'model_explanation':item['rationale'] if item else None,  # legacy field; current explanation may be application-derived
                'assessment_explanation':item['rationale'] if item else None,
                'score_record':snapshot.get('score_records',{}).get(cid) if snapshot else None,
                'score_decisions':[d for d in snapshot.get('score_decisions',[]) if d['concern_id']==cid] if snapshot else [],
                'conditions':meaning.conditions if meaning else [],'scoring_policy_version':snapshot.get('ordinal_policy') if snapshot else None,
                'origin':snapshot.get('score_records',{}).get(cid,{}).get('origin','unavailable' if not item or item['score'] is None else 'test_or_legacy_client') if snapshot else 'unavailable'}
        domains.append({'concern_id':cid,'label':definition['label'],'phase':definition['phase'],'facets':definition['facets'],'profiles':rows,
            'facet_updates':[t for t in session.transitions if t['concern_id']==cid],
            'original_aspect_meanings':[f.model_dump() for f in session.original_facets.values() if f.concern_id==cid],
            'modified_aspect_meanings':[f.model_dump() for f in session.facet_meanings if f.concern_id==cid]})
    legacy=session.legacy_export()
    return deepcopy({'schema_version':EXPORT_VERSION,
        'metadata':{'session_id':session.session_id,'experimental':True,'source':{'document':'SRA_LLM concept feasibility.pdf','scenario_pages':[5],'validation_pages':[8,9],'calibration_pages':[6,7],'GA':'Not available in reviewed sources'},
            'model':config('model'),'registry_version':REGISTRY['version'],'scenario_version':SCENARIO['version'],
            'policies':{'ordinal':config('ordinal'),'scoring':POLICY,'reassessment':config('reassessment'),'updates':config('updates'),'prompts':config('prompts')}},
        'final_summary':final_summary(session),
        'proposals':{'original':{'id':'original','text':SCENARIO['text']},'combined_modified':{'id':'combined_modified','text':session.combined_proposal,'hypothetical':True,
            'changes':[{'question_id':q['id'],'modification':q['contract']['modification'],'assumptions':q['contract']['assumptions']} for q in session.presented_followups if q.get('apply_to_joint')]} if session.joint_required else None},
        'domain_assessments':domains,'updates':session.transitions,
        'blockers_and_conditions':{**blocker_report(session),'conditions':session._discovery_boundaries(),'unmapped_issues':session.unmapped_issues},
        'aggregation':{name:snapshot['aggregate'] if snapshot else {'mean':None,'cap':None,'adjusted':None,'rounded':None,'reason':'No confirmed numerical profile.','coverage':'0/15','trace':{'denominator':0,'mean_inputs':[]}} for name,snapshot in snapshots.items()},
        'dialogue_and_confirmations':{'original_testimony':session.text,'initial_original_testimony':session.initial_text,'current_original_testimony':session.text,'evidence':{key:v.model_dump() for key,v in session.evidence.items()},'discovery':legacy['discovery'],
            'planned_followups':session.questions,'presented_followups':session.presented_followups,'answers':session.responses,'followup_stop_reason':session.followup_stop_reason,
            'joint_answers':session.joint_history,'corrections':session.corrections,'confirmed_interpretations':session.confirmations,'interpretation_versions':session.interpretations,'answer_revisions':session.revision_history,
            'confirmation_note':'Confirmation agrees on meaning, not scientific validity.'},
        'audit':{'model_diagnostics':session.inference,'boundary_nominations':session.boundary_nominations,'snapshots':snapshots,'facet_meanings':[f.model_dump() for f in session.facet_meanings],
            'original_facet_meanings':[f.model_dump() for f in session.original_facets.values()],
            'legacy_export_schema':'4.1.0','legacy_record':legacy}})

ASPECT_LABELS={'personal_privacy':'cameras viewing private spaces','perceived_safety':'physical safety','data_security':'security and access to data',
    'medical_public_benefit':'the medical purpose','distributive_equity':'fair access to benefits','acoustic_impact':'noise',
    'aesthetic_clutter':'visual clutter','visible_physical_intrusion':'visible aircraft','system_reliability':'technical reliability'}

def aspect_label(facet):return ASPECT_LABELS.get(facet,facet.replace('_',' '))


def clarification_needs(session):
    """Actual relevant missing meanings, never every unmentioned registry topic."""
    from .updates import modified_facets,facet_availability
    needs=[]
    if session.joint and session.joint['choice']!='unsure':
        for cid,aspect in modified_facets(session):
            fact=next((f for f in session.facet_meanings if f.concern_id==cid and f.facet==aspect),None)
            if fact is None or not facet_availability(session,fact):
                needs.append({'concern_id':cid,'facet':aspect,'context':'modified','reason':'Your view of '+aspect_label(aspect)+' with these changes is not yet clear.',
                    'question':'With these changes together, what is your view of '+aspect_label(aspect)+'? Does your earlier view still apply, or what is different?'})
    for fact in session.original_facets.values():
        if fact.position in {'uncertain','unassessed'}:
            needs.append({'concern_id':fact.concern_id,'facet':fact.facet,'context':'original','reason':'Your original view of '+aspect_label(fact.facet)+' is undecided.',
                'question':'For the original proposal, what about '+aspect_label(fact.facet)+' are you unsure of, or what would you need to know?'})
    snapshot=session.conditional if session.joint and session.joint['choice']!='unsure' else session.final
    if snapshot:
        for c in snapshot['assessment']['concerns']:
            if c['score'] is None and c['facets'] and not any(n['concern_id']==c['concern_id'] for n in needs):
                needs.append({'concern_id':c['concern_id'],'facet':c['facets'][0],'context':'modified' if snapshot==session.conditional else 'original',
                    'reason':c['rationale'],'question':'Please clarify your view of '+aspect_label(c['facets'][0])+' for this proposal.'})
    return needs


def citizen_summary(session):
    """One authoritative display: structured meanings, not independent model rationales."""
    stance=session.draft.current_route_stance.interpretation
    positions={'supported':'accept','opposed':'oppose','mixed':'accept some parts of','uncertain':'are unsure about','unassessed':'have not stated a view of'}
    opposed=[aspect_label(f.facet) for f in session.original_facets.values() if f.position=='opposed']
    line='You '+positions[stance]+' the original route'
    if stance=='opposed' and opposed:line+=' because of '+(' and '.join(opposed) if len(opposed)<3 else ', '.join(opposed[:-1])+' and '+opposed[-1])
    lines=[line+'.']
    medical=session.original_facets.get('welfare_equity:medical_public_benefit')
    benefit=medical.position if medical else session.draft.medical_public_benefit_support.interpretation
    if benefit=='supported':lines.append('You support its medical purpose.')
    elif benefit in {'opposed','uncertain','mixed'}:lines.append('Your view of its medical purpose is '+{'opposed':'opposed','uncertain':'undecided','mixed':'mixed'}[benefit]+'.')
    for fact in session.original_facets.values():
        if fact.position=='supported' and fact.facet!='medical_public_benefit':lines.append('You find '+aspect_label(fact.facet)+' acceptable in the original proposal.')
    remaining=[];resolved=[]
    if session.joint:
        if session.joint['choice']=='accept':lines.append('With the changes described together, you would accept the route.')
        elif session.joint['choice']=='reject':lines.append('With the changes described together, you would still oppose the route.')
        else:lines.append('You are unsure whether you would accept the changes together.')
        for fact in session.facet_meanings:
            from .updates import facet_availability
            if not facet_availability(session,fact):continue
            if fact.position in {'opposed','mixed'}:remaining.append(aspect_label(fact.facet))
            elif fact.position=='supported':resolved.append(aspect_label(fact.facet))
    return {'lines':lines,'remaining_objections':remaining,'resolved_aspects':resolved,'unresolved':clarification_needs(session)}
