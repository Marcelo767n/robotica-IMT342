"""Órdenes del panel de RViz (JSON por /irb120/panel/orden) y estado de vuelta (/irb120/panel/estado).

Sin ROS: el puente solo mueve cadenas de texto. Formato de una orden:
    {"id": 7, "accion": "objetivo", "q": [j1..j6]}      ángulos en grados
    {"id": 8, "accion": "ik", "pose": [x, y, z, roll, pitch, yaw]}   mm y grados
    {"id": 9, "accion": "enviar", "q": [...]}           también: cancelar, sincronizar,
    {"accion": "paso", "valor": 5}                      herramienta ("tcp"|"brida"), terminar
    trayectoria, vista_previa (hasta 64 KiB), pausar, reanudar, buzon_tomar, buzon_vaciar, punto_externo:
    ver panel/trayectoria.py y panel/buzon.py (el resto de órdenes: máx. 4 KiB).
El resultado vuelve en estado["respuesta"] (mismo id) y, para "ik", en estado["ik"].
"""
import json
import math
import threading

from irb120_control.rws_j6 import Refused
from irb120_control.panel.estado import ACCIONES_GRANDES, ACTIONS, MAX_ORDEN_BYTES, MAX_ORDEN_GRANDE_BYTES

MAX_ORDER_BYTES = MAX_ORDEN_BYTES
LOG_LINES = 60


def finite(value):
    """JSON estricto: NaN/inf → null, en cualquier nivel."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(item) for item in value]
    return value


class Ordenes:
    def __init__(self, panel):
        self.panel = panel
        self.lock = threading.Lock()
        self.respuesta = None
        self.ik = None

    def atender(self, texto):
        """Ejecuta una orden; nunca lanza: el resultado queda en self.respuesta."""
        ident, accion = None, None
        try:
            if len(texto) > MAX_ORDEN_GRANDE_BYTES:
                raise Refused('Orden demasiado grande.')
            try:
                body = json.loads(texto)
            except ValueError as exc:
                if len(texto) > MAX_ORDEN_BYTES:   # solo «trayectoria» y «vista_previa» pasan de 4 KiB
                    raise Refused('Orden demasiado grande.') from exc
                raise Refused('Orden no válida (JSON).') from exc
            if not isinstance(body, dict):
                raise Refused('Orden no válida (se espera un objeto JSON).')
            ident, accion = body.get('id'), body.get('accion')
            if accion not in ACTIONS:
                raise Refused(f'Acción desconocida: {accion}.')
            if len(texto) > MAX_ORDEN_BYTES and accion not in ACCIONES_GRANDES:
                raise Refused('Orden demasiado grande.')
            result = self.panel.handle(accion, body)
            with self.lock:
                if accion == 'ik':
                    self.ik = {'id': ident, **{k: v for k, v in result.items() if k != 'objetivo'}}
                self.respuesta = {'id': ident, 'accion': accion, 'ok': True, 'error': None}
        except Refused as exc:
            self._fallo(ident, accion, str(exc))
        except Exception as exc:  # p. ej. fallo de red al terminar: se informa, el nodo sigue
            self._fallo(ident, accion, f'Fallo: {exc}')
        return self.respuesta

    def _fallo(self, ident, accion, error):
        with self.lock:
            self.respuesta = {'id': ident, 'accion': accion, 'ok': False, 'error': error}
        self.panel.say(f'Orden «{accion}» rechazada: {error}')

    def estado(self):
        shot = self.panel.snapshot()
        shot['registro'] = shot['registro'][-LOG_LINES:]
        with self.lock:
            shot['respuesta'], shot['ik'] = self.respuesta, self.ik
        return json.dumps(finite(shot), ensure_ascii=False, allow_nan=False)
