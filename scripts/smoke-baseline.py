#!/usr/bin/env python3
"""Synthetic Phase-1 smoke runner; actual live output or labelled empty mock flow."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from iam_sra.baseline_session import BaselineSession
from iam_sra.baseline_client import BaselineClient, MockBaselineClient
from iam_sra.privacy import require_safe_data, screened_export, safe_message

CASES=[
 {'id':'unaware','perspective':'personal','stakeholder':'citizen','city':'withheld','familiarity':'no',
  'concept':'I do not know what a drone is.', 'delivery':'I have not heard of delivery drones.',
  'understanding':'I have not heard about these uses before. I do not know their effects.',
  'experience':'I have no experience with these uses.',
  'needs':'I am unsure what to ask for.', 'opportunity':'I have not been invited to a discussion.'},
 {'id':'reasoned_opposition','perspective':'personal','stakeholder':'citizen','city':'coimbra','familiarity':'little',
  'concept':'An aircraft without a pilot on board.', 'delivery':'I have heard of carrying medical materials.',
  'understanding':'I am opposed to drones near homes because repeated sound could interrupt sleep. I want sound measurements, not assurances.',
  'experience':'Last year I attended a public bus-route consultation and suggested a stop near the clinic. I do not know if my contribution changed a decision. I have not attended a drone consultation.',
  'needs':'I want evidence about sound at homes.', 'opportunity':'I would take part, but evening meetings conflict with caring responsibilities.'},
 {'id':'authority','perspective':'organisation','stakeholder':'authority','city':'milan','familiarity':'little',
  'concept':'An aircraft controlled without a pilot on board.', 'delivery':'I have heard of parcel delivery.',
  'understanding':'I personally know little about the operational details. My role concerns planning, not certifying aircraft.',
  'experience':'Our planning team attended a public seminar about drones. I listened but did not make a contribution.',
  'needs':'I would like balanced information to help our team discuss possible effects.', 'opportunity':'I do not know where to contribute comments.'}]
PROBES={'scope':'The bus consultation and drone activities are different experiences.',
 'reasoning':'Repeated sound could interrupt rest depending on when people sleep. I do not know measured levels.',
 'contribution':'I only listened and made no contribution.',
 'domain':'The experience was about another transport service, not drones.',
 'influence':'I do not know whether anything changed.'}


def run(case,client):
    s=BaselineSession();s.set_context(case['perspective'],case['stakeholder'],case['city'])
    while s.state=='interview':
        q=s.current_question;s.answer(case.get(q['id'],PROBES.get(q['id'],'')),client)
        if s.state=='review':s.confirm(True,actor='automation')
    s.complete(actor='automation')
    before=s.export()
    # Exercise a real correction through the same controller and frozen prompts.
    target=next((e for e in reversed(s.events) if e['control']=='answer' and e['question']['id']!='familiarity'),None)
    if target:
        s.edit_answer(target['id']);s.answer(target['text']+' I am reporting my own view or experience, not independent verification.',client)
        if s.state=='review':s.confirm(True,actor='automation')
        if s.state=='interview':s.finish()
        s.complete(actor='automation')
    s.handoff();return {'case_id':case['id'],'before_correction':before,'actual_output':s.export(),
        'human_review_status':'pending','automation':'Scripted confirmations; not citizen validation or proof of semantic accuracy.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--mock',action='store_true');p.add_argument('--output',default='.runtime/baseline-smoke.json');a=p.parse_args()
    client=MockBaselineClient() if a.mock else BaselineClient();rows=[]
    for case in CASES:
        start=time.monotonic()
        try:row=run(case,client);row['status']='completed'
        except Exception as exc:row={'case_id':case['id'],'status':'failed','error_code':getattr(exc,'code','validation'),'message':safe_message(exc)}
        row['latency_seconds']=round(time.monotonic()-start,3);rows.append(row)
    data={'runner':'baseline-smoke-2.0.0','mock':a.mock,'semantic_pass':None,'cases':rows}
    screened_export(data);path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'mock':a.mock,'cases':[{'id':r['case_id'],'status':r['status'],'latency_seconds':r['latency_seconds'],'error_code':r.get('error_code')} for r in rows]}))
    return 0 if all(r['status']=='completed' for r in rows) else 2
if __name__=='__main__':raise SystemExit(main())
