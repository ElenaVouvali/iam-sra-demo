"""Serial bounded FN replay with mandatory correctness checks and truthful exits."""
import argparse,json,time
from pathlib import Path
from iam_sra.session import Session,State
from iam_sra.conversation_client import ConversationClient
from iam_sra.updates import facet_state
from iam_sra.replay_checks import check_export,stage_metrics,live_response_received,write_report

def replay(client):
    s=Session();start=time.monotonic();stage='initial interpretation'
    row={'dialogue_completed':False,'structural_evidence_checks_passed':False,'rubric_checks_passed':False,
         'live_model_used':False,'scripted_citizen_confirmations':True,'scientific_validation':False}
    try:
        text=json.loads(Path('eval/fn_reference.json').read_text())['citizen_text']
        s.begin();s.submit(text,client)
        assert s.initial is None and not any(i.get('kind','').endswith('scoring') for i in s.inference)
        s.finish_discovery();stage='initial confirmed scoring';s.continue_initial(True,client)
        initial=s.initial
        while s.state==State.FOLLOWUPS:
            q=s.current_question;stage='follow-up '+q['id']
            s.respond(q['choices'][1] if q['id']=='q3' else q['choices'][0],'',client)
        if s.joint_required:
            stage='explicit joint acceptance'
            unchanged=[key for key,f in s.original_facets.items() if f.facet=='medical_public_benefit' and f.position=='supported' and facet_state(s,f.concern_id,f.facet)[0]=='untested']
            s.record_joint('accept',[],'',client,{key:{'response':'yes','clarification':''} for key in unchanged})
        stage='final confirmed scoring';s.continue_final(True,client)
        row.update(dialogue_completed=True,session=s.export())
        stage='mandatory correctness checks'
        row.update(check_export(row['session'],initial,{'facets':[['welfare_equity','medical_public_benefit'],['noise','acoustic_impact'],['perceived_safety_privacy','personal_privacy']],
                'exclude':['airspace_capacity','infrastructure_land_use']}))
        stage='revision invalidation check'
        s.rewind('q1')
        stale_ok=s.final is None and s.conditional is None and s.updated_confirmed is None and s.conditional_confirmed is None and s._pending_final_original is None and s.initial==initial and bool(s.revision_history)
        row['structural_evidence_checks'].append({'check':'answer_revision_invalidates_dependents','passed':stale_ok})
        row['structural_evidence_checks_passed']=row['structural_evidence_checks_passed'] and stale_ok
        row['revision_check']={'passed':stale_ok,'revision_history':s.revision_history}
        if not row['structural_evidence_checks_passed'] or not row['rubric_checks_passed']:row['failure_stage']='mandatory correctness checks'
    except Exception as exc:
        row.update(failure_stage=stage,error_type=type(exc).__name__,error=str(exc))
    metrics=stage_metrics(s,client)
    row.update(latency_seconds=round(time.monotonic()-start,3),stage_metrics=metrics,inference=s.inference,
        last_diagnostics=getattr(client,'last_diagnostics',[]),last_settings=getattr(client,'last_settings',{}),
        last_raw_trace=getattr(client,'last_trace',[]))
    row['live_model_used']=isinstance(client,ConversationClient) and live_response_received(s,client)
    row['success']=row['dialogue_completed'] and row['structural_evidence_checks_passed'] and row['rubric_checks_passed'] and row['live_model_used']
    return row

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='.runtime/fn-evidence-replay.json')
    p.add_argument('--no-live',action='store_true',help='Record blocked/unexecuted check without contacting any endpoint.')
    args=p.parse_args()
    row=({'dialogue_completed':False,'structural_evidence_checks_passed':False,'rubric_checks_passed':False,'live_model_used':False,
          'success':False,'failure_stage':'not_attempted','reason':'Live testing explicitly disabled; no inference attempted.','stage_metrics':{}}
         if args.no_live else replay(ConversationClient()))
    write_report(args.output,row)
    print(json.dumps({k:v for k,v in row.items() if k not in {'session','inference','last_raw_trace','last_settings','last_diagnostics','revision_check'}}),flush=True)
    return 0 if row['success'] else 1
if __name__=='__main__':raise SystemExit(main())
