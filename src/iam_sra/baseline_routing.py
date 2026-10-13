"""Proposed evidence requirements and deterministic routing; no readiness scale.

Frozen instruments without this policy continue through their original selectors.
Rule names are allowlisted; configuration never supplies executable expressions.
"""
from copy import deepcopy

REQUIREMENTS={
 'familiarity_self_report':('familiarity',{'self_report'}),
 'concept_definition':('concept',{'concept_explanation'}),
 'delivery_use':('delivery',{'use_knowledge'}),
 'effect_reasoning':('understanding',{'explained_impact'}),
 'experience_context':('exposure',{'learning_exposure'}),
 'information_need':('information',{'information_need'}),
 'participation_access':('opportunity',{'opportunity','barrier','intention'}),
 'actual_contribution':('participation',{'contribution'}),
 'experience_domain':('exposure',{'learning_exposure','contribution'}),
 'reported_outcome':('influence',{'influence'}),
 'scope_resolution':(None,set()),
}
CONDITIONS={'none','material_ambiguity','understanding_claim_without_reason',
 'actual_exposure_without_contribution_evidence','actual_experience_unknown_domain','actual_contribution_without_outcome'}
INTERACTIONS={'unsure','declined','confused','already_answered'}
ACTUAL={'learning_exposure','contribution','influence'}


def validate_registry(instrument):
    policy=instrument['routing'];items=instrument['core_questions']+instrument['probes']
    if not 1<=policy['maximum_questions']<=8 or not 0<=policy['maximum_probes']<=2:
        raise ValueError('Unsupported baseline question budget.')
    if policy['maximum_consecutive_probes']!=1 or policy['reserve_remaining_core_slots'] is not True:
        raise ValueError('Unsupported baseline scheduling policy.')
    if set(policy['role_mapping'])!=set(instrument['stakeholders']):raise ValueError('Every role needs an explicit mapping.')
    if len({q['id'] for q in items})!=len(items):raise ValueError('Question IDs must be unique.')
    required={'id','target_requirement','applicable_perspectives','applicable_roles','prerequisites','variants',
              'response_format','completion_rule','probe_condition','priority','source_reference','review_status','version','locale'}
    for q in items:
        if not required<=q.keys():raise ValueError('Incomplete baseline question registry.')
        if q['target_requirement'] not in REQUIREMENTS or q['probe_condition'] not in CONDITIONS:
            raise ValueError('Unknown baseline routing rule.')
        if q['completion_rule']!='answered_or_addressed' or set(q['prerequisites'])-{'confirmed_active_evidence'}:
            raise ValueError('Unknown baseline completion/prerequisite rule.')
        if set(q['applicable_perspectives'])-set(instrument['perspectives']) or set(q['applicable_roles'])-set(instrument['stakeholders']):
            raise ValueError('Unknown question applicability.')
        if q['response_format'] not in {'selection','text'}:raise ValueError('Unknown response format.')
        if not isinstance(q['priority'],int):raise ValueError('Question priority must be an integer.')
    experience=next(q for q in items if q['id']=='experience')
    if any('organisation_'+r not in experience['variants'] for r in policy['role_mapping'].values()):
        raise ValueError('Missing organisational role wording.')


def active_events(events):return [e for e in events if e['active'] and e['confirmed']]
def relevant(c):return c.get('subject') in {'respondent','organisation'}
def positive(c):return c.get('status')=='supported' and relevant(c)
def actual(c):return positive(c) and c['kind'] in ACTUAL and c['temporality']=='actual'
def references(rows):return sorted({c['evidence_id'] for c in rows})


def compatible_context(a,b):
    """Only link claims when their cited words identify the same activity.

    Matching actor/domain and absent dates do not establish activity identity.
    """
    if a['subject']!=b['subject']:return False
    if a['domain'] in {'IAM','transferable'} and b['domain'] in {'IAM','transferable'} and a['domain']!=b['domain']:return False
    aa=(a.get('activity_quote') or '').strip().casefold()
    ba=(b.get('activity_quote') or '').strip().casefold()
    if not aa or not ba or aa!=ba:return False
    if a.get('time_quote') and b.get('time_quote') and a['time_quote'].casefold()!=b['time_quote'].casefold():return False
    return True


def same_effect_scope(assertion, explanation):
    """Conservatively pair effect claims only when their exact spans overlap."""
    a=(assertion.get('span_quote') or '').strip().casefold()
    b=(explanation.get('span_quote') or '').strip().casefold()
    return bool(a and b and (a in b or b in a))


