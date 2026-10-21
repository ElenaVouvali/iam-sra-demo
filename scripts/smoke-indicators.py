#!/usr/bin/env python3
"""Small live Qwen smoke using real sources and explicitly synthetic citizen answers."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from iam_sra.conversation_session import ConversationSession
from iam_sra.assessment import AssessmentError
from iam_sra.indicator_client import IndicatorClient
from iam_sra.privacy import screened_export, safe_message, safe_diagnostics
from iam_sra.settings import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True, help='Existing verified local model origin; starts no service.')
    parser.add_argument('--case', choices=['uncertain','disagreement','explicit_disagreement'])
    parser.add_argument('--output', type=Path, default=ROOT/'.runtime/indicator-live-smoke')
    args=parser.parse_args()
    import httpx
    with httpx.Client(timeout=5, trust_env=False) as http:
        response=http.get(args.base_url.rstrip('/')+'/v1/models');response.raise_for_status()
        if not any(m['id']=='Qwen/Qwen3-8B' for m in response.json()['data']):
            parser.error('The existing endpoint does not advertise the required alias.')
    output=args.output;output.mkdir(parents=True, exist_ok=True)
    runs=[]
    cases=[('uncertain','I do not know anything about drone noise and cannot explain it yet.'),
           ('disagreement','Repeated flights could interrupt sleep even when each flight is brief. I would propose avoiding night flights and checking residents\u2019 experience before deciding the hours.'),
           ('explicit_disagreement','My condition is that there should be no night flights because repeated interruptions can disturb sleep. I have never taken part in a drone project.')]
    for name,answer in cases:
        if args.case and name != args.case: continue
        started=time.monotonic();client=IndicatorClient(base_url=args.base_url)
        session=ConversationSession();session.set_context('personal','citizen','madrid')
        session.finish();session.confirm_general();session.decline_scenario();session.confirm_final()
        session.select_indicators(['indicator-07'],'general_understanding','Synthetic medical delivery discussion')
        record={'case':name,'synthetic':True,'model_alias':'Qwen/Qwen3-8B','status':'failed'}
        try:
            session.indicator_answer(answer,client)
            # Curated synthetic reference expectation, never sent as a target
            # level. Behave like a participant who notices a misinterpretation.
            if name in {'disagreement','explicit_disagreement'}:
                observations=session.indicators.current['pending']['reading']['observations']
                def preserves_proposal(items):
                    return any(o['kind']=='condition' and o['actor']=='self' and o['domain']=='IAM' for o in items)
                record['initial_proposal_preserved']=preserves_proposal(observations)
                record['interpretation_correction_requested']=not record['initial_proposal_preserved']
                if record['interpretation_correction_requested']:
                    session.indicator_correct('I explained a possible effect and proposed safeguards. I am not claiming past action or only promising future participation. Please preserve my reasoning and the proposed conditions.',client)
                    observations=session.indicators.current['pending']['reading']['observations']
                record['reviewed_proposal_preserved']=preserves_proposal(observations)
                if not record['reviewed_proposal_preserved']:
                    raise AssessmentError('The interpretation still loses the proposed safeguard after participant correction.',code='interpretation_semantic')
            session.indicator_confirm();session.indicator_finish()
            session.indicator_suggest(client)
            row=session.indicators.current
            record.update(tool_status=row['tool']['status'], selected_statement_id=row['tool']['selected_statement_id'],
                          explanation=row['tool']['explanation'])
            if name=='uncertain':
                record['expected_abstention_observed']=row['tool']['status']=='abstained'
                session.indicator_review('unsure',session.indicators.revision)
            elif row['tool']['statement']:
                alternative=next(s for s in session.indicators.scale('indicator-07') if s['id']!=row['tool']['statement']['id'])
                session.indicator_review('select',session.indicators.revision,alternative['id'],
                    'Synthetic disagreement test: this statement feels closer to my situation.')
                record['separate_disagreement_preserved']=row['participant']['disagrees_with_tool']
            else:
                record['separate_disagreement_preserved']=False
                session.indicator_review('select',session.indicators.revision,'indicator-07-crl-1',
                    'Synthetic selection after abstention.')
            data=session.browser_export();data.update(synthetic=True,data_classification='SYNTHETIC_TEST_ONLY')
            text=json.dumps(screened_export(data),ensure_ascii=False,indent=2)
            (output/(name+'.json')).write_text(text+'\n')
            (output/(name+'.jsonl')).write_text(json.dumps(screened_export(data),ensure_ascii=False)+'\n')
            record['session_completed']=True
            if not record.get('expected_abstention_observed', record.get('separate_disagreement_preserved', False)):
                raise AssessmentError('The session completed but the required smoke outcome was not observed.',code='smoke_expectation')
            record['status']='completed'
        except Exception as exc:
            if session.indicators and session.indicators.current:
                record['confirmed_observations'] = session.indicators.evidence()
                partial=session.browser_export();partial.update(synthetic=True,data_classification='SYNTHETIC_TEST_ONLY',run_status='incomplete')
                (output/(name+'-incomplete.json')).write_text(json.dumps(screened_export(partial),ensure_ascii=False,indent=2)+'\n')
            record['failure']={'code':getattr(exc,'code','runtime'),'message':safe_message(exc),
                               'diagnostics':safe_diagnostics(getattr(client,'last_diagnostics',[]))}
        record.update(duration_seconds=round(time.monotonic()-started,3),
                      metrics=getattr(client,'session_metrics',{}))
        runs.append(record)
    report={'synthetic_only':True,'policy':'indicator-matching-draft-1.0.0','runs':runs,
            'interpretation':'Live semantic observations, not independent or empirical validation.',
            'bank':session.indicators.identity(),
            'provenance':{k:session.provenance[k] for k in ('code_commit','working_tree_dirty','code_snapshot_sha256')}}
    (output/'summary.json').write_text(json.dumps(screened_export(report),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if all(r['status']=='completed' for r in runs) else 1


if __name__=='__main__':raise SystemExit(main())
