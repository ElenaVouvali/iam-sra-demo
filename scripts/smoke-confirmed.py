"""Bounded synthetic live confirmation sessions; every attempt, including failures.

Does not restart services, install packages, or substitute mocks.
"""
import argparse
import json
import time
from pathlib import Path
import subprocess
from iam_sra.conversation_client import ConversationClient
from iam_sra.session import Session, State
from iam_sra.settings import config

CASES=[
 ('support','I support the lifesaving hospital deliveries. I accept the original route: the hum is tolerable and navigation cameras do not worry me.'),
 ('opposition','I support saving lives with medical deliveries, but I reject the original route because the hum would disturb my evenings and cameras watching my windows violate my privacy. I would accept if the hum were inaudible and cameras could never view my property.'),
 ('uncertainty','I am unsure about the original route and do not know whether the sound or cameras would be acceptable.'),
 ('mixed','The hospital service is a vital public benefit. I reject the evening hum, but camera shielding would address my personal privacy concern. I would accept the noise if the evening flights stopped. I have not decided about the full route.')]
CASES.append(('fn_reference',json.loads(Path('eval/fn_reference.json').read_text())['citizen_text']))
parser=argparse.ArgumentParser();parser.add_argument('--ids',default='support,opposition,uncertainty,mixed');parser.add_argument('--output',default='.runtime/confirmed-smoke.json');parser.add_argument('--original-correction',action='store_true',help='Synthetic FN citizen explicitly corrects only the original noise position before final confirmation.');args=parser.parse_args()
results=[]
for cid,text in CASES:
 if cid not in args.ids.split(','):continue
 s=Session();c=ConversationClient();start=time.monotonic();stage='interpretation';attempt={'case':cid,'mode':'LIVE','synthetic':True,'success':False,'stages':[],'model':config('model')}
 def mark(label):
  attempt['stages'].append({'stage':label,'diagnostics':c.last_diagnostics,'settings':c.last_settings})
 try:
  s.begin();s.submit(text,c);mark(stage)
  attempt['initial_interpretation']=s.draft.model_dump()
  assert s.initial is None and all(x['stage'] in {'mapping','scope_review'} for x in c.last_diagnostics)
  s.confirm(True);stage='initial scoring';s.score_initial(c);mark(stage)
  initial=s.initial
  stage='followups';s.begin_followups()
  while s.state==State.FOLLOWUPS:
   q=s.questions[len(s.responses)]
   # Only synthetic citizens; scripted choices are explicitly recorded as such.
   index=0 if cid!='uncertainty' and q['id']!='q3' else len(q['choices'])-1
   s.respond(q['choices'][index],'',c);mark('followup '+q['id'])
  if args.original_correction:
   stage='targeted original correction'
   s.correct('noise','I misspoke about the original sound. I accept the steady hum at60 meters and all stated original operating hours without acoustic reservations. My objection to the original cameras remains unchanged.','Correct my acoustic interpretation only; not a hypothetical change.',c)
   mark(stage)
   attempt['original_correction']=True
  stage='joint interpretation'
  if s.joint_required:
   choice='unsure' if cid=='uncertainty' else 'accept'
   clarification='' if choice=='unsure' else 'For this exact combined proposal, the quiet daytime flights and shielded viewing are acceptable to me. I continue to support the lifesaving medical public service. I have no remaining acoustic or personal viewing-privacy objection.'
   s.record_joint(choice,[],clarification,c);mark(stage)
  s.confirm_updated(True);stage='final scoring';s.score_final(c);mark(stage)
  assert s.initial==initial
  exported=s.export();assert json.loads(s.jsonl())==exported
  attempt.update(success=True,initial_scores={x['concern_id']:x['score'] for x in s.initial['assessment']['concerns'] if x['score'] is not None},
   final_original_scores={x['concern_id']:x['score'] for x in s.final['assessment']['concerns'] if x['score'] is not None},
   conditional_scores={x['concern_id']:x['score'] for x in s.conditional['assessment']['concerns'] if x['score'] is not None} if s.conditional else None,
   aggregates={'initial':s.initial['aggregate'],'final_original':s.final['aggregate'],'conditional':s.conditional['aggregate'] if s.conditional else None},
   question_ids=[r['question_id'] for r in s.responses],initial_preserved=True,score_free_initial_interpretation=True)
 except Exception as exc:
  mark(stage+' failure');attempt.update(failure_stage=stage,error=str(exc),error_type=type(exc).__name__)
 attempt['latency_seconds']=round(time.monotonic()-start,3)
 gpu=subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True)
 attempt['gpu_after_sample']=gpu.stdout.strip().splitlines()
 results.append(attempt)
 Path(args.output).parent.mkdir(parents=True,exist_ok=True)
 Path(args.output).write_text(json.dumps({'notice':'Engineering smoke test, not scientific validation; all attempted cases included.','attempts':results},indent=2)+'\n')
 print(json.dumps({k:v for k,v in attempt.items() if k not in {'stages','aggregates','initial_interpretation'}}),flush=True)
