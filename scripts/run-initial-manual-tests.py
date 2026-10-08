"""Run human-authored initial-stage cases through the live UI backend.

No mocks, automatic answer corrections or second-stage follow-ups.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import httpx
from iam_sra.conversation_client import ConversationClient
from iam_sra.session import Session
from iam_sra.settings import config, CONCERNS, BASE_URL


def compare(case,snapshot):
    actual={c['concern_id']:c['score'] for c in snapshot['assessment']['concerns']}
    scores=[{'concern_id':cid,'expected':case['expected_scores'].get(cid),'actual':actual.get(cid)}
            for cid in CONCERNS if actual.get(cid)!=case['expected_scores'].get(cid)]
    actual_facets={(d['concern_id'],d['facet']):d['score'] for d in snapshot.get('score_decisions',[])}
    expected_facets={(cid,facet):score for cid,facets in case['expected_facets'].items() for facet,score in facets.items()}
    facets=[{'concern_id':cid,'facet':facet,'expected':expected_facets.get((cid,facet)),'actual':actual_facets.get((cid,facet))}
            for cid,facet in sorted(set(actual_facets)|set(expected_facets))
            if actual_facets.get((cid,facet))!=expected_facets.get((cid,facet))]
    mapped={(c['concern_id'],facet) for c in snapshot['assessment']['concerns'] for facet in c.get('facets',[])}
    coverage=[{'concern_id':cid,'facet':facet,'issue':'missing_evidenced_facet' if (cid,facet) in expected_facets else 'unexpected_facet'} for cid,facet in sorted(mapped.symmetric_difference(set(expected_facets)))]
    ag=snapshot['aggregate'];expected=case['expected_aggregation']
    observed={**ag,'minimum':ag['trace']['selected_minimum'],'cap_applied':ag['trace']['cap_applied']}
    arithmetic=[]
    for key in ['coverage','mean','minimum','cap','cap_applied','adjusted','rounded']:
        a=observed[key];e=expected[key]
        same=(abs(a-e)<1e-9 if isinstance(a,(int,float)) and isinstance(e,(int,float)) else a==e)
        if not same:arithmetic.append({'field':key,'expected':e,'actual':a})
    return {'concern_scores':scores,'facet_scores':facets,'mapping_coverage':coverage,'aggregation':arithmetic,'matches_expected':not(scores or facets or coverage or arithmetic)}


def compare_meaning(case,facets,evidence):
    actual={(f.concern_id,f.facet):f for f in facets}
    positions=[];conditions=[]
    for cid,targets in case.get('expected_positions',{}).items():
        for facet,expected in targets.items():
            value=actual.get((cid,facet))
            observed=value.position if value else None
            if observed!=expected:positions.append({'concern_id':cid,'facet':facet,'expected':expected,'actual':observed})
    for cid,targets in case.get('expected_conditions',{}).items():
        for facet,expected in targets.items():
            value=actual.get((cid,facet));refs=value.condition_ids if value else []
            words=' '.join(evidence[r].text for r in refs if r in evidence)
            valid=bool(refs)==expected['required']
            if expected.get('verbatim_fragment'):valid=valid and expected['verbatim_fragment'] in words
            if not valid:conditions.append({'concern_id':cid,'facet':facet,'expected':expected,'actual_ids':refs})
    return {'positions':positions,'conditions':conditions}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids',help='Comma-separated case IDs; overrides --split')
    parser.add_argument('--output',default=str(ROOT/'.runtime/initial-manual-live-results.json'))
    parser.add_argument('--base-url',default=BASE_URL)
    parser.add_argument('--mapping-only',action='store_true',help='Compare facet coverage, positions and conditions before numerical scoring')
    parser.add_argument('--check-followups',action='store_true',help='Also compare follow-up IDs selected from the live interpretation against the authored follow-up pack')
    parser.add_argument('--case-file',type=Path,default=ROOT/'manual-tests/initial-assessment-cases.json',help='Alternative human-authored case pack')
    parser.add_argument('--split',choices=['development','fresh_validation','all'],default='development',help='Default: original 24 development cases. Explicit --ids overrides this selection.')
    args=parser.parse_args()
    pack=json.loads(args.case_file.read_text())
    followup_targets={c['id']:c for c in json.loads((ROOT/'manual-tests/followup-assessment-cases.json').read_text())['cases']} if args.check_followups else {}
    if pack.get('mapping_only') and not args.mapping_only:
        parser.error('This case pack tests mapping only; use --mapping-only.')
    cases=pack['cases']
    if args.ids:
        selected=set(args.ids.split(','));unknown=selected-{c['id'] for c in cases}
        if unknown:parser.error('Unknown cases: '+','.join(sorted(unknown)))
        cases=[c for c in cases if c['id'] in selected]
    elif args.split!='all':cases=[c for c in cases if c.get('evaluation_split','development')==args.split]
    if args.check_followups and any(c['id'] not in followup_targets or c['response']!=followup_targets[c['id']]['response'] for c in cases):
        parser.error('--check-followups requires cases matching the initial/follow-up T01–T32 packs.')
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'scope':'Initial mapping only.' if args.mapping_only else 'Initial interpretation and scoring only; no second-stage actions.',
            'notice':'Human-authored targets; numerical differences require semantic review, not automatic tuning.',
            'model':config('model'),'policy':config('scoring'),'registry_version':config('concerns')['version'],
            'prompts':config('prompts'),'selected_ids':[c['id'] for c in cases],
            'scripted_confirmation':True,'case_file':str(args.case_file),'base_url':args.base_url,'live_model_used':False,'attempts':[]}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    def save():output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    try:
        response=httpx.get(args.base_url.rstrip('/')+'/v1/models',timeout=10,trust_env=False)
        response.raise_for_status();report['server_models']=response.json()
    except Exception as exc:
        report.update(blocked=True,error=str(exc),error_type=type(exc).__name__,cases_not_run=[c['id'] for c in cases]);save()
        print('Live model unavailable: '+str(exc)+'\nReport: '+str(output),flush=True);return 2
    for case in cases:
        s=Session();client=ConversationClient(base_url=args.base_url);started=time.monotonic()
        row={'id':case['id'],'response':case['response'],'success':False};stage='interpretation'
        try:
            s.begin();s.submit(case['response'],client)
            row['interpretation']=s.draft.model_dump()
            row['facet_meanings']=[f.model_dump() for f in s.original_facets.values()]
            if args.mapping_only:
                actual={(f.concern_id,f.facet) for f in s.original_facets.values()}
                expected={(cid,f) for cid,facets in case['expected_facets'].items() for f in facets}
                coverage=[{'concern_id':cid,'facet':f,'issue':'missing_evidenced_facet' if (cid,f) in expected else 'unexpected_facet'} for cid,f in sorted(actual.symmetric_difference(expected))]
                row.update(success=True,comparison={'mapping_coverage':coverage,'matches_expected':not coverage})
            else:
                s.confirm(True,defer_discovery=True)
                stage='initial_scoring';s.score_initial(client)
                row.update(success=True,initial=s.initial,comparison=compare(case,s.initial))
            semantics=compare_meaning(case,s.original_facets.values(),s.evidence)
            row['comparison'].update(semantics)
            row['comparison']['matches_expected']=row['comparison']['matches_expected'] and not any(semantics.values())
            row['comparison']['unresolved_reviews']=s.mapping_review_errors
            row['comparison']['matches_expected']=row['comparison']['matches_expected'] and not s.mapping_review_errors
            if args.check_followups:
                from iam_sra.updates import select_followups
                questions=select_followups(s.draft,s.evidence,False,list(s.original_facets.values()),assessed_scores={c['concern_id']:c['score'] for c in s.initial['assessment']['concerns'] if c['status']=='assessed'}) if not args.mapping_only else []
                expected=followup_targets[case['id']]['expected_question_ids'] if not args.mapping_only else []
                actual=[q['id'] for q in questions]
                row['followups']={'expected_ids':expected,'actual_ids':actual,
                    'missing_ids':sorted(set(expected)-set(actual)),
                    'unexpected_ids':sorted(set(actual)-set(expected)),
                    'status':'not_checked_without_initial_scores' if args.mapping_only else 'checked'}
                if not args.mapping_only:
                    row['comparison']['followups_match_expected']=set(actual)==set(expected)
                    row['comparison']['matches_expected']=row['comparison']['matches_expected'] and row['comparison']['followups_match_expected']
        except Exception as exc:
            row.update(failure_stage=stage,error=str(exc),error_type=type(exc).__name__)
        row.update(latency_seconds=round(time.monotonic()-started,3),inference=s.inference,
                   last_diagnostics=client.last_diagnostics,last_settings=client.last_settings,
                   last_trace=client.last_trace)
        report['live_model_used']=report['live_model_used'] or any(m.get('generation_calls',0)>0
            for m in [client.last_metrics]+[record.get('metrics',{}) for record in s.inference])
        report['attempts'].append(row);save()
        print(json.dumps({'id':case['id'],'success':row['success'],'comparison':row.get('comparison'),'error':row.get('error')},ensure_ascii=False),flush=True)
    report['completed']=True
    report['all_matches_expected']=all(a['success'] and a['comparison']['matches_expected'] for a in report['attempts'])
    save();print('Report: '+str(output),flush=True)
    return 0 if report['all_matches_expected'] else 1

if __name__=='__main__':raise SystemExit(main())
