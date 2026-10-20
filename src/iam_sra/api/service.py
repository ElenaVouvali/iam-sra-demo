"""Bounded, single-process session/job service; one managed inference lane.

The existing clients acquire the global non-reentrant LLM transport lock. This
module never acquires it. Candidate controllers are private copies: expired,
cancelled or timed-out work cannot commit a late result to a live session.
"""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json
from queue import Queue, Empty, Full
import secrets
import threading
import time
from uuid import uuid4
from .adapter import ControllerAdapter
from .errors import APIError
from .schemas import ActionRequest, JobView
from ..assessment import AssessmentError
from ..privacy import PrivacyError, require_safe_data


@dataclass
class Record:
    id: str
    owner: str
    engine: object
    created: float
    touched: float
    view: dict
    version: int = 0
    generation: int = 0
    busy: str | None = None
    preview: dict | None = None
    retry: dict | None = None
    receipts: OrderedDict = field(default_factory=OrderedDict)


@dataclass
class Job:
    id: str
    session_id: str
    owner: str
    generation: int
    action: str
    data: dict
    candidate: object
    deadline: float
    created: float
    version: int
    status: str = 'queued'
    finished: float | None = None
    error: dict | None = None


class AssessmentService:
    def __init__(self, adapter=None, *, capacity=32, queue_size=8, session_ttl=3600,
                 session_max_age=14400, job_timeout=600, result_ttl=300,
                 result_capacity=128, clock=time.monotonic):
        self.adapter = adapter or ControllerAdapter()
        self.capacity = capacity
        self.session_ttl = session_ttl
        self.session_max_age = session_max_age
        self.job_timeout = job_timeout
        self.result_ttl = result_ttl
        self.result_capacity = result_capacity
        self.clock = clock
        self.records = {}
        self.jobs = OrderedDict()
        self.expired = OrderedDict()
        self.lock = threading.RLock()
        self.queue = Queue(maxsize=queue_size)
        self.stopped = threading.Event()
        self.worker = threading.Thread(target=self._work, name='iam-sra-inference', daemon=True)
        self.sweeper = threading.Thread(target=self._sweep, name='iam-sra-expiry', daemon=True)
        self.worker.start()
        self.sweeper.start()

    def close(self):
        self.stopped.set()
        with self.lock:
            for record in list(self.records.values()):
                self._invalidate(record)
            self.records.clear()
            for job in self.jobs.values():
                job.data = {}
                job.candidate = None
        # The transport's external deadline bounds requests. A stuck external
        # call cannot be killed safely in a thread; its lane stays occupied and
        # its result is fenced out until the process is shut down.

    def _sweep(self):
        while not self.stopped.wait(.5):
            with self.lock:
                self._prune()

    def _invalidate(self, record):
        record.generation += 1
        record.preview = None
        record.retry = None
        record.receipts.clear()
        if record.busy:
            job = self.jobs.get(record.busy)
            if job:
                job.status = 'cancelled'
                job.finished = self.clock()
                job.data = {}
                job.candidate = None
            record.busy = None

    def _prune(self):
        now = self.clock()
        for sid, record in list(self.records.items()):
            if now - record.touched >= self.session_ttl or now - record.created >= self.session_max_age:
                self._invalidate(record)
                self.expired[sid] = (record.owner, now)
                del self.records[sid]
        while len(self.expired) > self.capacity * 2:
            self.expired.popitem(last=False)
        for sid, (_, at) in list(self.expired.items()):
            if now - at > self.result_ttl:
                del self.expired[sid]
        for job in list(self.jobs.values()):
            if job.status in {'queued', 'running'} and now >= job.deadline:
                job.status = 'failed'
                job.error = APIError('timeout', 504).public()
                job.finished = now
                record = self.records.get(job.session_id)
                if record and record.busy == job.id:
                    record.busy = None
                    record.generation += 1
                    record.version += 1
                    job.version = record.version
                    record.view['version'] = record.version
                    record.preview = None
                job.data = {}
                job.candidate = None
            if job.finished is not None and now - job.finished >= self.result_ttl:
                self.jobs.pop(job.id, None)
        finished = [job for job in self.jobs.values() if job.finished is not None]
        for job in finished[:-self.result_capacity]:
            self.jobs.pop(job.id, None)

    def _record(self, sid, owner):
        self._prune()
        record = self.records.get(sid)
        if not record or record.owner != owner:
            if sid in self.expired and self.expired[sid][0] == owner:
                raise APIError('session_expired', 410)
            raise APIError('not_found', 404)
        record.touched = self.clock()
        return record

    def create(self, owner):
        # Readiness and privacy work take place outside the store lock.
        engine = self.adapter.create()
        sid = str(uuid4())
        view = self.adapter.present(engine, sid, 0)
        with self.lock:
            self._prune()
            if len(self.records) >= self.capacity:
                raise APIError('capacity', 503)
            now = self.clock()
            record = Record(sid, owner, engine, now, now, view)
            self.records[sid] = record
            return self._view(record)

    def owned_sessions(self, owner):
        with self.lock:
            self._prune()
            return [{'id': record.id, 'version': record.version, 'state': record.view['state']}
                    for record in self.records.values() if record.owner == owner]

    def _view(self, record):
        value = deepcopy(record.view)
        value.update(version=record.version, busy_job=record.busy,
                     preview=None if not record.preview else {
                         'id': record.preview['id'], 'action': record.preview['action'],
                         'fields': deepcopy(record.preview['data']),
                         'message': 'Private details were removed. Confirm this cleaned text only if it still says what you meant.'},
                     retry_draft=deepcopy(record.retry))
        if record.busy:
            value['allowed_actions'] = ['reset']
        elif record.preview:
            value['allowed_actions'] = list(dict.fromkeys(value['allowed_actions'] + ['confirm_cleaned', 'discard_preview']))
        return value

    def read(self, sid, owner):
        with self.lock:
            return self._view(self._record(sid, owner))

    @staticmethod
    def _binding(record):
        engine = record.engine
        return (record.generation, record.version, engine.state,
                (engine.current_question or {}).get('id'),
                (engine.pending or {}).get('id'), len(engine.information_exposures))

    @staticmethod
    def _fingerprint(action, data):
        # Called only AFTER input screening. No raw secret or rejected original
        # is hashed, retained in receipts, or copied into a queue entry.
        return sha256(json.dumps([action, data], sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def _receipt(self, record, key, fingerprint, result):
        record.receipts[key] = (fingerprint, deepcopy(result))
        while len(record.receipts) > 128:
            record.receipts.popitem(last=False)
        return result

    def submit(self, sid, owner, raw):
        try:
            request, data = ActionRequest.parse(raw)
        except (ValueError, TypeError):
            raise APIError('invalid_request') from None
        action = request.action
        key = str(request.request_id)
        submission_version = request.expected_version
        # Check ownership before screening someone else's request or spending NLP.
        with self.lock:
            record = self._record(sid, owner)
            if (record.preview and action not in {'confirm_cleaned', 'discard_preview'}
                    and key not in record.receipts and submission_version == record.version):
                # A new submission supersedes the prior cleaned draft even if
                # its screening then fails. Keep neither the unsafe replacement
                # nor a confirmation that now refers to the wrong intended text.
                record.preview = None
                record.version += 1
                submission_version = record.version
        cleaned, changed = self.adapter.prepare(action, data)
        fingerprint = self._fingerprint(action, cleaned)
        with self.lock:
            record = self._record(sid, owner)
            if key in record.receipts:
                previous, response = record.receipts[key]
                if previous != fingerprint:
                    raise APIError('duplicate_conflict', 409)
                previous_job = response[1].get('job_id')
                if previous_job and previous_job not in self.jobs:
                    return 200, {'session': self._view(record), 'duplicate': True, 'result_expired': True}
                return deepcopy(response)
            if submission_version != record.version:
                raise APIError('stale_action', 409)
            if record.busy and action != 'reset':
                raise APIError('session_busy', 409)
            allowed = self.adapter.allowed(record.engine)
            if action in {'confirm_cleaned', 'discard_preview'}:
                if not record.preview:
                    raise APIError('stale_action', 409)
            elif action not in allowed:
                raise APIError('invalid_action', 409)
            if action == 'confirm_cleaned':
                preview = record.preview
                if (not secrets.compare_digest(preview['id'], data['preview_id'])
                        or preview['binding'] != self._binding(record)):
                    raise APIError('stale_action', 409)
                action, cleaned = preview['action'], deepcopy(preview['data'])
                # Re-screen the cleaned operation rather than treating a token
                # as a privacy bypass. Confirmation cannot replace its payload.
                cleaned, changed_again = self.adapter.prepare(action, cleaned)
                if changed_again:
                    raise APIError('privacy', 422)
            elif action == 'discard_preview':
                record.preview = None
                record.version += 1
                return self._receipt(record, key, fingerprint, (200, {'session': self._view(record)}))
            self.adapter.validate_action(record.engine, action, cleaned)
            if changed:
                record.version += 1
                record.preview = {'id': secrets.token_hex(24), 'action': action,
                                  'data': cleaned, 'binding': self._binding(record)}
                return self._receipt(record, key, fingerprint, (200, {'session': self._view(record)}))
            if action == 'reset':
                # Factory/resource checks run without holding the shared store.
                pass
            else:
                return self._enqueue(record, action, cleaned, key, fingerprint)
        engine = self.adapter.create()
        new_view = self.adapter.present(engine, sid, 0)
        with self.lock:
            record = self._record(sid, owner)
            if record.version != submission_version:
                raise APIError('stale_action', 409)
            self._invalidate(record)
            record.version += 1
            record.engine, record.view = engine, new_view
            return self._receipt(record, key, fingerprint, (200, {'session': self._view(record)}))

    def _enqueue(self, record, action, cleaned, key, fingerprint):
        # Reserve before changing the revision. The queue has one controlled
        # worker; the HTTP threads never take the engine's LLM transport lock.
        if self.queue.full():
            raise APIError('queue_full', 429)
        if action in {'back', 'edit_answer', 'edit_context', 'correct_interpretation'}:
            self._invalidate(record)
        now = self.clock()
        job = Job(str(uuid4()), record.id, record.owner, record.generation,
                  action, deepcopy(cleaned), deepcopy(record.engine), now + self.job_timeout,
                  now, record.version + 1)
        try:
            self.queue.put_nowait(job.id)
        except Full:
            raise APIError('queue_full', 429) from None
        self.jobs[job.id] = job
        record.busy = job.id
        record.preview = None
        record.retry = None
        record.version += 1
        return self._receipt(record, key, fingerprint,
                             (202, {'job_id': job.id, 'session': self._view(record)}))

    def _work(self):
        while not self.stopped.is_set():
            try:
                jid = self.queue.get(timeout=.2)
            except Empty:
                continue
            try:
                with self.lock:
                    self._prune()
                    job = self.jobs.get(jid)
                    if not job or job.status != 'queued':
                        continue
                    record = self.records.get(job.session_id)
                    if not record or record.generation != job.generation:
                        continue
                    job.status = 'running'
                    candidate, data = job.candidate, deepcopy(job.data)
                failure = None
                returned = None
                try:
                    returned = self.adapter.apply(candidate, job.action, data, job.deadline)
                    view = self.adapter.present(candidate, job.session_id, job.version + 1)
                except APIError as exc:
                    failure = exc
                except PrivacyError as exc:
                    failure = APIError(exc.code, 503 if exc.code == 'privacy_unavailable' else 422)
                except AssessmentError as exc:
                    failure = APIError('timeout' if exc.code == 'timeout' else 'model_failure', 503)
                except Exception:
                    # No exception repr, traceback, model text or server address
                    # enters a response, retained job, access log or result.
                    failure = APIError('model_failure', 503)
                safe_failed_attempt = None
                if failure and job.action == 'answer' and candidate.failed_attempt:
                    try:
                        require_safe_data(candidate.failed_attempt)
                        safe_failed_attempt = deepcopy(candidate.failed_attempt)
                    except PrivacyError:
                        pass
                with self.lock:
                    self._prune()
                    record = self.records.get(job.session_id)
                    if (not record or record.generation != job.generation
                            or record.busy != job.id or job.status != 'running'):
                        continue
                    record.busy = None
                    record.version += 1
                    record.preview = None
                    if failure:
                        job.status, job.error = 'failed', failure.public()
                        if safe_failed_attempt:
                            record.engine.failed_attempt = safe_failed_attempt
                        if job.action in {'answer', 'correct_interpretation', 'ask_information'}:
                            record.retry = {'action': job.action, 'data': data}
                    else:
                        record.engine, record.view = candidate, view
                        record.view['returned_text'] = returned
                        record.retry = None
                        job.status = 'completed'
                    job.version = record.version
                    job.finished = self.clock()
                    job.data, job.candidate = {}, None
            finally:
                self.queue.task_done()

    def job(self, jid, owner):
        with self.lock:
            self._prune()
            job = self.jobs.get(jid)
            if not job or job.owner != owner:
                raise APIError('not_found', 404)
            record = self._record(job.session_id, owner)
            # A timeout remains observable as a failure; correction/reset results
            # are unavailable even when a previously issued job ID is replayed.
            timeout_current = ((job.error or {}).get('code') == 'timeout'
                               and record.generation == job.generation + 1
                               and record.version == job.version)
            if record.generation != job.generation and not timeout_current:
                raise APIError('job_obsolete', 410)
            return JobView(id=jid, session_id=job.session_id, status=job.status,
                           version=job.version, error=job.error).model_dump()

    def export(self, sid, owner):
        with self.lock:
            record = self._record(sid, owner)
            if record.busy:
                raise APIError('session_busy', 409)
            if record.engine.state != 'final':
                raise APIError('invalid_action', 409)
            candidate, generation = deepcopy(record.engine), record.generation
        value = self.adapter.export(candidate)
        with self.lock:
            record = self._record(sid, owner)
            if record.generation != generation or record.busy:
                raise APIError('stale_action', 409)
        return value

    def delete(self, sid, owner, expected_version):
        with self.lock:
            record = self._record(sid, owner)
            if record.version != expected_version:
                raise APIError('stale_action', 409)
            self._invalidate(record)
            self.expired[sid] = (owner, self.clock())
            del self.records[sid]
