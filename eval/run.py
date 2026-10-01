"""Synthetic engineering evaluation, never scientific validation."""
import argparse
import json
import time
from pathlib import Path
from iam_sra.settings import ROOT, config
from iam_sra.llm_client import LLMClient
from iam_sra.mock import assess as mock_assess
from iam_sra.scoring import aggregate
from iam_sra.assessment import AssessmentError
p=argparse.ArgumentParser();p.add_argument("--mock",action="store_true");p.add_argument("--repeats",type=int,default=3);p.add_argument("--output",default=".runtime/evaluation.json");a=p.parse_args()
if not 1<=a.repeats<=5:p.error("repeats must be 1–5")
cases=json.loads((ROOT/"eval/cases.json").read_text())
ref=json.loads((ROOT/"eval/fn_reference.json").read_text())
cases.append({"id":"fn_reference","text":ref['citizen_text'],"expected_stance":"opposed","expected_concerns":["noise","perceived_safety_privacy"]})
client=mock_assess if a.mock else LLMClient()
rows=[]
for case in cases:
    for repeat in range(a.repeats):
        start=time.monotonic()
        row={"id":case['id'],"repeat":repeat,"mode":"MOCK" if a.mock else "LIVE","schema_and_evidence_pass":False}
        try:
            result=client(case['text'])
            scores={c.concern_id:c.score for c in result.concerns if c.status=='assessed'}
            actual=set(scores);expected=set(case['expected_concerns'])
            row.update(schema_and_evidence_pass=True,scores=scores,stance=result.current_route_stance.interpretation,stance_agreement=result.current_route_stance.interpretation==case['expected_stance'] if case['expected_stance'] else None,concern_precision=len(actual&expected)/len(actual) if actual else None,concern_recall=len(actual&expected)/len(expected) if expected else None,unexpected_concerns=sorted(actual-expected),aggregate=aggregate(result))
            if case['id']=='fn_reference':row['reference_score_deltas']={k:scores[k]-v for k,v in ref['scores'].items() if k in scores}
        except AssessmentError as exc:row['error']=str(exc);row['failure_category']=exc.code
        if not a.mock:
            row['attempts']=getattr(client,'last_diagnostics',[])
            row['schema_pass']=row['attempts'][-1]['schema_pass'] if row['attempts'] else False
            row['evidence_pass']=row['attempts'][-1]['evidence_pass'] if row['attempts'] else None
            row['eligibility_pass']=row['attempts'][-1].get('eligibility_pass') if row['attempts'] else None
        row['latency_seconds']=round(time.monotonic()-start,3);rows.append(row)
        print(case['id'],repeat,row['schema_and_evidence_pass'],row['latency_seconds'],flush=True)
variation={c['id']:{i:sorted(set(r['scores'].get(i) for r in rows if r['id']==c['id'] and 'scores' in r and i in r['scores'])) for i in set(k for r in rows if r['id']==c['id'] for k in r.get('scores',{}))} for c in cases}
output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps({"notice":"Synthetic engineering evaluation; not scientific validation. No raw citizen text logged.","mode":"MOCK" if a.mock else "LIVE","prompt_version":config("prompts")["version"],"model":config("model"),"results":rows,"score_variation":variation},indent=2)+'\n')
