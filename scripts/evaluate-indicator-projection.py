#!/usr/bin/env python3
"""Offline lexical baseline for concern-to-indicator candidates and saved transcripts."""
import argparse, json, os, sys
from pathlib import Path


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--transcript',action='append',default=[],help='Completed screened synthetic export; repeat as needed.')
    p.add_argument('--output',required=True)
    p.add_argument('--limit',type=int,default=3)
    args=p.parse_args(argv)
    if not 1<=args.limit<=5:p.error('--limit must be 1–5.')
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    if not out.is_relative_to((root/'.runtime').resolve()) or out.exists():p.error('Use a new output directory under ignored .runtime/.')
    sys.path.insert(0,str(root/'src'))
    from iam_sra.readiness_bank import load_bank
    from iam_sra.conversation_corpus import rank
    from iam_sra.privacy import screened_export
    bank=load_bank()
    cases=json.loads((root/'eval/iam_indicator_concern_cases_v1.json').read_text())['cases']
    # Use only the official indicator name and definition. This deliberately
    # simple retrieval baseline is for review, not an approved classifier.
    records=[{'id':row['id'],'search_text':row['name']+' '+row['definition']} for row in bank['indicators']]
    case_results=[];tp=fp=fn=0;unmapped_total=unmapped_correct=0;multi_total=multi_hits=0
    for case in cases:
        ranked=rank(case['evidence'],records,args.limit)
        candidates=[row for row in ranked if row['retrieval_score']>0]
        predicted={row['id'] for row in candidates};expected=set(case['expected_indicator_ids'])
        tp+=len(predicted&expected);fp+=len(predicted-expected);fn+=len(expected-predicted)
        if len(expected)>1:multi_total+=1;multi_hits+=int(bool(predicted&expected))
        if case['expected_unmapped']:
            unmapped_total+=1;unmapped_correct+=int(not predicted)
        case_results.append({'case_id':case['id'],'fictional_evidence_id':'fixture:'+case['id'],
            'exact_evidence':case['evidence'],'expected_indicator_ids':sorted(expected),
            'expected_unmapped':case['expected_unmapped'],'mapping_rationale':case['rationale'],
            'candidate_mappings':[{'indicator_id':r['id'],
                'retrieval_score':r['retrieval_score'],'evidence_id':'fixture:'+case['id'],
                'evidence_quote':case['evidence'],'status':'unreviewed_candidate'} for r in candidates],
            'false_positive_ids':sorted(predicted-expected),'missed_expected_ids':sorted(expected-predicted)})
    transcript_results=[]
    for raw in args.transcript:
        path=Path(raw).resolve();data=screened_export(json.loads(path.read_text()))
        conv=data['conversation'];messages={m['id']:m for m in conv.get('messages',[]) if m.get('role')=='respondent' and m.get('active',True)}
        mapped_by_evidence={}
        for ann in conv.get('annotations',[]):
            mapped_by_evidence.setdefault(ann['evidence_id'],set()).update(ann.get('indicator_ids',[]))
        rows=[]
        for concern in conv.get('concern_ledger',[]):
            evidence=[]
            for eid in concern.get('evidence_ids',[]):
                msg=messages.get(eid)
                if msg and msg.get('evidence_status')=='respondent_provided':
                    ids=sorted(mapped_by_evidence.get(eid,set())|set(concern.get('indicator_ids',[])))
                    evidence.append({'evidence_id':eid,'quote':msg['text'],'candidate_indicator_ids':ids,
                                     'mapping_status':'unreviewed_candidate' if ids else 'unmapped_by_current_chat'})
            if evidence:
                rows.append({'topic':concern.get('topic'),'spontaneously_raised':concern.get('spontaneously_raised'),
                    'suggested_by_interviewer':concern.get('suggested_by_interviewer'),
                    'selected_priority':concern.get('selected_priority'),'evidence':evidence})
        transcript_results.append({'path':str(path),'profile':conv.get('profile'),'depth':conv.get('depth'),
            'stage':conv.get('stage'),'partial':conv.get('completion',{}).get('partial'),
            'concerns_with_evidence':rows,'qwen_candidate_mapping_count':sum(
                bool(e['candidate_indicator_ids']) for row in rows for e in row['evidence']),
            'interpretation':'Existing per-turn Qwen annotations were inspected as saved; this evaluator does not call a model.'})
    precision=tp/(tp+fp) if tp+fp else None;recall=tp/(tp+fn) if tp+fn else None
    output={'schema_version':'iam-indicator-projection-eval-1.0.0','benchmark_status':'offline lexical candidate retrieval; not a semantic assessor or validated mapping model',
        'bank_version':bank.get('version'),'bank_sha256':bank['bank_sha256'],
        'candidate_limit':args.limit,'metrics':{'case_count':len(cases),'tp':tp,'fp':fp,'fn':fn,
            'precision':precision,'recall':recall,'f1':(2*precision*recall/(precision+recall)) if precision and recall else 0.0,
            'unmapped_cases':unmapped_total,'correctly_unmapped':unmapped_correct,
            'multi_indicator_cases':multi_total,'multi_indicator_cases_with_any_expected_hit':multi_hits},
        'cases':case_results,'completed_transcripts':transcript_results,
        'limitations':['Lexical ranking can miss paraphrases and over-map shared terms; all candidates remain unreviewed.',
            'Expected mappings are evaluation labels based on official indicator wording and require FN/IAM methodological review.',
            'The animal-wildlife unmapped case tests that the system can preserve a real concern without forcing a v4 indicator.',
            'This is not a 15-indicator assessment, readiness score or SRL synthesis.']}
    # Every benchmark query passed require_clean through rank(); transcript
    # exports passed screened_export() before their evidence was copied here.
    # Do not rescan the combined bundle: concatenated approved quotes can trip
    # cross-field NER heuristics even though each source record passed.
    out.mkdir(parents=True)
    target=out/'indicator-projection-evaluation.json';target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');target.chmod(0o600)
    summary={'metrics':output['metrics'],'artifact':str(target),'transcripts':len(transcript_results)}
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
