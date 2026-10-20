"""Public errors never carry exception strings, transport bodies or addresses."""
MESSAGES = {
    'invalid_request': 'Check the submitted fields and try again.',
    'invalid_action': 'This action is not available at the current step. Refresh the interview.',
    'stale_action': 'The interview has changed. Review its current step before submitting again.',
    'duplicate_conflict': 'This retry identifier was already used for another action.',
    'session_busy': 'An action is already processing. Wait for it, or deliberately reset the interview.',
    'session_expired': 'This interview has expired. Start a new interview.',
    'not_found': 'The requested interview or job is not available.',
    'job_obsolete': 'This result is no longer current after a correction, reset or expiry.',
    'capacity': 'The service is at capacity. Try again shortly.',
    'queue_full': 'The assessment queue is full. Your answer was not queued; try again shortly.',
    'privacy': 'Private or sensitive content was withheld. Remove identifying details and retry.',
    'privacy_unavailable': 'Local privacy resources are unavailable. Ask the operator to run the privacy preflight before starting.',
    'source_unavailable': 'The reviewed source corpus is unavailable or out of date. Ask the operator to rebuild and verify it on the trusted host.',
    'timeout': 'The processing time limit was reached. Review the current step and retry; no late result will be applied.',
    'model_failure': 'Assessment could not complete. Your confirmed evidence is unchanged. You may retry this step.',
    'csrf': 'The browser security check failed. Refresh this page and try again.',
    'origin': 'This request did not come from a configured application origin.',
    'deployment': 'The API requires one process with threaded requests. Ask the operator to check its deployment configuration.',
}


class APIError(Exception):
    def __init__(self, code, status=400):
        self.code = code
        self.status = status
        super().__init__(code)

    def public(self):
        return {'code': self.code, 'message': MESSAGES.get(self.code, MESSAGES['model_failure']),
                'retryable': self.code in {'queue_full', 'capacity', 'timeout', 'model_failure', 'session_busy'}}
