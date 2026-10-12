#!/usr/bin/env python3
"""Real local detector preflight. Only synthetic fixtures; no fixture text in output."""
import argparse
from importlib.metadata import version, PackageNotFoundError
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from iam_sra.privacy import VERSION, PrivacyError, require_clean
from iam_sra.readiness_retrieval import corpus

FIXTURES = [
    ('pin','My PIN is 1846.','block'),
    ('password','My password is synthetic-secret-xyz.','block'),
    ('card','My card number is 4111 1111 1111 1111.','block'),
    ('account','My bank account is 123456789012.','block'),
    ('email','Email me at alice@example.com.','preview'),
    ('phone','Call +1 202-555-0123.','preview'),
    ('name','I am Alice Example.','preview'),
    ('address','I live at 42 Example Street.','preview'),
    ('numbers','60 meters, 15 flights, year 2026, project 101271620.','allow'),
    ('places','The industrial park and central hospital.','allow'),
    ('caring','Evening meetings conflict with caring responsibilities.','allow'),
]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='.runtime/privacy-preflight.json');args=p.parse_args()
    report={'privacy_contract':VERSION,'fixture_origin':'synthetic','live_presidio_used':False,
            'status':'blocked','reason_codes':[],'cases':[],'dependencies':{}}
    for package in ('presidio-analyzer','spacy','en-core-web-sm'):
        try: report['dependencies'][package]=version(package)
        except PackageNotFoundError: report['dependencies'][package]=None
    for name,text,expected in FIXTURES:
        try: require_clean(text);actual='allow'
        except PrivacyError as exc:
            if exc.code=='privacy_unavailable':
                report['reason_codes'].append('privacy_resources_unavailable');break
            actual='preview' if exc.preview else 'block'
        report['cases'].append({'id':name,'expected':expected,'actual':actual,'passed':actual==expected})
    else:
        report['live_presidio_used']=True
        try: corpus();report['corpus_screened']=True
        except PrivacyError: report['corpus_screened']=False;report['reason_codes'].append('corpus_privacy_check_failed')
        report['status']='passed' if report['corpus_screened'] and all(c['passed'] for c in report['cases']) else 'failed'
    # This fixed structural preflight contains no submitted input, exception body,
    # mappings or hashes of secrets. It is not a citizen export or download.
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return 0 if report['status']=='passed' else 2
if __name__=='__main__':raise SystemExit(main())
