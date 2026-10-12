#!/usr/bin/env python3
"""Small live descriptive smoke suite; saves real outputs, never numerical targets."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import httpx
from iam_sra.session import Session
from iam_sra.readiness_client import ReadinessClient
from iam_sra.settings import BASE_URL

CASES = [
 ('informed_opposition','I oppose this corridor. Repeated flights could disturb people resting during the day. I would want measurements at different times and a comparison with road deliveries.'),
 ('uninformed_support','Yes, I accept everything without reservations. I do not know how the service works.'),
 ('uncertain','I cannot decide yet and do not know which evidence to ask for.'),
 ('transferable_participation','I attended a bus-route consultation last year and proposed a stop near the clinic. I do not know if my comment changed anything. I have not attended a drone consultation.'),
 ('opportunity_barrier','I would take part, but I do not know any way to contact the organisers. Evening meetings conflict with caring for my father.')]


def main():
    p=argparse.ArgumentParser();p.add_argument('--base-url',default=BASE_URL);p.add_argument('--output',default='.runtime/readiness-live-smoke.json');args=p.parse_args()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    report={'assessment_mode':'acceptance_and_readiness_evidence','live_model_used':False,'cases':[], 'semantic_validation':False}
    try:
        with httpx.Client(timeout=10,trust_env=False) as http:
            response=http.get(args.base_url.rstrip('/')+'/v1/models');response.raise_for_status()
    except httpx.HTTPError as exc:
        report.update(status='blocked',error=str(exc));output.write_text(json.dumps(report,indent=2));print(json.dumps(report));return 2
    for name,text in CASES:
        s=Session();client=ReadinessClient(base_url=args.base_url);started=time.monotonic()
        row={'id':name,'input':text}
        try:
            s.submit(text,client);s.confirm(True);s.finish()
            row.update(success=True,actual_output=s.export())
        except Exception as exc: row.update(success=False,error=str(exc))
        row['latency_seconds']=round(time.monotonic()-started,3)
        row['model_trace']=getattr(client,'last_trace',[])
        report['live_model_used']|=bool(row['model_trace'])
        report['cases'].append(row)
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({'id':name,'success':row['success'],'records':s.current_profile['records'],'error':row.get('error')},ensure_ascii=False),flush=True)
    report['status']='completed';output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return 0 if all(r['success'] for r in report['cases']) else 1

if __name__=='__main__':raise SystemExit(main())
