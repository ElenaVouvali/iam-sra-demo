#!/usr/bin/env python3
"""Run fictional citizen stress personas through the existing IAM chat/API."""
import argparse, importlib.util, json, os, statistics, sys, time
from pathlib import Path
from uuid import uuid4


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',default='http://127.0.0.1:18005')
    p.add_argument('--case',default='all')
    p.add_argument('--respondent',choices=['scripted','agent'],default='scripted')
    p.add_argument('--adaptive',type=int,choices=[0,3],required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--case-timeout-seconds',type=int,default=3600)
    p.add_argument('--max-turns',type=int,default=120)
    p.add_argument('--thinking',action='store_true')
    args=p.parse_args(argv)
    root=Path(__file__).resolve().parents[1]
    out=Path(args.output).resolve()
    if not out.is_relative_to((root/'.runtime').resolve()) or out.exists():p.error('Use a new output path under ignored .runtime/.')
    bank=json.loads((root/'eval/fn_citizen_stress_v1.json').read_text())
    cases={row['id']:row for row in bank['scenarios']}
    selected=list(cases) if args.case=='all' else [args.case]
    if not set(selected)<=set(cases):p.error('Unknown stress scenario ID.')
    os.environ.update(IAM_BASE_URL=args.base_url.rstrip('/'),IAM_MODEL_THINKING='1' if args.thinking else '0',
        IAM_CHAT_SYNTHETIC_REHEARSAL='1',IAM_CHAT_ADAPTIVE_MODE='1' if args.adaptive else '0',
        IAM_CHAT_MAX_ADAPTIVE_QUESTIONS=str(args.adaptive))
    sys.path.insert(0,str(root/'src'))
    spec=importlib.util.spec_from_file_location('smoke_fn_interview',root/'scripts/smoke-fn-interview.py')
    harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(harness)
    harness.require_unmanaged_endpoint(root)
    import httpx
    from iam_sra.settings import MODEL
    with httpx.Client(trust_env=False,timeout=5) as http:
        r=http.get(args.base_url.rstrip('/')+'/v1/models');r.raise_for_status()
        if not any(m['id']==MODEL for m in r.json().get('data',[])):p.error('Expected Qwen model is not loaded.')
    from iam_sra.api import create_app
    from iam_sra.privacy import screened_export
    from iam_sra.synthetic_respondent import LLMRespondent
    from iam_sra.chat_session import direct_intent
    out.mkdir(parents=True)
    app=create_app({'TESTING':True});manager=app.extensions['iam_sra'];reports=[]
    try:
        for case in selected:
            scenario=cases[case];persona=scenario['persona'];answers=scenario['answers']
            client=app.test_client();boot=client.get('/v1/capabilities')
            csrf={'X-CSRF-Token':boot.json['csrf_token']}
            depth=scenario['depth']
            created=client.post('/v1/sessions',json={'mode':'chat','depth':depth},headers=csrf)
            if created.status_code!=201:raise RuntimeError(f'{case}: session creation failed ({created.status_code})')
            view=created.json['session'];sid=view['id'];state=manager.records[sid].engine.chat
            responder=LLMRespondent(persona,base_url=args.base_url) if args.respondent=='agent' else None
            start=time.monotonic();deadline=start+args.case_timeout_seconds;steps=0;asked={};failure=None
            correction='';correction_triggered=False;simplification_triggered=False;respondent_latencies=[]
            def submit(text):
                nonlocal view,steps
                steps+=1
                if steps>args.max_turns or time.monotonic()>deadline:raise RuntimeError('case_limit')
                r=client.post(f'/v1/sessions/{sid}/actions',headers=csrf,json={'action':'chat_message','data':{'text':text},'expected_version':view['version'],'request_id':str(uuid4())})
                if r.status_code!=202:raise RuntimeError(f'action_rejected_{r.status_code}')
                jid=r.json['job_id']
                while time.monotonic()<deadline:
                    j=client.get('/v1/jobs/'+jid)
                    if j.status_code!=200:raise RuntimeError('job_missing')
                    if j.json['job']['status'] in {'failed','cancelled'}:raise RuntimeError('job_failed')
                    if j.json['job']['status']=='completed':
                        current=client.get(f'/v1/sessions/{sid}')
                        if current.status_code!=200:raise RuntimeError('session_view_withheld')
                        view=current.json['session'];return
                    time.sleep(.05)
                raise RuntimeError('job_timeout')
            try:
                submit('A. Citizen')
                while view['chat']['stage']=='conversation':
                    state=manager.records[sid].engine.chat;goal=state.objective
                    if correction=='go_back':
                        correction='replace';submit('back');continue
                    if correction=='replace':
                        correction='';submit('Correction: the newsletter described a proposed route, not a confirmed test.');continue
                    if goal=='area':answer=persona['city']
                    elif goal=='citizen_duration':answer='B' if depth=='extended' else 'A'
                    elif responder:
                        question=next(m for m in reversed(view['chat']['messages']) if m['role']=='assistant')
                        history=[{'role':m['role'],'text':m['text']} for m in view['chat']['messages'][-6:]]
                        respondent_started=time.monotonic()
                        result=responder.respond({'question_text':question['text'],'response_options':view['chat'].get('response_options',[])},history)
                        respondent_latencies.append(round(time.monotonic()-respondent_started,3))
                        answer=result['text'] or {'skip':'skip this question','unsure':'I do not know.','decline':'prefer not to answer'}.get(result['control'],'')
                    elif goal=='open_more' and case=='S6_challenging_correction_refusal_extended':
                        answer='What is the capital of Norway?'
                    elif goal=='different_impacts' and case=='S6_challenging_correction_refusal_extended' and not simplification_triggered:
                        answer='Could you put that more simply?';simplification_triggered=True
                    elif goal=='different_impacts' and case=='S6_challenging_correction_refusal_extended':
                        answer='People near the route may hear more noise than people farther away.'
                    elif goal=='local_awareness' and case=='S6_challenging_correction_refusal_extended':
                        answer='I may have heard about a local test, but I am not sure.'
                    elif goal=='local_basis' and case=='S6_challenging_correction_refusal_extended' and not correction_triggered:
                        answer='The newsletter made me think a local test had happened.'
                    else:
                        queue=answers.get(goal,'I do not know enough to answer that.')
                        if isinstance(queue,list):
                            n=asked.get(goal,0);answer=queue[min(n,len(queue)-1)];asked[goal]=n+1
                        else:answer=queue
                    print(json.dumps({'case':case,'step':steps+1,'goal':goal,
                        'elapsed_seconds':round(time.monotonic()-start,1),'event':'answer_submitted'},ensure_ascii=False),
                        file=sys.stderr,flush=True)
                    if goal=='local_basis' and case=='S6_challenging_correction_refusal_extended' and not correction_triggered:
                        correction='go_back';correction_triggered=True
                    submit(answer)
                if view['chat']['stage']=='summary':submit('no changes')
                if view['chat']['stage']=='review':
                    submit('E' if view['chat'].get('suggestion',{}).get('level') else 'I am not sure')
                while view['chat']['stage']=='review_addition':submit('no changes')
            except Exception as exc:
                failure=str(exc)[:100]
            response=client.get(f'/v1/sessions/{sid}/export')
            if response.status_code!=200:reports.append({'case':case,'failure':failure or 'json_export_unavailable'});continue
            try:data=screened_export(response.json)
            except ValueError:reports.append({'case':case,'failure':'json_export_withheld'});continue
            name=out/case
            name.with_suffix('.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            name.with_suffix('.json').chmod(0o600)
            conversation=data['conversation']
            (out/(case+'.md')).write_text(harness.render_transcript(conversation))
            (out/(case+'.md')).chmod(0o600)
            jsonl=client.get(f'/v1/sessions/{sid}/export?format=jsonl')
            if jsonl.status_code==200:
                (out/(case+'.jsonl')).write_text(jsonl.get_data(as_text=True));(out/(case+'.jsonl')).chmod(0o600)
            trace_ok=False
            try:trace=manager.developer_trace(sid)
            except ValueError:trace=None
            if trace:
                (out/(case+'-trace.json')).write_text(json.dumps(trace,ensure_ascii=False,indent=2)+'\n')
                (out/(case+'-trace.json')).chmod(0o600);trace_ok=True
            c=conversation;metrics=c['observable_metrics'];turns=[m for m in c['messages'] if m['role']=='respondent']
            generation_latencies=[m.get('generation_http_seconds') for m in metrics if m.get('generation_http_seconds')]
            sorted_latencies=sorted(generation_latencies)
            p95=(sorted_latencies[max(0,int(.95*len(sorted_latencies)+.999)-1)] if sorted_latencies else None)
            failures=c.get('failures',[])
            reports.append({'case':case,'persona_id':case,'depth':depth,'respondent':args.respondent,'adaptive_questions':args.adaptive,
                'stage':c['stage'],'partial':c['completion']['partial'],'failure':failure,'fallback_count':sum(m.get('act') in {'failure','authored_fallback'} for m in c['messages']),
                'interpretation_failures':sum(f.get('stage')=='chat_turn' and f.get('category')!='operational_limit' for f in failures),
                'technical_failures':sum(f.get('category') in {'model_transport','model_schema','operational_limit'} for f in failures),
                'token_budget_failures':sum(f.get('code')=='budget' for f in failures),
                'timeout_failures':sum(f.get('code')=='timeout' for f in failures),
                'scoring_executed':sum(m.get('generation_calls',0) or 0 for m in metrics if m.get('stage')=='generic_profile_match')>0,
                'score_diagnostics':(manager.records[sid].engine.chat._last_decision.get('score_flag_diagnostics') or {}),
                'score_status':(c.get('suggestion') or {}).get('status'),'level':(c.get('suggestion') or {}).get('level'),
                'interview_turns':len(turns),'generation_calls':sum(m.get('generation_calls',0) or 0 for m in metrics),
                'scoring_generation_calls':sum(m.get('generation_calls',0) or 0 for m in metrics if m.get('stage')=='generic_profile_match'),
                'generation_http_seconds':generation_latencies,
                'interviewer_latency_median_seconds':round(statistics.median(generation_latencies),3) if generation_latencies else None,
                'interviewer_latency_p95_seconds':p95,
                'respondent_generation_seconds':respondent_latencies,
                'adaptive_question_events':sum(e.get('event')=='adaptive_question' for e in c.get('routing_events',[])),
                'adaptive_probe_events':sum(e.get('event')=='adaptive_probe' for e in c.get('routing_events',[])),
                'routing_events':c.get('routing_events',[]),'json_export':True,'jsonl_export':jsonl.status_code==200,'trace_saved':trace_ok,
                'elapsed_seconds':round(time.monotonic()-start,2),'artifacts':{'json':str(name.with_suffix('.json')),'jsonl':str(out/(case+'.jsonl')),'markdown':str(out/(case+'.md')),'trace':str(out/(case+'-trace.json')) if trace_ok else None}})
            print(json.dumps({'case':case,'stage':c['stage'],'goal':manager.records[sid].engine.chat.objective,'steps':steps}),file=sys.stderr,flush=True)
    finally:manager.close()
    result={'schema_version':'iam-sra-citizen-stress-results-1.0.0','model_expected':MODEL,'base_url':args.base_url,
        'thinking_enabled':args.thinking,'respondent':args.respondent,'adaptive_questions':args.adaptive,
        'independent_validation':False,'cases':reports}
    (out/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(out/'metrics.json').chmod(0o600)
    print(json.dumps(result,ensure_ascii=False))
    return 0 if len(reports)==len(selected) else 1


if __name__=='__main__':raise SystemExit(main())
