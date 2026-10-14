#!/usr/bin/env python3
"""Run isolated synthetic respondents through the IAM-SRA2 controller."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--persona',action='append',help='Persona ID; repeat to select a small smoke suite.')
    parser.add_argument('--all',action='store_true',help='Run all 18 personas.')
    parser.add_argument('--repetitions',type=int,default=1)
    parser.add_argument('--seeds',type=int,nargs='+',default=[11])
    parser.add_argument('--backend',choices=('scripted','llm'),default='scripted')
    parser.add_argument('--live',action='store_true',help='Use the existing model endpoint for answers, interpretation and planning.')
    parser.add_argument('--base-url',default=os.environ.get('IAM_BASE_URL','http://127.0.0.1:18000'))
    parser.add_argument('--policy-version',choices=('1.1','1.2'),default='1.2')
    parser.add_argument('--output',type=Path,default=Path('.runtime/synthetic-evaluation'))
    args=parser.parse_args()
    if args.backend=='llm' and not args.live:parser.error('The LLM respondent requires --live.')
    if args.all and args.persona:parser.error('Use --all or --persona, not both.')
    if args.live:
        import httpx
        try:
            with httpx.Client(timeout=2,trust_env=False) as client:
                client.get(args.base_url.rstrip('/')+'/health').raise_for_status()
                models=client.get(args.base_url.rstrip('/')+'/v1/models');models.raise_for_status()
                if not any(m.get('id')=='Qwen/Qwen3-8B' for m in models.json().get('data',[])):
                    parser.error('The existing endpoint does not advertise Qwen/Qwen3-8B; no service was changed.')
        except Exception as exc:parser.error(f'Model service health check failed; no service was changed ({type(exc).__name__}).')
        os.environ['IAM_BASE_URL']=args.base_url
    from iam_sra.synthetic_runner import run_evaluation
    from iam_sra.synthetic_respondent import load_personas
    persona_ids=args.persona or (None if args.all else [p['persona_id'] for p in load_personas()['personas'][:2]])
    try:
        result=run_evaluation(args.output,persona_ids,args.repetitions,args.seeds,args.backend,
            offline=not args.live,policy_version=args.policy_version,synthetic_fixture=not args.live)
    except (OSError,ValueError,RuntimeError) as exc:parser.error(str(exc))
    print(json.dumps({'runs':result['runs'],'completed_runs':result['completed_runs'],
        'failed_runs':result['failed_runs'],'output':str(args.output),'semantic_accuracy':None}))
    return 0 if result['failed_runs']==0 else 2


if __name__=='__main__':raise SystemExit(main())
