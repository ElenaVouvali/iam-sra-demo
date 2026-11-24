#!/usr/bin/env python3
"""Rehearse all FN flows against an existing model with isolated in-process APIs.

Only registered FN fictional answers and separately labelled synthetic variants are used.
Never connects to a participant API or changes a running service. Exports are
screened; rejected model output is not logged. Labelled opening checks do not
establish general interview or readiness-scoring accuracy.
"""
import argparse
import json
import os
import subprocess
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
    parser.add_argument('--opening-only',action='store_true',
        help='Check the citizen definition/uses against actual Qwen, without scoring or completing an interview.')
    parser.add_argument('--opening-variant',choices=['reference','paraphrase','uncertain','all'],default='reference')
    parser.add_argument('--model-variant',choices=['fp16','awq'],default=os.getenv('IAM_MODEL_VARIANT','fp16'))
    parser.add_argument('--backend',choices=['vllm','cpu'],default='vllm',
        help='CPU uses the existing pinned CPU benchmark; it does not verify vLLM/GPU performance.')
    parser.add_argument('--cpu-threads',type=int,default=4)
    parser.add_argument('--cpu-generation-seconds',type=int,default=300)
    parser.add_argument('--cpu-python',help='Existing Python with pinned torch/transformers; default .venv/bin/python')
    args=parser.parse_args()
    if not args.allow_live:parser.error('Explicit --allow-live is required for synthetic model calls.')
    if args.opening_only and args.case not in {'citizen_short','citizen_extended'}:
        parser.error('--opening-only requires --case citizen_short or citizen_extended')
    if args.opening_variant!='reference' and not args.opening_only:
        parser.error('--opening-variant requires --opening-only')
    if args.backend=='cpu' and args.model_variant!='fp16':
        parser.error('The CPU benchmark supports the preserved fp16 checkpoint only.')
    if args.backend=='cpu' and not args.opening_only:
        parser.error('CPU verification is bounded to --opening-only; full interviews use the existing vLLM endpoint')
    origin=urlsplit(args.base_url)
    if origin.scheme not in {'http','https'} or not origin.hostname or origin.username or origin.password or origin.path not in {'','/'} or origin.query or origin.fragment:
        parser.error('Use the verified model origin, without credentials or a path.')
    root=Path(__file__).resolve().parents[1];output=Path(args.output).resolve()
    if not output.is_relative_to((root/'.runtime').resolve()):parser.error('Keep exports under ignored .runtime/.')
    if output.exists():parser.error('Use a new output directory; preserve previous runs.')
    os.environ['IAM_MODEL_VARIANT']=args.model_variant
    os.environ['IAM_BASE_URL']=args.base_url.rstrip('/')
    os.environ['IAM_CHAT_SYNTHETIC_REHEARSAL']='1'
    sys.path.insert(0,str(root/'src'))
    import httpx
    from iam_sra.settings import MODEL
    if args.backend=='vllm':
        try:
            with httpx.Client(trust_env=False,timeout=5) as http:
                r=http.get(args.base_url.rstrip('/')+'/v1/models');r.raise_for_status()
                assert any(m['id']==MODEL for m in r.json().get('data',[]))
        except (httpx.HTTPError,ValueError,AssertionError):
            print(json.dumps({'live_inference':'unavailable','cases_executed':0,'services_changed':False}));return 2
    from iam_sra.api import create_app
    from iam_sra.chat_policy import CITIZEN_DURATION
    from iam_sra.privacy import screened_export
    fixture=json.loads((root/'eval/fn_golden_paths.json').read_text())['flows']
    variants=json.loads((root/'eval/fn_interpretation_cases.json').read_text())['variants']
    rehearsals=[(key,variant) for key in (fixture if args.case=='all' else [args.case])
                for variant in (['reference','paraphrase','uncertain'] if args.opening_variant=='all' else [args.opening_variant])]
    output.mkdir(parents=True,exist_ok=False)
    app=create_app({'TESTING':True});manager=app.extensions['iam_sra'];reports=[]
    worker=None
    if args.backend=='cpu':
        from iam_sra.chat_client import ChatClient
        from iam_sra.assessment import AssessmentError
        if not 1<=args.cpu_threads<=16 or not 10<=args.cpu_generation_seconds<=3600:
            parser.error('Use 1–16 CPU threads and a 10–3600 second generation limit')
        environment=os.environ.copy()
        environment.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',PYTHONPATH=str(root/'src'))
        worker=subprocess.Popen([args.cpu_python or str(root/'.venv/bin/python'),'-u',
            str(root/'scripts/fn-cpu-worker.py'),str(args.cpu_threads),str(args.cpu_generation_seconds)],
            cwd=root,env=environment,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        class CPUChatClient(ChatClient):
            def __init__(self):super().__init__(base_url='cpu-local')
            def _start(self):
                super()._start()
                self._deadline=min(time.monotonic()+2*args.cpu_generation_seconds+600,
                                   getattr(self,'external_deadline',float('inf')))
                self.last_settings['expected_deployment']={'device':'cpu','dtype':'float32',
                    'backend':'transformers_xgrammar_cpu','threads':args.cpu_threads}
            def _post_json(self,client,path,payload,stage,phase):
                # Main-process screening/validation is unchanged. The worker
                # only supplies the existing CPU benchmark's inference transport.
                self.last_metrics['tokenize_calls' if phase=='tokenization' else 'generation_calls']+=1
                try:
                    worker.stdin.write(json.dumps({'path':path,'payload':payload,'stage':stage,'phase':phase})+'\n')
                    worker.stdin.flush()
                    response=json.loads(worker.stdout.readline())
                    if 'error' in response:raise ValueError
                except (OSError,ValueError):
                    raise AssessmentError('The isolated CPU inference worker failed.',code='transport') from None
                self.last_diagnostics.extend(response['diagnostics'])
                return response['body']
        manager.adapter.clients_factory=lambda engine:{'chat':CPUChatClient(),'indicator':None,'chat_score':None}
    try:
        for key,variant_name in rehearsals:
            browser=app.test_client();bootstrap=browser.get('/v1/capabilities')
            headers={'X-CSRF-Token':bootstrap.json['csrf_token']}
            r=browser.post('/v1/sessions',json={'mode':'chat','depth':'extended' if key=='citizen_extended' else 'short'},headers=headers)
            if r.status_code!=201:
                reports.append({'case':key,'status':'source_or_privacy_unavailable','http_status':r.status_code});continue
            view=r.json['session'];sid=view['id'];started=time.monotonic();steps=0;checks=[]
            answers={row['id']:row['answer'] for row in fixture[key]}
            variant=variants.get(variant_name,{})
            answers.update(variant.get('answers',{}))
            def submit(text):
                nonlocal view,steps
                steps+=1
                r=browser.post(f'/v1/sessions/{sid}/actions',headers=headers,json={'action':'chat_message','data':{'text':text},'expected_version':view['version'],'request_id':str(uuid4())})
                if r.status_code!=202:raise RuntimeError('submission_rejected')
                jid=r.json['job_id'];deadline=time.monotonic()+int(os.getenv('IAM_SRA_JOB_TIMEOUT','600'))
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
                    current=manager.records[sid].engine.chat
                    goal=current.objective
                    if args.opening_only and goal=='healthcare_awareness':break
                    reference=next((row for row in fixture[key] if row['id']==goal),None)
                    canonical=(current.messages[-1]['text']==CITIZEN_DURATION if goal=='citizen_duration'
                        else bool(reference and reference['question'] in current.messages[-1]['text']))
                    failures=len(current.failures)
                    submit(('35 minutes' if key=='citizen_extended' else '20 minutes') if goal=='citizen_duration' else answers.get(goal,'I do not know.'))
                    current=manager.records[sid].engine.chat
                    coverage=current.fn.coverage.get(goal,{})
                    expected=variant.get('expected_statuses',{}).get(goal,
                        'unknown' if reference and reference['answer_kind']=='uncertain' else 'explored')
                    actual_kind=current.fn.facts.get(goal)
                    readings=variant.get('accepted_readings',{}).get(goal)
                    reading_ok=({'status':coverage.get('status'),'answer_kind':actual_kind} in readings
                        if readings else coverage.get('status')==expected)
                    topics_ok=goal not in variant.get('no_topics',[]) or not current.concerns
                    checks.append({'goal':goal,'canonical_question':canonical,
                        'coverage_status':coverage.get('status'),
                        'answer_kind':actual_kind,'expected_status':expected,
                        'accepted_readings':readings,'interpretation_matches':reading_ok and topics_ok,
                        'new_failures':len(current.failures)-failures})
                    if current.failed_turn_id:raise RuntimeError('interpretation_failed')
                    if not coverage and current.objective==goal:
                        raise RuntimeError('unexpected_clarification_of_reference_answer')
                if not args.opening_only:
                    if view['chat']['stage']=='summary':submit('no changes')
                    if view['chat']['stage']=='review':submit('A' if view['chat']['suggestion'].get('level') else 'E')
                    while view['chat']['stage']=='review_addition' and steps<105:submit('no changes')
            except RuntimeError as exc:failure=str(exc) # Fixed safe codes only.
            result=browser.get(f'/v1/sessions/{sid}/export')
            if result.status_code!=200:
                reports.append({'case':key,'status':'export_unavailable','http_status':result.status_code,'failure':failure});continue
            data=screened_export(result.json);c=data['conversation'];metrics=c['observable_metrics']
            (output/(key+('' if variant_name=='reference' else '-'+variant_name)+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            turns=sum(m['role']=='respondent' for m in c['messages'])
            fallbacks=sum(m.get('act') in {'authored_fallback','failure'} for m in c['messages'])
            required_opening={'area','citizen_duration','drone_recognition','drone_description','drone_uses'}
            if key=='citizen_extended':required_opening.add('drone_other_uses')
            output_tokens=sum(m.get('generated_tokens') or 0 for m in metrics)
            generation_seconds=sum(m.get('generation_http_seconds') or 0 for m in metrics)
            reports.append({'case':key,'stage':c['stage'],'partial':c['completion']['partial'],
                'scope':'citizen_opening_only' if args.opening_only else 'full_interview',
                'opening_variant':variant_name,
                'backend':args.backend,'model':c.get('model_provenance'),'reference_checks':checks,
                'generated_tokens':output_tokens or None,'generation_http_seconds':round(generation_seconds,3) or None,
                'output_tokens_per_http_second':round(output_tokens/generation_seconds,3) if generation_seconds and output_tokens else None,
                'model_wait_seconds':round(sum(m.get('model_wait_seconds') or 0 for m in metrics),3),
                'interpretation_checks_passed':bool(checks) and all(
                    row['canonical_question'] and row['interpretation_matches'] and not row['new_failures'] for row in checks),
                'opening_passed':bool(args.opening_only and not failure
                    and manager.records[sid].engine.chat.objective=='healthcare_awareness'
                    and required_opening <= {row['goal'] for row in checks}
                    and all(row['interpretation_matches'] and row['canonical_question'] and not row['new_failures'] for row in checks)),
                'methodological_complete':all(s['status'] in {'explored','not_applicable'} for s in c['fn_interview']['stages']),
                'unresolved_gaps':c['fn_interview']['unresolved_gaps'],'level':(c.get('suggestion') or {}).get('level'),
                'score_status':(c.get('suggestion') or {}).get('status'),'validation':(c.get('participant_review') or {}).get('validation'),
                'respondent_turns':turns,'generation_calls':sum(m.get('generation_calls') or 0 for m in metrics),
                'fallback_count':fallbacks,'fallbacks_per_respondent_turn':round(fallbacks/max(1,turns),4),
                'technical_failure_count':sum(m.get('act')=='failure' for m in c['messages']),
                'generation_wall_seconds':round(sum(m['wall_seconds'] for m in metrics),3),
                'elapsed_seconds':round(time.monotonic()-started,3),'failures':c['failures'],'failure':failure})
    finally:
        manager.close()
        if worker is not None:
            worker.terminate()
            try:worker.wait(timeout=10)
            except subprocess.TimeoutExpired:worker.kill();worker.wait()
    report=screened_export({'classification':'synthetic','fn_example_replay':True,
                           'living_lab_evidence':False,'services_changed':False,'cases':reports})
    (output/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
    return 0 if len(reports)==len(rehearsals) and all(
        r.get('opening_passed') if args.opening_only else
        r.get('stage')=='ended' and not r.get('failure') and not r.get('partial') and r.get('interpretation_checks_passed')
        for r in reports) else 1


if __name__=='__main__':raise SystemExit(main())
