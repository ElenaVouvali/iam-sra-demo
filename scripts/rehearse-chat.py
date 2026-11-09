#!/usr/bin/env python3
"""Fixed authored turns through the sibling evaluator API adapter; no new agent."""
import argparse
import json
import re
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'iam-sra-evaluation'))
from iam_eval.adapter import APIAdapter


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--api-url',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case');parser.add_argument('--allow-live',action='store_true');args=parser.parse_args()
    cases=json.loads((ROOT/'eval/chat_rehearsals_v1.json').read_text())['cases']
    if args.case:cases=[c for c in cases if c['id']==args.case]
    if not cases:parser.error('Unknown case')
    args.output.mkdir(parents=True,exist_ok=False)
    summary=[]
    for case in cases:
        adapter=APIAdapter(args.api_url,max_requests=400,max_assessor_calls=100)
        started=time.monotonic();status='failed';export=None;submitted=0;failure_meta=None;not_submitted=0
        try:
            _,caps=adapter._request('GET','/v1/capabilities');adapter.csrf=caps['csrf_token']
            if not caps.get('synthetic_fixture') and not (args.allow_live and caps.get('chat',{}).get('synthetic_rehearsal')):
                raise ValueError('Use a trusted synthetic fixture or explicitly configured isolated synthetic rehearsal API; never a production participant dataset.')
            _,body=adapter._request('POST','/v1/sessions',{'mode':'chat','depth':case['depth']},retry=False)
            adapter.view=body['session']
            for message in case['messages']:
                stage=adapter.view['chat']['stage']
                if stage in {'ended','scope_change'}:break
                summary_command=message.strip().casefold()
                if stage=='summary' and summary_command not in {'looks right','no changes','continue','show the result','show summary','okay','ok','that is right'} and not any(word in summary_command for word in ('correct','change','actually')):
                    not_submitted += 1
                    print(case['id'], 'Scripted reply not submitted after wrap-up:', message,flush=True)
                    continue
                if stage in {'review','review_addition'} and message.strip().casefold() in {'stop'}:
                    not_submitted += 1
                    continue
                adapter.act('chat_message',{'text':message})
                submitted += 1
                print(case['id'], 'You:', message, '\nAI:', adapter.view['chat']['messages'][-1]['text'],flush=True)
            export=adapter.export()
            status='completed_journey' if export['conversation']['stage'] in {'review','review_addition','ended'} else 'partial'
            if export['conversation']['classification']!='synthetic':raise ValueError('Synthetic classification was not retained')
            (args.output/(case['id']+'.json')).write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n')
        except Exception as exc:
            status='failed_'+type(exc).__name__
            # EvalFailure carries only safe structural category/component/code;
            # never serialize its message or request/response text.
            failure_meta={key:getattr(exc,key) for key in ('category','component','code') if getattr(exc,key,None)}
            print(case['id'], 'STOPPED:', json.dumps(failure_meta,sort_keys=True),flush=True)
            if adapter.view:
                try:
                    export=adapter.export();(args.output/(case['id']+'-partial.json')).write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n')
                except Exception:pass
        finally:
            try:adapter.close()
            except Exception:pass
        conversation=(export or {}).get('conversation',{})
        messages=conversation.get('messages',[])
        assistant_questions=[m['text'].strip() for m in messages if m.get('role')=='assistant' and '?' in m.get('text','')]
        normalized=[re.sub(r'\W+',' ',q.casefold()).strip() for q in assistant_questions]
        repeats=sum(normalized.count(q)-1 for q in set(normalized))
        failures=conversation.get('failures',[])
        turn_failures=[f for f in failures if f.get('stage')=='chat_turn']
        judgment_failures=[f for f in failures if f.get('stage') in {'generic_profile_match','indicator_projection'}]
        events=conversation.get('routing_events',[])
        metrics=conversation.get('observable_metrics',[])
        suggestion=conversation.get('suggestion') or {}
        indicator_projection=conversation.get('indicator_projection',{})
        coverage=conversation.get('objective_coverage',[])
        summary.append({'case':case['id'],'profile':case.get('profile'),'depth':case['depth'],
                        'classification':'SYNTHETIC_TEST_DATA','status':status,
                        'failure':failure_meta,
                        'final_stage':conversation.get('stage'),'successful_submitted_turns':submitted,
                        'scripted_messages_not_submitted_after_wrapup':not_submitted,
                        'failed_turns':len(turn_failures),'failed_judgments':len(judgment_failures),
                        'generation_calls':sum(m.get('generation_calls') or 0 for m in metrics),
                        'generation_attempts':sum(f.get('attempts',0) for f in failures),
                        'retry_attempts':sum(max(0,f.get('attempts',0)-1) for f in failures),
                        'fallbacks':[{'reason':e.get('reason'),'objective_id':e.get('objective_id')} for e in events if e.get('event') in {'authored_fallback','question_fallback'}],
                        'question_count':len(assistant_questions),'exact_question_repeats':repeats,
                        'elapsed_seconds':round(time.monotonic()-started,3),
                        'generation_latency_seconds':round(sum(m.get('wall_seconds',0) for m in metrics),3),
                        'missing_objectives':[r['objective_id'] for r in coverage if r['status'] in {'not_explored','not_selected'}],
                        'reached_provisional_result':bool(suggestion),
                        'suggestion_status':suggestion.get('status'),'suggested_level':suggestion.get('level'),
                        'failure_diagnostics':failures,
                        'scale_id':(conversation.get('scale') or {}).get('source',{}).get('document'),
                        'scale_version':(conversation.get('scale') or {}).get('rubric_version'),
                        'respondent_review_stage_reached':conversation.get('stage') in {'review','review_addition','ended'},
                        'json_export_succeeded':bool(export),'indicator_results_individually_reviewed':indicator_projection.get('participant_reviewed',False),
                        'citation_validity':'checked by server validator when suggested; otherwise not applicable',
                        'known_untested':'Human semantic review and the full set of natural-language controls remain pending.',
                        'surface':'actual_api','semantic_review':'pending_human_review'})
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{'case':r['case'],'status':r['status'],'elapsed_seconds':r['elapsed_seconds'],
                       'stage':r['final_stage'],'suggestion_status':r['suggestion_status']} for r in summary]))

if __name__=='__main__':main()
