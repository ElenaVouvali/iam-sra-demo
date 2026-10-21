#!/usr/bin/env python3
"""Bounded synthetic matching comparison; no desired levels are sent to the model."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from iam_sra.readiness_bank import load_bank
from iam_sra.indicator_assessment import resolved_scale
from iam_sra.indicator_client import IndicatorClient, POLICY
from iam_sra.privacy import screened_export, safe_message
from iam_sra.settings import ROOT


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--base-url',required=True)
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--baseline-results',type=Path)
 p.add_argument('--case')
 p.add_argument('--resume-from',type=Path,help='Reuse completed records; retry only failures, retaining the original report.')
 args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 bank=load_bank();cases=json.loads((ROOT/'eval/indicator_questionnaire_cases_v02.json').read_text())['cases']
 baseline={r['case_id']:r for r in map(json.loads,args.baseline_results.read_text().splitlines())} if args.baseline_results else {}
 completed={r['case_id']:r for r in map(json.loads,args.resume_from.read_text().splitlines()) if r['status']=='completed'} if args.resume_from else {}
 if any(r.get('policy')!=POLICY for r in completed.values()):
  p.error('Resume records belong to another or unidentified policy. Keep that report and use a fresh output for this policy.')
 records=[]
 for case in cases:
  if args.case and args.case!=case['id']:continue
  if case['id'] in completed:
   records.append(completed[case['id']]);print(case['id'],'reused completed result',flush=True);continue
  profile=case['profile'];client=IndicatorClient(base_url=args.base_url);started=time.monotonic()
  previous=baseline.get(case['id'])
  scope=previous['scope'] if previous else {'response_profile':profile,'context':'general_understanding',
      'use_case':'Synthetic proposed healthcare delivery service','organisation_or_unit':'Municipal planning unit' if profile=='organisational' else '',
      'responsibilities':'Planning and coordination' if profile=='organisational' else '',
      'technical_object':'Synthetic system prototype' if profile=='technical' else '',
      'object_version':'A' if profile=='technical' else '', 'intended_environment':'Laboratory; intended local delivery environment' if profile=='technical' else '',
      'component_scope':'system' if profile=='technical' else ''}
  evidence=previous['input'] if previous else [{'evidence_id':'case_answer_1','answer':case['answer'],'question':case['question'],
      'meaning':case['annotation']['meaning'],'observations':case['annotation']['observations'],
      'information_context':'before_tool_information','scope':scope}]
  record={'case_id':case['id'],'profile':profile,'policy':POLICY,'synthetic':True,'status':'failed','scope':scope,'input':evidence,'expectation':case['expectation']}
  try:
   item=next(i for i in bank['indicators'] if i['id']==case['indicator_id'])
   result=client.match(item,scope,resolved_scale(bank,case['indicator_id'],profile),evidence)
   record.update(status='completed',result=result)
   selected=next((s for s in bank['statements'] if s['id']==result['selected_statement_id']),None)
   level=selected['level'] if selected else None;expected=case['expectation'];levels=expected['acceptable_levels']
   record['checks']={'quotation_integrity':True,'selected_level':level,'allowed_abstention':level is None and expected['abstention_allowed'],
      'within_authored_expectation':level in levels if level is not None else expected['abstention_allowed'],
      'above_authored_range':bool(level is not None and (not levels or level>max(levels))),
      'below_authored_range':bool(level is not None and levels and level<min(levels))}
  except Exception as exc:record['failure']={'code':getattr(exc,'code','runtime'),'message':safe_message(exc)}
  record.update(seconds=round(time.monotonic()-started,3),calls=getattr(client,'session_metrics',{}).get('generation_calls',0))
  records.append(record)
  (args.output/'evaluation-results.jsonl').write_text(''.join(json.dumps(screened_export(r),ensure_ascii=False)+'\n' for r in records))
  print(case['id'],record['status'],record.get('checks',{}).get('selected_level'),flush=True)
 # Include reused tail records too; the incremental file alone can otherwise
 # end at the last newly executed case and disagree with summary.json.
 (args.output/'evaluation-results.jsonl').write_text(''.join(json.dumps(screened_export(r),ensure_ascii=False)+'\n' for r in records))
 summary={'synthetic_only':True,'benchmark_version':'indicator-comparison-0.2.0','policy':POLICY,
    'provenance':{'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'component_sha256':{p:sha256((ROOT/p).read_bytes()).hexdigest() for p in ('src/iam_sra/indicator_client.py','src/iam_sra/questionnaire.py')},
    'working_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True))},
    'bank_source':bank['source'],'runs':records,'comparison':[],'meaning':'Exploratory synthetic comparison. The fixed annotations can be wrong; authored expectations remain provisional. This is not an accuracy estimate.'}
 for record in records:
  old=baseline.get(record['case_id'])
  if old:summary['comparison'].append({'case_id':record['case_id'],'baseline_status':old['status'],'baseline_selected':old.get('result',{}).get('selected_statement_id'),'baseline_calls':old['calls'],'baseline_seconds':old['seconds'],
    'revised_status':record['status'],'revised_selected':record.get('result',{}).get('selected_statement_id'),'revised_calls':record['calls'],'revised_seconds':record['seconds']})
 (args.output/'summary.json').write_text(json.dumps(screened_export(summary),ensure_ascii=False,indent=2)+'\n')
 lines=['# Exploratory synthetic comparison','',summary['meaning'],'','| Case | Baseline | Revised | Calls | Seconds |','| --- | --- | --- | --- | --- |']
 for r in records:lines.append(f"| {r['case_id']} | {baseline.get(r['case_id'],{}).get('result',{}).get('selected_statement_id','unavailable')} | {r.get('result',{}).get('selected_statement_id',r['status'])} | {r['calls']} | {r['seconds']} |")
 lines+=['','Failures remain failures. Range checks and paraphrase consistency are diagnostic signals, not empirical validation. Review selected statements and explanations manually.']
 (args.output/'summary.md').write_text('\n'.join(lines)+'\n')
 return 0 if all(r['status']=='completed' for r in records) else 1

if __name__=='__main__':raise SystemExit(main())
