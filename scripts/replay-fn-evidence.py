"""One bounded live FN replay; scripted choices/confirmations are engineering checks only."""
import json,time,argparse
from pathlib import Path
from iam_sra.session import Session,State
from iam_sra.conversation_client import ConversationClient
from iam_sra.updates import facet_state
p=argparse.ArgumentParser();p.add_argument('--output',default='.runtime/fn-evidence-replay.json');args=p.parse_args()
s=Session();c=ConversationClient();start=time.monotonic();stage='initial interpretation';record={'live':True,'synthetic_scripted_confirmation':True,'success':False,'not_scientific_validation':True}
try:
 text=json.loads(Path('eval/fn_reference.json').read_text())['citizen_text']
 s.begin();s.submit(text,c);record['initial_mapping']=s.draft.model_dump();record['initial_facets']={k:f.model_dump() for k,f in s.original_facets.items()}
 assert s.initial is None
 s.finish_discovery();stage='initial confirmed scoring';s.continue_initial(True,c);record['initial_snapshot']=s.initial
 while s.state==State.FOLLOWUPS:
  q=s.current_question;stage='follow-up '+q['id'];s.respond(q['choices'][1] if q['id']=='q3' else q['choices'][0],'',c)
 if s.joint_required:
  stage='explicit joint acceptance'
  unchanged=[key for key,f in s.original_facets.items() if f.facet=='medical_public_benefit' and f.position=='supported' and facet_state(s,f.concern_id,f.facet)[0]=='untested']
  s.record_joint('accept',[],'',c,{key:{'response':'yes','clarification':''} for key in unchanged})
 stage='final meaning confirmation and scoring';s.continue_final(True,c)
 record.update(success=True,session=s.export())
except Exception as exc:record.update(error_type=type(exc).__name__,error=str(exc),failure_stage=stage,meanings=s.draft.model_dump() if s.draft else None)
record.update(latency_seconds=round(time.monotonic()-start,3),inference=s.inference,last_diagnostics=c.last_diagnostics,last_raw_trace=c.last_trace,last_settings=c.last_settings)
path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ['success','latency_seconds','failure_stage','error'] if k in record}),flush=True)
