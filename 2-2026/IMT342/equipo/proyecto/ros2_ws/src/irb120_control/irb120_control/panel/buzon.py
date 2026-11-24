"""Buzón de puntos: lista acotada de poses que llegan de RViz, de la visión o de scripts HTTP.

El Estudio las toma con `buzon_tomar` (no se borran al leer) y las convierte en puntos de la trayectoria.
Cada entrada: {id, origen ('rviz'|'vision'|'http'), nombre, pose [x, y, z mm, roll, pitch, yaw °] en el punto
`herramienta` ('tcp'|'brida'), q [°] o None, t (segundos Unix)}. Sin ROS: se prueba solo.
"""
import collections
import threading
import time

from irb120_control.rws_j6 import Refused

ORIGENES = ('rviz', 'vision', 'http')
MAX_ENTRADAS = 50
MAX_RECHAZOS = 10
EN_ESTADO = 20           # entradas que viajan en cada estado


class Buzon:
    def __init__(self, capacidad=MAX_ENTRADAS, reloj=time.time):
        self.mutex = threading.Lock()
        self.entradas = collections.deque(maxlen=capacidad)
        self.rechazos = collections.deque(maxlen=MAX_RECHAZOS)
        self.reloj = reloj
        self.ultimo_id = 0     # los ids siguen creciendo tras vaciar: un cliente con desde_id no se confunde

    def agregar(self, origen, pose, herramienta, nombre=None, q=None):
        if origen not in ORIGENES:
            raise Refused(f'Origen «{origen}» desconocido.')
        if nombre is not None and (not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 40):
            raise Refused('El nombre debe ser un texto de 1 a 40 caracteres.')
        with self.mutex:
            self.ultimo_id += 1
            entrada = {'id': self.ultimo_id, 'origen': origen, 'nombre': nombre.strip() if nombre else f'P{self.ultimo_id}',
                       'pose': [float(v) for v in pose], 'herramienta': herramienta,
                       'q': None if q is None else [float(v) for v in q], 't': self.reloj()}
            self.entradas.append(entrada)
            return dict(entrada)

    def rechazar(self, origen, motivo):
        with self.mutex:
            self.rechazos.append({'origen': origen, 'motivo': motivo, 't': self.reloj()})

    def tomar(self, desde_id=0):
        """Entradas con id > desde_id (no las borra) y el último id emitido."""
        if isinstance(desde_id, bool) or not isinstance(desde_id, int) or desde_id < 0:
            raise Refused('«desde_id» debe ser un entero ≥ 0.')
        with self.mutex:
            return [dict(e) for e in self.entradas if e['id'] > desde_id], self.ultimo_id

    def vaciar(self):
        with self.mutex:
            self.entradas.clear()

    def ultimas(self, n=EN_ESTADO):
        with self.mutex:
            return [dict(e) for e in list(self.entradas)[-n:]]

    def ultimos_rechazos(self):
        with self.mutex:
            return [dict(r) for r in self.rechazos]
