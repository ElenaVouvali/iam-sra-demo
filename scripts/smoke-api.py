#!/usr/bin/env python3
"""Verify deployed API transport with synthetic text and real privacy/corpus gates.

This short decline-path journey makes no model requests. It is not semantic
validation. --base-url may include the tool prefix once the real donor proxy is
available, e.g. http://127.0.0.1:5001/api/sra-assessment/.
"""
import argparse
import json
import time
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8001/')
    args = parser.parse_args()
    view = None
    csrf = None
    stage = 'capabilities'
    try:
        with httpx.Client(base_url=args.base_url.rstrip('/') + '/', timeout=30,
                          trust_env=False, follow_redirects=False) as client:
            def call(method, path, *, status=200, **kwargs):
                response = client.request(method, path, **kwargs)
                if response.status_code != status:
                    # Never print response bodies, exception URLs or credentials.
                    raise RuntimeError(stage + ': unexpected HTTP status ' + str(response.status_code))
                if response.headers.get('cache-control') != 'no-store':
                    raise RuntimeError('Missing no-store response header')
                return response

            bootstrap = call('GET', 'v1/capabilities')
            capabilities = bootstrap.json()
            if capabilities['synthetic_fixture'] or not capabilities['readiness']['ready']:
                raise RuntimeError('Real privacy and corpus readiness required')
            cookie = bootstrap.headers.get('set-cookie', '')
            if 'HttpOnly' not in cookie or 'SameSite=Strict' not in cookie:
                raise RuntimeError('Owner-cookie attributes missing')
            csrf = capabilities['csrf_token']
            headers = {'X-CSRF-Token': csrf}
            stage = 'health and ownership'
            call('GET', 'v1/health')
            call('POST', 'v1/sessions', status=403, json={})
            view = call('POST', 'v1/sessions', status=201, json={}, headers=headers).json()['session']
            path = 'v1/sessions/' + view['id']
            with httpx.Client(base_url=client.base_url, trust_env=False) as other:
                other.get('v1/capabilities').raise_for_status()
                if other.get(path).status_code != 404:
                    raise RuntimeError('Owner isolation failed')

            def action(name, data=None):
                nonlocal view, stage
                stage = name
                payload = {'action': name, 'data': data or {},
                           'expected_version': view['version'], 'request_id': str(uuid4())}
                response = call('POST', path + '/actions', status=202, json=payload, headers=headers).json()
                view = response['session']
                deadline = time.monotonic() + 650
                while time.monotonic() < deadline:
                    job = call('GET', 'v1/jobs/' + response['job_id']).json()['job']
                    if job['status'] == 'completed':
                        view = call('GET', path).json()['session']
                        return
                    if job['status'] in {'failed', 'cancelled'}:
                        raise RuntimeError('Action failed: ' + (job.get('error') or {}).get('code', 'cancelled'))
                    time.sleep(.25)
                raise RuntimeError('Job polling deadline exceeded')

            action('set_context', {'perspective': 'personal', 'role': 'citizen', 'city': 'madrid'})
            action('finish')
            action('confirm_general')
            if view['state'] == 'offer':
                action('decline_scenario')
            action('confirm_final')
            if view['results'] != dict(crl=None, trl=None, orl=None, srl=None, provisional_citizen_estimate=None):
                raise RuntimeError('Unexpected score in empty-evidence journey')
            for format in ('json', 'jsonl'):
                stage = 'export ' + format
                response = call('GET', path + '/export', params={'format': format})
                if 'attachment;' not in response.headers.get('content-disposition', ''):
                    raise RuntimeError('Export attachment header missing')
                if json.loads(response.content)['export_profile'] != 'browser_evidence':
                    raise RuntimeError('Unexpected export profile')
            stage = 'end session'
            call('DELETE', path, status=204,
                 headers={**headers, 'X-Session-Version': str(view['version'])})
            view = None
            print('PASS: real privacy/corpus; HTTP cookies, CSRF, ownership, jobs, decline/final flow, null scores and JSON/JSONL exports. No model requests.')
        return 0
    except (httpx.HTTPError, ValueError, KeyError, RuntimeError) as exc:
        print('FAIL: ' + (str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__))
        return 1
    finally:
        # Best effort cleanup after a failed run; no credentials are written out.
        if view and csrf:
            try:
                with httpx.Client(base_url=args.base_url.rstrip('/') + '/', trust_env=False, timeout=5) as cleanup:
                    cleanup.cookies.update(client.cookies)
                    path = 'v1/sessions/' + view['id']
                    current = cleanup.get(path).json()['session']
                    cleanup.delete(path, headers={'X-CSRF-Token': csrf, 'X-Session-Version': str(current['version'])})
            except Exception:
                pass


if __name__ == '__main__':
    raise SystemExit(main())
