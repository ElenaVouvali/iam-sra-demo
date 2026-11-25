#!/usr/bin/env python3
"""Compare the frozen lexical top-three baseline with bounded concern rules."""
import argparse
import json
import re
import sys
from pathlib import Path


def metrics(rows):
    tp=fp=fn=0;per={f'indicator-{i:02d}':{'tp':0,'fp':0,'fn':0} for i in range(1,16)}
    unmapped=correct_unmapped=ambiguous=correct_ambiguous=0;multi=multi_hit=0
    case_rows=[]
    for case, predicted, status in rows:
        expected=set(case['expected_indicator_ids']);predicted=set(predicted)
        t=predicted&expected;f=predicted-expected;n=expected-predicted
        tp+=len(t);fp+=len(f);fn+=len(n)
        for iid in per:
            per[iid]['tp']+=int(iid in t);per[iid]['fp']+=int(iid in f);per[iid]['fn']+=int(iid in n)
        if case.get('expected_unmapped'):
            unmapped+=1;correct_unmapped+=int(status=='unmapped' and not predicted)
        if case.get('expected_ambiguous'):
            ambiguous+=1;correct_ambiguous+=int(status=='ambiguous' and not predicted)
        if len(expected)>1:multi+=1;multi_hit+=int(bool(t))
        case_rows.append({'case_id':case['id'],'expected_ids':sorted(expected),
            'predicted_ids':sorted(predicted),'status':status,'tp_ids':sorted(t),
            'fp_ids':sorted(f),'fn_ids':sorted(n),'reference_rationale':case['rationale']})
    precision=tp/(tp+fp) if tp+fp else 0.0;recall=tp/(tp+fn) if tp+fn else 0.0
    return {'case_count':len(rows),'tp':tp,'fp':fp,'fn':fn,'precision':precision,
        'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0.0,
        'unmapped_cases':unmapped,'correctly_unmapped':correct_unmapped,
        'ambiguous_cases':ambiguous,'correctly_ambiguous':correct_ambiguous,
        'multi_indicator_cases':multi,'multi_indicator_cases_with_any_expected_hit':multi_hit,
        'per_indicator':per,'cases':case_rows}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transcript',action='append',default=[])
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    if not out.is_relative_to((root/'.runtime').resolve()) or out.exists():parser.error('Use a new output directory under ignored .runtime/.')
    sys.path.insert(0,str(root/'src'))
    from iam_sra.readiness_bank import load_bank
    from iam_sra.conversation_corpus import rank
    from iam_sra.indicator_projection import project_concerns
    from iam_sra.privacy import screened_export
    bank=load_bank();cases=json.loads((root/'eval/iam_indicator_concern_holdout_v2.json').read_text())['cases']
    definitions=[{'id':row['id'],'search_text':row['name']+' '+row['definition']} for row in bank['indicators']]
    baseline_rows=[];projection_rows=[];case_outputs=[]
    for case in cases:
        evidence_id='fixture:'+case['id']
        lexical=rank(case['evidence'],definitions,3)
        lexical_ids=[r['id'] for r in lexical if r['retrieval_score']>0]
        baseline_rows.append((case,lexical_ids,'candidate_unreviewed' if lexical_ids else 'unmapped'))
        concerns=[{'topic':'respondent concern','evidence_ids':[evidence_id],
            'spontaneously_raised':True,'suggested_by_interviewer':False,
            'selected_priority':False,'explored':False}]
        message={'id':evidence_id,'role':'respondent','active':True,
            'evidence_status':'respondent_provided','text':case['evidence']}
        projected=project_concerns(concerns,[message],bank)['results'][0]
        candidate_ids=[m['indicator_id'] for m in projected['candidate_mappings']]
        projection_rows.append((case,candidate_ids,projected['status']))
        case_outputs.append({'case_id':case['id'],'exact_evidence':case['evidence'],
            'baseline_ids':lexical_ids,'projection':projected,
            'reference_ids':case['expected_indicator_ids'],
            'expected_unmapped':case['expected_unmapped'],
            'expected_ambiguous':case['expected_ambiguous'],
            'reference_rationale':case['rationale']})
    baseline=metrics(baseline_rows);revised=metrics(projection_rows)
    transcript_results=[]
    for value in args.transcript:
        path=Path(value).resolve();data=screened_export(json.loads(path.read_text()));conv=data['conversation']
        # Re-evaluate archived respondent evidence with the current projector;
        # historical JSON files remain untouched and are not assumed to have
        # contained this field when they were originally exported.
        active=[m for m in conv.get('messages',[]) if m.get('role')=='respondent'
            and m.get('active',True) and m.get('evidence_status')=='respondent_provided']
        projection=project_concerns(conv.get('concern_ledger',[]),active,bank)
        visible=[m.get('text','') for m in conv.get('messages',[]) if m.get('role')=='assistant']
        internal_leaks=[]
        leak_pattern=re.compile(r'\b(?:indicator-(?:0[1-9]|1[0-5])|citizen_(?:short|extended)-[1-9]|organisational-[1-9]|technical-[1-9]|evidence-\d+|m\d{1,5})\b',re.I)
        for index,text in enumerate(visible):
            if leak_pattern.search(text):internal_leaks.append({'assistant_message_index':index,'categories':['internal_reference']})
        transcript_results.append({'path':str(path),'profile':conv.get('profile'),'depth':conv.get('depth'),
            'stage':conv.get('stage'),'partial':conv.get('completion',{}).get('partial'),
            'projection':projection,'participant_internal_reference_leaks':internal_leaks})
    output={'schema_version':'iam-indicator-projection-evaluation-2.0.0',
        'benchmark_status':'synthetic challenge benchmark; exploratory labels are provisional and require IAM/FN expert review',
        'method':{'version':1,'type':'bounded definition-grounded concept rules',
            'llm_calls':0,'repeated_per_turn':False,'bank_version':bank.get('bank_version'),
            'bank_sha256':bank['bank_sha256']},
        'lexical_baseline':{'method':'existing top-three rank over official indicator names and full definitions',
            'metrics':{k:v for k,v in baseline.items() if k!='cases'},'cases':baseline['cases']},
        'revised_projection':{'metrics':{k:v for k,v in revised.items() if k!='cases'},'cases':revised['cases']},
        'case_details':case_outputs,'completed_transcripts':transcript_results,
        'limitations':['The rules are transparent semantic guards but remain phrase-dependent and do not replace expert interpretation.',
            'Synthetic reference mappings are provisional labels, not approved ground truth.',
            'No live Qwen projection was run; the A30 host has no unique idle GPU.',
            'Candidates are unreviewed concern mappings, not readiness statements or indicator scores.']}
    out.mkdir(parents=True)
    target=out/'indicator-projection-evaluation-v2.json';target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');target.chmod(0o600)
    print(json.dumps({'artifact':str(target),'baseline':output['lexical_baseline']['metrics'],
        'revised':output['revised_projection']['metrics'],'transcripts':len(transcript_results)},ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