def scope_issues(claims):
    claims=[c for c in claims if not c.get('clarified_by_evidence_ids')]
    issues=[]
    for c in claims:
        if not relevant(c) and c.get('subject')!='unknown':continue
        flags=list(c.get('ambiguities',[]))
        if c['kind'] in ACTUAL and c.get('subject')=='unknown' and 'subject' not in flags:flags.append('subject')
        if flags:issues.append({'dimension':c['dimension'],'ambiguity':flags[0],'evidence_ids':[c['evidence_id']]})
    for dim in {c['dimension'] for c in claims}:
        pos=[c for c in claims if c['dimension']==dim and actual(c)]
        neg=[c for c in claims if c['dimension']==dim and c['kind']=='absence' and relevant(c)]
        for a in pos:
            for b in neg:
                if a['subject']!=b['subject']:continue
                if a['domain'] in {'IAM','transferable'} and b['domain'] in {'IAM','transferable'} and a['domain']!=b['domain']:continue
                # Different stated activities/periods are not assumed identical.
                if a.get('time_quote') and b.get('time_quote') and a['time_quote'].casefold()!=b['time_quote'].casefold():continue
                if a.get('activity_quote') and b.get('activity_quote') and a['activity_quote'].casefold()!=b['activity_quote'].casefold():continue
                issues.append({'dimension':dim,'ambiguity':'activity','evidence_ids':references([a,b])})
    return sorted(issues,key=lambda x:(x['dimension'],x['ambiguity'],x['evidence_ids']))


def requirement_state(item,claims,subjects=None):
    claims=[c for c in claims if not c.get('clarified_by_evidence_ids')]
    original=[c for c in claims if subjects is None or c.get('subject') in subjects|{'unknown'}]
    if subjects is not None:claims=[c for c in claims if c.get('subject') in subjects]
    req=item['target_requirement'];dim,kinds=REQUIREMENTS[req]
    dimensions={'exposure','participation'} if req=='experience_context' else {dim}
    issues=[i for i in scope_issues(original) if i['dimension'] in dimensions]
    if issues:return 'ambiguous_scope',sorted({eid for i in issues for eid in i['evidence_ids']})
    rows=[c for c in claims if c['dimension']==dim and relevant(c)]
    if req=='experience_context':
        rows=[c for c in claims if c['dimension'] in {'exposure','participation'} and relevant(c)]
        kinds={'learning_exposure','contribution'}
    if req=='experience_domain':rows=[c for c in claims if c['kind'] in {'learning_exposure','contribution'} and relevant(c)]
    satisfied=[c for c in rows if positive(c) and c['kind'] in kinds and not c.get('ambiguities')]
    if req in {'experience_context','actual_contribution','experience_domain','reported_outcome'}:
        satisfied=[c for c in satisfied if actual(c)]
    if req=='experience_domain':satisfied=[c for c in satisfied if c['domain'] in {'IAM','transferable'}]
    if req=='reported_outcome':satisfied=[c for c in satisfied if c.get('outcome_relation')=='reported_link']
    if satisfied:return 'satisfied',references(satisfied)
    unknown=[c for c in rows if c['kind']=='unknown' or c.get('status')=='unknown']
    absent=[c for c in rows if c['kind']=='absence' or c.get('status')=='explicit_absence']
    if unknown:return 'unknown',references(unknown)
    if absent:return 'explicit_absence',references(absent)
    return 'missing',references(rows)


def evidence_status(c):
    if c.get('clarified_by_evidence_ids'):return 'clarified_scope'
    if c.get('ambiguities'):return 'unresolved_contradiction' if 'contradiction' in c['ambiguities'] else 'ambiguous_scope'
    return {'self_report':'familiarity_self_report','recognition':'recognition_only',
        'claim_without_detail':'assertion_without_explanation','explained_impact':'reasoned_explanation',
        'learning_exposure':'self_reported_actual_activity','contribution':'self_reported_actual_contribution',
        'influence':'self_reported_outcome' if c.get('outcome_relation')=='reported_link' else 'outcome_relationship_unknown',
        'absence':'explicit_absence','unknown':'unknown'}.get(c['kind'],c['kind'])


