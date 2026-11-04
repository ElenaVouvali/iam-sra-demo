#!/usr/bin/env python3
"""Fixed authored turns through the sibling evaluator API adapter; no new agent."""
import argparse
import json
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
        started=time.monotonic();status='failed';export=None
        try:
            _,caps=adapter._request('GET','/v1/capabilities');adapter.csrf=caps['csrf_token']
            if not caps.get('synthetic_fixture') and not (args.allow_live and caps.get('chat',{}).get('synthetic_rehearsal')):
                raise ValueError('Use a trusted synthetic fixture or explicitly configured isolated synthetic rehearsal API; never a production participant dataset.')
            _,body=adapter._request('POST','/v1/sessions',{'mode':'chat','depth':case['depth']},retry=False)
            adapter.view=body['session']
            for message in case['messages']:
                if adapter.view['chat']['stage']=='ended':break
                if message=='stop' and adapter.view['chat']['stage']=='summary':
                    print(case['id'], 'Already at automatic wrap-up; redundant scripted stop not submitted.',flush=True)
                    continue
                adapter.act('chat_message',{'text':message})
                print(case['id'], 'You:', message, '\nAI:', adapter.view['chat']['messages'][-1]['text'],flush=True)
            export=adapter.export()
            status='completed_journey' if export['conversation']['stage'] in {'summary','review','review_addition','ended'} else 'partial'
            if export['conversation']['classification']!='synthetic':raise ValueError('Synthetic classification was not retained')
            (args.output/(case['id']+'.json')).write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n')
        except Exception as exc:
            status='failed_'+type(exc).__name__
            if adapter.view:
                try:
                    export=adapter.export();(args.output/(case['id']+'-partial.json')).write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n')
                except Exception:pass
        finally:
            try:adapter.close()
            except Exception:pass
        summary.append({'case':case['id'],'classification':'SYNTHETIC_TEST_DATA','status':status,
                        'seconds':round(time.monotonic()-started,3),'surface':'actual_api',
                        'semantic_review':'pending_human_review','suggestion':(export or {}).get('conversation',{}).get('suggestion')})
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{'case':r['case'],'status':r['status'],'seconds':r['seconds']} for r in summary]))

if __name__=='__main__':main()
