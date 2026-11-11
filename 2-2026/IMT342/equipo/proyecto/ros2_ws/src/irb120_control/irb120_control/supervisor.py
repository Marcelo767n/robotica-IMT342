"""Guardas del ensayo de UN eje. Todas las magnitudes articulares aquí son grados.

Sin ROS ni red: el mismo supervisor se ensaya con tiempos/estados simulados.
No calcula colisiones ni sustituye las protecciones del controlador.
"""
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
import sys

import numpy as np
import yaml

from irb120_conexion.rutas import PROJECT
sys.path.insert(0, str(PROJECT / 'hito2'))
from irb120.dh import JOINT_LIMITS_DEG
from irb120.lspb import plan_lspb
from irb120.jacobian import geometric_jacobian


class Rejected(ValueError):
    pass


def vector(values):
    out = np.array(values, dtype=float, copy=True)
    if out.shape != (6,) or not np.isfinite(out).all():
        raise Rejected('Se necesitan exactamente seis ángulos finitos; no se aceptan ceros de relleno.')
    return out


def bounds(values):
    out = np.array(values, dtype=float, copy=True)
    if out.shape != (6, 2) or not np.isfinite(out).all() or np.any(out[:, 0] >= out[:, 1]):
        raise Rejected('Los límites deben ser seis pares [mínimo, máximo] finitos y ordenados.')
    return out


@dataclass
class Policy:
    limits: np.ndarray
    window: np.ndarray
    step: float = 1.0
    speed: float = .5
    acceleration: float = .5
    following: float = .3
    stationary: float = .01
    start_drift: float = .02
    state_timeout: float = .1
    heartbeat_timeout: float = .25
    loop_timeout: float = .05
    settle_timeout: float = 3.0
    max_session_s: float = 120.0
    min_sigma: float = .01
    expires: float = float('inf')
    expected_start: np.ndarray | None = None
    simulation_only: bool = False

    def __post_init__(self):
        self.limits, self.window = bounds(self.limits), bounds(self.window)
        if self.expected_start is not None:self.expected_start=vector(self.expected_start)
        if np.any(self.limits[:, 0] < JOINT_LIMITS_DEG[:, 0]) or np.any(self.limits[:, 1] > JOINT_LIMITS_DEG[:, 1]):
            raise Rejected('La configuración no puede ampliar los límites nominales del IRB120.')
        if np.any(self.window[:, 0] < self.limits[:, 0]) or np.any(self.window[:, 1] > self.limits[:, 1]):
            raise Rejected('La ventana de ensayo excede los límites efectivos.')
        names = ('step','speed','acceleration','following','stationary','start_drift','state_timeout',
                 'heartbeat_timeout','loop_timeout','settle_timeout','max_session_s','min_sigma')
        if any(not math.isfinite(getattr(self, n)) or getattr(self, n) <= 0 for n in names):
            raise Rejected('Los límites de velocidad, tiempo y error deben ser positivos y finitos.')
        step_limit=10. if self.simulation_only is True else 1.
        if self.step>step_limit or max(self.speed,self.acceleration)>1:
            raise Rejected(f'Paso máximo {step_limit:g}°; velocidad y aceleración máximas 1°/s y 1°/s². '
                           'El recorrido ampliado solo está habilitado en simulación.')
        if self.loop_timeout >= self.state_timeout or self.following > .5 or self.max_session_s > 300:
            raise Rejected('Límites temporales/de seguimiento incompatibles con el ensayo inicial.')
        if self.stationary>.01 or self.start_drift>.02 or self.state_timeout>.2 or self.heartbeat_timeout>.5 or self.loop_timeout>.05 or self.min_sigma<.01:
            raise Rejected('La ficha no puede relajar los máximos de reposo, deriva, vigencia o singularidad del ensayo.')

    @classmethod
    def demo(cls, q=None, margin=2., step=1.):
        q = vector([0,-20,20,0,30,0] if q is None else q)
        effective = JOINT_LIMITS_DEG + np.array([margin, -margin])
        span=max(2.,step+.5)
        return cls(effective, np.column_stack((np.maximum(q-span,effective[:,0]),np.minimum(q+span,effective[:,1]))),
                   step=step,simulation_only=True)

    @classmethod
    def physical(cls, path):
        data = yaml.safe_load(Path(path).read_text())
        if not isinstance(data, dict) or data.get('schema') != 1:
            raise Rejected('Falta la ficha de sesión EGM (schema: 1).')
        required = ('backup_verified','controller_limits_verified','joint_mapping_verified',
                    'egm_configuration_verified','comm_timeout_stop_verified','trajectory_clearance_verified',
                    'tool_and_load_verified','initial_posture_verified')
        checks = data.get('verified', {})
        missing = [k for k in required if checks.get(k) is not True]
        go = data.get('go', {})
        if missing or go.get('decision') != 'GO' or not go.get('operator') or not go.get('laboratory_responsible'):
            raise Rejected('Ficha incompleta/NO-GO. Verificar: ' + ', '.join(missing or ['operador, responsable y GO']))
        try:
            expiry = datetime.fromisoformat(str(go['valid_until'])).timestamp()
            approval = datetime.fromisoformat(str(go['approved_at'])).timestamp()
            # Las fechas deben declarar zona horaria: no se asume la zona de la máquina.
            if datetime.fromisoformat(str(go['valid_until'])).tzinfo is None or datetime.fromisoformat(str(go['approved_at'])).tzinfo is None:
                raise ValueError('Fechas sin zona horaria')
        except (KeyError, ValueError, TypeError) as exc:
            raise Rejected('El GO requiere approved_at y valid_until con zona horaria.') from exc
        now = datetime.now(timezone.utc).timestamp()
        if not approval <= now < expiry or expiry-approval > 7200:
            raise Rejected('El GO está vencido, es futuro o dura más de dos horas.')
        controller = bounds(data.get('controller_limits_deg'))
        margin = float(data.get('margin_deg', 2))
        if not math.isfinite(margin) or margin < 2:
            raise Rejected('El ensayo mantiene al menos 2° de margen a los límites.')
        effective = np.column_stack((np.maximum(controller[:,0],JOINT_LIMITS_DEG[:,0])+margin,
                                     np.minimum(controller[:,1],JOINT_LIMITS_DEG[:,1])-margin))
        settings = data.get('test', {})
        args = {name: settings.get(name) for name in ('step','speed','acceleration','following','stationary','start_drift','state_timeout',
                'heartbeat_timeout','loop_timeout','settle_timeout','max_session_s','min_sigma')}
        if any(value is None for value in args.values()):
            raise Rejected('La ficha debe declarar todos los parámetros test; no se rellenan valores físicos.')
        initial=vector(data.get('initial_joints_deg'))
        window=bounds(data.get('approved_joint_window_deg'))
        if np.max(np.abs(window-initial[:,None]))>2:
            raise Rejected('La ventana inicial no puede alejarse más de 2° de la postura aprobada.')
        return cls(effective,window,expires=expiry,expected_start=initial,**args), data