def enrich_profile(result,events,instrument,respondent=None):
    active=active_events(events);claims=result['claims']
    # A confirmed clarification can resolve a specific flagged scope without
    # rewriting the original event or claiming that the reported event is true.
    result['scope_clarifications']=[]
    for e in active:
        if e['question']['id']!='scope' or e['control']!='answer':continue
        flag=e['question'].get('variant_id');trigger=e['question'].get('triggering_evidence_ids',[])
        for old in claims:
            if old['evidence_id'] not in trigger:continue
            new=[c for c in e['claims'] if c['dimension']==old['dimension'] and c['kind']==old['kind']
                 and not c.get('ambiguities') and relevant(c) and
                 (flag=='subject' or flag=='activity' and c.get('activity_quote') or
                  flag=='time' and c.get('time_quote') or flag=='meaning')]
            if not new:continue  # Conflicting accounts require correction, not an assumed resolution.
            old['clarified_by_evidence_ids']=references(new)
            result['scope_clarifications'].append({'original_evidence_id':old['evidence_id'],
                'clarification_event_id':e['id'],'evidence_ids':references(new),'scope':flag})
    issues=scope_issues(claims)
    perspective=respondent['perspective'] if respondent else active[-1].get('answering_perspective') if active else None
    subjects={'respondent','organisation'} if perspective=='organisation' else {'respondent'}
    result['unresolved_scope']=sorted({i['dimension'] for i in issues})
    for dim,row in result['coverage'].items():
        if dim in result['unresolved_scope']:row['status']='scope_unclear'
        elif row['status']=='scope_unclear':
            dimrows=[c for c in claims if c['dimension']==dim]
            row['status']='evidence_recorded' if any(positive(c) for c in dimrows) else 'explicit_absence'
        row['evidence_statuses']=sorted({evidence_status(c) for c in claims if c['dimension']==dim})
    result['ambiguities']=issues
    result['requirements']={q['id']:{'target_requirement':q['target_requirement'],
        'status':requirement_state(q,claims,subjects)[0],'evidence_ids':requirement_state(q,claims,subjects)[1]}
        for q in instrument['core_questions']}
    result['interview_dispositions']={}
    for q in instrument['core_questions']:
        answered=next((e for e in reversed(active) if e['question']['id']==q['id']),None)
        related=next((e for e in reversed(active) if q['dimension'] in e['question'].get('covers',[e['question']['dimension']])
                      and (e['control'] in {'skip','unsure','decline'} or e.get('interaction') in INTERACTIONS)),None)
        state,ids=requirement_state(q,claims,subjects)
        if not answered and related and state!='satisfied':answered=related
        disposition=('declined' if answered and (answered['control']=='decline' or answered.get('interaction')=='declined') else
            'skipped' if answered and answered['control']=='skip' else
            'unknown' if answered and (answered['control']=='unsure' or answered.get('interaction') in {'unsure','confused'}) else
            'answered' if answered else 'already_covered' if state=='satisfied' else
            'unknown' if state=='unknown' else 'answered' if state=='explicit_absence' else
            'budget_limited' if len(active)>=instrument['routing']['maximum_questions'] else 'not_asked')
        result['interview_dispositions'][q['id']]={'disposition':disposition,'requirement_status':state,'evidence_ids':ids}
        if respondent and (respondent['perspective'] not in q['applicable_perspectives'] or respondent['stakeholder_category'] not in q['applicable_roles']):
            result['interview_dispositions'][q['id']]['disposition']='not_applicable'


