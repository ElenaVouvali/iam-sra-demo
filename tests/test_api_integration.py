"""Explicit synthetic API journeys, not live model or detector validation."""
from copy import deepcopy
import json
import threading
import time
from uuid import uuid4
import pytest

pytest.importorskip('flask', reason='Install the separate requirements-api.txt to test the API')
from iam_sra.api import create_app
from iam_sra.api.adapter import ControllerAdapter, information
from iam_sra.api.service import AssessmentService
from iam_sra.api.errors import APIError
from iam_sra.assessment import AssessmentError
from iam_sra.baseline_client import MockBaselineClient
from iam_sra.conversation_session import ConversationSession
from iam_sra.conversation_benchmark import FixtureClient, FixtureComposer, load_cases, resolve
from iam_sra.synthetic_runner import synthetic_collection
from iam_sra.settings import ROOT
from iam_sra.privacy import PrivacyError


class Browser:
    def __init__(self, app):
        self.client = app.test_client()
        bootstrap = self.client.get('/v1/capabilities')
        assert bootstrap.status_code == 200, bootstrap.json
        self.csrf = bootstrap.json['csrf_token']
        self.capabilities = bootstrap.json
        self.view = None

    def new(self):
        response = self.client.post('/v1/sessions', json={}, headers={'X-CSRF-Token': self.csrf})
        assert response.status_code == 201, response.json
        self.view = response.json['session']
        return self.view

    def read(self):
        response = self.client.get('/v1/sessions/' + self.view['id'])
        assert response.status_code == 200, response.json
        self.view = response.json['session']
        return self.view

    def submit(self, action, data=None, *, version=None, request_id=None):
        return self.client.post('/v1/sessions/' + self.view['id'] + '/actions',
            json={'action': action, 'data': data or {}, 'expected_version': self.view['version'] if version is None else version,
                  'request_id': request_id or str(uuid4())}, headers={'X-CSRF-Token': self.csrf})

    def act(self, action, data=None, *, allow_failure=False):
        response = self.submit(action, data)
        assert response.status_code in {200, 202}, response.json
        self.view = response.json['session']
        if response.status_code == 202:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                result = self.client.get('/v1/jobs/' + response.json['job_id'])
                assert result.status_code == 200, result.json
                if result.json['job']['status'] in {'completed', 'failed'}:
                    if not allow_failure:
                        assert result.json['job']['status'] == 'completed', result.json
                    self.read()
                    return result.json['job']
                time.sleep(.005)
            raise AssertionError('Synthetic job did not finish')
        return response.json


@pytest.fixture
def make_api():
    managers = []

    def make(case=None, *, clients=None, engine=None, **limits):
        if clients is None:
            clients = lambda e: {'baseline': FixtureClient(case) if case else MockBaselineClient(),
                                 'planner': None, 'information': FixtureComposer(), 'score': MockScore()}
        adapter = ControllerAdapter(
            engine_factory=engine or (lambda: ConversationSession(synthetic_collection())),
            clients_factory=clients, readiness=lambda: {'privacy': 'synthetic-detector-fixture', 'corpus': 'synthetic-corpus-fixture'})
        manager = AssessmentService(adapter, **limits)
        managers.append(manager)
        app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret-not-for-deployment-00000000'}, service=manager)
        return app, manager

    yield make
    for manager in managers:
        manager.close()


class MockScore:
    def assign(self, payload):
        from iam_sra.citizen_score import empty_assessment
        return empty_assessment('Synthetic fixture abstains; no positive anchor assessment.')


def start(browser, perspective='personal'):
    browser.new()
    browser.act('set_context', {'perspective': perspective, 'role': 'citizen', 'city': 'madrid'})
    return browser


def conclude_general(browser):
    if browser.view['state'].endswith('_review') and browser.view['pending']:
        browser.act('confirm_answer')
    browser.act('finish')
    browser.act('confirm_general')


def finish_declined(browser):
    conclude_general(browser)
    if browser.view['state'] == 'offer':
        browser.act('decline_scenario')
    browser.act('confirm_final')


