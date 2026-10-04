"""Deterministic, score-free supplementary questions for the original proposal."""
from copy import deepcopy
from pydantic import Field
from .schemas import Strict, ConcernID
from .settings import CONCERNS, config

class Boundary(Strict):
    concern_id: ConcernID
    status: str = Field(pattern='^(yes|no|unsure)$')
    excerpts: list[str] = Field(min_length=1,max_length=3)
    validated_facets: list[str] = Field(default_factory=list,max_length=2)
    decisiveness_checked: bool = False

class DiscoveryFacts(Strict):
    reasons_explicit: bool = False
    reasons_evidence: list[str] = Field(default_factory=list,max_length=3)
    no_reservations: bool = False
    no_reservations_evidence: list[str] = Field(default_factory=list,max_length=3)
    blockers: list[Boundary] = Field(default_factory=list,max_length=15)
    unmapped_issues: list[str] = Field(default_factory=list,max_length=5)


def next_question(session):
    policy=config('discovery')
    if session.discovery_finished or len(session.discovery_responses)>=policy['maximum_questions']:return None
    done={r['selection_key'] for r in session.discovery_responses}
    def make(kind,target=None,reason=''):
        key=kind+':'+(target or 'overall')
        if key in done:return None
        stance=session.draft.current_route_stance.interpretation
        template=kind
        if kind=='reasons':template='reasons_'+(stance if stance!='unassessed' else 'uncertain')
        label=CONCERNS[target]['label'] if target in CONCERNS else next((i['wording'] for i in session.unmapped_issues if i['id']==target),'')
        text=policy['questions'][template].format(topic=label)
        if kind=='blocker':
            c=next((c for c in session.draft.concerns if c.concern_id==target),None)
            wording=next((session.evidence[r].text for r in c.excerpts if r in session.evidence),'') if c else ''
            text='You said: “'+wording+'”\nIf the other issues were resolved but '+label.lower()+' stayed as originally described, would you still oppose the route?'
        choices={'stance':['supported','opposed','mixed','uncertain'],
            'reasons':list(CONCERNS)+['other','cannot_specify']+(['no_reservations'] if stance=='supported' else []),
            'topic':['supported','opposed','mixed','uncertain','cannot_specify'],
            'changes':['yes','no','unsure'], 'blocker':['yes','no','unsure'], 'unmapped':['cannot_specify']}[kind]
        return {'id':'D'+str(len(session.discovery_responses)+1),'selection_key':key,'kind':kind,'concern_id':target if target in CONCERNS else None,
            'issue_id':target if kind=='unmapped' else None,'facets':deepcopy(CONCERNS[target]['facets']) if target in CONCERNS else [],
            'text':text,'choices':choices,'multiple':kind=='reasons','context':'original','selection_reason':reason,'policy_version':policy['version']}
    stance=session.draft.current_route_stance.interpretation
    if stance=='unassessed':
        q=make('stance',reason='Overall original-proposal stance is not explicit.')
        if q:return q
    if session.no_reservations:return None
    by={c.concern_id:c for c in session.draft.concerns}
    clear_topics=[c for c in by.values() if c.status=='mapped' and (c.position!='unassessed' or c.conditional_willingness!='not_stated')]
    if (not clear_topics) and not session.discovery_topics:
        q=make('reasons',reason='No assessment topic/reason is evidenced; acceptance and rejection are treated symmetrically.')
        if q:return q
    # Canonical ordering keeps priority stable across model array ordering.
    topics=[cid for cid in CONCERNS if cid in session.discovery_topics]+[cid for cid in CONCERNS if cid in by and cid not in session.discovery_topics and cid not in session.discovery_candidate_exclusions]
    for cid in topics:
        c=by.get(cid)
        if c is None or c.status=='needs_clarification' or not c.facets or c.position=='unassessed' or (c.position=='uncertain' and not c.conditions):
            q=make('topic',cid,'Topic selected or meaning/facet/needed information remains unclear.')
            if q:return q
    for cid in topics:
        c=by.get(cid)
        if c and c.status=='mapped' and c.position in {'opposed','mixed'} and c.conditional_willingness=='not_stated' and cid not in session.acceptable_changes:
            q=make('changes',cid,'Possible acceptance changes have not been stated.')
            if q:return q
    for cid in topics:
        c=by.get(cid)
        if c and c.status=='mapped' and c.position in {'opposed','mixed'} and cid not in session.blockers:
            q=make('blocker',cid,'Whether this objection is independently decisive is not explicit.')
            if q:return q
    for issue in session.unmapped_issues:
        q=make('unmapped',issue['id'],'Issue has no supported canonical mapping; preserve and clarify its wording.')
        if q:return q
    return None


def report(session):
    coverage=[]
    # Actual facets, not just broad registry relevance, govern test coverage.
    for c in session.draft.concerns:
        gates=[]
        if c.concern_id=='perceived_safety_privacy' and 'personal_privacy' in c.facets:gates.append('q1')
        if c.concern_id=='technical_safety_security_privacy' and 'data_security' in c.facets:gates.append('q1')
        if c.concern_id in {'noise','visual_pollution'}:gates.append('q2')
        if c.concern_id=='welfare_equity' and 'medical_public_benefit' in c.facets:gates.append('q3')
        actual=[q['id'] for q in session.questions if q['id'] in gates]
        coverage.append({'concern_id':c.concern_id,'facets':c.facets,'status':'clarified' if c.status=='mapped' else 'needs_clarification',
            'hypothetical_question_ids':actual,'hypothetical_note':'See actual answers and facet tracking.' if actual else 'Clarified or recorded, but not tested by a relevant hypothetical modification.'})
    return {'policy_version':config('discovery')['version'],'finished':session.discovery_finished,'stop_reason':session.discovery_stop_reason,
        'presented_questions':deepcopy(session.discovery_questions),'responses':deepcopy(session.discovery_responses),
        'events':deepcopy(session.discovery_events),'excluded_initial_candidates':deepcopy(session.discovery_candidate_exclusions),'selected_topics':deepcopy(session.discovery_topics),'no_reservations':session.no_reservations,
        'blockers':deepcopy(session.blockers),'boundary_nominations':deepcopy(session.boundary_nominations),'acceptable_changes':session._discovery_boundaries(),
        'unmapped_issues':deepcopy(session.unmapped_issues),'topic_followup_coverage':coverage,
        'unresolved_questions':[{'question_id':q['id'],'reason':q['selection_reason'],'status':'skipped' if any(r['question_id']==q['id'] and r['skipped'] for r in session.discovery_responses) else 'unanswered'} for q in session.discovery_questions if not any(r['question_id']==q['id'] and not r['skipped'] for r in session.discovery_responses)],
        'unresolved_topics':list(dict.fromkeys([cid for cid in session.discovery_topics if not any(c.concern_id==cid and c.status=='mapped' for c in session.draft.concerns)]+[c.concern_id for c in session.draft.concerns if c.status=='needs_clarification' or c.position in {'uncertain','unassessed'}])),
        'unconfirmed_acceptance_changes':[c.concern_id for c in session.draft.concerns if c.position in {'opposed','mixed'} and c.conditional_willingness=='not_stated' and c.concern_id not in session.acceptable_changes],
        'unknown_blocker_topics':[c.concern_id for c in session.draft.concerns if c.position in {'opposed','mixed'} and (c.concern_id not in session.blockers or session.blockers[c.concern_id]['status']=='unsure')],
        'limit':config('discovery')['maximum_questions'],'scoring_effect':'None from topic selection or blocker metadata; scoring rules unchanged.'}
