#!/usr/bin/env python3
"""Independently compare a reference replay with fixture-derived FN branches."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from iam_sra.fn_interview import specification
from iam_sra.fn_reference_audit import audit

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',choices=['citizen_short','citizen_extended'])
    parser.add_argument('export',type=Path)
    args=parser.parse_args()
    fixture=json.loads((ROOT/'eval/fn_golden_paths.json').read_text())
    data=json.loads(args.export.read_text())
    print(json.dumps(audit(args.case,data,fixture,specification()),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
