"""Loopback-only web UI and token issuer; no Cloud credentials are supplied here."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from tokens import issue_token

STATIC = Path(__file__).with_name('static')
HOSTS = {'localhost:3000', '127.0.0.1:3000'}
ORIGINS = {'http://' + host for host in HOSTS}


def upstream_ready():
    for url in ('http://127.0.0.1:7880/', 'http://127.0.0.1:8081/'):
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status != 200:
                    return False
        except (OSError, urllib.error.URLError):
            return False
    return True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Do not log request paths, query strings, or credentials.
        pass

    def send_content(self, status, body, content_type='application/json; charset=utf-8'):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy',
                         "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self' ws://127.0.0.1:7880; media-src 'self' blob:; "
                         "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        if self.headers.get('Host') not in HOSTS:
            self.send_content(403, {'error': '僅允許 localhost:3000 或 127.0.0.1:3000。'})
            return False
        return True

    def do_GET(self):
        if not self.valid_host():
            return
        if self.path == '/health':
            ready = upstream_ready()
            self.send_content(200 if ready else 503, {'ready': ready})
            return
        routes = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                  '/audio.js': ('audio.js', 'text/javascript; charset=utf-8'),
                  '/style.css': ('style.css', 'text/css; charset=utf-8'),
                  '/livekit-client.js': ('livekit-client.js', 'text/javascript; charset=utf-8')}
        entry = routes.get(self.path)
        if entry is None:
            self.send_content(404, {'error': '找不到頁面。'})
            return
        try:
            self.send_content(200, (STATIC / entry[0]).read_bytes(), entry[1])
        except FileNotFoundError:
            self.send_content(503, {'error': '網頁資源尚未建立，請重新建置 web image。'})

    def do_POST(self):
        if not self.valid_host():
            return
        if self.path != '/api/token':
            self.send_content(404, {'error': '找不到端點。'})
            return
        if self.headers.get('Origin') not in ORIGINS:
            self.send_content(403, {'error': '不允許此來源。'})
            return
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            self.send_content(415, {'error': '需要 application/json。'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1024:
                raise ValueError
            if json.loads(self.rfile.read(length)) != {}:
                raise ValueError
        except (ValueError, UnicodeError):
            self.send_content(400, {'error': '請使用空 JSON 物件。'})
            return
        if not upstream_ready():
            self.send_content(503, {'error': 'LiveKit 或 Agent 尚未就緒，請檢查 docker compose ps 與日誌。'})
            return
        try:
            result = issue_token(os.environ.get('LIVEKIT_API_KEY', ''), os.environ.get('LIVEKIT_API_SECRET', ''))
        except ValueError:
            self.send_content(503, {'error': '本機服務憑證設定錯誤。'})
            return
        result['url'] = 'ws://127.0.0.1:7880'
        self.send_content(200, result)


if __name__ == '__main__':
    print('本機語音測試：http://localhost:3000', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 3000), Handler).serve_forever()