def test_complete_synthetic_interview_information_and_exports(make_api):
    case = load_cases(ROOT/'eval/conversation_meeting_cases_v2.json')['cases'][0]
    app, service = make_api(case)
    browser = Browser(app)
    browser.new()
    browser.act('set_context', case['context'])
    saw_information = False
    saw_review = False
    saw_reflection = False
    for _ in range(60):
        state = browser.view['state']
        if state.endswith('_interview'):
            if browser.view['stage'] == 'scenario' and not saw_information:
                browser.act('ask_information', {'question': case['information_question']})
                exposure = browser.view['information'][-1]
                assert exposure['content']['excerpts']
                browser.act('acknowledge', {'exposure_id': exposure['id']})
                assert browser.view['information'][-1]['acknowledged']
                saw_information = True
            if (browser.view['stage'] == 'scenario' and saw_information and not saw_reflection
                    and 'start_reflection' in browser.view['allowed_actions']
                    and any(row['stage'] == 'scenario' for row in browser.view['answers'])):
                browser.act('start_reflection')
                saw_reflection = True
            engine = service.records[browser.view['id']].engine
            _, answer, _ = resolve(case, engine.current_question)
            browser.act('answer', {'text': answer['text'], 'control': answer.get('control', 'answer')})
        elif state in {'general_review', 'scenario_review'}:
            saw_review = True
            assert browser.view['pending'] is not None
            browser.act('confirm_answer')
        elif state == 'general_baseline_review':
            browser.act('confirm_general')
        elif state == 'offer':
            assert browser.view['scenarios']
            browser.act('select_scenario', {'scenario_id': browser.view['scenarios'][0]['id']})
            browser.act('accept_scenario')
        elif state in {'scenario_baseline_review', 'final_review'}:
            browser.act('confirm_final')
        elif state == 'final':
            break
        else:
            raise AssertionError(state)
    assert browser.view['state'] == 'final'
    assert saw_review and saw_information
    assert saw_reflection
    assert browser.view['results'] == {'crl': None, 'trl': None, 'orl': None, 'srl': None,
                                        'provisional_citizen_estimate': None}
    browser.act('provisional_estimate')
    estimate = browser.view['results']['provisional_citizen_estimate']
    assert estimate['status'] == 'draft_provisional_model_judgement'
    assert estimate['crl'] is None and estimate['approved_by'] is None
    for format in ('json', 'jsonl'):
        response = browser.client.get('/v1/sessions/' + browser.view['id'] + '/export?format=' + format)
        assert response.status_code == 200, response.json
        assert response.headers['Cache-Control'] == 'no-store'
        assert 'attachment;' in response.headers['Content-Disposition']
        value = json.loads(response.data)
        assert value['numerical_srl'] is None and value['numerical_orl'] is None and value['numerical_trl'] is None
        assert value['information_exposures']
        assert value['schema_version'] == '1.0.0' and value['export_profile'] == 'browser_evidence'
        serialized = response.data.decode()
        for forbidden in ('"inference"', '"diagnostics"', '"base_url"', '"local_path"', '/home/evouvali', '"prompts"'):
            assert forbidden not in serialized
        if format == 'jsonl':
            assert len(response.data.decode().splitlines()) == 1


def test_decline_scenario_organisation_scope_and_back(make_api):
    app, service = make_api()
    browser = start(Browser(app), perspective='organisation')
    browser.act('answer', {'text': 'little'})
    browser.act('answer', {'text': 'I have general concerns about noise.'})
    assert browser.view['state'] == 'general_review'
    browser.act('back')
    assert browser.view['state'] == 'general_interview'
    assert browser.view['returned_text'] == 'I have general concerns about noise.'
    browser.act('answer', {'text': 'I would like more general information.'})
    browser.act('correct_interpretation', {'text': 'I mean general information about drone noise.'})
    assert browser.view['state'] == 'general_review'
    browser.act('confirm_answer')
    finish_declined(browser)
    assert browser.view['state'] == 'final'
    assert 'provisional_estimate' not in browser.view['allowed_actions']
    assert browser.submit('provisional_estimate').status_code == 409
    value = service.export(browser.view['id'], service.records[browser.view['id']].owner)
    assert value['scenario_decision'] == 'declined'
    assert value['changes']['corrections']


