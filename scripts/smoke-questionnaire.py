#!/usr/bin/env python3
"""Small real-controller/live-model smoke, explicitly synthetic and never stakeholder data."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from iam_sra.conversation_session import ConversationSession
from iam_sra.indicator_client import IndicatorClient, POLICY
from iam_sra.privacy import screened_export, safe_message
from iam_sra.settings import ROOT


def main():
    wall_started=time.monotonic()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scenario',help='Optional existing source case ID; use the isolated review corpus for expansion cases.')
    p.add_argument('--case',choices=['uncertain','disagreement','organisational','technical'])
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    cases=json.loads((ROOT/'eval/indicator_questionnaire_cases_v02.json').read_text())['cases']
    definitions=[('uncertain','no-information'),('disagreement','noise-would'),
                 ('organisational','organisation-plan'),('technical','technical-lab')]
    records=[]
    for name,key in definitions:
        if args.case and name!=args.case:continue
        case=next(c for c in cases if c['id']==key);s=ConversationSession();client=IndicatorClient(base_url=args.base_url)
        started=time.monotonic();record={'scenario_id':args.scenario,'case':name,'synthetic':True,'status':'failed','policy':POLICY}
        try:
            profile=case['profile'];s.start_assessment(profile,'Synthetic proposed healthcare delivery service',indicator_ids=[case['indicator_id']])
            if profile!='citizen':
                s.indicator_scope(organisation_or_unit='Municipal planning unit' if profile=='organisational' else '',
                    responsibilities='Planning and coordination' if profile=='organisational' else '',
                    technical_object='Synthetic system prototype' if profile=='technical' else '',
                    object_version='A' if profile=='technical' else '',intended_environment='Laboratory; intended local delivery environment' if profile=='technical' else '',component_scope='system' if profile=='technical' else 'unsure')
            if args.scenario:s.indicator_case(args.scenario)
            s.indicator_answer(case['answer'],client)
            if name=='disagreement':
                s.indicator_correct('Please retain the proposed safeguard and its reason. This is a proposal, not a report of past participation.',client)
                if s.indicators.current['pending'].get('correction_offer'):
                    record['correction_offered_answer_edit']=True  # Original facts remain the only evidence.
            s.indicator_confirm();s.indicator_finish();s.indicator_suggest(client)
            row=s.indicators.current;record['tool_statement_id']=row['tool']['selected_statement_id'];record['tool_explanation']=row['tool']['explanation']
            if name=='uncertain':
                record['expected_abstention_observed']=row['tool']['statement'] is None
                s.indicator_review('unsure',s.indicators.revision)
            else:
                alternate=next(a for a in s.indicators.scale(case['indicator_id']) if a['id']!=row['tool']['selected_statement_id'])
                s.indicator_review('select',s.indicators.revision,alternate['id'],'Synthetic participant selection; a different description fits my situation.')
                record['separate_judgments_preserved']=row['participant']['statement']['id']!=row['tool']['selected_statement_id']
            s.complete_assessment();record['status']='completed'
        except Exception as exc:record['failure']={'code':getattr(exc,'code','runtime'),'message':safe_message(exc)}
        data=s.browser_export();data.update(synthetic=True,data_classification='SYNTHETIC_TEST_ONLY',run_status=record['status'])
        clean=screened_export(data)
        (args.output/(name+'.json')).write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n')
        (args.output/(name+'.jsonl')).write_text(json.dumps(clean,ensure_ascii=False)+'\n')
        record.update(seconds=round(time.monotonic()-started,3),metrics=getattr(client,'session_metrics',{}))
        records.append(record)
        (args.output/(name+'-run.json')).write_text(json.dumps(screened_export(record),ensure_ascii=False,indent=2)+'\n')
        print(name,record['status'],record.get('tool_statement_id'),record.get('failure',{}),flush=True)
    report={'wall_seconds':round(time.monotonic()-wall_started,3),'model_alias':'Qwen/Qwen3-8B','implementation_sha256':{p:sha256((ROOT/p).read_bytes()).hexdigest() for p in ('src/iam_sra/indicator_client.py','src/iam_sra/indicator_assessment.py','src/iam_sra/questionnaire.py')},'synthetic_only':True,'policy':POLICY,'runs':records,'bank':s.indicators.identity(),'questionnaire':s.indicators.questionnaire_identity(),
            'limitation':'Shared-model exploratory checks, not empirical or methodological validation.'}
    (args.output/'summary.json').write_text(json.dumps(screened_export(report),ensure_ascii=False,indent=2)+'\n')
    return 0 if all(r['status']=='completed' for r in records) else 1

if __name__=='__main__':raise SystemExit(main())
