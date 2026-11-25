#!/usr/bin/env python3
"""Rehearse all FN flows against an existing model with isolated in-process APIs.

Uses registered FN fictional answers, or an opt-in fictional respondent agent.
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
from copy import deepcopy


def load_agent_personas(root):
    from iam_sra.synthetic_respondent import load_personas
    from iam_sra.privacy import require_safe_data
    bank=load_personas(root/'eval/fn_agent_personas_v1.json')
    personas={p['fn_case']:p for p in bank['personas']}
    if len(personas)!=len(bank['personas']) or set(personas)!={'citizen_short','citizen_extended','organisational','technical'}:
        raise ValueError('Each FN agent case needs one distinct synthetic persona.')
    # load_personas validates the exact existing schema identifier. Screen the
    # actual persona content; schema identifiers are never participant prose.
    require_safe_data({'purpose':bank.get('purpose'),'personas':bank['personas']})
    return personas


def agent_reply(responder,chat):
    """Only participant-visible material goes to the respondent, never goals/scales."""
    question=next(m for m in reversed(chat['messages']) if m['role']=='assistant')
    history=[{'role':m['role'],'text':m['text']} for m in chat['messages'][-6:]]
    result=responder.respond({'question_text':question['text'],
        'response_options':chat.get('response_options',[])},history)
    if result['text'].strip():
        # The simulated spoken answer is authoritative. A contradictory control
        # hint must not replace ordinary uncertainty with an invented refusal.
        return result['text']
    return {'skip':'skip this question','unsure':'I do not know.','decline':'prefer not to answer'}.get(
        result['control'],result['text'])


def require_unmanaged_endpoint(root):
    """A separate benchmark must not race a public review's idle watcher."""
    import fcntl
    if os.getenv('IAM_SRA_ON_DEMAND_GPU','0')!='0':
        raise ValueError('Run this isolated test with IAM_SRA_ON_DEMAND_GPU=0 against your existing model.')
    lock=root/'.runtime/fn-review/share.lock'
    if lock.exists():
        with lock.open('r') as handle:
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                # Only the sharing launcher's pre-publication child may use
                # its exact owned model. No API/idle watcher exists yet.
                from iam_sra.model_lifecycle import ProjectA2
                origin=urlsplit(os.getenv('IAM_BASE_URL',''))
                token=os.getenv('IAM_SRA_VALIDATION_LEASE','')
                if origin.hostname=='127.0.0.1' and origin.port and token:
                    backend=ProjectA2(origin.port,root=root)
                    marker=backend._marker() or {}
                    if marker.get('lease_id')==token and backend.owns_running_model():
                        return
                raise ValueError('Stop the FN sharing launcher before this isolated test; its idle watcher could unload the model.') from None
            finally:fcntl.flock(handle,fcntl.LOCK_UN)


def live_scoring_failures(report, *, thinking=False):
    """A publication gate, distinct from protocol/fixture success or FN approval."""
    expected={'citizen_short','citizen_extended','organisational','technical'}
    rows=report.get('cases',[])
    failures=[]
    if (report.get('live_inference')!='executed' or report.get('respondent')!='agent'
            or len(rows)!=4 or {r.get('case') for r in rows}!=expected):
        failures.append('Four full live agent interviews are required.')
    for row in rows:
        numeric=(row.get('score_status')=='suggested' and type(row.get('level')) is int
            and 1<=row['level']<=9 and row.get('score_citation_count',0)>0
            and row.get('score_boundary_present'))
        abstained=row.get('score_status')=='abstained' and row.get('level') is None
        valid=(row.get('backend')=='vllm' and not row.get('controlled_api_fixture',True)
            and str(row.get('respondent_backend','')).startswith('existing_qwen_synthetic-')
            and row.get('scope')=='full_interview' and row.get('protocol_passed')
            and not row.get('failure') and not row.get('failures') and not row.get('partial')
            and row.get('generation_calls',0)>0 and row.get('agent_generation_calls',0)>0
            and row.get('scoring_generation_calls',0)>0 and (numeric or abstained)
            and row.get('model_suggestion_unchanged_after_review')
            and row.get('json_export_succeeded') and row.get('jsonl_export_succeeded')
            and row.get('markdown_export_succeeded')
            and row.get('thinking_enabled')==thinking
            and (not thinking or row.get('reasoning_characters',0)>0))
        if not valid:failures.append(str(row.get('case','unknown'))+': live scoring/review checks failed.')
    return failures