def test_two_owners_cannot_read_mutate_jobs_or_export_each_other(make_api):
    app, service = make_api()
    first = start(Browser(app))
    second = start(Browser(app))
    assert first.csrf != second.csrf
    response = first.submit('answer', {'text': 'little'})
    jid = response.json['job_id']
    sid = first.view['id']
    assert second.client.get('/v1/sessions/' + sid).status_code == 404
    assert second.client.get('/v1/jobs/' + jid).status_code == 404
    assert second.client.get('/v1/sessions/' + sid + '/export').status_code == 404
    assert second.client.post('/v1/sessions/' + sid + '/actions', json={
        'action': 'reset', 'data': {}, 'request_id': str(uuid4()), 'expected_version': 0},
        headers={'X-CSRF-Token': second.csrf}).status_code == 404
    assert second.read()['question']['id'] == 'familiarity'


def test_csrf_origin_cookie_and_cache_boundaries(make_api):
    app, service = make_api()
    browser = Browser(app)
    response = browser.client.get('/v1/capabilities')
    cookie = response.headers.get('Set-Cookie', '')
    # The initial cookie is issued by the first capabilities request.
    initial = app.test_client().get('/v1/capabilities').headers['Set-Cookie']
    assert 'HttpOnly' in initial and 'SameSite=Strict' in initial
    assert response.headers['Cache-Control'] == 'no-store'
    assert browser.client.post('/v1/sessions', json={}).status_code == 403
    assert browser.client.post('/v1/sessions', json={}, headers={
        'X-CSRF-Token': browser.csrf, 'Origin': 'https://foreign.invalid'}).status_code == 403
    browser.new()
    assert browser.client.get('/v1/anything').is_json
    assert browser.client.get('/v1/anything').status_code == 404
    assert browser.client.get('/v1/health', environ_overrides={'wsgi.multiprocess': True}).status_code == 503


def test_stale_duplicate_and_invalid_actions(make_api):
    app, service = make_api()
    browser = Browser(app)
    browser.new()
    key = str(uuid4())
    data = {'perspective': 'personal', 'role': 'citizen', 'city': 'madrid'}
    response = browser.submit('set_context', data, request_id=key)
    assert response.status_code == 202
    repeated = browser.submit('set_context', data, request_id=key)
    assert repeated.status_code == 202
    assert repeated.json['job_id'] == response.json['job_id']
    assert browser.submit('set_context', {**data, 'city': 'milan'}, request_id=key).status_code == 409
    assert browser.submit('finish', version=0).status_code == 409
    assert browser.submit('invent_scoring').status_code == 400
    assert browser.submit('reset', request_id='password=not-an-opaque-uuid').status_code == 400


@pytest.mark.parametrize('field', ['place', 'function', 'role', 'perspective', 'city'])
def test_credentials_blocked_before_hash_queue_or_retention(make_api, field, monkeypatch):
    app, service = make_api()
    browser = Browser(app)
    browser.new()
    data = {'perspective': 'organisation', 'role': 'citizen', 'city': 'other', 'place': '', 'function': ''}
    data[field] = 'password=synthetic-sensitive-value'
    def forbidden_hash(*args):
        raise AssertionError('Blocked input must not be fingerprinted')
    monkeypatch.setattr(service, '_fingerprint', forbidden_hash)
    response = browser.submit('set_context', data)
    assert response.status_code == 422
    record = service.records[browser.view['id']]
    assert not record.receipts and not record.preview and not record.busy
    assert not service.jobs
    assert 'synthetic-sensitive-value' not in response.data.decode()


