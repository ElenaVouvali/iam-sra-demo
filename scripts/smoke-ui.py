"""Live Streamlit renderer; all outcome reporting includes failures, no test double."""
import json
import argparse
import os
import time
from streamlit.testing.v1 import AppTest
from iam_sra.settings import ROOT
parser=argparse.ArgumentParser();parser.add_argument('--output',default='.runtime/smoke-ui-confirmed.json');args=parser.parse_args()
os.environ['IAM_MOCK']='0'
start=time.monotonic();report={'mode':'LIVE','synthetic':True,'success':False,'stage':'startup'}
def click(app,label):
 next(b for b in app.button if b.label==label).click().run(timeout=400)
 if app.exception or app.error:raise RuntimeError('UI failed: '+str([e.value for e in app.error]))
try:
 app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=400).run()
 click(app,'Begin')
 app.text_area(key='citizen_answer').set_value(json.loads((ROOT/'eval/fn_reference.json').read_text())['citizen_text'])
 report['stage']='interpretation';click(app,'Interpret response')
 assert app.session_state.session.initial is None and not app.metric
 if any(b.label=='Finish discovery' for b in app.button):click(app,'Finish discovery')
 next(c for c in app.checkbox if c.label=='This interpretation reflects what I meant').check().run()
 click(app,'Confirm meaning');report['stage']='initial scoring';click(app,'Calculate initial provisional scores')
 original=app.session_state.session.initial
 app.checkbox(key='all_questions').check().run();click(app,'Continue to follow-ups')
 report['stage']='followups'
 for q,index in zip(app.session_state.session.questions,[0,2,2]):
  app.radio(key='choice_'+q['id']).set_value(q['choices'][index]);click(app,'Interpret and record follow-up')
 report['stage']='joint interpretation';app.radio(key='joint_choice').set_value('unsure');click(app,'Interpret combined-proposal response')
 next(c for c in app.checkbox if c.label=='The updated original and hypothetical interpretations reflect what I meant').check().run()
 click(app,'Confirm updated meaning');report['stage']='final scoring';click(app,'Calculate final provisional scores')
 s=app.session_state.session
 assert s.initial==original and len(app.get('download_button'))==2 and len(app.dataframe[0].value)==15
 report.update(success=True,initial_preserved=True,score_free_submission=True,download_count=2,comparison_count=15,
  initial=s.initial['aggregate'],final_original=s.final['aggregate'],conditional=s.conditional,question_ids=[r['question_id'] for r in s.responses])
except Exception as exc:report.update(error_type=type(exc).__name__,error=str(exc))
report['latency_seconds']=round(time.monotonic()-start,3)
(ROOT/args.output).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
if not report['success']:raise SystemExit(1)
