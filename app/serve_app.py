#!/usr/bin/env python3
"""IAM-IQ-derived static SPA server and bounded same-origin assessment proxy.

HOST=127.0.0.1 PORT=5001; IAM_SRA_UI_PORT also supported. Target table and
K8S_HOST / IAMIQ_IN_CLUSTER semantics are shared with vite.config.js.
"""
import json
import os
import posixpath
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
HERE = Path(__file__).resolve().parent
DIST = HERE / 'dist'
TABLE = json.loads((HERE / 'proxy-routes.json').read_text())
HOP_BY_HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers',
              'transfer-encoding', 'upgrade', 'content-length', 'server', 'date'}
REQUEST_HEADERS = {'content-type', 'accept', 'accept-language', 'cookie', 'origin',
                   'x-csrf-token', 'x-session-version', 'sec-fetch-site'}
MAX_BODY = 32768


def target(tool):
    route = TABLE['routes'][tool]
    value = os.environ.get(route['targetEnv'])
    if not value:
        value = ('http://' + route['service'] if os.environ.get('IAMIQ_IN_CLUSTER') == '1'
                 else f"http://{os.environ.get('K8S_HOST', TABLE['defaultHost'])}:{route['nodePort']}")
    parts = urllib.parse.urlsplit(value)
    if (parts.scheme not in {'http', 'https'} or not parts.netloc or parts.username or parts.password
            or parts.path not in {'', '/'} or parts.query or parts.fragment):
        raise ValueError('Configure an HTTP backend origin without credentials or path.')
    return value.rstrip('/')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


# Do not inherit HTTP_PROXY or follow redirects with ownership cookies.
UPSTREAM = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def log_message(self, *args):
        pass  # Assessment paths/queries never enter access-content logs.

    def send_json(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)

    def is_api(self):
        return urllib.parse.urlsplit(self.path).path == '/api' or self.path.startswith('/api/')

    def proxy(self):
        parts = urllib.parse.urlsplit(self.path)
        segments = parts.path.split('/', 3)
        tool = segments[2] if len(segments) > 2 else ''
        if tool not in TABLE['routes']:
            return self.send_json(404, {'error': 'Unknown tool.'})
        if self.headers.get('Transfer-Encoding'):
            return self.send_json(400, {'error': 'Unsupported request framing.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.send_json(400, {'error': 'Invalid request length.'})
        if length < 0 or length > MAX_BODY:
            return self.send_json(413, {'error': 'Request too large.'})
        body = self.rfile.read(length) if length else None
        path = '/' + (segments[3] if len(segments) > 3 else '')
        url = target(tool) + path + ('?' + parts.query if parts.query else '')
        headers = {key: value for key, value in self.headers.items() if key.lower() in REQUEST_HEADERS}
        req = urllib.request.Request(url, data=body, method=self.command, headers=headers)
        try:
            with UPSTREAM.open(req, timeout=TABLE.get('timeoutMs', 30000) / 1000) as response:
                status, response_headers, payload = response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            status, response_headers, payload = exc.code, exc.headers, exc.read()
        except Exception:
            return self.send_json(502, {'error': 'Assessment service is unavailable. Try again shortly.'})
        if 300 <= status < 400:
            return self.send_json(502, {'error': 'Unexpected assessment service redirect.'})
        self.send_response(status)
        # items() preserves repeated Set-Cookie headers.
        for key, value in response_headers.items():
            if key.lower() not in HOP_BY_HOP:
                self.send_header(key, value)
        self.send_header('Content-Length', response_headers.get('Content-Length', '0') if self.command == 'HEAD' else str(len(payload)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)

    def do_GET(self):
        if self.is_api():
            return self.proxy()
        path = posixpath.normpath(urllib.parse.urlsplit(self.path).path)
        if not (DIST / path.lstrip('/')).is_file():
            if path.startswith('/assets/') or posixpath.splitext(path)[1]:
                return self.send_json(404, {'error': 'Not found.'})
            self.path = '/index.html'
        return super().do_GET()

    def do_HEAD(self):
        if self.is_api():
            return self.proxy()
        return super().do_HEAD()

    def mutate(self):
        if self.is_api():
            return self.proxy()
        return self.send_json(405, {'error': 'Method not allowed.'})

    do_POST = do_DELETE = mutate

    def not_allowed(self):
        self.send_json(405, {'error': 'Method not allowed.'})
    do_PUT = do_PATCH = do_OPTIONS = not_allowed

    def end_headers(self):
        if not self.is_api():
            self.send_header('Cache-Control', 'public, max-age=31536000, immutable' if self.path.startswith('/assets/') else 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        super().end_headers()


if __name__ == '__main__':
    if not (DIST / 'index.html').is_file():
        raise SystemExit('Run npm run build first: dist/index.html is missing.')
    for tool in TABLE['routes']:
        target(tool)  # Fail configuration before opening a socket.
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('IAM_SRA_UI_PORT', os.environ.get('PORT', '5001')))
    print(f'IAM-SRA on http://{host}:{port}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