def test_cleaned_preview_binding_confirmation_and_stale_rejection(make_api):
    app, service = make_api()
    browser = start(Browser(app))
    browser.act('answer', {'text': 'little'})
    response = browser.act('answer', {'text': 'Alice Example thinks drone noise matters.'})
    preview = browser.view['preview']
    assert preview and 'Alice Example' not in json.dumps(preview)
    assert '[private detail removed]' in preview['fields']['text']
    assert not service.jobs or not any(j.status in {'queued', 'running'} for j in service.jobs.values())
    wrong = browser.submit('confirm_cleaned', {'preview_id': '0' * 48})
    assert wrong.status_code == 409
    browser.act('confirm_cleaned', {'preview_id': preview['id']})
    assert browser.view['state'] == 'general_review'
    assert 'Alice Example' not in browser.view['pending']['text']
    assert browser.submit('confirm_cleaned', {'preview_id': preview['id']}).status_code == 409
    browser.act('back')
    browser.act('answer', {'text': 'Alice Example thinks access matters.'})
    old = browser.view['preview']['id']
    browser.act('discard_preview')
    assert browser.submit('confirm_cleaned', {'preview_id': old}).status_code == 409


def test_reset_invalidates_running_job_and_discards_late_result(make_api):
    entered, release = threading.Event(), threading.Event()
    class BlockingClient(MockBaselineClient):
        def extract_baseline(self, *args, **kwargs):
            entered.set()
            release.wait(3)
            return super().extract_baseline(*args, **kwargs)
    app, service = make_api(clients=lambda e: {'baseline': BlockingClient(), 'planner': None})
    browser = start(Browser(app))
    browser.act('answer', {'text': 'little'})
    response = browser.submit('answer', {'text': 'Drone noise concerns me.'})
    browser.view = response.json['session']
    jid = response.json['job_id']
    assert entered.wait(1)
    assert browser.read()['busy_job'] == jid
    assert browser.submit('answer', {'text': 'Another answer.'}).status_code == 409
    browser.act('reset')
    assert browser.view['state'] == 'general_welcome'
    assert browser.client.get('/v1/jobs/' + jid).status_code == 410
    release.set()
    service.queue.join()
    assert browser.read()['state'] == 'general_welcome'
    assert browser.view['pending'] is None


def test_new_blocked_submission_invalidates_existing_cleaned_preview(make_api):
    app, service = make_api()
    browser = start(Browser(app))
    browser.act('answer', {'text': 'little'})
    browser.act('answer', {'text': 'Alice Example has concerns about noise.'})
    previous = browser.view['preview']['id']
    previous_version = browser.view['version']
    response = browser.submit('answer', {'text': 'password=synthetic-sensitive-value'})
    assert response.status_code == 422
    browser.read()
    assert browser.view['version'] > previous_version
    assert browser.view['preview'] is None
    assert browser.view['question']['id'] != 'familiarity'
    assert browser.submit('confirm_cleaned', {'preview_id': previous}).status_code == 409
    record = service.records[browser.view['id']]
    assert 'synthetic-sensitive-value' not in repr(record)
    browser.act('answer', {'text': 'I would like information about noise.'})
    assert browser.view['state'] == 'general_review'


def test_queue_saturation_timeout_and_expiry(make_api):
    entered, release = threading.Event(), threading.Event()
    class BlockingClient(MockBaselineClient):
        def extract_baseline(self, *args, **kwargs):
            entered.set()
            release.wait(3)
            return super().extract_baseline(*args, **kwargs)
    app, service = make_api(queue_size=1, job_timeout=1, session_ttl=10,
                            clients=lambda e: {'baseline': BlockingClient(), 'planner': None})
    first, second, third = [start(Browser(app)) for _ in range(3)]
    for browser in (first, second, third):
        browser.act('answer', {'text': 'little'})
    r1 = first.submit('answer', {'text': 'General noise concerns.'})
    first.view = r1.json['session']
    assert entered.wait(1)
    r2 = second.submit('answer', {'text': 'General access concerns.'})
    assert r2.status_code == 202
    assert third.submit('answer', {'text': 'General information needs.'}).status_code == 429
    current = service.clock()
    service.clock = lambda: current + 2
    timed_out = first.client.get('/v1/jobs/' + r1.json['job_id'])
    assert timed_out.json['job']['error']['code'] == 'timeout'
    first.read()
    assert timed_out.json['job']['version'] == first.view['version']
    first.act('reset')
    assert first.client.get('/v1/jobs/' + r1.json['job_id']).status_code == 410
    service.clock = lambda: current + 20
    assert third.client.get('/v1/sessions/' + third.view['id']).status_code == 410
    release.set()


