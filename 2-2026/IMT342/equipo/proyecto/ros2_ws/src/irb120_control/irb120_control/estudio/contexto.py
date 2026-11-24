"""Estado compartido del Estudio entre pestañas: trayectoria en edición, plan, hilos y avisos. Sin widgets."""
import json
from pathlib import Path
import queue
import threading

from irb120_control.estudio import biblioteca
from irb120_control.estudio.formato import seis
from irb120_control.estudio.modelo_editor import Editor
from irb120_control.trayectorias import a_ordenes, planificar

try:
    from irb120_conexion.rutas import PROJECT
except Exception:  # fuera del árbol del proyecto
    PROJECT = Path(__file__).resolve().parents[5]
CARPETA_TRAYECTORIAS = Path(PROJECT) / 'salidas' / 'trayectorias'
CARPETA_MATEMATICA = Path(PROJECT) / 'salidas' / 'matematica'


class Contexto:
    def __init__(self, cliente, carpeta=None):
        self.cliente = cliente
        self.carpeta = Path(carpeta) if carpeta else CARPETA_TRAYECTORIAS
        self.numero = None               # Nº de PLC (1–99) o None
        self.ruta = None                 # archivo de la biblioteca que se está editando
        self.guardado = None             # firma de lo último guardado/abierto
        self.editor = Editor()
        self.nombre, self.cerrar, self.repeticiones, self.herramienta = 'Trayectoria 1', True, 1, 'tcp'
        self.velocidad = None            # None: usar la del panel (o 20 % sin panel)
        self.plan = None
        self.plan_error = None
        self.planificando = False
        self.plan_tray = None            # Trayectoria con la que se calculó el plan
        self.plan_velocidad = None
        self.ultimo_buzon = 0
        self.oscuro = True
        self.proyeccion = False
        self.escuchas = []
        self.mensaje_cb = lambda texto, nivel='info': None
        self.cola = queue.Queue()

    # ------------------------------------------------------------ avisos entre pestañas
    def avisar(self, evento):
        for f in self.escuchas:
            try:
                f(evento)
            except Exception as exc:
                self.mensaje_cb(f'Error al actualizar la vista: {exc}', 'falla')

    def mensaje(self, texto, nivel='info'):
        self.mensaje_cb(texto, nivel)

    # ------------------------------------------------------------ hilos
    def en_hilo(self, trabajo, listo):
        """Ejecuta trabajo() fuera de Tk; listo(resultado, error) se llama luego desde Tk (vía drenar)."""
        def correr():
            try:
                res, err = trabajo(), None
            except Exception as exc:
                res, err = None, exc
            self.cola.put(lambda: listo(res, err))
        threading.Thread(target=correr, daemon=True, name='estudio-trabajo').start()

    def drenar(self):
        while True:
            try:
                f = self.cola.get_nowait()
            except queue.Empty:
                return
            try:
                f()
            except Exception as exc:
                self.mensaje(f'Error: {exc}', 'falla')

    # ------------------------------------------------------------ datos del panel
    def estado(self):
        e, _ = self.cliente.instantanea()
        return e if isinstance(e, dict) else {}

    def q_medido(self):
        return seis(self.estado().get('medido'))

    def velocidad_efectiva(self):
        if self.velocidad is not None:
            return self.velocidad
        try:
            return min(100., max(1., float(self.estado().get('velocidad_pct') or 20.)))
        except (TypeError, ValueError):
            return 20.

    @property
    def hay_panel(self):
        return self.cliente.conectado

    # ------------------------------------------------------------ trayectoria y plan
    def trayectoria(self):
        return self.editor.a_trayectoria(self.nombre, self.cerrar, self.repeticiones, self.herramienta)

    def cambio(self, evento='lista'):
        """La trayectoria o sus parámetros cambiaron: el plan ya no vale."""
        self.plan = self.plan_error = self.plan_tray = None
        self.avisar(evento)
        self.avisar('plan')

    def puede_enviar(self):
        return bool(self.plan is not None and self.plan.ok and self.hay_panel and not self.planificando)

    def planificar(self):
        """Valida y planifica en un hilo; el resultado llega por avisar('plan')."""
        if self.planificando:
            return
        try:
            tray = self.trayectoria()
            if not tray.puntos:
                raise ValueError('Añade al menos un punto.')
        except ValueError as exc:
            self.plan = None
            self.plan_error = str(exc)
            self.avisar('plan')
            return
        q0 = self.q_medido()
        if q0 is None:
            self.plan_error = 'No hay postura medida del robot para empezar el primer tramo.'
            self.avisar('plan')
            return
        vel = self.velocidad_efectiva()
        self.planificando, self.plan_error = True, None
        self.avisar('plan')

        def listo(plan, err):
            self.planificando = False
            if err is not None:
                self.plan, self.plan_error = None, f'No se pudo planificar: {err}'
            else:
                self.plan, self.plan_tray, self.plan_velocidad = plan, tray, vel
            self.avisar('plan')
        self.en_hilo(lambda: planificar(tray, q0, vel), listo)

    def cuerpo_envio(self, factor=None):
        """Cuerpo común de 'trayectoria' y 'vista_previa' (None si no hay plan)."""
        if self.plan is None:
            return None
        cuerpo = {'trayectoria': self.plan_tray.to_dict(), 'ordenes': a_ordenes(self.plan),
                  'velocidad_pct': self.plan_velocidad}
        if factor is not None:
            cuerpo['factor'] = factor
        return cuerpo

    # ------------------------------------------------------------ biblioteca
    def firma(self):
        return json.dumps([self.nombre, self.cerrar, self.repeticiones, self.herramienta, self.numero,
                           [p.to_dict() for p in self.editor.puntos]], sort_keys=True)

    def marcar_guardado(self):
        self.guardado = self.firma()

    def sucio(self):
        """Hay cambios sin guardar (una trayectoria vacía y sin archivo no cuenta)."""
        if self.guardado is None:
            return len(self.editor) > 0
        return self.firma() != self.guardado

    def nueva(self):
        from irb120_control.estudio.modelo_editor import Editor
        self.editor = Editor()
        self.nombre = biblioteca.nombre_unico(self.carpeta, 'Trayectoria nueva')
        self.cerrar, self.repeticiones, self.numero, self.ruta = False, 1, None, None
        self.marcar_guardado()
        self.cambio('lista')

    def abrir(self, ruta):
        from irb120_control.trayectorias import Trayectoria
        tray = Trayectoria.cargar(ruta)
        self.editor.cargar(tray)
        self.nombre, self.cerrar, self.repeticiones, self.herramienta = (
            tray.nombre, tray.cerrar, tray.repeticiones, tray.herramienta)
        self.numero, self.ruta = biblioteca.numero_de(ruta), Path(ruta)
        self.marcar_guardado()
        self.cambio('lista')
        return tray

    cargar = abrir

    def guardar(self, reemplazar=False):
        """Guarda sobre el archivo actual (renombrándolo si cambió nombre o número). Puede lanzar Ocupado."""
        tray = self.trayectoria()
        if not tray.puntos:
            raise ValueError('No hay puntos que guardar.')
        self.ruta = biblioteca.guardar(tray, self.carpeta, self.numero, self.ruta, reemplazar)
        self.marcar_guardado()
        return self.ruta

    def guardar_como(self, nombre, numero, reemplazar=False):
        antes = (self.nombre, self.numero, self.ruta)
        self.nombre, self.numero, self.ruta = nombre.strip(), numero, None
        try:
            return self.guardar(reemplazar)
        except Exception:
            self.nombre, self.numero, self.ruta = antes
            raise

    def borrar_archivo(self, ruta):
        """Mueve a la papelera; si era el abierto, queda en edición sin archivo."""
        nueva = biblioteca.a_papelera(ruta)
        if self.ruta is not None and Path(ruta) == self.ruta:
            self.ruta, self.guardado = None, None
        return nueva
