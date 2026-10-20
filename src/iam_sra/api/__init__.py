"""Flask application factory for the IAM-SRA2 conversation API.

Assessment state stays server-side. The signed HttpOnly cookie contains only an
opaque owner nonce and CSRF nonce; it never contains answers or assessments.
"""
import atexit
import json
import os
import secrets
from flask import Flask, Response, jsonify, request, session
from werkzeug.exceptions import HTTPException
from pydantic import ValidationError
from .adapter import ControllerAdapter
from .errors import APIError
from .schemas import API_VERSION, Empty
from .service import AssessmentService
from ..privacy import PrivacyError
from ..settings import config as engine_config


def create_app(config=None, *, service=None):
    app = Flask(__name__)
    origin_port = os.getenv('IAM_SRA_UI_PORT', '5001')
    app.config.update(
        SECRET_KEY=os.getenv('IAM_SRA_API_SECRET') or secrets.token_hex(32),
        SESSION_COOKIE_NAME='iam_sra_owner', SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict', SESSION_COOKIE_SECURE=os.getenv('IAM_SRA_COOKIE_SECURE', '0') == '1',
        SESSION_COOKIE_PATH='/', MAX_CONTENT_LENGTH=32768,
        ALLOWED_ORIGINS=[value.strip() for value in os.getenv(
            'IAM_SRA_ALLOWED_ORIGINS', f'http://127.0.0.1:{origin_port},http://localhost:{origin_port}').split(',') if value.strip()],
    )
    if config:
        app.config.update(config)
    if len(app.config['SECRET_KEY']) < 32:
        raise ValueError('IAM_SRA_API_SECRET must contain at least 32 characters.')
    adapter = ControllerAdapter()
    if service is not None and not app.config['TESTING']:
        raise ValueError('Injected assessment services require explicit TESTING configuration.')

    def setting(name, default, maximum):
        value = int(os.getenv(name, str(default)))
        if not 1 <= value <= maximum:
            raise ValueError(f'{name} is outside its supported bounds.')
        return value

    manager = service or AssessmentService(
        adapter, capacity=setting('IAM_SRA_MAX_SESSIONS', 32, 1000),
        queue_size=setting('IAM_SRA_QUEUE_SIZE', 8, 64),
        session_ttl=setting('IAM_SRA_SESSION_TTL', 3600, 86400),
        session_max_age=setting('IAM_SRA_SESSION_MAX_AGE', 14400, 86400),
        job_timeout=setting('IAM_SRA_JOB_TIMEOUT', 600, 1800),
        result_ttl=setting('IAM_SRA_RESULT_TTL', 300, 3600),
        result_capacity=setting('IAM_SRA_MAX_RESULTS', 128, 1000))
    app.extensions['iam_sra'] = manager
    if service is None:
        # Preflight is startup work, outside a browser/proxy request. A missing
        # dependency leaves the API available to explain its readiness failure.
        try:
            manager.adapter.readiness()
        except APIError:
            pass
    atexit.register(manager.close)

    def owner():
        value = session.get('owner')
        if not value:
            raise APIError('csrf', 403)
        return value

    @app.before_request
    def boundary():
        if request.environ.get('wsgi.multiprocess'):
            raise APIError('deployment', 503)
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            request_origin = request.headers.get('Origin')
            allowed = set(app.config['ALLOWED_ORIGINS']) | {request.host_url.rstrip('/')}
            if (request_origin and request_origin not in allowed
                    or request.headers.get('Sec-Fetch-Site') == 'cross-site'):
                raise APIError('origin', 403)
            expected = session.get('csrf')
            supplied = request.headers.get('X-CSRF-Token', '')
            if not expected or not secrets.compare_digest(expected, supplied):
                raise APIError('csrf', 403)
            if request.method != 'DELETE' and not request.is_json:
                raise APIError('invalid_request', 415)

    @app.after_request
    def response_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-IAM-SRA-API-Version'] = API_VERSION
        return response

    @app.errorhandler(APIError)
    def public_error(exc):
        response = jsonify(api_version=API_VERSION, error=exc.public())
        if exc.code in {'capacity', 'queue_full'}:
            response.headers['Retry-After'] = '5'
        return response, exc.status

    @app.errorhandler(PrivacyError)
    def privacy_error(exc):
        return public_error(APIError(exc.code, 503 if exc.code == 'privacy_unavailable' else 422))

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return public_error(APIError('not_found' if exc.code == 404 else 'invalid_request', exc.code))

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        # Deliberately omit exception bodies and tracebacks; logs may contain
        # neither respondent text nor model/backend transport data.
        return public_error(APIError('model_failure', 500))

    @app.get('/v1/health')
    def health():
        readiness = manager.adapter.readiness()
        return jsonify(api_version=API_VERSION, status='ready', components=readiness,
                       deployment='single-process-in-memory', inference_lanes=1)

    @app.get('/v1/capabilities')
    def capabilities():
        if 'owner' not in session:
            session['owner'] = secrets.token_hex(32)
            session['csrf'] = secrets.token_hex(32)
        try:
            readiness = {'ready': True, 'components': manager.adapter.readiness()}
        except APIError as exc:
            readiness = {'ready': False, 'error': exc.public()}
        return jsonify(api_version=API_VERSION, application='IAM-SRA', assessment='IAM-SRA2',
                       tool_id='sra-assessment', mode='retrieval_grounded_conversation',
                       engine_version=engine_config('conversation')['version'],
                       synthetic_fixture=manager.adapter.fixture,
                       csrf_token=session['csrf'], onboarding=manager.adapter.onboarding(),
                       sessions=manager.owned_sessions(session['owner']), readiness=readiness,
                       limitations=['Draft instrument; self-reports are not externally verified.',
                                    'This interview does not establish TRL, ORL or overall SRL.'])

    @app.post('/v1/sessions')
    def create_session():
        try:
            Empty.model_validate(request.get_json())
        except (ValueError, TypeError):
            raise APIError('invalid_request') from None
        return jsonify(session=manager.create(owner())), 201

    @app.get('/v1/sessions/<sid>')
    def read_session(sid):
        return jsonify(session=manager.read(sid, owner()))

    @app.post('/v1/sessions/<sid>/actions')
    def action(sid):
        status, value = manager.submit(sid, owner(), request.get_json())
        return jsonify(value), status

    @app.get('/v1/jobs/<jid>')
    def read_job(jid):
        return jsonify(job=manager.job(jid, owner()))

    @app.get('/v1/sessions/<sid>/export')
    def export_session(sid):
        format = request.args.get('format', 'json')
        if format not in {'json', 'jsonl'} or set(request.args) - {'format'}:
            raise APIError('invalid_request')
        value = manager.export(sid, owner())
        body = json.dumps(value, ensure_ascii=False, indent=2 if format == 'json' else None,
                          separators=None if format == 'json' else (',', ':')) + '\n'
        response = Response(body, content_type='application/json' if format == 'json' else 'application/x-ndjson')
        response.headers['Content-Disposition'] = f'attachment; filename="iam-sra2.{format}"'
        return response

    @app.delete('/v1/sessions/<sid>')
    def end_session(sid):
        try:
            raw_version = request.headers.get('X-Session-Version', '')
            if not raw_version.isdigit():
                raise ValueError()
            version = int(raw_version)
        except ValueError:
            raise APIError('invalid_request') from None
        manager.delete(sid, owner(), version)
        return '', 204

    return app