def test_failed_answer_preserves_unresolved_history_and_safe_errors(make_api):
    class FailingClient(MockBaselineClient):
        def extract_baseline(self, *args, **kwargs):
            raise AssessmentError('Do not expose /private/model/host or raw transport response', code='transport')
    app, service = make_api(clients=lambda e: {'baseline': FailingClient(), 'planner': None})
    browser = start(Browser(app))
    browser.act('answer', {'text': 'little'})
    job = browser.act('answer', {'text': 'I would like information about noise.'}, allow_failure=True)
    assert job['status'] == 'failed'
    assert '/private/model' not in json.dumps(job)
    assert browser.view['retry_draft']['data']['text'] == 'I would like information about noise.'
    finish_declined(browser)
    exported = browser.client.get('/v1/sessions/' + browser.view['id'] + '/export').json
    assert exported['failure_history'][0]['resolution'] == 'unresolved_at_stage_boundary'
    assert exported['failure_history'][0]['text'] == 'I would like information about noise.'
    assert exported['numerical_srl'] is None


def test_source_and_detector_readiness_fail_closed(make_api, monkeypatch):
    adapter = ControllerAdapter()
    monkeypatch.setattr('iam_sra.api.adapter.detector', lambda: (_ for _ in ()).throw(PrivacyError('unavailable', unavailable=True)))
    with pytest.raises(APIError) as failure:
        adapter.readiness()
    assert failure.value.code == 'privacy_unavailable'
    monkeypatch.setattr('iam_sra.api.adapter.detector', lambda: object())
    monkeypatch.setattr('iam_sra.conversation_corpus.load_corpus', lambda: (_ for _ in ()).throw(ValueError('/private/source/path')))
    with pytest.raises(APIError) as failure:
        adapter.readiness()
    assert failure.value.code == 'source_unavailable'


def test_information_projection_preserves_citations():
    data = information({'id': 'explanation_1', 'kind': 'explanation', 'text': 'Synthetic source text.',
                        'content': {'excerpts': [{'passage_id': 'p1', 'quotation': 'Synthetic source text.'}],
                                    'passages': [{'id': 'p1', 'document_title': 'Synthetic reference', 'location': 'section 1'}]}})
    assert data['content']['excerpts'][0]['source'] == {'document_title': 'Synthetic reference', 'location': 'section 1'}


def test_production_adapter_checks_corpus_and_creates_private_clients():
    """Exercise the non-fixture apply path without a live model or private sources."""
    collection = synthetic_collection()
    engine = ConversationSession(collection)
    created = []

    def clients(candidate):
        client = MockBaselineClient()
        created.append(client)
        return {'baseline': client, 'planner': None}

    adapter = ControllerAdapter(clients_factory=clients, readiness=lambda: {'corpus': 'test-fixture'})
    adapter._collection = collection
    assert not adapter.fixture
    context = {'perspective': 'personal', 'role': 'citizen', 'city': 'madrid'}
    deadline = time.monotonic() + 5
    adapter.apply(engine, 'set_context', context, deadline)
    adapter.apply(engine, 'answer', {'text': 'little', 'control': 'answer'}, deadline)
    assert engine.state == 'general_interview'
    assert len(created) == 2 and created[0] is not created[1]
    assert all(client.external_deadline == deadline for client in created)
    adapter._collection = {**collection, 'version': 'changed-test-source'}
    with pytest.raises(APIError) as failure:
        adapter.apply(engine, 'finish', {}, deadline)
    assert failure.value.code == 'source_unavailable'


def test_unsafe_candidate_output_and_export_are_withheld(make_api, monkeypatch):
    app, service = make_api()
    browser = start(Browser(app))
    original = service.adapter.apply

    def unsafe_candidate(engine, *args):
        returned = original(engine, *args)
        engine.general.respondent['function'] = 'password=synthetic-sensitive-value'
        return returned

    monkeypatch.setattr(service.adapter, 'apply', unsafe_candidate)
    job = browser.act('answer', {'text': 'little'}, allow_failure=True)
    assert job['status'] == 'failed' and job['error']['code'] == 'privacy'
    assert 'synthetic-sensitive-value' not in json.dumps(job)
    assert browser.view['question']['id'] == 'familiarity'
    assert browser.view['respondent']['function'] is None
    monkeypatch.setattr(service.adapter, 'apply', original)
    finish_declined(browser)
    service.records[browser.view['id']].engine.general.respondent['function'] = 'password=synthetic-sensitive-value'
    response = browser.client.get('/v1/sessions/' + browser.view['id'] + '/export')
    assert response.status_code == 422 and response.json['error']['code'] == 'privacy'
    assert 'synthetic-sensitive-value' not in response.data.decode()


