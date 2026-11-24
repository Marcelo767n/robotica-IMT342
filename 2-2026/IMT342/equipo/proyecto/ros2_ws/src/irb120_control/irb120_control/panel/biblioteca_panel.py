"""Biblioteca y grabación de trayectorias dentro del panel de RViz (sin Estudio).

  trayectorias_listar            → lista de salidas/trayectorias/NN_*.json (también en el estado, 'biblioteca')
  trayectoria_ejecutar           {archivo, bucle, velocidad_pct?}  planifica AQUÍ desde la postura medida y ejecuta
  trayectoria_vista_previa       {archivo}                         anima el robot naranja, sin mover el real
  grabar_punto / grabar_borrar_ultimo / grabar_vaciar / grabar_guardar {nombre, bucle}

Las vistosas son las de número 10–19 (bucle por defecto). Lo grabado se guarda desde el 20.
Con un módulo sin MoveL (v4) se fuerza «articular» en todos los puntos. Sin ROS ni HTTP: se prueba solo.
"""
from pathlib import Path
import threading
import time

from irb120_control.estudio import biblioteca
from irb120_control.panel.cinematica import pose_of
from irb120_control.rws_j6 import Refused
from irb120_control.trayectorias import Punto, Trayectoria

try:
    from irb120_conexion.rutas import PROJECT
except Exception:  # fuera del árbol del proyecto
    PROJECT = Path(__file__).resolve().parents[5]
CARPETA = Path(PROJECT) / 'salidas' / 'trayectorias'
VISTOSAS = range(10, 20)
PRIMER_NUMERO_GRABADO = 20
MAX_PUNTOS = 100
REFRESCO_S = 3.


