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
from iam_sra.settings import BASE_URL, ROOT, config
from iam_sra.readiness_retrieval import ExplanationClient, corpus_hash
from iam_sra.readiness_report import markdown_report

CASES = [
 ('informed_opposition','I oppose this corridor. Repeated flights could disturb people resting during the day. I would want measurements at different times and a comparison with road deliveries.'),
 ('uninformed_support','Yes, I accept everything without reservations. I do not know how the service works.'),
 ('uncertain','I cannot decide yet and do not know which evidence to ask for.'),
 ('transferable_participation','I attended a bus-route consultation last year and proposed a stop near the clinic. I do not know if my comment changed anything. I have not attended a drone consultation.'),
 ('opportunity_barrier','I would take part, but I do not know any way to contact the organisers. Evening meetings conflict with caring for my father.')]


def run_meeting_case(case, client, explanation_client, session=None):
    """Normal controller, actual question context, explicit automated confirmation."""
    s = session or Session(assessment_mode='acceptance_and_readiness_evidence')
    automated = []
    def confirm():
        s.confirm(True)
        automated.append(s.confirmations[-1]['event_id'])
    s.submit(case['initial_answer'], client); confirm()
    initial = s.initial_readiness
    s.ask_information(case['optional_information_question'], explanation_client)
    s.display_information()
    s.start_learning()
    while s.state == 'interview':
        q = s.current_question
        if q is None: break
        answer = case['followup_by_question_id'].get(q['id'])
        if answer is None: answer = case['followup_by_criterion'].get(q['criterion_id'])
        if answer is None:
            s.skip(); continue
        s.respond(answer, client); confirm()
    if s.state != 'final': s.finish()
    before_correction = s.export()
    candidates = [e for e in s.events if e['active'] and e['kind'] == 'readiness_followup' and e['control'] == 'answer']
    if candidates:
        event = candidates[-1]
        s.edit_answer(event['id'])
        if s.final_readiness is not None: raise AssertionError('Correction failed to invalidate final profile.')
        s.correct(event['text'] + case['correction_suffix'], client); confirm()
        s.finish()
    if s.initial_readiness != initial: raise AssertionError('Immutable initial snapshot changed.')
    data = s.export()
    data['automation'] = {'confirmation_event_ids':automated, 'meaning':'Scripted confirmation, not actual citizen validation', 'information_display':'Presented to automated runner, not proof of human exposure'}
    return {'actual_output':data, 'before_correction':before_correction,
            'researcher_report':markdown_report(data),
            'structural_checks':{'initial_preserved':True, 'null_numbers':data['numerical_crl'] is None and data['numerical_srl'] is None},
            'semantic_review':{'status':'human_review_required', 'expected_invariants':case['should_infer'], 'prohibited_inferences':case['must_not_infer']}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--meeting',action='store_true');p.add_argument('--base-url',default=BASE_URL);p.add_argument('--output',default='.runtime/readiness-live-smoke.json');args=p.parse_args()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    definitions = json.loads((ROOT/'eval/meeting_cases.json').read_text())['cases'] if args.meeting else None
    report={'versions':{'model':config('model'),'instrument':config('readiness')['version'],'corpus':config('readiness_corpus')['version'],'corpus_sha256':corpus_hash(config('readiness_corpus')),'extraction_prompt':ReadinessClient.prompt_version,'explanation_prompt':ExplanationClient.prompt_version},'scripted_confirmation':'automation, not citizen validation','assessment_mode':'acceptance_and_readiness_evidence','live_model_used':False,'cases':[], 'semantic_validation':False}
    try:
        with httpx.Client(timeout=10,trust_env=False) as http:
            response=http.get(args.base_url.rstrip('/')+'/v1/models');response.raise_for_status()
    except httpx.HTTPError as exc:
        report.update(status='blocked',error=str(exc),semantic_review_status='blocked_no_live_outputs');
        if definitions: report['cases']=[{'id':c['id'],'status':'blocked','success':False,'actual_output':None,'human_review':'No live output to inspect.'} for c in definitions]
        output.write_text(json.dumps(report,indent=2));print(json.dumps(report));return 2
    selected = [(c['id'],c['initial_answer']) for c in definitions] if definitions else CASES
    for name,text in selected:
        s=Session();client=ReadinessClient(base_url=args.base_url);started=time.monotonic()
        row={'id':name,'input':text}
        try:
            if definitions:
                row.update(run_meeting_case(next(c for c in definitions if c['id']==name), client, ExplanationClient(base_url=args.base_url), session=s))
                row['success'] = True
            else:
                s.submit(text,client);s.confirm(True);s.finish()
                row.update(success=True,actual_output=s.export())
        except Exception as exc: row.update(success=False,error=str(exc),partial_output=s.export())
        row['latency_seconds']=round(time.monotonic()-started,3)
        row['model_trace']=getattr(client,'last_trace',[])
        report['live_model_used']|=bool(row['model_trace'])
        report['cases'].append(row)
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({'id':name,'success':row['success'],'records':(row.get('actual_output',{}).get('final_readiness_profile') or s.current_profile)['records'],'error':row.get('error')},ensure_ascii=False),flush=True)
    report['status']='completed';report['semantic_review_status']='human_review_required';output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return 0 if all(r['success'] for r in report['cases']) else 1

if __name__=='__main__':raise SystemExit(main())
