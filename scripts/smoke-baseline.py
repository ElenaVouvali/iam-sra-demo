#!/usr/bin/env python3
"""Run versioned synthetic baseline journeys; semantic review remains explicit."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from iam_sra.baseline_benchmark import load_bank, report, write_report
from iam_sra.baseline_client import BaselineClient, MockBaselineClient
from iam_sra.settings import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mock',action='store_true',help='Empty extraction fixture; not model accuracy. Privacy screening remains active.')
    parser.add_argument('--benchmark',type=Path,default=ROOT/'eval/benchmarks/baseline_adaptive_v3.json')
    parser.add_argument('--case',action='append',help='Run a case ID; repeat to select several.')
    parser.add_argument('--output',type=Path,default=ROOT/'.runtime/baseline-adaptive-benchmark.json')
    parser.add_argument('--cpu',action='store_true',help='Pinned local model, CPU-only Transformers/XGrammar; no GPU service.')
    parser.add_argument('--cpu-threads',type=int,default=4)
    parser.add_argument('--cpu-generation-seconds',type=int,default=300)
    args=parser.parse_args()
    if args.cpu and args.mock:parser.error('--cpu and --mock are mutually exclusive')
    runtime=None
    if args.cpu:
        # Reuse locally installed privacy resources without changing either environment.
        import importlib.util, site
        if importlib.util.find_spec('presidio_analyzer') is None:
            resources=ROOT/'.venv-privacy/lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
            if resources.is_dir():site.addsitedir(str(resources))
        from iam_sra.cpu_benchmark import CPURuntime, CPUBaselineClient
        try:runtime=CPURuntime(args.cpu_threads,args.cpu_generation_seconds)
        except ValueError as exc:parser.error(str(exc))
    try: bank=load_bank(args.benchmark)
    except (OSError,ValueError,KeyError) as exc:parser.error(str(exc))
    cases=bank['cases']
    if args.case:
        unknown=set(args.case)-{c['id'] for c in cases}
        if unknown:parser.error('Unknown case IDs: '+', '.join(sorted(unknown)))
        cases=[c for c in cases if c['id'] in args.case]
    def progress(status,case_id):
        print(json.dumps({'case':case_id,'execution':status}),flush=True)
    data=report(bank,args.benchmark,cases,(lambda: CPUBaselineClient(runtime)) if runtime else MockBaselineClient if args.mock else BaselineClient,mock=args.mock,progress=progress)
    if runtime:
        data['provenance']['runtime']=runtime.metadata()
        data['provenance']['model_mode']='cpu_local'
    data=write_report(data,args.output)
    print(json.dumps({'execution_status':data['execution_status'],'semantic_pass':None,
        'semantic_review_status':'pending','artifact_status':data['artifact_status'],'output':str(args.output),
        'cases':[{'id':r['case_id'],'execution':r['execution_status'],'routing_pass':r['routing_pass'],
                  'invariants_pass':r['invariants_pass'],'artifact_status':r['artifact_status'],
                  'export_error_code':r.get('export_error_code')} for r in data['cases']]}))
    return 0 if data['execution_status']=='completed' and data['artifact_status']=='complete' and all(r['routing_pass'] and r['invariants_pass'] for r in data['cases']) else 2


if __name__=='__main__':raise SystemExit(main())
