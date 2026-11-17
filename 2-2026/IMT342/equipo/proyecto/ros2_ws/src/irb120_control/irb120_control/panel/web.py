"""Página web local OPCIONAL (./iniciar.sh panel --web): mismo estado que el panel de RViz."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading

from irb120_control.rws_j6 import Refused
from irb120_control.panel.estado import ACTIONS


def serve(panel, port, page=None):
    """Servidor solo en 127.0.0.1. Las órdenes exigen el testigo de la página y Host local."""
    token = secrets.token_urlsafe(24)
    page = (page or Path(__file__).with_name('web.html').read_text(encoding='utf-8'))
    page = page.replace('__TOKEN__', token).encode()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body, mime='application/json'):
            if not isinstance(body, bytes):
                body = json.dumps(body, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def local(self):
            real_port = self.server.server_address[1]
            return self.headers.get('Host', '') in (f'127.0.0.1:{real_port}', f'localhost:{real_port}')

        def do_GET(self):
            if not self.local():
                return self.reply(403, {'ok': False, 'error': 'Solo acceso local.'})
            if self.path == '/':
                return self.reply(200, page, 'text/html; charset=utf-8')
            if self.path == '/estado':
                return self.reply(200, panel.snapshot())
            self.reply(404, {'ok': False, 'error': 'No existe.'})

        def do_POST(self):
            action = self.path[len('/api/'):] if self.path.startswith('/api/') else None
            sent = self.headers.get('X-Panel-Token', '')
            if not self.local() or action not in ACTIONS or not hmac.compare_digest(sent.encode(), token.encode()):
                return self.reply(403, {'ok': False, 'error': 'Petición no autorizada.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= 4096:
                    raise ValueError('tamaño')
                body = json.loads(self.rfile.read(length) or b'{}')
                if not isinstance(body, dict):
                    raise ValueError('forma')
            except ValueError:
                return self.reply(400, {'ok': False, 'error': 'Cuerpo no válido.'})
            try:
                self.reply(200, {'ok': True, **panel.handle(action, body)})
            except Refused as exc:
                self.reply(200, {'ok': False, 'error': str(exc)})
            except Exception as exc:  # p. ej. fallo de red al terminar
                self.reply(200, {'ok': False, 'error': f'Fallo: {exc}'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True, name='panel-http').start()
    return server, token
