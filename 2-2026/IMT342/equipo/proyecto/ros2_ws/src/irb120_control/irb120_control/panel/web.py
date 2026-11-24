"""Página web local OPCIONAL (./iniciar.sh panel --web): mismo estado que el panel de RViz.

El testigo de las órdenes también se guarda en ~/.cache/irb120/panel_token_<puerto> (0600, directorio 0700; otra
carpeta con IRB120_CACHE) para que el Estudio pueda dar órdenes; se borra al cerrar el servidor."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading

from irb120_control.rws_j6 import Refused
from irb120_control.panel.estado import ACCIONES_GRANDES, ACTIONS, MAX_ORDEN_BYTES, MAX_ORDEN_GRANDE_BYTES


def carpeta_cache():
    return Path(os.environ.get('IRB120_CACHE') or Path.home() / '.cache' / 'irb120')


def ruta_testigo(port):
    return carpeta_cache() / f'panel_token_{port}'


def guardar_testigo(port, token):
    """Escribe el testigo con permisos 0600 en un directorio 0700. Devuelve la ruta (None si no se pudo)."""
    path = ruta_testigo(port)
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            os.fchmod(fd, 0o600)
            os.write(fd, token.encode())
        finally:
            os.close(fd)
        return path
    except OSError:
        return None


def borrar_testigo(ruta):
    if ruta is not None:
        try:
            Path(ruta).unlink()
        except OSError:
            pass


class Servidor(ThreadingHTTPServer):
    ruta_testigo = None

    def server_close(self):
        super().server_close()
        borrar_testigo(self.ruta_testigo)


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
                if not 0 <= length <= (MAX_ORDEN_GRANDE_BYTES if action in ACCIONES_GRANDES else MAX_ORDEN_BYTES):
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

    server = Servidor(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.ruta_testigo = guardar_testigo(server.server_address[1], token)
    threading.Thread(target=server.serve_forever, daemon=True, name='panel-http').start()
    return server, token
