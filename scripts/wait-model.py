#!/usr/bin/env python3
"""Bounded model readiness check; no service changes or response-body logging."""
import argparse
import os
import time
from urllib.parse import urlsplit

import httpx


def project_local_endpoint(base, port):
    try:
        value = urlsplit(base)
        return (value.scheme == 'http' and value.hostname in {'127.0.0.1', 'localhost'}
                and value.port == port and value.username is None and value.password is None
                and value.path in {'', '/'} and not value.query and not value.fragment)
    except ValueError:
        return False


def ready(client, base, deadline, clock=time.monotonic):
    try:
        for path in ('/health', '/v1/models'):
            remaining = deadline - clock()
            if remaining <= 0:
                return False
            response = client.get(base.rstrip('/') + path, timeout=min(5, remaining))
            response.raise_for_status()
        models = response.json().get('data', [])
        return isinstance(models, list) and any(isinstance(row, dict)
            and row.get('id') == 'Qwen/Qwen3-8B' for row in models)
    except (httpx.HTTPError, ValueError, AttributeError, TypeError):
        return False


def wait(client, base, timeout=180, *, clock=time.monotonic, sleep=time.sleep):
    started = clock()
    deadline = started + timeout
    announce_at = started
    while clock() < deadline:
        if ready(client, base, deadline, clock):
            print('Qwen/Qwen3-8B is ready. Retry your retained answer in the UI.', flush=True)
            return True
        current = clock()
        if current >= announce_at:
            print(f'Waiting for model loading: {int(current - started)}s elapsed.', flush=True)
            announce_at = current + 15
        if current < deadline:
            sleep(min(2, deadline - current))
    print('Model readiness timed out. Inspect: tail -n 60 .runtime/vllm.log', flush=True)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--check-local-only', action='store_true',
                        help='Validate the endpoint before any project recovery action.')
    args = parser.parse_args()
    if not 1 <= args.timeout <= 600:
        parser.error('--timeout must be between 1 and 600 seconds')
    port = int(os.getenv('IAM_VLLM_PORT', '8000'))
    base = os.getenv('IAM_BASE_URL', f'http://127.0.0.1:{port}').rstrip('/')
    if args.check_local_only:
        if project_local_endpoint(base, port):
            return 0
        print('The configured endpoint is not this project’s local model endpoint. '
              'No process was stopped. Run scripts/diagnose-model.py.')
        return 1
    with httpx.Client(trust_env=False, follow_redirects=False) as client:
        return 0 if wait(client, base, args.timeout) else 1


if __name__ == '__main__':
    raise SystemExit(main())
