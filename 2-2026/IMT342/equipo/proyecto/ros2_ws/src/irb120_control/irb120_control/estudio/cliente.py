"""Cliente HTTP del panel: GET /estado y POST /api/<accion> con testigo. Sin Tk; nunca lanza al llamador."""
import json
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

PUERTO = 8770
SIN_CONEXION = 'Sin conexión con el panel (./brazo.sh panel)'

# Estado de ejemplo para --demo (sesión del 17/11): sin panel, todo se puede planificar y ver.
DEMO = {'simulado': True, 'modo': 'DEMO', 'motores': 'motoron', 'servidor_activo': True, 'listo': True,
        'ocupado': False, 'herramienta': 'tcp', 'velocidad_pct': 20, 'faltas': [],
        'medido': [0.0, 0.0, 0.0, 0.0, 30.0, 0.0],
        'objetivo': [0.89, 30.11, -45.06, 27.40, 12.52, 147.38],
        'verificacion': {'ik_fk': {'pos_mm': 2e-10, 'rot_deg': 3e-10, 'ok': True}, 'ida_vuelta_ok': True,
                         'controlador': {'pos_mm': .0004, 'rot_deg': .0002, 'ok': True, 'valida': True},
                         'robot': {'pos_mm': .12, 'rot_deg': .01, 'max_eje_deg': .02, 'ok': True}},
        'registro': ['Modo DEMO: sin panel ni robot.'], 'buzon': [],
        'trayectoria': {'fase': 'lista', 'mensaje': 'Sin trayectoria en curso.'}}


def carpeta_cache():
    return Path(os.environ.get('IRB120_CACHE') or Path.home() / '.cache' / 'irb120')


class Cliente:
    def __init__(self, puerto=PUERTO, demo=False, periodo=.5, carpeta=None):
        self.puerto, self.demo, self.periodo = int(puerto), demo, periodo
        self.base = f'http://127.0.0.1:{self.puerto}'
        self.carpeta = Path(carpeta) if carpeta else carpeta_cache()
        self.lock = threading.Lock()
        self.ultimo = dict(DEMO) if demo else None
        self.error = None if demo else 'Conectando…'
        self.recibido = time.monotonic() if demo else None
        self._stop = threading.Event()

    # ------------------------------------------------------------ estado
    def leer_una_vez(self):
        if self.demo:
            return
        try:
            with urllib.request.urlopen(f'{self.base}/estado', timeout=1.) as r:
                datos = json.loads(r.read().decode('utf-8'))
            if not isinstance(datos, dict):
                raise ValueError('la respuesta no es un objeto JSON')
            with self.lock:
                self.ultimo, self.error, self.recibido = datos, None, time.monotonic()
        except Exception as exc:  # panel cerrado, JSON roto…
            with self.lock:
                self.error = f'{SIN_CONEXION}: {exc}'

    def iniciar(self):
        if self.demo:
            return

        def ciclo():
            while not self._stop.is_set():
                self.leer_una_vez()
                self._stop.wait(self.periodo)
        threading.Thread(target=ciclo, daemon=True, name='estudio-sondeo').start()

    def detener(self):
        self._stop.set()

    def instantanea(self):
        """(estado | None, error | None): el último estado recibido (puede ser viejo si hay error)."""
        with self.lock:
            return self.ultimo, self.error

    @property
    def conectado(self):
        with self.lock:
            return not self.demo and self.error is None and self.ultimo is not None

    # ------------------------------------------------------------ órdenes
    def testigo(self):
        try:
            return (self.carpeta / f'panel_token_{self.puerto}').read_text().strip() or None
        except OSError:
            return None

    def accion(self, nombre, cuerpo=None, timeout=5.):
        """POST /api/<nombre>. Siempre devuelve un dict {'ok': bool, 'error'?: str, ...}."""
        if self.demo:
            return {'ok': False, 'error': 'Modo demo: no hay panel al que enviar.'}
        token = self.testigo()
        if token is None:
            return {'ok': False, 'error': f'No encuentro el testigo del panel en {self.carpeta}.'}
        pedido = urllib.request.Request(
            f'{self.base}/api/{nombre}', data=json.dumps(cuerpo or {}).encode('utf-8'), method='POST',
            headers={'Content-Type': 'application/json', 'X-Panel-Token': token})
        try:
            with urllib.request.urlopen(pedido, timeout=timeout) as r:
                datos = json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            msg = 'testigo rechazado (¿se reinició el panel?)' if exc.code == 403 else f'HTTP {exc.code}'
            return {'ok': False, 'error': f'El panel respondió: {msg}.'}
        except Exception as exc:
            return {'ok': False, 'error': f'{SIN_CONEXION}: {exc}'}
        return datos if isinstance(datos, dict) else {'ok': False, 'error': 'Respuesta no válida del panel.'}
