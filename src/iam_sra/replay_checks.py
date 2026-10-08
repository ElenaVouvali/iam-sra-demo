"""Engineering replay assertions. No scientific validity or fixed live integers."""
from collections import defaultdict
from .schemas import Assessment
from .scoring import aggregate
from .ordinal import AnchorFacts, NumericScore, decide

def check_export(record, initial_before=None, expected=None):
    checks=[];rubric=[]
    def require(name,ok,detail=''):
        checks.append({'check':name,'passed':bool(ok),'detail':detail})
    evidence=record['dialogue_and_confirmations']['evidence']
    snapshots=record['audit']['snapshots']
    confirmations=record['dialogue_and_confirmations']['confirmed_interpretations']
    require('all_15_domains',len(record['domain_assessments'])==15)
    for name,snapshot in snapshots.items():
        if not snapshot:continue
        require(name+':published_aggregate',record['aggregation'][name]==snapshot['aggregate'])
        require(name+':aggregate_arithmetic',aggregate(Assessment.model_validate(snapshot['assessment']))==snapshot['aggregate'])
        require(name+':confirmed_meaning',any(c['sha256']==snapshot['interpretation_sha256'] for c in confirmations))
        require(name+':score_records',len(snapshot.get('score_records',{}))==15)
        for decision in snapshot.get('score_decisions',[]):
            refs=decision.get('evidence_ids',[])+decision.get('condition_ids',[])
            require(name+':evidence:'+decision['concern_id']+':'+decision['facet'],bool(refs) and all(r in evidence for r in refs))
            if name=='conditional_modified':
                require(name+':context:'+decision['facet'],all(evidence[r]['context']=='modified' for r in decision.get('evidence_ids',[])))
            source=decision.get('source_decision',decision)
            facts=source.get('descriptive_facts')
            if source.get('model_assigned_score') is not None or source.get('origin')=='llm_assigned_score':
                numeric=NumericScore.model_validate(source['model_proposed_description'])
                ok=numeric.score==source['score']==source.get('model_assigned_score')
                ok=ok and all(r in evidence for r in numeric.evidence_ids)
                if numeric.score==9:
                    ids=source.get('endorsement_source_ids',[])
                    ok=ok and bool(ids) and all(evidence[r]['source'] in {'citizen_original','citizen_discovery','citizen_correction'} for r in ids) and bool((source.get('endorsement_review') or {}).get('supported'))
                rubric.append({'check':name+':llm_score_preserved:'+source['concern_id']+':'+source['facet'],'passed':bool(ok),'detail':'Numerical provenance and evidence validation, not independent semantic validation.'})
            elif facts:
                result=decide(AnchorFacts.model_validate(facts),source.get('confirmed_position','uncertain'),source.get('highest_criterion_verified',False))
                ok=result['score']==source['score'] and result['anchor_rule_id']==source['anchor_rule_id']
                if source['score']==9:
                    ids=source.get('endorsement_source_ids',[])
                    ok=ok and bool(ids) and all(evidence[r]['source'] in {'citizen_original','citizen_discovery','citizen_correction'} for r in ids) and bool((source.get('endorsement_review') or {}).get('supported'))
                rubric.append({'check':name+':anchor:'+source['concern_id']+':'+source['facet'],'passed':bool(ok)})
            else:rubric.append({'check':name+':anchor_description_available','passed':False})
    initial=snapshots.get('initial_original')
    if initial_before is not None:require('immutable_initial_snapshot',initial==initial_before)
    if expected:
        facets={(f['concern_id'],f['facet']) for f in record['audit']['original_facet_meanings'] if f['position']!='unassessed'}
        require('required_fn_facets',set(map(tuple,expected.get('facets',[])))<=facets)
        require('excluded_fn_topics',not set(expected.get('exclude',[]))&{cid for cid,f in facets})
        presented=record['dialogue_and_confirmations']['presented_followups']
        require('relevant_fn_questions',{'q1','q2'}<={q['id'] for q in presented})
        require('no_routine_reconfirmation',not any(q['id'].startswith('original_check') for q in presented))
    conditional=snapshots.get('conditional_modified')
    if conditional:
        joint=record['dialogue_and_confirmations']['joint_answers']
        require('explicit_joint_decision',bool(joint) and joint[-1]['choice'] in {'accept','reject'})
    return {'structural_evidence_checks':checks,'rubric_checks':rubric,
        'structural_evidence_checks_passed':all(c['passed'] for c in checks),
        'rubric_checks_passed':bool(rubric) and all(c['passed'] for c in rubric)}

def stage_metrics(session,client=None):
    """Deduplicate metrics copied into snapshots/audit; failures are included."""
    entries={}
    def visit(value):
        if isinstance(value,dict):
            if 'request_id' in value:entries[value['request_id']]=value
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(session.inference)
    if client:visit(getattr(client,"last_settings",{}))
    for snapshot in [session.initial,session.final,session.conditional]:
        if snapshot:visit(snapshot)
    stages=defaultdict(lambda:{'model_calls':0,'retries':0,'cache_hits':0,'latency_seconds':0})
    for metric in entries.values():
        row=stages[metric['stage']]
        for field in ['model_calls','retries','latency_seconds']:row[field]+=metric.get(field,0)
        row['cache_hits']+=int(metric.get('cache_hit',False))
    return dict(stages)


def live_response_received(session,client):
    """A failed connection is an attempted request, not model inference."""
    diagnostics=[d for row in session.inference for d in row.get('diagnostics',[])]+getattr(client,'last_diagnostics',[])
    return any('prompt_tokens' in d and not d.get('cache_hit') and d.get('failure')!='transport' for d in diagnostics)

def write_report(path,record):
    """Keep previous replay artifacts even when the default path is reused."""
    import json
    from pathlib import Path
    from uuid import uuid4
    path=Path(path)
    if path.exists():path=path.with_name(path.stem+'-'+uuid4().hex[:8]+path.suffix)
    path.parent.mkdir(parents=True,exist_ok=True)
    record['report_path']=str(path)
    path.write_text(json.dumps(record,indent=2)+'\n')
    return path
