"""Synthetic software/model evaluation; FN labels are illustrative references."""
import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path
from iam_sra.settings import ROOT, config
from iam_sra.schemas import SCHEMA_VERSION
from iam_sra.conversation_client import ConversationClient
from iam_sra.mock import MockConversationClient
from iam_sra.session import Session
from iam_sra.schemas import Assessment
from iam_sra.scoring import aggregate
from iam_sra.assessment import AssessmentError

def evaluate_result(result, case, ref):
    scores={c.concern_id:c.score for c in result.concerns if c.status=='assessed'}
    actual=set(scores);required=set(case['required_concerns']);optional=set(case.get('optional_concerns',[]))
    checks={'required_concerns':required<=actual,'no_unexpected_concerns':not actual-required-optional}
    for key,actual_value in [('expected_stance',result.current_route_stance.interpretation),('expected_medical_support',result.medical_public_benefit_support.interpretation),('expected_conditions',bool(result.acceptance_conditions))]:
        if case.get(key) is not None:checks[key]=case[key]==actual_value
    by_id={c.concern_id:c for c in result.concerns}
    for cid,expected in case.get('expected_willingness',{}).items():
        checks['willingness_'+cid]=cid in by_id and by_id[cid].conditional_willingness==expected
    for cid,(lower,upper) in case.get('score_ranges',{}).items():
        checks['provisional_anchor_band_'+cid]=cid in scores and lower<=scores[cid]<=upper
    row={'scores':scores,'assessment':result.model_dump(),'aggregate':aggregate(result),'checks':checks,'qualitative_agreement':all(checks.values()),'missing_required':sorted(required-actual),'unexpected_concerns':sorted(actual-required-optional),'stance':result.current_route_stance.interpretation,'medical_support':result.medical_public_benefit_support.interpretation,'conditions_present':bool(result.acceptance_conditions)}
    if case['id']=='fn_reference':
        row['fn_source_labels']=ref['scores']
        row['fn_source_score_deltas']={cid:scores[cid]-score if cid in scores else None for cid,score in ref['scores'].items()}
        row['fn_missing_source_dimensions']=sorted(set(ref['scores'])-actual)
        row['fn_mean_difference']=row['aggregate']['mean']-ref['mean'] if row['aggregate']['mean'] is not None else None
        row['fn_final_difference']=row['aggregate']['rounded']-ref['illustrative_final'] if row['aggregate']['rounded'] is not None else None
    return row

def summary(rows):
    total=len(rows);accepted=[r for r in rows if r['accepted']]
    return {'attempted':total,'accepted':len(accepted),'failures':total-len(accepted),'acceptance_rate_all_attempts':len(accepted)/total if total else None,'qualitative_agreement_all_attempts':sum(r.get('qualitative_agreement',False) for r in rows)/total if total else None,'failure_categories':{code:sum(r.get('failure_category')==code for r in rows) for code in sorted({r['failure_category'] for r in rows if not r['accepted']})},'latency_median_seconds':statistics.median(r['latency_seconds'] for r in rows) if rows else None,'latency_max_seconds':max((r['latency_seconds'] for r in rows),default=None)}

