#!/usr/bin/env python3
"""Rehearse all FN flows against an existing model with isolated in-process APIs.

Only registered FN fictional answers and authored unknown replies are used.
Never connects to a participant API or changes a running service. Exports are
screened; rejected model output is not logged. Success is not semantic validation.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default=os.getenv('IAM_BASE_URL','http://127.0.0.1:18000'))
    parser.add_argument('--allow-live',action='store_true')
    parser.add_argument('--case',choices=['all','citizen_short','citizen_extended','organisational','technical'],default='all')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if not args.allow_live:parser.error('Explicit --allow-live is required for synthetic model calls.')
    origin=urlsplit(args.base_url)
    if origin.scheme not in {'http','https'} or not origin.hostname or origin.username or origin.password or origin.path not in {'','/'} or origin.query or origin.fragment:
        parser.error('Use the verified model origin, without credentials or a path.')
    root=Path(__file__).resolve().parents[1];output=Path(args.output).resolve()
    if not output.is_relative_to((root/'.runtime').resolve()):parser.error('Keep exports under ignored .runtime/.')
    if output.exists():parser.error('Use a new output directory; preserve previous runs.')
    os.environ['IAM_BASE_URL']=args.base_url.rstrip('/')
    os.environ['IAM_CHAT_SYNTHETIC_REHEARSAL']='1'
    sys.path.insert(0,str(root/'src'))
    import httpx
    try:
        with httpx.Client(trust_env=False,timeout=5) as http:
            r=http.get(args.base_url.rstrip('/')+'/v1/models');r.raise_for_status()
            assert any(m['id']=='Qwen/Qwen3-8B' for m in r.json().get('data',[]))
    except (httpx.HTTPError,ValueError,AssertionError):
        print(json.dumps({'live_inference':'unavailable','cases_executed':0,'services_changed':False}));return 2
    from iam_sra.api import create_app
    from iam_sra.privacy import screened_export
    fixture=json.loads((root/'eval/fn_golden_paths.json').read_text())['flows']
    output.mkdir(parents=True,exist_ok=False)
    app=create_app({'TESTING':True});manager=app.extensions['iam_sra'];reports=[]
    try:
        for key in fixture if args.case=='all' else [args.case]:
            browser=app.test_client();bootstrap=browser.get('/v1/capabilities')
            headers={'X-CSRF-Token':bootstrap.json['csrf_token']}
            r=browser.post('/v1/sessions',json={'mode':'chat','depth':'extended' if key=='citizen_extended' else 'short'},headers=headers)
            if r.status_code!=201:
                reports.append({'case':key,'status':'source_or_privacy_unavailable','http_status':r.status_code});continue
            view=r.json['session'];sid=view['id'];started=time.monotonic();steps=0
            answers={row['id']:row['answer'] for row in fixture[key]}
            def submit(text):
                nonlocal view,steps
                steps+=1
                r=browser.post(f'/v1/sessions/{sid}/actions',headers=headers,json={'action':'chat_message','data':{'text':text},'expected_version':view['version'],'request_id':str(uuid4())})
                if r.status_code!=202:raise RuntimeError('submission_rejected')
                jid=r.json['job_id'];deadline=time.monotonic()+600
                while time.monotonic()<deadline:
                    result=browser.get('/v1/jobs/'+jid)
                    if result.status_code!=200:raise RuntimeError('job_unavailable')
                    job=result.json['job']
                    if job['status'] in {'completed','failed','cancelled'}:
                        if job['status']!='completed':raise RuntimeError('job_failed')
                        view=browser.get(f'/v1/sessions/{sid}').json['session'];return
                    time.sleep(.05)
                raise RuntimeError('job_timeout')
            failure=None
            try:
                submit('A. Citizen' if key.startswith('citizen') else 'B. Organisation or institution' if key=='organisational' else 'C. Technology expert or researcher')
                while view['chat']['stage']=='conversation' and steps<100:
                    submit(answers.get(manager.records[sid].engine.chat.objective,'I do not know.'))
                if view['chat']['stage']=='summary':submit('no changes')
                if view['chat']['stage']=='review':submit('A' if view['chat']['suggestion'].get('level') else 'E')
                while view['chat']['stage']=='review_addition' and steps<105:submit('no changes')
            except RuntimeError as exc:failure=str(exc) # Fixed safe codes only.
            result=browser.get(f'/v1/sessions/{sid}/export')
            if result.status_code!=200:
                reports.append({'case':key,'status':'export_unavailable','http_status':result.status_code,'failure':failure});continue
            data=screened_export(result.json);c=data['conversation'];metrics=c['observable_metrics']
            (output/(key+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            turns=sum(m['role']=='respondent' for m in c['messages'])
            fallbacks=sum(m.get('act')=='authored_fallback' for m in c['messages'])
            reports.append({'case':key,'stage':c['stage'],'partial':c['completion']['partial'],
                'methodological_complete':all(s['status'] in {'explored','not_applicable'} for s in c['fn_interview']['stages']),
                'unresolved_gaps':c['fn_interview']['unresolved_gaps'],'level':(c.get('suggestion') or {}).get('level'),
                'score_status':(c.get('suggestion') or {}).get('status'),'validation':(c.get('participant_review') or {}).get('validation'),
                'respondent_turns':turns,'generation_calls':sum(m.get('generation_calls') or 0 for m in metrics),
                'fallback_count':fallbacks,'fallbacks_per_respondent_turn':round(fallbacks/max(1,turns),4),
                'generation_wall_seconds':round(sum(m['wall_seconds'] for m in metrics),3),
                'elapsed_seconds':round(time.monotonic()-started,3),'failures':c['failures'],'failure':failure})
    finally:manager.close()
    report=screened_export({'classification':'synthetic_FN_examples_not_Living_Lab_evidence','services_changed':False,'cases':reports})
    (output/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
    return 0 if len(reports)==(4 if args.case=='all' else 1) and all(r.get('stage')=='ended' and not r.get('failure') and not r.get('partial') for r in reports) else 1


if __name__=='__main__':raise SystemExit(main())