def adaptive_plan(events,instrument,respondent):
    validate_registry(instrument)
    from .baseline import profile
    active=active_events(events);current=profile(active,instrument,respondent);claims=current['claims'];policy=instrument['routing']
    done={e['question']['id'] for e in active};omitted=[];cores=[];probes=[]
    subjects={'respondent','organisation'} if respondent['perspective']=='organisation' else {'respondent'}
    scoped_claims=[c for c in claims if c.get('subject') in subjects]
    suppressed={d for e in active if e['control'] in {'skip','unsure','decline'} or e.get('interaction') in INTERACTIONS
                for d in e['question'].get('covers',[e['question']['dimension']])}
    suppressed|={c['dimension'] for c in scoped_claims if c['kind']=='unknown'}
    role=policy['role_mapping'].get(respondent['stakeholder_category'],policy['default_role'])
    def prepare(q,reason,trigger=(),ambiguity=None):
        r=deepcopy(q);variant='organisation_'+role if respondent['perspective']=='organisation' and 'organisation_'+role in q['variants'] else 'organisation' if respondent['perspective']=='organisation' else 'personal'
        if ambiguity in q['variants']:variant=ambiguity
        r.update(question_text=q['variants'][variant],variant_id=variant,
            is_probe=q in instrument['probes'],selection_reason=reason,
            triggering_evidence_ids=list(trigger),routing_version=policy['version'],
            claim_scope='respondent_or_organisation' if respondent['perspective']=='organisation' else 'respondent')
        if q['id']=='experience' and any(actual(c) and c['kind']=='learning_exposure' for c in scoped_claims):
            r['question_text']=q['when_exposure_already_reported'];r['variant_id']='contribution_after_exposure'
        return r
    for q in sorted(instrument['core_questions'],key=lambda q:(q['priority'],q['id'])):
        if q['id'] in done:continue
        if respondent['perspective'] not in q['applicable_perspectives'] or respondent['stakeholder_category'] not in q['applicable_roles']:
            omitted.append({'question_id':q['id'],'rule_id':'not_applicable','reason':'Outside this respondent scope.'});continue
        state,ids=requirement_state(q,claims,subjects)
        if q['dimension'] in suppressed:
            omitted.append({'question_id':q['id'],'rule_id':'respondent_suppressed_topic',
                'reason':'Respondent skipped, declined or expressed uncertainty; no repeated probe.',
                'target_requirement':q['target_requirement'],'triggering_evidence_ids':ids})
            continue
        if state in {'satisfied','unknown','explicit_absence'}:
            omitted.append({'question_id':q['id'],'rule_id':'confirmed_evidence_covers_item' if state=='satisfied' else 'confirmed_answer_addresses_item',
                            'reason':'Confirmed evidence satisfies the requirement.' if state=='satisfied' else 'Absence/uncertainty already expressed; not evidence of sufficiency.',
                            'target_requirement':q['target_requirement'],'triggering_evidence_ids':ids});continue
        cores.append(prepare(q,'Highest-priority missing shared objective.'))
    def rows(kind):return [c for c in scoped_claims if actual(c) and c['kind']==kind]
    issues=[i for i in current['ambiguities'] if i['dimension'] not in suppressed]
    candidates={
      'material_ambiguity':issues[0]['evidence_ids'] if issues else [],
      'understanding_claim_without_reason':references([c for c in scoped_claims if positive(c) and c['kind']=='claim_without_detail'
          and not any(positive(explained) and explained['kind']=='explained_impact' and same_effect_scope(c,explained)
                      for explained in scoped_claims)]) ,
      'actual_exposure_without_contribution_evidence':references([a for a in rows('learning_exposure') if not any(c['dimension']=='participation' and c['kind']!='intention' and compatible_context(a,c) for c in scoped_claims)]),
      'actual_experience_unknown_domain':references([c for c in rows('learning_exposure')+rows('contribution') if c['domain']=='unknown']),
      'actual_contribution_without_outcome':references([a for a in rows('contribution') if not any(
          (c['dimension']=='influence' or c['dimension']=='participation' and c['kind']=='absence') and compatible_context(a,c) for c in scoped_claims)]),
    }
    for q in sorted(instrument['probes'],key=lambda q:(q['priority'],q['id'])):
        if q['id'] in done or q['dimension'] in suppressed:continue
        if respondent['perspective'] not in q['applicable_perspectives'] or respondent['stakeholder_category'] not in q['applicable_roles']:
            omitted.append({'question_id':q['id'],'rule_id':'not_applicable','reason':'Outside this respondent scope.'});continue
        ids=candidates[q['probe_condition']]
        if not ids:continue
        item=prepare(q,'Clarify confirmed evidence: '+q['probe_condition'],ids,issues[0]['ambiguity'] if q['id']=='scope' else None)
        if q['id']=='scope':item['dimension']=issues[0]['dimension'];item['covers']=[item['dimension']]
        else:item['covers']=[item['dimension']]
        probes.append(item)
    slots=policy['maximum_questions']-len(active)
    if slots<=0:
        return None,omitted+[{'question_id':q['id'],'rule_id':'total_question_budget','reason':'Question budget reached.'} for q in cores+probes]
    used=sum(e['question']['is_probe'] for e in active)
    allow_probe=used<policy['maximum_probes'] and (not active or not active[-1]['question']['is_probe']) and slots>len(cores)
    if allow_probe and probes:
        latest={c['evidence_id'] for c in active[-1]['claims']} if active else set()
        immediate=[q for q in probes if q['id']=='scope' or latest.intersection(q['triggering_evidence_ids'])]
        if immediate:return immediate[0],omitted
    if cores:return cores[0],omitted
    if allow_probe and probes:return probes[0],omitted
    return None,omitted+[{'question_id':q['id'],'rule_id':'probe_budget_or_suppression','reason':'No further useful clarification within policy.'} for q in probes]
