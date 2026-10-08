"""Collect separate live development and validation reports; never rewrite prompts or targets."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    stages=[
        ('development-mapping',['--mapping-only','--split','development','--check-followups']),
        ('privacy-mapping',['--mapping-only','--case-file','manual-tests/privacy-mapping-cases.json']),
        ('development-scores',['--split','development','--check-followups']),
        ('validation',['--split','fresh_validation','--check-followups']),
    ]
    results=[]
    for name,args in stages:
        output=ROOT/'.runtime'/('calibration-'+name+'.json')
        print('Running '+name,flush=True)
        status=subprocess.run([sys.executable,str(ROOT/'scripts/run-initial-manual-tests.py'),
            *args,'--output',str(output)],cwd=ROOT).returncode
        results.append({'stage':name,'exit_code':status,'report':str(output)})
        summary=ROOT/'.runtime/calibration-summary.json'
        summary.write_text(json.dumps({'stages':results,
            'complete':len(results)==len(stages),
            'all_passed':len(results)==len(stages) and all(r['exit_code']==0 for r in results),
            'notice':'Authored experimental targets, not validated SRL ground truth. Validation results are separate; do not tune to them.'},indent=2)+'\n')
        if status not in (0,1):
            print('Stopped: live runner unavailable or invalid configuration. See '+str(output),flush=True)
            return status
    print('Reports: '+str(ROOT/'.runtime/calibration-summary.json'),flush=True)
    return 0 if all(r['exit_code']==0 for r in results) else 1


if __name__=='__main__':raise SystemExit(main())
