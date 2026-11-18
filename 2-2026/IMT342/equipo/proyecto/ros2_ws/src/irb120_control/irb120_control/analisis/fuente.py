"""Lectura del estado del panel (solo GET, nunca órdenes) y entrada para los cálculos."""
from dataclasses import dataclass
import json
import threading
import time
import urllib.request

DEFAULT_URL = 'http://127.0.0.1:8770/estado'
SIN_CONEXION = 'Sin conexión con el panel (./brazo.sh panel)'

# Postura medida y objetivo de ejemplo (sesión del 17/11) para --demo y pruebas.
DEMO = {'simulado': True, 'modo': 'DEMO', 'ocupado': False, 'herramienta': 'tcp', 'velocidad_pct': 20,
        'medido': [7.020, 10.217, -33.334, 48.945, -1.479, 103.570],
        'objetivo': [0.89, 30.11, -45.06, 27.40, 12.52, 147.38],
        'verificacion': {'pose_deseada': None, 'inicio': None}}


@dataclass(frozen=True)
class Entrada:
    """Lo que necesitan los cálculos, en grados/mm, ya validado."""
    medido: tuple
    objetivo: tuple
    herramienta: str
    pose_deseada: tuple | None
    inicio: tuple | None
    velocidad_pct: float


def _six(values):
    if not isinstance(values, (list, tuple)) or len(values) != 6:
        return None
    try:
        return tuple(float(v) for v in values)
    except (TypeError, ValueError):
        return None


def entrada(estado):
    """Entrada desde el JSON del panel; None si aún no hay medida u objetivo."""
    if not isinstance(estado, dict):
        return None
    medido, objetivo = _six(estado.get('medido')), _six(estado.get('objetivo'))
    if medido is None or objetivo is None:
        return None
    check = estado.get('verificacion') or {}
    tool = estado.get('herramienta') if estado.get('herramienta') in ('tcp', 'brida') else 'tcp'
    try:
        pct = float(estado.get('velocidad_pct') or 20.)
    except (TypeError, ValueError):
        pct = 20.
    pose = _six(check.get('pose_deseada')) if check.get('origen') == 'ik' else None
    return Entrada(medido, objetivo, tool, pose, _six(check.get('inicio')), min(100., max(1., pct)))


class Fuente:
    """Sondea GET /estado en un hilo; la interfaz lee .ultimo sin bloquearse."""

    def __init__(self, url=DEFAULT_URL, periodo=.5, demo=False, opener=urllib.request.urlopen):
        self.url, self.periodo, self.demo, self.opener = url, periodo, demo, opener
        self.lock = threading.Lock()
        self.ultimo = dict(DEMO) if demo else None
        self.error = None if demo else 'Conectando…'
        self.recibido = time.monotonic() if demo else None
        self._stop = threading.Event()

    def leer_una_vez(self):
        try:
            with self.opener(self.url, timeout=1.) as response:
                data = json.loads(response.read().decode('utf-8'))
            if not isinstance(data, dict):
                raise ValueError('respuesta no es un objeto JSON')
            with self.lock:
                self.ultimo, self.error, self.recibido = data, None, time.monotonic()
        except Exception as exc:  # panel cerrado, puerto ocupado, JSON roto…
            with self.lock:
                self.error = f'{SIN_CONEXION}: {exc}'

    def iniciar(self):
        if self.demo:
            return
        def run():
            while not self._stop.is_set():
                self.leer_una_vez()
                self._stop.wait(self.periodo)
        threading.Thread(target=run, daemon=True, name='analisis-fuente').start()

    def detener(self):
        self._stop.set()

    def instantanea(self):
        with self.lock:
            return self.ultimo, self.error
