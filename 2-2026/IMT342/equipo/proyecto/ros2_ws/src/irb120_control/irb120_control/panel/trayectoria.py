"""Ejecución de trayectorias verificadas en el panel: una orden por tramo, con comprobaciones antes de cada una.

Flujo de `trayectoria` (el Estudio manda la trayectoria y las órdenes que él calculó):
  1. El panel RE-PLANIFICA con `planificar()` desde la postura medida ahora y la velocidad del panel.
  2. Exige plan apto y que las órdenes recibidas coincidan con las recalculadas (mismos tipos, q a 0,01°,
     pose_tool0 a 0,01 mm / 1e-5). Si no, rechaza: la postura cambió desde que se planificó.
  3. Un hilo ejecuta cada vuelta y cada tramo. Antes de enviar (sección 5 de CONTEXTO_Y_OBJETIVOS): modelo frente
     al controlador ABB y límites; si el punto se dio como pose, además IK → FK y ida y vuelta IK(FK(q)).
     Las vueltas 2... se re-planifican desde la postura real (si la trayectoria no es cerrada, la vuelta
     empieza en el último punto, algo que el plan de la vuelta 1 no cubre).
  4. Al llegar se registra el error por eje (° y % del recorrido) y dx/dy/dz del TCP real frente al pedido.

PARAR: el robot real solo se detiene ENTRE órdenes. «cancelar» y «pausar» actúan al terminar el tramo en curso
(un tramo puede durar segundos). Para parar YA: habilitador, Stop o paro de emergencia del FlexPendant.

`vista_previa` anima el objetivo naranja con las muestras q(t) del plan, sin enviar nada al robot.
Sin ROS ni HTTP: se prueba solo.
"""
import collections
import math
import threading
import time

import numpy as np

from irb120_control.rws_j6 import Refused
from irb120_control.rws_mover import move_tramo
from irb120_control.panel import verificacion
from irb120_control.panel.cinematica import pose_of
from irb120_control.trayectorias import Trayectoria, a_ordenes, planificar

TOL_Q_DEG = 0.01             # órdenes recibidas frente a las recalculadas
TOL_POS_MM = 0.01
TOL_CUATERNION = 1e-5
TOL_POSTURA_DEG = 0.05       # postura real frente a la esperada (en el punto de paso y al reanudar)
UMBRAL_QUIETO_DEG = 0.01     # igual que el planificador: por debajo no se envía nada
FACTOR_MAX = 4.
DT_VISTA_S = 0.05
MAX_RESULTADOS = 60
CAMBIO = 'la postura cambió desde que se planificó: volver a planificar en el Estudio'


def _numeros(valor, n):
    ok = (isinstance(valor, (list, tuple)) and len(valor) == n and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in valor))
    return [float(v) for v in valor] if ok else None


def comparar_ordenes(recibidas, esperadas):
    """None si coinciden; si no, el motivo en una frase."""
    if not isinstance(recibidas, list) or len(recibidas) != len(esperadas):
        return f'se recibieron {len(recibidas) if isinstance(recibidas, list) else 0} órdenes y el plan tiene {len(esperadas)}'
    for i, (got, want) in enumerate(zip(recibidas, esperadas), start=1):
        if not isinstance(got, dict) or got.get('tipo') != want['tipo']:
            return f"tramo {i}: tipo distinto ({got.get('tipo') if isinstance(got, dict) else '?'} ≠ {want['tipo']})"
        q, pose = _numeros(got.get('q'), 6), _numeros(got.get('pose_tool0'), 7)
        if q is None or pose is None:
            return f'tramo {i}: q o pose_tool0 no válidos'
        error = max(abs(a - b) for a, b in zip(q, want['q']))
        if error > TOL_Q_DEG:
            return f'tramo {i}: q difiere {error:.3f}°'
        if max(abs(a - b) for a, b in zip(pose[:3], want['pose_tool0'][:3])) > TOL_POS_MM:
            return f'tramo {i}: pose_tool0 difiere en posición'
        # q y -q son el mismo giro
        signo = 1. if sum(a * b for a, b in zip(pose[3:], want['pose_tool0'][3:])) >= 0 else -1.
        if max(abs(a - signo * b) for a, b in zip(pose[3:], want['pose_tool0'][3:])) > TOL_CUATERNION:
            return f'tramo {i}: pose_tool0 difiere en orientación'
    return None


