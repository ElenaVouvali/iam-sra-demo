"""Readable, versioned exports and a deterministic single headline."""
from copy import deepcopy
from .settings import SCENARIO, CONCERNS, REGISTRY, POLICY, config
from .updates import blocker_report, initial_meaning

EXPORT_VERSION='5.4.0'
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
    from .assessment_review import progression
    progressive=progression(session) if session.final and not session.joint and not session.include_reference_questions and any(r['presented_question'].get('apply_to_joint') for r in session.responses) else None
    if progressive and progressive['aggregate']['rounded'] is not None:
        selected='bounded_followup';snapshot=progressive;context='independent_hypotheses'
        explanation=progressive['meaning']
    needs=clarification_needs(session)
    if not selected:
        explanation=('SRL unavailable: '+ ' '.join(n['reason'] for n in needs) if needs else 'SRL unavailable: we could not establish a clear position from your answers. You can edit an earlier answer whenever you are ready.')
    accepts_without_reservations=bool(session.no_reservations and original_position=='supported' and not attempted)
    direct_acceptance=bool(not selected and accepts_without_reservations and session.discovery_finished and not session.draft.concerns)
    acceptance_rule=config('discovery')['overall_acceptance_rule']
    if direct_acceptance:
        context='original'
        explanation='You confirmed that you accept the proposal without reservations. This gives an overall score of 9/9 under the explicit acceptance rule; individual concerns remain unassessed.'
    limitations=['Experimental scenario assessment; no psychometric or population validity.','Coverage changes across proposals are not personal improvement or decline.']
    if attempted and not conditional_available:limitations.append('The modified proposal was considered, but its numerical assessment is unavailable. Any displayed score describes the original proposal.')
    return {'headline_score':snapshot['aggregate']['rounded'] if snapshot else acceptance_rule['score'] if direct_acceptance else None,'selected_profile':'confirmed_overall_acceptance' if direct_acceptance else selected,
        'score_basis':acceptance_rule['basis'] if direct_acceptance else 'bounded_followup_progression' if selected=='bounded_followup' else 'concern_aggregation' if snapshot else None,
        'overall_acceptance_rule':deepcopy(acceptance_rule) if direct_acceptance else None,
        'score_evidence_ids':[eid for r in session.discovery_responses if 'no_reservations' in r['selections'] for eid in r['evidence_ids']] if direct_acceptance else [],'proposal_context':context,
        'proposal_id':'combined_modified' if context=='modified' else 'original' if context else None,
        'proposal':session.combined_proposal if context=='modified' else SCENARIO['text'] if context else None,
        'explanation':explanation,'clarification_needs':needs,'citizen_summary':citizen_summary(session),'coverage':snapshot['aggregate']['coverage'] if snapshot else session.final['aggregate']['coverage'] if session.final else '0/15',
        'modified_assessment_attempted':attempted,'modified_aggregate_available':conditional_available,
        'accepts_without_reservations':accepts_without_reservations,'original_route_position':original_position,'modified_route_position':modified_position,
        'medical_public_benefit_support':session.draft.medical_public_benefit_support.interpretation,
        'remaining_conditions':[{'evidence_id':r,'citizen_quote':session.evidence[r].text,'context':session.evidence[r].context} for r in dict.fromkeys(
            ([r for f in session.facet_meanings if f.position!='supported' or not f.applicability_explicit for r in f.condition_ids] if context=='modified' else [r for c in session.draft.concerns for r in c.conditions]))],
        'decisive_remaining_boundaries':{cid:b for cid,b in (blocker_report(session)['modified'] if context=='modified' else blocker_report(session)['original']).items() if (b.get('independently_decisive') is True if context=='modified' else b.get('status')=='yes' and b.get('confirmed') is True)},
        'remaining_modified_topics':deepcopy(session.joint['remaining_concern_ids']) if session.joint else [],
        'limitations':limitations,'selection_rule':'Independent default follow-ups → experimental bounded progression when assessable; combined-proposal assessment remains separate. Confirmed overall acceptance without reservations and no concern aggregate → direct overall 9; otherwise conditional aggregate available → conditional; else final-original available → original; else unavailable. Never select an initial score.'}


