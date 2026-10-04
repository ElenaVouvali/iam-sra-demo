"""One bounded live no-reservations UI path; no mock or service restart."""
import json
import os
import time
from streamlit.testing.v1 import AppTest
from iam_sra.settings import ROOT
os.environ['IAM_MOCK']='0'
start=time.monotonic();result={'mode':'LIVE','synthetic':True,'success':False,'stage':'startup'}
def click(app,label):
 next(b for b in app.button if b.label==label).click().run(timeout=400)
 if app.exception or app.error:raise RuntimeError('Controlled UI failure: '+str([e.value for e in app.error]))
try:
 app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=400).run()
 click(app,'Begin');app.text_area(key='citizen_answer').set_value('I accept the proposal as described, with no reservations or conditions.')
 result['stage']='interpretation';click(app,'Interpret response')
 assert app.session_state.session.initial is None and not app.metric
 if any(b.label=='Finish discovery' for b in app.button):click(app,'Finish discovery')
 app.checkbox(key='confirm_'+str(app.session_state.session.version)).check().run()
 click(app,'Confirm meaning');result['stage']='initial scoring';click(app,'Calculate initial provisional scores')
 initial=app.session_state.session.initial
 click(app,'Continue to follow-ups')
 if app.session_state.session.questions:raise RuntimeError('Unexpected FN gate for bare acceptance; inspect model mapping.')
 app.checkbox(key='updated_confirm_'+str(app.session_state.session.version)).check().run()
 click(app,'Confirm updated meaning');result['stage']='final scoring';click(app,'Calculate final provisional scores')
 s=app.session_state.session
 assert s.initial==initial and len(app.dataframe[0].value)==15 and len(app.get('download_button'))==2
 assert json.loads(s.jsonl())==s.export()
 result.update(success=True,initial_preserved=True,comparison_rows=15,exports=2,session=s.export())
except Exception as exc:
 result.update(error=str(exc),error_type=type(exc).__name__)
 if 'app' in globals() and 'session' in app.session_state:result['inference']=app.session_state.session.inference
result['latency_seconds']=round(time.monotonic()-start,3)
(ROOT/'.runtime/discovery-ui-live.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in {'session','inference'}}))
