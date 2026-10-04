"""Bounded live engineering checks. Scripted confirmation is not scientific validation."""
import json,time,argparse,subprocess
from pathlib import Path
from iam_sra.session import Session,State
from iam_sra.conversation_client import ConversationClient
CASES={
 'support':'I accept the proposal as described. I support lifesaving hospital deliveries. The hum is tolerable and navigation cameras do not concern me.',
 'opposition':'I oppose the original route because the hum would disturb my balcony and cameras might view my windows. Shielding the cameras and reducing the sound would make those aspects acceptable, but I am unsure about the whole route.',
 'uncertainty':'I am unsure whether this proposal is acceptable. I need information about public funding and fair access for underserved neighborhoods.',
 'mixed':'I support lifesaving medical deliveries, but I reject cameras viewing my windows and noise disturbing my balcony. I could accept only with camera shielding and less sound.'}
p=argparse.ArgumentParser();p.add_argument('--ids',default=','.join(CASES));p.add_argument('--joint',choices=['accept','unsure'],default='unsure');p.add_argument('--output',default='.runtime/updates-smoke.json');args=p.parse_args();results=[]
for name in args.ids.split(','):
 s=Session();c=ConversationClient();start=time.monotonic();stage='interpretation';r={'case':name,'mode':'LIVE','synthetic':True,'success':False}
 try:
  s.begin();s.submit(CASES[name],c);assert s.initial is None
  s.finish_discovery('user_stop');stage='initial confirmation and scoring';s.continue_initial(True,c)
  initial=json.dumps(s.initial,sort_keys=True)
  while s.state==State.FOLLOWUPS:
   q=s.current_question;stage='follow-up '+q['id'];s.respond(q['choices'][0],'',c)
  if s.joint_required:
   stage='joint proposal interpretation'
   s.record_joint(args.joint,[],('I accept the combined proposal. Camera shielding makes private-space viewing acceptable, and the bundled altitude, sound and curfew changes make the noise acceptable. I still support lifesaving medical deliveries under these changes.' if args.joint=='accept' else 'I am not sure about accepting all these changes together.'),c)
  stage='updated confirmation and final scoring';s.continue_final(True,c)
  assert json.dumps(s.initial,sort_keys=True)==initial
  record=s.export();assert record['schema_version']=='5.1.0' and len(record['domain_assessments'])==15
  r.update(success=True,final_summary=record['final_summary'],aggregation=record['aggregation'],updates=record['updates'])
 except Exception as e:r.update(error=str(e),failure_stage=stage,error_type=type(e).__name__)
 r.update(latency_seconds=round(time.monotonic()-start,3),inference=s.inference,settings=c.last_settings,diagnostics=c.last_diagnostics)
 r['gpu_after_sample']=subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout.splitlines()
 results.append(r);path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'notice':'Every attempted live engineering case; not scientific validation. Joint uncertainty deliberately leaves the conditional assessment unavailable.','attempts':results},indent=2)+'\n')
 print(json.dumps({k:r[k] for k in ['case','success','latency_seconds','error','failure_stage'] if k in r}),flush=True)
