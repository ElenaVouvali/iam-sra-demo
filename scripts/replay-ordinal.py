"""Bounded serial interpretation + confirmed numerical contrasts. Never use mocks."""
import argparse,json,time
from pathlib import Path
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import EvidenceItem,freeze
from iam_sra.settings import SCENARIO
from iam_sra.replay_checks import write_report

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',nargs='+');p.add_argument('--budget-seconds',type=int,default=240)
    p.add_argument('--output',default='.runtime/ordinal-replay.json');p.add_argument('--no-live',action='store_true')
    args=p.parse_args();fixture=json.loads(Path('eval/ordinal_cases.json').read_text())
    selected=[c for c in fixture['cases'] if not args.cases or c['id'] in args.cases]
    results=[];deadline=time.monotonic()+max(1,min(args.budget_seconds,600))
    for case in selected:
        if args.no_live or time.monotonic()>=deadline:break
        c=ConversationClient();c.bind_session(case['id'],0);c.external_deadline=min(deadline,time.monotonic()+90)
        start=time.monotonic();stage='interpretation';row={'id':case['id'],'attempted':True,'dialogue_completed':False,
            'structural_evidence_checks_passed':False,'rubric_checks_passed':False,'live_model_used':False};stages=[];responses=[]
        evidence={'O.p001':EvidenceItem(id='O.p001',text=case['text'],context='original',source='citizen_original')}
        try:
            m=c.interpret(evidence);stages.extend(c.last_settings.get('request_metrics',[]));responses.extend(c.last_diagnostics);row['meaning']=m.model_dump()
            ids={x.concern_id for x in m.concerns};mapping_ok=set(case.get('require',[]))<=ids and not set(case.get('exclude',[]))&ids
            stage='scripted meaning confirmation and scoring'
            # Scripted engineering confirmation; no claim of citizen agreement.
            frozen=freeze(m,evidence,1,'original',SCENARIO['text'])
            a=c.score(frozen);stages.extend(c.last_settings.get('request_metrics',[]))
            values={x.concern_id:x.score for x in a.concerns};ds=c.last_score_decisions
            rubric_ok=bool(ds) and all(d.get('model_assigned_score')==d['score'] and (d['score']!=9 or d.get('highest_criterion_verified')) for d in ds)
            if case.get('no_highest'):rubric_ok=rubric_ok and all(v!=9 for v in values.values())
            row.update(dialogue_completed=True,structural_evidence_checks_passed=mapping_ok and all(values[cid] is None for cid in case.get('exclude_scores',[])),
                rubric_checks_passed=rubric_ok,scores=values,decisions=ds,attribution=c.last_candidate_projections)
            if not row['structural_evidence_checks_passed'] or not rubric_ok:row['failure_stage']='mandatory correctness checks'
        except Exception as exc:row.update(failure_stage=stage,error_type=type(exc).__name__,error=str(exc));stages.extend(c.last_settings.get('request_metrics',[]))
        row.update(latency_seconds=round(time.monotonic()-start,3),request_metrics=stages,last_diagnostics=c.last_diagnostics,last_raw_trace=c.last_trace)
        responses.extend(c.last_diagnostics)
        row['live_model_used']=any('prompt_tokens' in d and not d.get('cache_hit') and d.get('failure')!='transport' for d in responses)
        row['success']=row['dialogue_completed'] and row['structural_evidence_checks_passed'] and row['rubric_checks_passed'] and row['live_model_used']
        results.append(row);print(json.dumps({k:v for k,v in row.items() if k not in {'meaning','scores','decisions','attribution','request_metrics','last_raw_trace','last_diagnostics'}}),flush=True)
    pending=[c['id'] for c in selected if c['id'] not in {r['id'] for r in results}]
    record={'fixture_version':fixture['version'],'scientific_validation':False,'attempts':results,'not_attempted':pending,
        'live_testing_disabled':args.no_live,'scripted_confirmations':True}
    path=write_report(args.output,record)
    print(json.dumps({'report_path':str(path),'attempts':len(results),'not_attempted':pending}),flush=True)
    return 0 if results and not pending and all(r['success'] for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