def export_session(session):
    from .assessment_review import final_review
    review=final_review(session)
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
            'progression_decision':next((d for d in review['progression']['decisions'] if d['concern_id']==cid),None) if review['progression'] else None,
            'original_aspect_meanings':[f.model_dump() for f in session.original_facets.values() if f.concern_id==cid],
            'modified_aspect_meanings':[f.model_dump() for f in session.facet_meanings if f.concern_id==cid]})
    aggregations={name:snapshot['aggregate'] if snapshot else {'mean':None,'cap':None,'adjusted':None,'rounded':None,'reason':'No confirmed numerical profile.','coverage':'0/15','trace':{'denominator':0,'mean_inputs':[]}} for name,snapshot in snapshots.items()}
    if review['progression']:aggregations['bounded_followup']=review['progression']['aggregate']
    legacy=session.legacy_export()
    return deepcopy({'schema_version':EXPORT_VERSION,
        'metadata':{'session_id':session.session_id,'experimental':True,'source':{'document':'SRA_LLM concept feasibility.pdf','scenario_pages':[5],'validation_pages':[8,9],'calibration_pages':[6,7],'GA':'GA.pdf, Task 3.2 and Part B pp.5/16: reflective indicators, citizen agency and Living Lab validation; numerical progression is experimental, not specified by the GA.'},
            'model':config('model'),'registry_version':REGISTRY['version'],'scenario_version':SCENARIO['version'],
            'policies':{'ordinal':config('ordinal'),'scoring':POLICY,'reassessment':config('reassessment'),'updates':config('updates'),'prompts':config('prompts')}},
        'final_summary':final_summary(session),
        'final_assessment_review':review,
        'proposals':{'original':{'id':'original','text':SCENARIO['text']},
            'independent_hypotheses':[{'question_id':q['id'],'modification':q['contract']['modification'],'targets':q['contract']['targets'],'assumptions':q['contract']['assumptions']} for q in session.presented_followups if q.get('apply_to_joint')],
            'combined_modified':{'id':'combined_modified','text':session.combined_proposal,'hypothetical':True,
            'changes':[{'question_id':q['id'],'modification':q['contract']['modification'],'assumptions':q['contract']['assumptions']} for q in session.presented_followups if q.get('apply_to_joint')]} if session.joint else None},
        'domain_assessments':domains,'updates':session.transitions,
        'blockers_and_conditions':{**blocker_report(session),'conditions':session._discovery_boundaries(),'unmapped_issues':session.unmapped_issues},
        'aggregation':aggregations,
        'dialogue_and_confirmations':{'original_testimony':session.text,'initial_original_testimony':session.initial_text,'current_original_testimony':session.text,'evidence':{key:v.model_dump() for key,v in session.evidence.items()},'discovery':legacy['discovery'],
            'planned_followups':session.questions,'presented_followups':session.presented_followups,'answers':session.responses,'followup_stop_reason':session.followup_stop_reason,
            'joint_answers':session.joint_history,'corrections':session.corrections,'confirmed_interpretations':session.confirmations,'interpretation_versions':session.interpretations,'answer_revisions':session.revision_history,
            'confirmation_note':'Confirmation agrees on meaning, not scientific validity.'},
        'audit':{'model_diagnostics':session.inference,'boundary_nominations':session.boundary_nominations,'snapshots':snapshots,'facet_meanings':[f.model_dump() for f in session.facet_meanings],
            'original_facet_meanings':[f.model_dump() for f in session.original_facets.values()],
            'legacy_export_schema':'4.1.0','legacy_record':legacy}})

ASPECT_LABELS={'personal_privacy':'cameras viewing private spaces','perceived_safety':'physical safety','data_security':'security and access to data',
    'medical_public_benefit':'the medical purpose','distributive_equity':'fair access to benefits','acoustic_impact':'noise',
    'aesthetic_clutter':'visual clutter','visible_physical_intrusion':'visible aircraft','system_reliability':'technical reliability',
    'participation_skills':'residents learning how to participate and report problems',
    'training':'training and learning opportunities','airspace_traffic':'keeping aircraft safely separated in shared airspace',
    'rotor_wind':'air pushed down by the rotors',
    'awareness':'public information about the proposal','institutional_trust':'trust in the institutions responsible',
    'urban_mobility_plan':'integration with the city’s transport plans',
    'facility_siting':'where landing and support facilities would be located','land_allocation':'land allocated to drone facilities',
    'energy_demand':'energy use','emissions':'emissions',
    'cost_financing':'costs and how they would be funded','business_viability':'the service’s financial viability',
    'remote_access':'access for remote communities','vulnerable_access':'access for vulnerable groups',
    'transport_connections':'connections with other transport services','congestion':'effects on traffic congestion'}

def aspect_label(facet):return ASPECT_LABELS.get(facet,facet.replace('_',' '))


def supported_aspect_statement(facet):
    """Describe the mapped position in citizen language without changing its meaning."""
    if facet=='awareness':return 'You consider the public information about the proposal adequate.'
    if facet=='institutional_trust':return 'You express trust in the institutions responsible for the proposal.'
    return 'You find '+aspect_label(facet)+' acceptable in the original proposal.'


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
    if stance=='supported' and session.no_reservations:line+=' without stated reservations'
    lines=[line+'.']
    medical=session.original_facets.get('welfare_equity:medical_public_benefit')
    benefit=medical.position if medical else session.draft.medical_public_benefit_support.interpretation
    if benefit=='supported':lines.append('You support its medical purpose.')
    elif benefit in {'opposed','uncertain','mixed'}:lines.append('Your view of its medical purpose is '+{'opposed':'opposed','uncertain':'undecided','mixed':'mixed'}[benefit]+'.')
    for fact in session.original_facets.values():
        if fact.position=='supported' and fact.facet!='medical_public_benefit':lines.append(supported_aspect_statement(fact.facet))
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
