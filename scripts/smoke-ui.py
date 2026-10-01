"""Live Streamlit renderer plus Qwen inference; intentionally no test double."""
import json
import os
from pathlib import Path
from streamlit.testing.v1 import AppTest
from iam_sra.settings import ROOT
os.environ['IAM_MOCK']='0'
app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=120).run()
app.button[1].click().run()
app.text_area[0].set_value(json.loads((ROOT/'eval/fn_reference.json').read_text())['citizen_text'])
app.button[1].click().run(timeout=120)
if app.exception or app.error: raise RuntimeError('Live initial assessment failed')
original=app.session_state.session.original.model_dump()
app.checkbox[0].check().run()
next(b for b in app.button if b.label=='Continue to hypothetical questions').click().run()
for index in [0,1,1]:
    app.radio[0].set_value(app.radio[0].options[index])
    next(b for b in app.button if b.label=='Record and continue').click().run()
    if app.exception or app.error:raise RuntimeError('Live UI transition failed')
s=app.session_state.session
report={'mode':'LIVE','completed':s.state.value=='final_report','question_ids':[r['question_id'] for r in s.responses],'original_preserved':s.original.model_dump()==original,'export_schema_available':bool(s.export()),'download_button_rendered':len(app.get('download_button'))==1,'conditional_outcomes':[r['outcome'] for r in s.responses],'versions':s.export()['versions']}
(ROOT/'.runtime/smoke-ui-live.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert report['completed'] and report['original_preserved'] and report['question_ids']==['q1','q2','q3'] and report['download_button_rendered']
