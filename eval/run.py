#!/usr/bin/env python3
"""Compatibility entry point for offline CI; validates current flows with doubles."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--repeats', type=int, default=1)
    args = parser.parse_args()
    if not args.mock:
        parser.error('Use scripts/smoke-baseline.py or scripts/smoke-readiness-evidence.py for live evaluation.')
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    root = Path(__file__).resolve().parents[1]
    print('Offline flow verification with synthetic model/detector doubles; not model accuracy.', flush=True)
    for _ in range(args.repeats):
        result = subprocess.run([sys.executable, '-m', 'pytest', '-q',
            'tests/test_baseline_v2.py', 'tests/test_readiness_evidence_mode.py',
            'tests/test_readiness_score.py'], cwd=root)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