def write_summary(output,report):
    from iam_sra.privacy import require_clean
    lines=['# Synthetic FN interview pre-review','',
        'Automated tests only. Semantic accuracy and persona consistency need human review. This is not FN approval.','',
        'Surface: in-process Flask API. The Vue interface is not driven by this harness.','']
    if report.get('live_inference')=='unavailable':lines.append('No live interviews ran: the model endpoint was unavailable.')
    for row in report.get('cases',[]):
        lines.extend(['## '+row['case'],'',
            '- Protocol checks passed: '+str(row.get('protocol_passed',False)),
            '- End stage: '+str(row.get('stage','not reached')),
            '- Score status: '+str(row.get('score_status','not reached')),
            '- Interviewer generation calls: '+str(row.get('generation_calls',0)),
            '- Respondent generation calls: '+str(row.get('agent_generation_calls',0)),
            '- Failure: '+str(row.get('failure') or 'none recorded'),
            '- Persona consistency and judgment quality: pending human review.',''])
    markdown='\n'.join(lines)+'\n';require_clean(markdown)
    (output/'summary.md').write_text(markdown)


def render_transcript(conversation):
    from iam_sra.privacy import require_safe_data
    # Screen the semantic record before rendering, just as JSON exports do.
    # Flattening approved A–E control text into prose loses its metadata context
    # and makes the detector misread a choice marker as a person's initials.
    require_safe_data({'conversation':conversation})
    lines=['# Synthetic interview transcript','','Automated test, not stakeholder evidence or FN approval.','']
    for message in conversation['messages']:
        lines.extend(['## '+('Interviewer' if message['role']=='assistant' else 'Synthetic respondent'),'',message['text'],''])
        if message.get('scale'):
            lines.extend(f"{a['level']}. {a['label']}: {a['description']}" for a in message['scale']['anchors'])
            lines.append('')
    return '\n'.join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default=os.getenv('IAM_BASE_URL','http://127.0.0.1:18000'))
    parser.add_argument('--allow-live',action='store_true')
    parser.add_argument('--case',choices=['all','citizen_short','citizen_extended','organisational','technical'],default='all')
    parser.add_argument('--output',required=True)
    parser.add_argument('--opening-only',action='store_true',
        help='Check the citizen definition/uses against actual Qwen, without scoring or completing an interview.')
    parser.add_argument('--opening-variant',choices=['reference','paraphrase','uncertain','all'],default='reference')
    parser.add_argument('--model-variant',choices=['fp16','awq'],default=os.getenv('IAM_MODEL_VARIANT','fp16'))
    parser.add_argument('--thinking',action='store_true',help='Use the experimental reasoning-parser deployment (A2/AWQ or A30/FP16, 8192-token context).')
    parser.add_argument('--require-scoring',action='store_true',help='Require all four full live agent interviews to call the scorer and complete result/review, allowing honest model abstention.')
    parser.add_argument('--save-traces',action='store_true',help='Save screened controller decision summaries for these owned synthetic sessions; never raw thinking.')
    parser.add_argument('--respondent',choices=['reference','agent'],default='reference',
        help='Reference replays source answers; agent adapts the existing Qwen respondent to visible questions.')
    parser.add_argument('--respondent-no-think',action='store_true',help='Soft /no_think only for the fictional respondent; interviewer/scorer thinking remains enabled.')
    parser.add_argument('--max-agent-calls',type=int,default=60,help='Per-case respondent generation-call limit (4–200)')
    parser.add_argument('--max-turns',type=int,default=100,help='Per-case operational turn limit (10–150), never a readiness threshold')
    parser.add_argument('--case-timeout-seconds',type=int,default=3600,help='Per-case elapsed limit (60–7200)')
    parser.add_argument('--backend',choices=['vllm','cpu'],default='vllm',
        help='CPU uses the existing pinned CPU benchmark; it does not verify vLLM/GPU performance.')
    parser.add_argument('--cpu-threads',type=int,default=4)
    parser.add_argument('--cpu-generation-seconds',type=int,default=300)
    parser.add_argument('--cpu-python',help='Existing Python with pinned torch/transformers; default .venv/bin/python')
    args=parser.parse_args(argv)
    if args.respondent_no_think and (args.respondent!='agent' or not args.thinking):
        parser.error('--respondent-no-think requires --respondent agent --thinking.')
    if args.thinking and args.backend!='vllm':
        parser.error('--thinking requires --backend vllm and a matching reasoning-parser server.')
    if args.require_scoring and (args.respondent!='agent' or args.case!='all' or args.opening_only):
        parser.error('--require-scoring requires full --respondent agent --case all interviews.')
    if not args.allow_live:parser.error('Explicit --allow-live is required for synthetic model calls.')
    if not 4<=args.max_agent_calls<=200 or not 10<=args.max_turns<=150 or not 60<=args.case_timeout_seconds<=7200:
        parser.error('Use 4–200 agent calls, 10–150 turns and 60–7200 seconds per case.')
    if args.respondent=='agent' and (args.opening_only or args.opening_variant!='reference' or args.backend!='vllm'):
        parser.error('Agent mode runs full adaptive interviews with vLLM; opening variants belong to reference mode.')
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
    os.environ['IAM_MODEL_THINKING']='1' if args.thinking else '0'
    os.environ['IAM_BASE_URL']=args.base_url.rstrip('/')
    os.environ['IAM_CHAT_SYNTHETIC_REHEARSAL']='1'
    sys.path.insert(0,str(root/'src'))
    import httpx
    from iam_sra.settings import MODEL
    if args.respondent=='agent':
        try:require_unmanaged_endpoint(root)
        except ValueError as exc:parser.error(str(exc))
    personas=load_agent_personas(root) if args.respondent=='agent' else {}
    if args.backend=='vllm':
        try:
            with httpx.Client(trust_env=False,timeout=5) as http:
                r=http.get(args.base_url.rstrip('/')+'/v1/models');r.raise_for_status()
                assert any(m['id']==MODEL for m in r.json().get('data',[]))
        except (httpx.HTTPError,ValueError,AssertionError):
            output.mkdir(parents=True,exist_ok=False)
            unavailable={'classification':'synthetic','live_inference':'unavailable','cases_executed':0,
                'respondent':args.respondent,'services_changed':False,'surface':'in_process_flask_api',
                'thinking_enabled':args.thinking,
                'live_scoring_gate':{'passed':False,'failures':['The model endpoint was unavailable.']}}
            (output/'metrics.json').write_text(json.dumps(unavailable,indent=2)+'\n')
            write_summary(output,unavailable)
            print(json.dumps(unavailable));return 2
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
            name=key+('' if variant_name=='reference' else '-'+variant_name)
            case_deadline=started+args.case_timeout_seconds
            agent_metrics=[];asked={};responder=None
            if args.respondent=='agent':
                from iam_sra.synthetic_respondent import LLMRespondent
                responder=LLMRespondent(personas[key],base_url=args.base_url,soft_no_think=args.respondent_no_think)
            answers={row['id']:row['answer'] for row in fixture[key]}
            variant=variants.get(variant_name,{})
            answers.update(variant.get('answers',{}))
            def submit(text):
                nonlocal view,steps,failure_diagnostic
                if steps>=args.max_turns:raise RuntimeError('turn_limit')
                if time.monotonic()>=case_deadline:raise RuntimeError('case_timeout')
                steps+=1
                r=browser.post(f'/v1/sessions/{sid}/actions',headers=headers,json={'action':'chat_message','data':{'text':text},'expected_version':view['version'],'request_id':str(uuid4())})
                if r.status_code!=202:raise RuntimeError('submission_rejected')
                jid=r.json['job_id'];deadline=min(case_deadline,time.monotonic()+int(os.getenv('IAM_SRA_JOB_TIMEOUT','600')))
                while time.monotonic()<deadline:
                    result=browser.get('/v1/jobs/'+jid)
                    if result.status_code!=200:raise RuntimeError('job_unavailable')
                    job=result.json['job']
                    if job['status'] in {'completed','failed','cancelled'}:
                        if job['status']!='completed':
                            retained=manager.jobs.get(jid)
                            failure_diagnostic=deepcopy(retained.diagnostic) if retained else None
                            raise RuntimeError('job_failed')
                        current_view=browser.get(f'/v1/sessions/{sid}')
                        if current_view.status_code!=200 or 'session' not in current_view.json:
                            raise RuntimeError('session_view_withheld')
                        view=current_view.json['session']
                        if args.save_traces:
                            # Preserve the already-screened participant API view
                            # even if the later detailed export is withheld.
                            checkpoint=output/(name+'-view.json')
                            checkpoint.write_text(json.dumps(view,ensure_ascii=False,indent=2)+'\n')
                            checkpoint.chmod(0o600)
                        state=manager.records[sid].engine.chat
                        print(json.dumps({'case':key,'submitted_turns':steps,'stage':view['chat']['stage'],
                            'goal':state.objective,'interviewer_calls':state.calls}),file=sys.stderr,flush=True)
                        return
                    time.sleep(.05)
                raise RuntimeError('job_timeout')
            failure=None;failure_diagnostic=None;provisional=None
            try:
                submit('A. Citizen' if key.startswith('citizen') else 'B. Organisation or institution' if key=='organisational' else 'C. Technology expert or researcher')
                while view['chat']['stage']=='conversation':
                    current=manager.records[sid].engine.chat
                    goal=current.objective
                    if responder:
                        if view['chat']['scale'] is not None and not any(m.get('act')=='methodology' for m in view['chat']['messages']):
                            raise RuntimeError('premature_scale')
                        if goal=='area':answer=personas[key]['city']
                        elif goal=='citizen_duration':answer='B' if key=='citizen_extended' else 'A'
                        else:
                            question=view['chat']['messages'][-1]['text']
                            asked[question]=asked.get(question,0)+1
                            if asked[question]>2:raise RuntimeError('repeated_question')
                            used=sum(m.get('generation_calls',0) for m in agent_metrics)
                            if used+4>args.max_agent_calls:raise RuntimeError('agent_call_limit')
                            if steps>=args.max_turns:raise RuntimeError('turn_limit')
                            if time.monotonic()>=case_deadline:raise RuntimeError('case_timeout')
                            responder.external_deadline=case_deadline
                            try:answer=agent_reply(responder,view['chat'])
                            finally:agent_metrics.append(dict(getattr(responder,'last_metrics',{})))
                        old_failures=len(current.failures)
                        submit(answer)
                        current=manager.records[sid].engine.chat
                        checks.append({'goal':goal,'coverage_status':current.fn.coverage.get(goal,{}).get('status'),
                            'new_failures':len(current.failures)-old_failures})
                        if current.failed_turn_id:raise RuntimeError('interpretation_failed')
                        continue
                    if args.opening_only and goal=='healthcare_awareness':break
                    reference=next((row for row in fixture[key] if row['id']==goal),None)
                    node=current.fn.current(current.profile,current.depth,goal)
                    canonical=(current.messages[-1]['text']==CITIZEN_DURATION if goal=='citizen_duration'
                        else bool((reference and reference['question'] in current.messages[-1]['text'])
                                  or (reference is None and node
                                      and node['canonical_question'] in current.messages[-1]['text'])))
                    failures=len(current.failures)
                    submit(('35 minutes' if key=='citizen_extended' else '20 minutes') if goal=='citizen_duration' else answers.get(goal,'I do not know.'))
                    current=manager.records[sid].engine.chat
                    coverage=current.fn.coverage.get(goal,{})
                    expected=variant.get('expected_statuses',{}).get(goal,
                        'unknown' if reference and reference['answer_kind']=='uncertain' else 'explored')
                    actual_kind=current.fn.facts.get(goal)
                    readings=variant.get('accepted_readings',{}).get(goal)
                    # FN labels this qualified decision-making answer
                    # "uncertain". The controller deliberately preserves its
                    # explicit uncertainty marker while retaining the
                    # respondent's tentative, meaningful proposal as partial
                    # evidence. Audit that as a valid uncertain reading, not
                    # as a falsely certain answer.
                    if (not readings and reference and reference.get('answer_kind')=='uncertain'
                            and current.fn.facts.get(goal)=='partial'):
                        from iam_sra.fn_interview import explicit_answer_uncertainty
                        if explicit_answer_uncertainty(reference.get('answer',''))=='partial':
                            readings=[{'status':'explored','answer_kind':'partial'}]
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
                    provisional=deepcopy(view['chat'].get('suggestion'))
                    if view['chat']['stage']=='review':
                        submit(('E' if view['chat']['suggestion'].get('level') else 'I am not sure') if responder
                            else 'A' if view['chat']['suggestion'].get('level') else 'E')
                    while view['chat']['stage']=='review_addition':submit('no changes')
            except RuntimeError as exc:
                code=str(exc)
                failure=code if code in {'turn_limit','case_timeout','submission_rejected','job_unavailable',
                    'job_failed','job_timeout','premature_scale','repeated_question','agent_call_limit',
                    'interpretation_failed','unexpected_clarification_of_reference_answer','session_view_withheld'} else 'unexpected_runtime_failure'
            except (ValueError,httpx.HTTPError):failure='agent_or_privacy_failure' if responder else 'model_or_privacy_failure'
            result=browser.get(f'/v1/sessions/{sid}/export')
            if result.status_code!=200:
                reports.append({'case':key,'status':'export_unavailable','http_status':result.status_code,'failure':failure});continue
            try:data=screened_export(result.json)
            except ValueError:
                reports.append({'case':key,'status':'export_withheld','failure':'privacy_export_withheld'});continue
            c=data['conversation'];metrics=c['observable_metrics']
            name=key+('' if variant_name=='reference' else '-'+variant_name)
            (output/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            trace_saved=False
            if args.save_traces:
                try:trace=manager.developer_trace(sid)
                except ValueError:pass  # Privacy refusal withholds the optional diagnostic.
                else:
                    trace_path=output/(name+'-trace.json')
                    trace_path.write_text(json.dumps(trace,ensure_ascii=False,indent=2)+'\n')
                    trace_path.chmod(0o600);trace_saved=True
            jsonl=browser.get(f'/v1/sessions/{sid}/export?format=jsonl')
            jsonl_ok=jsonl.status_code==200
            if jsonl_ok:
                try:lines=[screened_export(json.loads(line)) for line in jsonl.get_data(as_text=True).splitlines() if line.strip()]
                except ValueError:jsonl_ok=False
                else:
                    jsonl_ok=bool(lines)
                    if jsonl_ok:(output/(name+'.jsonl')).write_text(''.join(json.dumps(line,ensure_ascii=False)+'\n' for line in lines))
            try:markdown=render_transcript(c)
            except ValueError:markdown_ok=False
            else:
                markdown_ok=True;(output/(name+'.md')).write_text(markdown)
            turns=sum(m['role']=='respondent' for m in c['messages'])
            question_fallbacks=sum(e.get('event')=='question_fallback' for e in c.get('routing_events',[]))
            fallbacks=sum(m.get('act') in {'authored_fallback','failure'} for m in c['messages'])+question_fallbacks
            required_opening={'area','citizen_duration','drone_recognition','drone_description','drone_uses'}
            if key=='citizen_extended':required_opening.add('drone_other_uses')
            output_tokens=sum(m.get('generated_tokens') or 0 for m in metrics)
            generation_seconds=sum(m.get('generation_http_seconds') or 0 for m in metrics)
            reference_audit=None
            if args.respondent=='reference' and key.startswith('citizen') and not args.opening_only:
                from iam_sra.fn_interview import specification as fn_specification
                from iam_sra.fn_reference_audit import audit as audit_reference
                reference_audit=audit_reference(key,data,fixture,fn_specification())
                (output/(name+'-reference-audit.json')).write_text(
                    json.dumps(reference_audit,ensure_ascii=False,indent=2)+'\n')
            reports.append({'case':key,'stage':c['stage'],'partial':c['completion']['partial'],
                'thinking_enabled':args.thinking,
                'reasoning_characters':sum(m.get('reasoning_characters',0) or 0 for m in metrics),
                'scoring_generation_calls':sum(m.get('generation_calls',0) or 0 for m in metrics if m.get('stage')=='generic_profile_match'),
                'score_citation_count':len((c.get('suggestion') or {}).get('citations',[])),
                'score_boundary_present':bool((c.get('suggestion') or {}).get('boundary')),
                'run_incomplete':c['stage']!='ended' or c['completion']['partial'],
                'scope':'citizen_opening_only' if args.opening_only else 'full_interview',
                'opening_variant':variant_name,
                'backend':args.backend,'model':c.get('model_provenance'),'reference_checks':checks,
                'reference_conditional_audit':reference_audit,
                'reference_conditional_audit_passed':None if reference_audit is None else bool(
                    not reference_audit['expected_but_unasked'] and not reference_audit['expected_but_uncovered']
                    and not reference_audit['unexpectedly_triggered'] and reference_audit['uncertainty_preserved']
                    and reference_audit['healthcare_prior_knowledge_not_exposure_id']),
                'respondent':args.respondent,'respondent_backend':getattr(responder,'backend','fn_reference_answers'),
                'respondent_thinking':'soft_disabled' if args.respondent_no_think else 'enabled' if args.thinking else 'disabled',
                'controlled_api_fixture':bool(bootstrap.json.get('synthetic_fixture')),
                'agent_generation_calls':sum(m.get('generation_calls',0) for m in agent_metrics),
                'agent_generated_tokens':sum(m.get('generated_tokens',0) for m in agent_metrics) or None,
                'agent_generation_http_seconds':round(sum(m.get('generation_http_seconds',0) for m in agent_metrics),3),
                'agent_model_wait_seconds':round(sum(m.get('model_wait_seconds',0) for m in agent_metrics),3),
                'persona_id':personas[key]['persona_id'] if responder else None,
                'persona_consistency':'pending_human_review' if responder else 'reference_fixture',
                'review_actor':'automation','independent_validation':False,
                'json_export_succeeded':True,'jsonl_export_succeeded':jsonl_ok,
                'markdown_export_succeeded':markdown_ok,
                'developer_trace_saved':trace_saved,
                'model_suggestion_unchanged_after_review':provisional==c.get('suggestion'),
                'protocol_passed':bool(c['stage']=='ended' and not failure and not c['completion']['partial']
                    and c.get('participant_review') and c.get('scale') and len(c['scale']['anchors'])==9
                    and not c['failures'] and jsonl_ok and c['classification']=='synthetic'
                    and all(stage['status'] in {'explored','not_applicable'} for stage in c['fn_interview']['stages'])
                    and (c.get('suggestion') or {}).get('status') in {'suggested','abstained'}
                    and provisional==c.get('suggestion')),
                'generated_tokens':output_tokens or None,'generation_http_seconds':round(generation_seconds,3) or None,
                'output_tokens_per_http_second':round(output_tokens/generation_seconds,3) if generation_seconds and output_tokens else None,
                'model_wait_seconds':round(sum(m.get('model_wait_seconds') or 0 for m in metrics),3),
                'interpretation_checks_passed':None if responder else bool(checks) and all(
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
                'question_wording_fallback_count':question_fallbacks,
                'technical_failure_count':sum(m.get('act')=='failure' for m in c['messages']),
                'generation_wall_seconds':round(sum(m['wall_seconds'] for m in metrics),3),
                'elapsed_seconds':round(time.monotonic()-started,3),'failures':c['failures'],'failure':failure,
                'failure_diagnostic':failure_diagnostic})
    finally:
        manager.close()
        if worker is not None:
            worker.terminate()
            try:worker.wait(timeout=10)
            except subprocess.TimeoutExpired:worker.kill();worker.wait()
    inference_status=('controlled_fixture' if any(row.get('controlled_api_fixture') for row in reports)
        else 'cpu_benchmark' if args.backend=='cpu' else 'executed')
    report=screened_export({'classification':'synthetic','fn_example_replay':args.respondent=='reference',
        'live_inference':inference_status,'thinking_enabled':args.thinking,
        'respondent':args.respondent,'surface':'in_process_flask_api','semantic_accuracy':None,
        'review_readiness':'manual_review_required','independent_validation':False,
        'limitations':['Using the same model for the respondent and interviewer is not independent semantic validation.',
            'Agent answers may drift from their fictional persona; inspect transcripts against the persona facts.',
            'This harness does not drive the Vue interface or validate browser layout.',
            'Automated review choices are test interactions, not participant agreement or FN approval.'],
        'living_lab_evidence':False,'services_changed':False,'cases':reports})
    gate_failures=live_scoring_failures(report,thinking=args.thinking)
    report['live_scoring_gate']={'passed':not gate_failures,'failures':gate_failures,
        'meaning':'Live completion and evidence/result transport checks; human semantic review remains required.'}
    (output/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    write_summary(output,report)
    print(json.dumps(report,ensure_ascii=False))
    return 0 if (not args.require_scoring or not gate_failures) and len(reports)==len(rehearsals) and all(
        r.get('protocol_passed') if args.respondent=='agent' else r.get('opening_passed') if args.opening_only else
        r.get('stage')=='ended' and not r.get('failure') and not r.get('partial') and r.get('interpretation_checks_passed')
        for r in reports) else 1


if __name__=='__main__':raise SystemExit(main())
