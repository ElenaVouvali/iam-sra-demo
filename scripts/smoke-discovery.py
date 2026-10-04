"""Bounded live original-context discovery; every attempted case is reported.

Synthetic engineering checks only. No restart, fallback, or scoring rule change.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path
from iam_sra.session import Session
from iam_sra.conversation_client import ConversationClient
from iam_sra.settings import config

CASES=[
 ('acceptance','I accept this proposal.','noise','The original hum is tolerable to me; I have no acoustic reservations.'),
 ('rejection','I reject this proposal.','perceived_safety_privacy','I reject navigation cameras viewing my windows. I would accept this aspect only if cameras could never view my property.'),
 ('uncertainty','I am not sure about this proposal.','cost_roi_business','I need to know who pays for the service and whether public funding is required; I have not decided.'),
 ('mixed','I accept some parts, but other parts would need changes.','welfare_equity','I support lifesaving medical deliveries, but I am unsure whether the service would reach underserved neighborhoods fairly.')]
p=argparse.ArgumentParser();p.add_argument('--output',default='.runtime/discovery-smoke.json');p.add_argument('--ids',default=','.join(x[0] for x in CASES));args=p.parse_args()
results=[]
for name,text,topic,clarification in CASES:
 if name not in args.ids.split(','):continue
 s=Session();client=ConversationClient();start=time.monotonic();stage='initial interpretation'
 result={'case':name,'synthetic':True,'mode':'LIVE','success':False,'stages':[],'model':config('model'),'scoring_policy_changed':False}
 def record(label):result['stages'].append({'stage':label,'diagnostics':client.last_diagnostics,'settings':client.last_settings})
 try:
  s.begin();s.submit(text,client);record(stage)
  result['initial_meaning']=s.draft.model_dump()
  assert s.initial is None and not any(x['stage']=='scoring' for x in s.inference)
  questions=[]
  while not s.discovery_finished:
   q=s.discovery_question
   if q is None:s.finish_discovery('sufficient');break
   questions.append(q);stage='discovery '+q['id']+' '+q['kind']
   if q['kind']=='stance':s.respond_discovery(['uncertain'],'',client)
   elif q['kind']=='reasons':s.respond_discovery([topic],'',client)
   elif q['kind']=='topic' and q['concern_id']==topic:s.respond_discovery([],clarification,client)
   elif q['kind']=='topic':s.respond_discovery([],'',client,skip=True)
   elif q['kind']=='changes':s.respond_discovery(['unsure'],'',client)
   elif q['kind']=='blocker':s.respond_discovery(['yes' if name=='rejection' else 'unsure'],'',client)
   else:s.respond_discovery([],'',client,skip=True)
   record(stage)
  result['consolidated_meaning']=s.draft.model_dump();result['discovery']={'questions':s.discovery_questions,'responses':s.discovery_responses,'blockers':s.blockers,'unmapped_issues':s.unmapped_issues}
  # Scripted confirmation tests plumbing, not citizen agreement or semantic correctness.
  stage='initial confirmation';s.confirm(True);assert s.initial is None
  stage='initial scoring';s.score_initial(client);record(stage)
  initial=s.initial;stage='FN question selection';s.begin_followups(False)
  # Preserve FN selection in results; this bounded check does not invent hypothetical answers.
  result['selected_fn_question_ids']=[q['id'] for q in s.questions]
  result.update(success=True,initial_scores={c['concern_id']:c['score'] for c in initial['assessment']['concerns'] if c['score'] is not None},aggregate=initial['aggregate'],score_free_until_confirmation=True)
 except Exception as exc:
  record(stage+' failure');result.update(error=str(exc),error_type=type(exc).__name__,failure_stage=stage,discovery={'questions':s.discovery_questions,'responses':s.discovery_responses,'blockers':s.blockers},consolidated_meaning=s.draft.model_dump() if s.draft else None)
 if s.draft:
  mapped={c.concern_id:c for c in s.draft.concerns}
  expected_stance={'acceptance':'supported','rejection':'opposed','uncertainty':'uncertain','mixed':'mixed'}[name]
  checks={'overall_stance':s.draft.current_route_stance.interpretation==expected_stance,'expected_topic':topic in mapped,
   'positive_noise':name!='acceptance' or (topic in mapped and mapped[topic].position=='supported'),
   'privacy_boundary':name!='rejection' or (topic in mapped and mapped[topic].position=='opposed' and mapped[topic].conditional_willingness=='willing'),
   'uncertain_finance':name!='uncertainty' or (topic in mapped and mapped[topic].position=='uncertain'),
   'medical_vs_equity':name!='mixed' or (topic in mapped and set(mapped[topic].facets)=={'medical_public_benefit','distributive_equity'}),
   'no_invented_awareness':s.draft.awareness_understanding.interpretation!='demonstrated'}
  result['qualitative_checks']=checks;result['all_qualitative_checks_passed']=all(checks.values())
 result['latency_seconds']=round(time.monotonic()-start,3)
 sample=subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True)
 result['gpu_after_sample']=sample.stdout.strip().splitlines()
 result['session_inference']=s.inference
 results.append(result)
 path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'notice':'All attempted synthetic engineering cases, not scientific validation. Topic selection and blocker choices do not establish numeric severity.','attempts':results},indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['case','success','latency_seconds','error','failure_stage','initial_scores'] if k in result}),flush=True)
