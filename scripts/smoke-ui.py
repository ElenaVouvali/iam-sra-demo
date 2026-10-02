"""Live Streamlit renderer plus Qwen inference; intentionally no test double."""
import json
import os
from pathlib import Path
from streamlit.testing.v1 import AppTest
from iam_sra.settings import ROOT
os.environ['IAM_MOCK']='0'
app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=200).run()
app.button[1].click().run()
app.text_area[0].set_value(json.loads((ROOT/'eval/fn_reference.json').read_text())['citizen_text'])
app.button[1].click().run(timeout=200)
if app.exception or app.error: raise RuntimeError('Live initial assessment failed')
original=app.session_state.session.original.model_dump()
app.checkbox[0].check().run()
app.checkbox(key="include_reference_questions").check().run()
next(b for b in app.button if b.label=='Continue to hypothetical questions').click().run()
for index in [0,2,2]:
    app.radio[0].set_value(app.radio[0].options[index])
    next(b for b in app.button if b.label=='Record and continue').click().run()
    if app.exception or app.error:raise RuntimeError('Live UI transition failed')
s=app.session_state.session
report={'mode':'LIVE','completed':s.state.value=='final_report','question_ids':[r['question_id'] for r in s.responses],'original_preserved':s.original.model_dump()==original,'export_schema_available':bool(s.export()),'download_button_rendered':len(app.get('download_button'))==1,'conditional_outcomes':[r['outcome'] for r in s.responses],'matched_rules':[m['rule_id'] for m in s.export()['conclusions']['matched_rules']],'numerical_update':s.export()['conclusions']['numerical_update'],'concern_validation':s.export()['conclusions']['concern_validation'],'residential_routing':s.export()['conclusions']['residential_routing'],'versions':s.export()['versions'],'original_scores':{c.concern_id:c.score for c in s.original.concerns if c.status=='assessed'},'aggregate':s.export()['original_aggregate'],'settings':s.export()['original_inference']['settings']}
(ROOT/'.runtime/smoke-ui-recalibrated.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert report['completed'] and report['original_preserved'] and report['question_ids']==['q1','q2','q3'] and report['download_button_rendered']

assert report["matched_rules"]==["remaining_objection"] and report["numerical_update"] is None

statuses={r['concern_id']:r['status'] for r in report['concern_validation']}
privacy=next((r for r in report['concern_validation'] if r['concern_id']=='perceived_safety_privacy'),None)
if privacy:
    assert next(t for t in privacy['tests'] if t['question_id']=='q1')['status']=='resolved_under_assumptions'
    assert privacy['status']==('partially_tested' if privacy['untested_facets'] else 'resolved_under_assumptions')
if 'noise' in statuses: assert statuses['noise']=='partially_tested'
if 'welfare_equity' in statuses: assert statuses['welfare_equity']=='unresolved'
assert report['residential_routing']['status']=='remaining'