class Ejecutor:
    def __init__(self, panel, sleep=time.sleep):
        self.panel, self.sleep = panel, sleep
        self.mutex = threading.Lock()
        self.fase = 'lista'      # lista | ejecutando | pausada | terminada | cancelada | error
        self.mensaje = ''
        self.nombre = None
        self.vuelta = self.vueltas = self.tramo = self.total = 0
        self.actual = None       # {'desde','hasta','tipo'} del tramo en curso
        self.resultados = collections.deque(maxlen=MAX_RESULTADOS)
        self.esperada = None     # postura en la que debe estar el robot entre tramos
        self.pausa = threading.Event()        # «pausar» pedido
        self.continuar = threading.Event()    # «reanudar» aceptado
        self.previsualizando = False
        self.progreso_vista = 0.

    # ---------- lectura ----------
    def leer_q(self):
        mover = self.panel.mover
        if not mover.lock.acquire(timeout=5.):
            raise Refused('El robot está ocupado con otra lectura; reintentar.')
        try:
            return [float(v) for v in mover.joints()[0]]
        except Refused:
            raise
        except Exception as exc:
            raise Refused(f'Sin lectura del robot: {exc}') from exc
        finally:
            mover.lock.release()

    def _planear(self, body):
        """(trayectoria, plan, q0, velocidad) re-planificados con la postura medida AHORA. Refused si no es apto."""
        try:
            tray = Trayectoria.from_dict(body.get('trayectoria'))
        except ValueError as exc:
            raise Refused(f'Trayectoria no válida: {exc}') from exc
        speed = self.panel.speed_pct
        if speed is None:
            raise Refused('Velocidad del panel desconocida (aún no se leyó del robot).')
        q0 = self.leer_q()
        try:
            plan = planificar(tray, q0, speed)
        except ValueError as exc:
            raise Refused(f'No se pudo planificar: {exc}') from exc
        if not plan.ok:
            raise Refused('El plan no es apto con la postura actual: ' + plan.resumen)
        return tray, plan, q0, speed

    def _reservar(self, vista):
        with self.panel.mutex:
            if self.panel.busy:
                raise Refused('Hay un envío o una trayectoria en curso.')
            if self.previsualizando:
                raise Refused('Hay una vista previa en curso: cancelarla primero.')
            if not vista and self.panel.problems:
                raise Refused('El robot no está listo: ' + '; '.join(self.panel.problems))
            if vista:
                self.previsualizando, self.progreso_vista = True, 0.
            else:
                self.panel.busy, self.panel.progress = True, ''
            self.panel.cancel.clear()

    # ---------- ejecución ----------
    def preparar(self, body):
        tray, plan, q0, speed = self._planear(body)
        esperadas = a_ordenes(plan)
        motivo = comparar_ordenes(body.get('ordenes'), esperadas)
        if motivo:
            extra = ''
            if isinstance(body.get('velocidad_pct'), (int, float)) and body['velocidad_pct'] != speed:
                extra = f" (se planificó al {body['velocidad_pct']} % y el panel está al {speed} %)"
            raise Refused(f'Orden rechazada: {CAMBIO}. Detalle: {motivo}{extra}.')
        self._reservar(vista=False)
        with self.mutex:
            self.fase, self.mensaje, self.nombre = 'ejecutando', 'Verificado: empieza la trayectoria.', tray.nombre
            self.vuelta, self.vueltas, self.tramo, self.total = 1, tray.repeticiones, 0, len(esperadas)
            self.actual, self.esperada = None, q0
            self.resultados.clear()
            self.pausa.clear(), self.continuar.clear()
        self.panel.say(f'Trayectoria «{tray.nombre}»: {plan.resumen} Velocidad {speed} %, {tray.repeticiones} vuelta(s).')
        hilo = threading.Thread(target=self._ejecutar, args=(tray, plan, esperadas, speed), daemon=True,
                                name='panel-trayectoria')
        self.panel.worker = hilo
        hilo.start()
        return self.estado()

    def _ejecutar(self, tray, plan, ordenes, speed):
        panel = self.panel
        try:
            with panel.mover.lock:
                state = panel.mover.status()
                if state['opmode'] in ('MANR', 'MANF') and not panel.mover.rmmp.granted:
                    panel.say('Acceso remoto: pulsar «Conceder» en el FlexPendant.')
                    panel.mover.ensure_rmmp(state)
            for vuelta in range(1, tray.repeticiones + 1):
                if vuelta > 1:
                    plan = planificar(tray, self.esperada, speed)
                    if not plan.ok:
                        raise Refused(f'La vuelta {vuelta} no es apta desde la postura actual: {plan.resumen}')
                    ordenes = a_ordenes(plan)
                with self.mutex:
                    self.vuelta = vuelta
                for i, (tramo, orden) in enumerate(zip(plan.tramos, ordenes)):
                    self._comprobar_cancelacion()
                    with self.mutex:
                        self.tramo = i + 1
                        self.actual = {'desde': tramo.desde, 'hasta': tramo.hasta, 'tipo': orden['tipo']}
                    self._tramo(tray, vuelta, tramo, orden)
                    ultimo = vuelta == tray.repeticiones and i == len(ordenes) - 1
                    if self.pausa.is_set() and not ultimo:
                        self._esperar_reanudar(vuelta, i + 1, len(ordenes))
            with self.mutex:
                self.fase, self.mensaje, self.actual = 'terminada', 'Trayectoria terminada.', None
            panel.say('Trayectoria terminada.')
        except Refused as exc:
            cancelada = panel.cancel.is_set()
            with self.mutex:
                self.fase, self.mensaje = ('cancelada' if cancelada else 'error'), str(exc)
            panel.say(('CANCELADA: ' if cancelada else 'DETENIDO: ') + str(exc))
        except Exception as exc:
            with self.mutex:
                self.fase, self.mensaje = 'error', f'Fallo: {exc}'
            panel.say(f'DETENIDO: fallo inesperado: {exc}')
        finally:
            self.pausa.clear()
            with panel.mutex:
                panel.busy, panel.progress = False, ''
            panel.poll()

    def _comprobar_cancelacion(self):
        if self.panel.cancel.is_set():
            raise Refused('CANCELADO entre tramos. El robot queda donde está.')

    def _esperar_reanudar(self, vuelta, hecho, de):
        with self.mutex:
            self.fase = 'pausada'
            self.mensaje = f'Pausada en el punto de paso (vuelta {vuelta}, tramo {hecho} de {de}).'
            self.continuar.clear()
        self.pausa.clear()
        self.panel.say(self.mensaje)
        while not self.continuar.wait(.1):
            self._comprobar_cancelacion()
        self._comprobar_cancelacion()
        with self.mutex:
            self.fase, self.mensaje = 'ejecutando', 'Reanudada.'

    def _tramo(self, tray, vuelta, tramo, orden):
        panel, mover = self.panel, self.panel.mover
        punto = next(p for p in tray.puntos if p.nombre == tramo.hasta)
        destino = orden['q']
        with mover.lock:
            q_ini = [float(v) for v in mover.joints()[0]]
            self._exigir_postura(q_ini)
            if max(abs(a - b) for a, b in zip(q_ini, destino)) < UMBRAL_QUIETO_DEG:
                panel.say(f'Tramo {tramo.desde} → {tramo.hasta}: ya está en el punto, sin movimiento.')
                return
            wanted = self._verificar(tray, punto, destino, q_ini, tramo)
            with panel.mutex:   # el robot naranja muestra el destino del tramo
                panel.target, panel.desired, panel.reachable, panel.start = list(destino), None, True, list(q_ini)
            panel.say(f"Vuelta {vuelta}, tramo {tramo.indice + 1}: {tramo.desde} → {tramo.hasta} ({orden['tipo']}).")
            result = move_tramo(mover, orden['tipo'], destino, orden['pose_tool0'], panel.timeout,
                                echo=panel._echo, cancel=panel.cancel)
        self._registrar(tray, vuelta, tramo, orden, q_ini, result['joints_deg'], wanted, result['max_error_deg'])

    def _exigir_postura(self, q):
        with self.mutex:
            esperada = self.esperada
        error = max(abs(a - b) for a, b in zip(q, esperada))
        if error > TOL_POSTURA_DEG:
            raise Refused(f'El robot no está donde debía (difiere {error:.3f}° del punto de paso): se detiene la '
                          'trayectoria. Revisar el robot y volver a planificar.')

    def _verificar(self, tray, punto, destino, q_ini, tramo):
        """Sección 5 de CONTEXTO_Y_OBJETIVOS aplicable al punto (reutiliza verificacion.evaluar). Con mover.lock
        tomado. Devuelve la pose pedida [mm, °] del punto en la herramienta de la trayectoria."""
        panel = self.panel
        q_abb, pose_abb = verificacion.pose_controlador(panel.mover)
        now = panel.clock()
        con_pose = punto.q is None
        check = verificacion.evaluar(destino, q_ini, punto.pose if con_pose else None, tray.herramienta,
                                     (q_abb, pose_abb, now), False, panel.simulated, now, True, q_ini)
        motivos = []
        if not check['limites_ok']:
            motivos.append('destino fuera de los límites articulares')
        modelo = check['controlador']
        if modelo is None or not modelo['valida']:
            motivos.append('sin comparación reciente con el controlador ABB')
        elif not modelo['ok']:
            motivos.append(f"modelo y controlador difieren {modelo['pos_mm']:.3f} mm / {modelo['rot_deg']:.3f}°")
        if con_pose:
            if not check['ik_fk']['ok']:
                motivos.append(f"IK→FK con error {check['ik_fk']['pos_mm']:.4f} mm / {check['ik_fk']['rot_deg']:.4f}°")
            if not check['ida_vuelta_ok']:
                motivos.append('la ida y vuelta IK(FK(q)) no recupera los ángulos')
        if motivos:
            raise Refused(f'Verificación bloqueó el tramo {tramo.indice + 1} ({tramo.desde} → {tramo.hasta}): '
                          + '; '.join(motivos) + '. El robot no se movió.')
        return check['pose_deseada']

    def _registrar(self, tray, vuelta, tramo, orden, q_ini, q_real, wanted, error_max):
        panel = self.panel
        real = pose_of(q_real, tray.herramienta)
        filas = verificacion.ejes(orden['q'], q_real, q_ini)
        dx, dy, dz = (r - w for r, w in zip(real[:3], wanted[:3]))
        fila = {'vuelta': vuelta, 'tramo': tramo.indice + 1, 'desde': tramo.desde, 'hasta': tramo.hasta,
                'tipo': orden['tipo'], 'q_pedida': orden['q'], 'q_real': q_real,
                'error_deg': [f['error_deg'] for f in filas], 'error_pct': [f['error_pct'] for f in filas],
                'dx_mm': dx, 'dy_mm': dy, 'dz_mm': dz, 'pos_mm': math.sqrt(dx * dx + dy * dy + dz * dz),
                'max_error_deg': error_max}
        with self.mutex:
            self.resultados.append(fila)
            self.esperada = list(q_real)
        pct = ', '.join(f"J{f['eje']} {f['error_deg']:+.3f}°" + ('' if f['error_pct'] is None else f" ({f['error_pct']:.2f} %)")
                        for f in filas)
        panel.say(f"LLEGADA a {tramo.hasta}: TCP real − pedido dx {dx:+.3f}, dy {dy:+.3f}, dz {dz:+.3f} mm; ejes: {pct}.")

    # ---------- pausa ----------
    def pausar(self):
        with self.mutex:
            if self.fase != 'ejecutando':
                raise Refused('No hay ninguna trayectoria en ejecución.')
            self.pausa.set()
            self.mensaje = 'Pausa pedida: se detendrá al terminar el tramo en curso.'
        self.panel.say(self.mensaje + ' Para parar YA: habilitador, Stop o paro de emergencia.')
        return self.estado()

    def reanudar(self):
        with self.mutex:
            if self.fase != 'pausada':
                raise Refused('La trayectoria no está pausada.')
            esperada = list(self.esperada)
        q = self.leer_q()
        error = max(abs(a - b) for a, b in zip(q, esperada))
        if error > TOL_POSTURA_DEG:
            raise Refused(f'El robot no está en el punto donde se pausó (difiere {error:.3f}°): no se reanuda. '
                          'Cancelar y volver a planificar.')
        with self.mutex:
            self.fase, self.mensaje = 'ejecutando', 'Reanudando.'
        self.continuar.set()
        return self.estado()

    # ---------- vista previa ----------
    def vista_previa(self, body):
        factor = body.get('factor', 1)
        if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not 0 < factor <= FACTOR_MAX:
            raise Refused(f'El factor de velocidad debe estar entre 0 y {FACTOR_MAX:g}.')
        tray, plan, _, _ = self._planear(body)
        self._reservar(vista=True)
        self.panel.say(f'Vista previa de «{tray.nombre}» (x{factor:g}): el robot real no se mueve.')
        hilo = threading.Thread(target=self._animar, args=(plan, float(factor)), daemon=True, name='panel-vista-previa')
        self.panel.worker = hilo
        hilo.start()
        return {'vista_previa': self.estado()['vista_previa']}

    def _poner_objetivo(self, q):
        with self.panel.mutex:
            self.panel.target, self.panel.desired, self.panel.reachable = [float(v) for v in q], None, True

    def _animar(self, plan, factor):
        panel = self.panel
        try:
            tramos = [(t, t.opciones[t.tipo].muestras) for t in plan.tramos if t.opciones]
            tramos = [(t, m) for t, m in tramos if m is not None and len(m.t) > 1]
            total = sum(float(m.t[-1] - m.t[0]) for _, m in tramos) or 1.
            hecho = 0.
            for tramo, m in tramos:
                t = np.asarray(m.t, dtype=float) - float(m.t[0])
                q = np.asarray(m.q, dtype=float)
                s = 0.
                while s < t[-1]:
                    if panel.cancel.is_set():
                        raise Refused('Vista previa cancelada.')
                    self._poner_objetivo([np.interp(s, t, q[:, j]) for j in range(6)])
                    self.progreso_vista = min(1., (hecho + s) / total)
                    self.sleep(DT_VISTA_S)
                    s += DT_VISTA_S * factor
                hecho += float(t[-1])
            if plan.tramos:
                self._poner_objetivo(plan.tramos[-1].qf)
            panel.say('Vista previa terminada: el objetivo naranja queda en el último punto.')
        except Refused as exc:
            panel.say(str(exc))
        except Exception as exc:
            panel.say(f'Vista previa detenida: {exc}')
        finally:
            self.previsualizando, self.progreso_vista = False, 0.

    # ---------- salida ----------
    def estado(self):
        with self.mutex:
            return {'fase': self.fase, 'nombre': self.nombre, 'vuelta': self.vuelta, 'vueltas': self.vueltas,
                    'tramo': self.tramo, 'total': self.total, 'actual': self.actual, 'mensaje': self.mensaje,
                    'resultados': list(self.resultados),
                    'vista_previa': {'activa': self.previsualizando, 'progreso': self.progreso_vista}}
