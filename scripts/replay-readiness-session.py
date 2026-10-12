#!/usr/bin/env python3
"""Replay actual answers against the current instrument, respecting question context."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import httpx
from iam_sra.readiness_session import ReadinessSession
from iam_sra.readiness_client import ReadinessClient
from iam_sra.settings import BASE_URL


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--report-only', action='store_true', help='Generate an evidence report without model calls or replay.')
    p.add_argument('--output', default='.runtime/readiness-session-replay.json')
    p.add_argument('--base-url', default=BASE_URL)
    args = p.parse_args()
    raw = Path(args.input).read_text()
    try: original = json.loads(raw)
    except json.JSONDecodeError: original = json.loads(next(line for line in raw.splitlines() if line.strip()))
    if args.report_only:
        from iam_sra.readiness_report import markdown_report
        output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown_report(original))
        print(str(output)); return 0
    if original.get('assessment_mode') != 'acceptance_and_readiness_evidence':
        p.error('Input must be an evidence-mode session; historical scores are not readiness data.')
    events = [e for e in original['questions_and_answers'] if e['active']]
    initial = next(e for e in events if e['kind'] == 'initial')
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    report = {'original_session_id': original['session_id'], 'live_model_used': False,
              'semantic_accuracy_verified': False, 'confirmation_basis':'scripted automation, not citizen validation', 'replayed': [], 'not_replayed': []}
    started = time.monotonic()
    session = ReadinessSession(); client = ReadinessClient(base_url=args.base_url)
    try:
        with httpx.Client(timeout=10, trust_env=False) as http:
            response = http.get(args.base_url.rstrip('/') + '/v1/models'); response.raise_for_status()
        session.submit(initial['text'], client); session.confirm(True)
        report['replayed'].append(initial['id'])
        report['initial_output'] = session.export()
        for event in events:
            if event['kind'] != 'readiness_followup': continue
            if any(r.get('elicitation_context') == 'after_information_exposure' for r in event.get('records', [])) or any(e.get('version_at_exposure', float('inf')) < event['version'] for e in original.get('information_exposures', [])):
                report['not_replayed'].append({'event_id':event['id'], 'reason':'Original answer followed information exposure; exact exposure is not recreated by this replay.'})
                continue
            current = session.current_question
            # A denial to a participation question cannot answer an opportunity
            # question merely because it was the next saved response.
            if current is None or current['criterion_id'] != event['criterion_id'] or current['id'] != event['question']['id']:
                report['not_replayed'].append({'event_id': event['id'], 'reason': 'Current question has a different context; no answer invented.'})
                continue
            if event['control'] in {'skip', 'unsure'}: session.skip(event['control'] == 'unsure')
            else:
                session.respond(event['text'], client); session.confirm(True)
            report['replayed'].append(event['id'])
        report['next_question'] = session.current_question
        session.finish('user_finish')
        report.update(status='completed', actual_output=session.export())
    except Exception as exc:
        report.update(status='failed' if session.inference else 'blocked', error=str(exc))
    report['live_model_used'] = any(i.get('raw_model_trace') for i in session.inference)
    report['latency_seconds'] = round(time.monotonic() - started, 3)
    if 'actual_output' not in report: report['partial_output'] = session.export()
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k:report.get(k) for k in ['status','live_model_used','replayed','not_replayed','next_question','error']}, ensure_ascii=False))
    return 0 if report['status'] == 'completed' else 2


if __name__ == '__main__': raise SystemExit(main())
