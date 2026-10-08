"""Transparent experimental progression policy; original/conditional ratings stay separate."""
from copy import deepcopy
from .settings import CONCERNS, config
from .schemas import Assessment
from .scoring import aggregate
from .updates import facet_state


def progression(session):
    """Derive at most one bounded adjustment per concern from confirmed independent gates."""
    policy=config('updates')['progression']
    base=session.final or session.initial
    if not base:return None
    assessment=Assessment.model_validate(base['assessment'])
    decisions=[]
    for c in assessment.concerns:
        facts=[f for f in session.original_facets.values() if f.concern_id==c.concern_id]
        required=[f.facet for f in facts if f.position in {'opposed','mixed'} or f.condition_ids]
        if not facts and (c.position in {'opposed','mixed'} or c.conditions):required=list(c.facets)
        states={f:facet_state(session,c.concern_id,f)[0] for f in required}
        refs=list(dict.fromkeys(r for f in required for r in facet_state(session,c.concern_id,f)[1]))
        relevant=[r for r in session.responses if not r.get('skipped') and any(t['concern_id']==c.concern_id and t['facet'] in required for t in r['presented_question']['contract']['targets'])]
        # New hypothetical reservations/conditions cannot silently become full resolution.
        qualifications=[]
        for r in relevant:
            patch=r.get('clarification_meaning')
            if r.get('clarification_context')=='original' or not patch:continue
            qualifications.extend(x for x in patch['concerns'] if x['concern_id']==c.concern_id and
                                  (x['position']!='supported' or x['conditions']))
        unresolved_conflict=any(p.get('target')==c.concern_id for p in session.conflicts.values())
        confirmed=bool(session.updated_confirmed) and bool(required) and not unresolved_conflict
        all_resolved=all(v=='resolved_under_modification' for v in states.values())
        all_tested=all(v in {'resolved_under_modification','partially_resolved','remaining_objection'} for v in states.values())
        delta=0
        if confirmed:
            if 'remaining_objection' in states.values():delta=policy['rejection_change']
            elif all_tested and (not all_resolved or not qualifications):
                delta=policy['maximum_positive_change_per_concern'] if all_resolved else policy['partial_change']
        old=c.score
        if old is not None:c.score=max(1,min(9,old+delta))
        gain=c.score-old if old is not None else 0
        if old is None:reason='No original concern score: unavailable evidence cannot receive a numerical adjustment.'
        elif delta<0:reason='The proposed mitigation was rejected for a required aspect; apply -2 once to this concern, bounded at 1.'
        elif delta==2:reason='All required aspects are fully addressed; apply +2 once to this concern, bounded at 9.'
        elif delta==1:reason='Required aspects were tested and the concern is partly addressed; apply +1 once, bounded at 9.'
        elif qualifications or unresolved_conflict:reason='Clarification retains a reservation, condition or conflict; no automatic adjustment.'
        else:reason='No confirmed evaluable mitigation outcome for all required aspects; retain the original-proposal score.'
        decisions.append({'concern_id':c.concern_id,'original_after_clarification':old,'progression_score':c.score,'gain':gain,
                          'required_facets':required,'gate_states':states,'evidence_ids':refs,'reason':reason,
                          'policy_version':policy['version'],'independent_hypotheses':True})
    ag=aggregate(assessment)
    priority=next((r for r in reversed(session.responses) if r['question_id']=='macro_policy'),None)
    requested=(config('updates')['macro_policy']['score_adjustments'].get(priority.get('code'),0)
               if session.updated_confirmed and priority and not priority.get('skipped') else 0)
    before=ag['rounded']
    ceiling=min(9,ag['cap']) if ag['cap'] is not None else 9
    after=max(1,min(ceiling,before+requested)) if before is not None else None
    ag['policy_adjustment']={'before':before,'requested':requested,'applied':after-before if before is not None else 0,
                             'after':after,'ceiling':ceiling,'question_id':'macro_policy'}
    ag['rounded']=after
    return {'assessment':assessment.model_dump(),'aggregate':ag,'decisions':decisions,
            'policy':deepcopy(policy),'basis':'bounded_followup_progression','proposal_context':'independent_hypotheses',
            'meaning':'Original-proposal baseline plus bounded independent-gate adjustments. This is not a conditional acceptance rating or proof of acceptance of combined changes.',
            'confirmation_sha256':session.updated_confirmed['sha256'] if session.updated_confirmed else None}


def final_review(session):
    """Presentation/export data share one arithmetic source and preserve all profiles."""
    from .reporting import final_summary
    summary=final_summary(session)
    progressive=progression(session)
    selected=progressive if summary['selected_profile']=='bounded_followup' else session.conditional if summary['selected_profile']=='conditional_modified' else session.final
    def by(snapshot):return {c['concern_id']:c for c in snapshot['assessment']['concerns']} if snapshot else {}
    initial=by(session.initial);original=by(session.final);last=by(selected)
    gains={d['concern_id']:d for d in progressive['decisions']} if progressive else {}
    rows=[]
    for cid in CONCERNS:
        a=initial.get(cid,{}).get('score');b=original.get(cid,{}).get('score');z=last.get(cid,{}).get('score')
        decision=gains.get(cid,{})
        refs=decision.get('evidence_ids',[])
        rows.append({'concern_id':cid,'initial_score':a,'validated_original_score':b,'final_score':z,
                     'change':z-a if a is not None and z is not None else None,
                     'progression_gain':decision.get('gain',0) if summary['selected_profile']=='bounded_followup' else None,
                     'original_reason':session.final.get('update_reasons',{}).get(cid,'') if session.final else '',
                     'update_reason':decision.get('reason','') if summary['selected_profile']=='bounded_followup' else last.get(cid,{}).get('rationale','Unavailable.'),
                     'evidence':[{'id':r,'text':session.evidence[r].text,'context':session.evidence[r].context} for r in refs if r in session.evidence]})
    policy_answers=[{'question_id':r['question_id'],'choice':r['choice'],'code':r['code'],
                     'clarification':r.get('clarification',''),'skipped':r.get('skipped',False),'numerical_change':config('updates')['macro_policy']['score_adjustments'].get(r.get('code'),0) if r['question_id']=='macro_policy' and session.updated_confirmed and not r.get('skipped') else 0,
                     'applied_change':progressive['aggregate']['policy_adjustment']['applied'] if progressive and r['question_id']=='macro_policy' and r is next((x for x in reversed(session.responses) if x['question_id']=='macro_policy'),None) else 0}
                    for r in session.responses if r['question_id'] in {'macro_policy','q3'}]
    return {'initial_aggregate':session.initial['aggregate'] if session.initial else None,
            'validated_original_aggregate':session.final['aggregate'] if session.final else None,
            'final_aggregate':selected['aggregate'] if selected else None,
            'final_headline':summary['headline_score'],'final_basis':summary['score_basis'],'final_profile':summary['selected_profile'],
            'progression':progressive,'concerns':rows,'policy_priority_answers':policy_answers,
            'same_coverage':bool(session.initial and selected and session.initial['aggregate']['missing']==selected['aggregate']['missing']),
            'experimental':True}
