#!/usr/bin/env python3
"""Replay CRL, ORL or TRL scoring on screened completed synthetic exports."""
import argparse, json, os, re, sys, time
from pathlib import Path


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',action='append',required=True,help='Completed screened session JSON for any profile; repeat for each case.')
    p.add_argument('--base-url',default='http://127.0.0.1:18005')
    p.add_argument('--output',required=True)
    args=p.parse_args(argv)
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    if not out.is_relative_to((root/'.runtime').resolve()) or out.exists():p.error('Use a new output directory under ignored .runtime/.')
    sys.path.insert(0,str(root/'src'))
    from iam_sra.privacy import screened_export
    from iam_sra.chat_policy import rubric
    from iam_sra.readiness_bank import load_bank
    from iam_sra.chat_score import ChatScoreClient, validate_profile_match
    from iam_sra.chat_session import score_evidence_mode
    from iam_sra.chat_session import participant_score_text
    from iam_sra.assessment import AssessmentError
    import httpx
    from urllib.parse import urlsplit
    base=args.base_url.rstrip('/')
    origin=urlsplit(base)
    if origin.hostname not in {'127.0.0.1','localhost'}:p.error('Scoring replay is restricted to the existing local endpoint.')
    with httpx.Client(trust_env=False,timeout=10) as client:
        response=client.get(base+'/v1/models');response.raise_for_status()
        from iam_sra.settings import MODEL
        if not any(row['id']==MODEL for row in response.json().get('data',[])):p.error('Expected Qwen model is not loaded.')
    import importlib.util
    spec=importlib.util.spec_from_file_location('smoke_fn_interview',root/'scripts/smoke-fn-interview.py')
    harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(harness)
    harness.require_unmanaged_endpoint(root)
    out.mkdir(parents=True);bank=load_bank();results=[]
    for raw_path in args.input:
        path=Path(raw_path).resolve()
        if not path.is_file():p.error(f'Input export not found: {path}')
        data=screened_export(json.loads(path.read_text()))
        conversation=data['conversation'];profile=conversation.get('profile');depth=conversation.get('depth') or 'short'
        if profile not in {'citizen','organisational','technical'} or depth not in {'short','extended'}:
            p.error(f'Not a supported CRL/ORL/TRL export: {path}')
        if profile!='citizen':depth='short'
        scale=rubric(bank,profile,depth)
        originals=[{'id':m['id'],'text':m['text'],'objective':m.get('objective_id'),
                    'evidence_mode':score_evidence_mode(m.get('objective_id')),
                    'information_exposure_ids':m.get('information_exposure_ids',[])}
                   for m in conversation['messages'] if m.get('role')=='respondent' and m.get('active')
                   and m.get('evidence_status')=='respondent_provided']
        payload={'profile':profile,'scope':conversation.get('context',{}),'anchors':scale['anchors'],
                 'guidance':scale['guidance'],'originals':originals,
                 'supplied_information':conversation.get('information_exposures',[]),
                 'exploration_gaps':conversation.get('fn_interview',{}).get('unresolved_gaps',[]),
                 'partial_interview':conversation.get('completion',{}).get('partial',True)}
        client=ChatScoreClient(base_url=base);started=time.monotonic();status='unavailable';value=None;error=None
        try:
            value=client.match_profile(payload)
            value=validate_profile_match(value,payload)
            value['explanation']=participant_score_text(value.get('explanation'))
            value['boundary']=participant_score_text(value.get('boundary'))
            status='suggested' if value.get('selected_anchor_id') else 'abstained'
        except (AssessmentError,httpx.HTTPError,ValueError) as exc:
            error={'code':getattr(exc,'code','model_transport'),'field':getattr(exc,'field',None),
                   'message':str(exc),'retry_diagnostics':getattr(client,'last_diagnostics',[])}
            findings=getattr(exc,'findings',[])
            if findings:
                error['privacy_findings']=[{'entity_type':row.get('entity_type'),
                    'field_path':row.get('field_path','root')} for row in findings]
        # Different stakeholder exports commonly share `technical.json` or
        # `citizen_short.json`; include the containing case directory so one
        # replay can never overwrite another case's result.
        key=re.sub(r'[^A-Za-z0-9_.-]+','_',path.parent.name+'_'+path.stem)
        code={'citizen':'CRL','organisational':'ORL','technical':'TRL'}[profile]
        result={'input':str(path),'session_id':data.get('session_id'),'profile':profile,'profile_scale':code,'depth':depth,
            'input_completion':conversation.get('completion'),'original_evidence_count':len(originals),
            'original_evidence_ids':[row['id'] for row in originals],
            'input_score_status':(conversation.get('suggestion') or {}).get('status'),
            'input_score_level':(conversation.get('suggestion') or {}).get('level'),
            'replay_status':status,'replayed_fields':value,
            'model_fields_before_validation':client.last_score_diagnostics,
            'validation_error':error,'generation_metrics':client.last_metrics,
            'generation_diagnostics':client.last_diagnostics,
            'thinking_enabled':client.last_settings.get('enable_thinking'),
            'elapsed_seconds':round(time.monotonic()-started,3),
            'reasoning_retention':'discarded; only final structured answer fields retained'}
        target=out/(key+'-score-replay.json');target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');target.chmod(0o600)
        results.append({'case':key,'profile_scale':code,'status':status,'selected_anchor_id':(value or {}).get('selected_anchor_id'),
            'alternative_anchor_id':(value or {}).get('alternative_anchor_id'),
            'validation_field':(error or {}).get('field'),'seconds':result['elapsed_seconds'],
            'artifact':str(target)})
        print(json.dumps(results[-1],ensure_ascii=False),flush=True)
    summary=out/'metrics.json';summary.write_text(json.dumps({'schema_version':'iam-sra-score-replay-1.0.0',
        'model_expected':MODEL,'base_url':base,'cases':results},ensure_ascii=False,indent=2)+'\n');summary.chmod(0o600)
    return 0


if __name__=='__main__':raise SystemExit(main())