class BibliotecaPanel:
    def __init__(self, panel, carpeta=None, clock=time.monotonic):
        self.panel, self.clock = panel, clock
        self.carpeta = Path(carpeta) if carpeta else CARPETA
        self.mutex = threading.Lock()
        self.puntos = []          # [{'nombre', 'q'}] de la grabación en curso
        self._lista, self._en, self._firma = [], None, None

    # ---------- biblioteca ----------
    def _firma_carpeta(self):
        try:
            return self.carpeta.stat().st_mtime_ns
        except OSError:
            return None

    def listar(self, forzar=False):
        with self.mutex:
            firma = self._firma_carpeta()
            if forzar or self._en is None or self.clock() - self._en > REFRESCO_S or firma != self._firma:
                self._lista = [self._fila(e) for e in biblioteca.listar(self.carpeta)]
                self._en, self._firma = self.clock(), firma
            return [dict(f) for f in self._lista]

    @staticmethod
    def _fila(e):
        vistosa = e.numero is not None and e.numero in VISTOSAS
        return {'archivo': e.ruta.name, 'numero': e.numero, 'nombre': e.nombre, 'puntos': e.puntos,
                'vistosa': vistosa, 'bucle_por_defecto': vistosa}

    def _cargar(self, archivo):
        if not isinstance(archivo, str) or not archivo or Path(archivo).name != archivo or not archivo.endswith('.json'):
            raise Refused('Archivo de trayectoria no válido.')
        ruta = self.carpeta / archivo
        if not ruta.is_file():
            raise Refused(f'No existe la trayectoria «{archivo}».')
        try:
            return Trayectoria.cargar(ruta)
        except (ValueError, OSError) as exc:
            raise Refused(f'No se pudo cargar «{archivo}»: {exc}') from exc

    def _preparar(self, body, bucle):
        tray = self._cargar(body.get('archivo'))
        if bucle is not None:
            tray.repeticiones = 0 if bucle else 1
        if not self.panel.capacidades()['lineal'] and any(p.tipo != 'articular' for p in tray.puntos):
            for p in tray.puntos:
                p.tipo = 'articular'
            self.panel.say('Módulo sin movimiento lineal (v4): todos los puntos de «%s» van en articular.' % tray.nombre)
        return {'trayectoria': tray.to_dict()}

    # ---------- acciones ----------
    def ejecutar(self, body):
        panel = self.panel
        bucle = body.get('bucle')
        if bucle is not None and not isinstance(bucle, bool):
            raise Refused('«bucle» debe ser verdadero o falso.')
        if bucle is None:
            bucle = False
        velocidad = body.get('velocidad_pct')
        if velocidad is not None and velocidad != panel.speed_pct:
            panel.set_speed(velocidad)
        cuerpo = self._preparar(body, bucle)
        planeado = panel.ejecutor._planear(cuerpo)    # Refused con resumen y primera regla si no es apto
        return {'trayectoria': panel.ejecutor.preparar(cuerpo, planeado)}

    def vista_previa(self, body):
        return self.panel.ejecutor.vista_previa(self._preparar(body, None))

    # ---------- grabación ----------
    def _nombre_libre(self):
        usados = {p['nombre'] for p in self.puntos}
        n = len(self.puntos) + 1
        while f'P{n}' in usados:
            n += 1
        return f'P{n}'

    def agregar(self, q, origen='postura medida'):
        with self.mutex:
            if len(self.puntos) >= MAX_PUNTOS:
                raise Refused(f'Máximo {MAX_PUNTOS} puntos por grabación.')
            punto = {'nombre': self._nombre_libre(), 'q': [float(v) for v in q]}
            self.puntos.append(punto)
        self.panel.say(f"Grabación: punto {punto['nombre']} ({origen}).")
        return dict(punto)

    def grabar_punto(self):
        q = self.panel.fresh_measurement()
        if q is None:
            raise Refused('Todavía no hay lectura reciente del robot: no se puede capturar el punto.')
        return {'punto': self.agregar(q)}

    def borrar_ultimo(self):
        with self.mutex:
            if not self.puntos:
                raise Refused('No hay puntos grabados.')
            quitado = self.puntos.pop()
        self.panel.say(f"Grabación: punto {quitado['nombre']} borrado.")
        return {}

    def vaciar(self):
        with self.mutex:
            self.puntos.clear()
        self.panel.say('Grabación vaciada.')
        return {}

    def guardar(self, body):
        nombre = body.get('nombre')
        if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 60:
            raise Refused('Escribir un nombre (1 a 60 caracteres).')
        bucle = body.get('bucle', False)
        if not isinstance(bucle, bool):
            raise Refused('«bucle» debe ser verdadero o falso.')
        with self.mutex:
            filas = [dict(p) for p in self.puntos]
        if len(filas) < 2:
            raise Refused('Capturar al menos 2 puntos antes de guardar.')
        puntos = []
        for fila in filas:
            try:
                pose = pose_of(fila['q'], 'tcp')
            except Exception:
                pose = None
            puntos.append(Punto(fila['nombre'], pose=pose, q=fila['q'], origen='captura', tipo='articular'))
        nombre = biblioteca.nombre_unico(self.carpeta, nombre.strip())
        try:
            numero = biblioteca.numero_libre(self.carpeta, PRIMER_NUMERO_GRABADO)
            if numero < PRIMER_NUMERO_GRABADO:
                raise ValueError('Los números 20–99 están ocupados.')
            tray = Trayectoria(nombre, puntos, cerrar=True, repeticiones=0 if bucle else 1)
            destino = biblioteca.guardar(tray, self.carpeta, numero)
        except (ValueError, OSError) as exc:
            raise Refused(f'No se pudo guardar: {exc}') from exc
        with self.mutex:
            self.puntos.clear()
        self.listar(forzar=True)
        self.panel.say(f'Trayectoria guardada: {destino.name} ({len(puntos)} puntos, Nº {numero}).')
        return {'archivo': destino.name, 'numero': numero}

    def estado_grabacion(self):
        with self.mutex:
            return {'puntos': [dict(p) for p in self.puntos], 'n': len(self.puntos)}