def test_correction_invalidates_dependent_scenario_and_old_jobs(make_api):
    app, service = make_api()
    browser = start(Browser(app))
    browser.act('answer', {'text': 'little'})
    job = browser.act('answer', {'text': 'I have concerns about noise.'})
    browser.act('confirm_answer')
    previous_answer = browser.view['answers'][-1]
    conclude_general(browser)
    browser.act('accept_scenario')
    assert browser.view['stage'] == 'scenario'
    browser.act('edit_answer', {'stage': 'general', 'event_id': previous_answer['id']})
    assert browser.view['stage'] == 'general'
    assert browser.view['scenario'] is None
    assert browser.client.get('/v1/jobs/' + job['id']).status_code == 410
    assert service.records[browser.view['id']].engine.superseded_scenarios


def test_end_session_versions_and_expired_job_receipts(make_api):
    app, service = make_api(result_ttl=1)
    browser = Browser(app)
    browser.new()
    key = str(uuid4())
    data = {'perspective': 'personal', 'role': 'citizen', 'city': 'madrid'}
    response = browser.submit('set_context', data, request_id=key)
    service.queue.join()
    browser.read()
    current = service.clock()
    service.clock = lambda: current + 2
    assert browser.client.get('/v1/jobs/' + response.json['job_id']).status_code == 404
    duplicate = browser.submit('set_context', data, version=0, request_id=key)
    assert duplicate.status_code == 200 and duplicate.json['duplicate']
    assert duplicate.json['session']['version'] == browser.view['version']
    headers = {'X-CSRF-Token': browser.csrf, 'X-Session-Version': str(browser.view['version'] - 1)}
    path = '/v1/sessions/' + browser.view['id']
    assert browser.client.delete(path, headers=headers).status_code == 409
    headers['X-Session-Version'] = str(browser.view['version'])
    assert browser.client.delete(path, headers=headers).status_code == 204
    assert browser.client.get(path).status_code == 410


def test_secure_cookie_mode_and_capacity(make_api):
    app, service = make_api(capacity=1)
    app.config['SESSION_COOKIE_SECURE'] = True
    cookie = app.test_client().get('/v1/capabilities', base_url='https://localhost').headers['Set-Cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie
    app.config['SESSION_COOKIE_SECURE'] = False
    first, second = Browser(app), Browser(app)
    first.new()
    response = second.client.post('/v1/sessions', json={}, headers={'X-CSRF-Token': second.csrf})
    assert response.status_code == 503 and response.json['error']['code'] == 'capacity'


@pytest.mark.presidio_live
def test_api_real_privacy_resources_context_preview():
    """Real local detector, synthetic context, real corpus; no inference calls."""
    from iam_sra.privacy import detector
    try:
        detector()
        from iam_sra.conversation_corpus import load_corpus
        load_corpus()
    except (PrivacyError, ValueError, OSError):
        pytest.skip('Pinned local detector and reviewed private corpus required')
    app = create_app({'TESTING': True})
    manager = app.extensions['iam_sra']
    try:
        browser = Browser(app)
        browser.new()
        browser.act('set_context', {'perspective': 'organisation', 'role': 'planning', 'city': 'other',
                                   'place': '', 'function': 'Planning policy; contact sample@example.org'})
        assert browser.view['preview']
        assert 'sample@example.org' not in json.dumps(browser.view)
        browser.act('confirm_cleaned', {'preview_id': browser.view['preview']['id']})
        assert browser.view['state'] == 'general_interview'
        assert browser.view['question']['id'] == 'familiarity'
    finally:
        manager.close()