class Supervisor:
    ACTIVE = {'ARMADO','MOVIENDO','ASENTANDO','FRENANDO','MANTENIENDO','PREPARANDO'}

    def __init__(self, policy, can_send=True):
        self.policy, self.can_send = policy, can_send
        self.state = 'SIN_DATOS'
        self.reason = 'Esperando seis ángulos medidos.'
        self.q = self.target = self.reference = self.anchor = None
        self.axis = 0
        self.measured_at = self.beat_at = self.last_cycle = None
        self.history = deque()
        self.trajectory = None
        self.started = self.armed_at = self.settled_at = None
        self.start = None
        self.velocity = np.zeros(6)
        self.revision = 0
        self.plan_revision = None
        self.guidance = False

    def fault(self, message):
        self.state, self.reason = 'FALLO', message
        self.trajectory = None
        self.reference = None

    def heartbeat(self, now):
        self.beat_at = now

    def ingest(self, q, now, healthy=True, guidance=True):
        self.healthy = bool(healthy)
        self.guidance = bool(guidance)
        try:
            q = vector(q)
            if np.any(q < self.policy.limits[:,0]) or np.any(q > self.policy.limits[:,1]):
                raise Rejected('Estado medido fuera de los límites efectivos/margen. No se habilita envío.')
            if self.q is None and self.policy.expected_start is not None and np.max(np.abs(q-self.policy.expected_start))>self.policy.start_drift:
                raise Rejected('La postura inicial no coincide con la ficha aprobada; no se habilita envío.')
            if self.state in self.ACTIVE and (np.any(q<self.policy.window[:,0]) or np.any(q>self.policy.window[:,1])):
                raise Rejected('El ángulo medido salió de la ventana revisada; se detiene el envío.')
        except (ValueError, TypeError) as exc:
            self.fault(str(exc)); return
        if (not healthy or (not guidance and self.state in self.ACTIVE-{'ARMADO'})) and self.state in self.ACTIVE:
            self.fault('EGM/RAPID/motores dejaron de estar activos.'); return
        self.q, self.measured_at = q, now
        self.history.append((now,q.copy()))
        while len(self.history)>1 and self.history[1][0] < now-.6:
            self.history.popleft()
        if self.state == 'SIN_DATOS':
            self.state = 'LISTO'
            self.synchronize()

    def synchronize(self):
        if self.state in self.ACTIVE-{'MANTENIENDO','PREPARANDO'}:
            raise Rejected('Esperar MANTENIENDO antes de preparar otro ensayo.')
        if self.q is None:
            raise Rejected('No hay ángulos medidos.')
        self.anchor, self.target = self.q.copy(), self.q.copy()
        self.revision += 1
        continuing=self.reference is not None and self.state in {'MANTENIENDO','PREPARANDO'}
        if continuing:self.start=self.reference.copy()
        self.state='PREPARANDO' if continuing else 'LISTO'
        self.reason=('Manteniendo la referencia anterior; ajustar otro eje y ARMAR de nuevo.' if continuing else
                     'Vista sincronizada. Ajustar UN eje; arrastrar no envía al robot.')

    def select(self, axis):
        if type(axis) is not int or not 0 <= axis < 6:
            raise Rejected('Seleccionar J1 a J6.')
        self.synchronize()
        self.axis = axis

    def preview(self, value):
        if self.state not in {'LISTO','PREPARANDO'}:
            raise Rejected('Seleccionar/sincronizar en reposo antes de modificar el objetivo.')
        if self.target is None or not math.isfinite(float(value)):
            raise Rejected('Objetivo inválido o sin estado inicial.')
        candidate = self.anchor.copy(); candidate[self.axis] = float(value)
        if np.any(candidate < self.policy.window[:,0]) or np.any(candidate > self.policy.window[:,1]):
            raise Rejected('Objetivo fuera de la ventana articular aprobada para esta prueba.')
        if abs(value-self.anchor[self.axis]) > self.policy.step+1e-10:
            raise Rejected(f'Paso máximo por ensayo: {self.policy.step:g}°. Sincronizar antes del siguiente.')
        self.target = candidate
        self.revision += 1
        self.reason = f'J{self.axis+1}: vista previa {value:.6f}°. Todavía no se envía.'

    def fresh(self, now):
        if self.measured_at is None or not 0 <= now-self.measured_at <= self.policy.state_timeout:
            raise Rejected('Datos medidos antiguos/ausentes; se rechaza el comando.')
        if self.beat_at is None or not 0 <= now-self.beat_at <= self.policy.heartbeat_timeout:
            raise Rejected('El supervisor ROS no está actualizando su señal de vida.')

    def arm(self, now, wall=None):
        if not self.can_send:
            raise Rejected('Modo VISTA: no existe transporte de consignas habilitado.')
        if self.state not in {'LISTO','PREPARANDO'}:
            raise Rejected('Armar solo después de sincronizar y previsualizar en reposo.')
        self.fresh(now)
        if (wall if wall is not None else datetime.now(timezone.utc).timestamp()) >= self.policy.expires:
            raise Rejected('GO vencido.')
        if not self.healthy:
            raise Rejected('Faltan estados EGM válido, RAPID_RUNNING o MOTORS_ON.')
        if len(self.history)<2 or now-self.history[0][0] < .5:
            raise Rejected('Esperar al menos 0.5 s de lecturas estacionarias.')
        if np.max(np.ptp(np.array([q for _,q in self.history]),axis=0)) > self.policy.stationary:
            raise Rejected('El brazo no está quieto; no se arma la prueba.')
        if np.max(np.abs(self.q-self.anchor)) > self.policy.start_drift:
            raise Rejected('El brazo cambió desde la vista previa. Sincronizar de nuevo.')
        delta = self.target-self.q
        others = np.delete(delta,self.axis)
        if np.max(np.abs(others)) > self.policy.start_drift or abs(delta[self.axis]) > self.policy.step+1e-10:
            raise Rejected('El objetivo ya no corresponde a un único eje desde el estado actual.')
        # Las cinco referencias no seleccionadas quedan fijadas al estado medido al armar.
        continuing=self.state=='PREPARANDO'
        start=self.reference.copy() if continuing else self.q.copy()
        if np.max(np.abs(start-self.q))>self.policy.start_drift:
            raise Rejected('La referencia mantenida aún no coincide con la postura medida.')
        target = start.copy(); target[self.axis] = self.target[self.axis]
        # Guardia geométrica adicional; no sustituye revisión de colisiones del recorrido.
        for q in np.linspace(start,target,41):
            sigma=float(np.linalg.svd(geometric_jacobian(np.deg2rad(q),reference='tool0'),compute_uv=False)[-1])
            if sigma<self.policy.min_sigma:
                raise Rejected('Recorrido cercano a singularidad según el Jacobiano propio; elegir otra postura.')
        self.target = target
        self.start = self.reference = start.copy()
        self.velocity = np.zeros(6)
        if not continuing:self.armed_at=now
        self.last_cycle = now
        self.plan_revision = self.revision
        self.state, self.reason = 'ARMADO', 'Primera consigna = postura medida. Esperar EGM Guidance activo antes de EJECUTAR.'

    def execute(self, now):
        if self.state != 'ARMADO' or self.plan_revision != self.revision:
            raise Rejected('El objetivo requiere un armado nuevo; no se repiten ejecuciones.')
        self.fresh(now)
        if not self.guidance:
            raise Rejected('PC armada en mantenimiento; falta activar Guidance en el procedimiento ABB.')
        if np.max(np.abs(self.q-self.start)) > self.policy.start_drift:
            self.fault('La postura cambió antes de ejecutar; sincronizar y rearmar.')
            raise Rejected('La postura cambió antes de ejecutar; desarmar y sincronizar.')
        self.trajectory = plan_lspb(self.start,self.target,np.full(6,self.policy.speed),
                                    np.full(6,self.policy.acceleration))
        self.started = now
        self.state, self.reason = 'MOVIENDO', f'Ensayo J{self.axis+1} con LSPB; duración {self.trajectory.tf:.2f} s.'

    def cancel(self, now):
        if self.state not in self.ACTIVE:
            return
        self.brake_q = self.reference.copy()
        self.brake_v = self.velocity.copy()
        self.brake_t = now
        self.brake_duration = float(np.max(np.abs(self.brake_v))/self.policy.acceleration)
        self.state, self.reason = 'FRENANDO', 'Cancelación: desacelerar y mantener. No es una parada de emergencia.'

    def disarm(self):
        if self.state in {'MOVIENDO','FRENANDO','ASENTANDO'} or np.max(np.abs(self.velocity)) > 1e-9:
            raise Rejected('Primero cancelar y esperar MANTENIENDO; no cortar la rampa de frenado.')
        self.reference = None
        self.state, self.reason = 'LISTO', 'Envío cerrado. El controlador debe finalizar EGM según su procedimiento.'

    def cycle(self, now, wall=None):
        if self.state not in self.ACTIVE:
            if self.measured_at is not None and now-self.measured_at > self.policy.state_timeout and self.state != 'FALLO':
                self.state, self.reason = 'SIN_DATOS', 'Estado antiguo. Al recuperar se requiere sincronizar y armar.'
            return None
        try:
            self.fresh(now)
            if now-self.last_cycle > self.policy.loop_timeout or now < self.last_cycle:
                raise Rejected('El ciclo EGM se retrasó; se detiene el envío y se requiere rearme.')
            if now-self.armed_at > self.policy.max_session_s or (wall or datetime.now(timezone.utc).timestamp()) >= self.policy.expires:
                raise Rejected('Sesión/GO vencido; se detiene el envío.')
            if np.max(np.abs(self.q-self.reference)) > self.policy.following:
                raise Rejected('Error de seguimiento excesivo; se detiene el envío.')
            if self.state=='ARMADO' and np.max(np.abs(self.q-self.start))>self.policy.start_drift:
                raise Rejected('La postura cambió durante el armado; no se continúa con una referencia antigua.')
            if np.max(np.abs(np.delete(self.q-self.start,self.axis))) > self.policy.start_drift:
                raise Rejected('Se movió una junta no seleccionada; se detiene el ensayo.')
            q, velocity = self.reference.copy(), np.zeros(6)
            if self.state == 'MOVIENDO':
                t=now-self.started
                q,velocity,_=self.trajectory.sample(t)
                if t>=self.trajectory.tf:
                    self.state, self.settled_at = 'ASENTANDO', now
                    self.reason = 'Objetivo enviado; comprobando llegada medida.'
            elif self.state == 'FRENANDO':
                t=min(max(now-self.brake_t,0),self.brake_duration)
                a=-np.sign(self.brake_v)*self.policy.acceleration
                q=self.brake_q+self.brake_v*t+.5*a*t*t
                velocity=self.brake_v+a*t
                if t>=self.brake_duration:
                    self.state,self.reason='MANTENIENDO','Cancelado y detenido en referencia. Desarmar antes de otro eje.'
                    velocity=np.zeros(6)
            elif self.state == 'ASENTANDO':
                if np.max(np.abs(self.q-self.target)) <= self.policy.start_drift:
                    self.state,self.reason='MANTENIENDO','Llegada medida dentro del criterio articular de esta sesión.'
                elif now-self.settled_at>self.policy.settle_timeout:
                    raise Rejected('El robot no alcanzó el objetivo en el tiempo de asentamiento.')
            if not np.isfinite(q).all() or np.any(q<self.policy.window[:,0]) or np.any(q>self.policy.window[:,1]):
                raise Rejected('La referencia salió de la ventana aprobada; no se transmite.')
            if np.max(np.abs(velocity)) > self.policy.speed+1e-9:
                raise Rejected('La referencia excede la velocidad configurada.')
            self.reference,self.velocity,self.last_cycle=q.copy(),velocity.copy(),now
            return q.copy()
        except Rejected as exc:
            self.fault(str(exc))
            return None