def gpu_snapshot():
    try:
        value=subprocess.run(['nvidia-smi','--query-gpu=index,uuid,name,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,check=True)
        return value.stdout.strip().splitlines()
    except (OSError,subprocess.SubprocessError):return None

def assess_case(text,client):
    """Use the application's score-free interpretation and confirmed initial review."""
    session=Session();session.begin();session.submit(text,client)
    session.finish_discovery();session.confirm(True);session.score_initial(client)
    return Assessment.model_validate(session.initial['assessment']),session

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mock',action='store_true');parser.add_argument('--repeats',type=int,default=3);parser.add_argument('--ids',help='Comma-separated case IDs');parser.add_argument('--output',default='.runtime/evaluation.json');parser.add_argument('--capture-raw',action='store_true',help='Explicitly save raw structured model outputs for synthetic cases only; not routine logs.')
    parser.add_argument('--sample-gpu',action='store_true',help='Record read-only GPU snapshots before/after each assessment; these are samples, not peak measurements.')
    parser.add_argument('--held-out',action='store_true',help='Use the separately frozen post-development paraphrases only.')
    args=parser.parse_args()
    if not 1<=args.repeats<=5:parser.error('repeats must be 1–5')
    cases=json.loads((ROOT/('eval/heldout.json' if args.held_out else 'eval/cases.json')).read_text());ref=json.loads((ROOT/'eval/fn_reference.json').read_text())
    if not args.held_out:
        cases.append({'id':'fn_reference','text':ref['citizen_text'],'required_concerns':ref['defensible_mapping']['required'],'optional_concerns':ref['defensible_mapping']['optional'],'expected_stance':'opposed','expected_medical_support':'supported','expected_conditions':True,'expected_willingness':{'noise':'willing','perceived_safety_privacy':'willing','welfare_equity':'not_stated'},'score_ranges':{'noise':[2,4],'perceived_safety_privacy':[2,4],'welfare_equity':[7,9]}})
    if args.ids:
        ids=set(args.ids.split(','));unknown=ids-{c['id'] for c in cases}
        if unknown:parser.error('Unknown case IDs: '+','.join(sorted(unknown)))
        cases=[c for c in cases if c['id'] in ids]
    client=MockConversationClient() if args.mock else ConversationClient();rows=[];output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    def write():
        variation={cid:{i:sorted({r['scores'][i] for r in rows if r['id']==cid and i in r.get('scores',{})}) for i in {k for r in rows if r['id']==cid for k in r.get('scores',{})}} for cid in {r['id'] for r in rows}}
        report={'notice':'Synthetic engineering evaluation, not scientific validation. Denominators include all attempted cases. Source integer agreement is empirical, never forced. Raw outputs saved only with explicit --capture-raw.','mode':'MOCK' if args.mock else 'LIVE','versions':{'schema':SCHEMA_VERSION,'prompt':config('prompts')['version'],'rubric':config('scoring')['rubric_version'],'registry':config('concerns')['version']},'model':config('model'),'settings':getattr(client,'last_settings',{}),'summary':summary(rows),'results':rows,'score_variation':variation}
        output.write_text(json.dumps(report,indent=2)+'\n')
    for case in cases:
        for repeat in range(args.repeats):
            start=time.monotonic();row={'id':case['id'],'repeat':repeat,'mode':'MOCK' if args.mock else 'LIVE','accepted':False,'qualitative_agreement':False}
            if args.sample_gpu:row['gpu_before']=gpu_snapshot()
            try:
                result,session=assess_case(case['text'],client)
                row.update(evaluate_result(result,case,ref),accepted=True,
                           scripted_confirmation=True,scope='Current confirmed initial assessment; no follow-ups.',
                           confirmed_meaning=session.confirmed,
                           stage_diagnostics=[{'stage':item['stage'],'diagnostics':item['diagnostics']} for item in session.inference])
                if args.capture_raw:row['stage_raw_traces']=[{'stage':item['stage'],'raw_model_trace':item['raw_model_trace']} for item in session.inference]
            except AssessmentError as exc:row.update(error=str(exc),failure_category=exc.code)
            row.update(attempts=getattr(client,'last_diagnostics',[]),raw_model_scores=getattr(client,'last_raw_scores',{}),latency_seconds=round(time.monotonic()-start,3))
            if args.capture_raw:row['raw_trace']=getattr(client,'last_trace',[])
            if args.sample_gpu:row['gpu_after']=gpu_snapshot()
            rows.append(row);write();print(case['id'],repeat,row['accepted'],row['qualitative_agreement'],row['latency_seconds'],flush=True)
    print(json.dumps(summary(rows),indent=2))
if __name__=='__main__':main()
