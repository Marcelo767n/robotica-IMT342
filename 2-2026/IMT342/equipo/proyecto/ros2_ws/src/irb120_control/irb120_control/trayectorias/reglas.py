"""Reglas de seguridad del Hito 2 evaluadas a lo largo de una trayectoria muestreada.

Unidades: grados, mm, s, N·m. Cada regla devuelve una `Regla` con estado 'ok' | 'aviso' | 'falla',
el peor valor, su umbral, el instante `t` del peor valor y una frase en español.
"""
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from irb120_control.analisis.modelo import hito2


@dataclass(frozen=True)
class Tolerancias:
    """Tabla de ARQUITECTURA_TRAYECTORIAS.md (más estrictas que el Hito 2)."""
    sigma_aviso: float = 0.04
    sigma_bloqueo: float = 0.02
    cond_aviso: float = 150.
    cond_bloqueo: float = 500.
    margen_aviso_deg: float = 15.
    margen_bloqueo_deg: float = 10.
    vel_aviso: float = 0.70       # fracción de la velocidad máxima del eje
    vel_bloqueo: float = 0.85
    acc_aviso: float = 0.70       # fracción de la aceleración del perfil
    acc_bloqueo: float = 1.0
    par_aviso: float = 0.70       # fracción de τ_ref
    par_bloqueo: float = 1.0
    salto_rama_deg: float = 5.
    z_aviso_mm: float = 100.
    z_bloqueo_mm: float = 30.
    ik_mm: float = 1e-3
    ik_deg: float = 1e-3


TOLERANCIAS = Tolerancias()


@dataclass
class Regla:
    nombre: str
    estado: str = 'ok'           # ok | aviso | falla
    valor: float | None = None
    limite: float | None = None
    t: float | None = None
    detalle: str = ''

    def to_dict(self):
        return {'nombre': self.nombre, 'estado': self.estado, 'valor': self.valor, 'limite': self.limite,
                't': self.t, 'detalle': self.detalle}


@dataclass
class Muestras:
    """Trayectoria muestreada: N muestras. q [°], qd [°/s], qdd [°/s²], tau [N·m], tcp [mm]."""
    t: np.ndarray
    q: np.ndarray
    qd: np.ndarray
    qdd: np.ndarray
    tau: np.ndarray
    sigma: np.ndarray
    cond: np.ndarray
    tcp: np.ndarray
    extra: dict = field(default_factory=dict)


def fmt(x, dec=2):
    """Número con coma decimal, como se muestra al usuario."""
    return f'{x:.{dec}f}'.replace('.', ',')


@lru_cache(maxsize=1)
def tau_ref():
    """τ_ref = 1,5 × máx |G(q)| por eje sobre el espacio articular (semilla fija); mín. 2 N·m en 4-6
    y, en el eje 1 (sin gravedad), el valor del eje 3."""
    h = hito2()
    lim = np.deg2rad(h['dh'].JOINT_LIMITS_DEG)
    rng = np.random.default_rng(20261120)
    qs = rng.uniform(lim[:, 0], lim[:, 1], size=(1000, 6))
    gmax = np.max(np.abs([h['dynamics'].gravity_vector(q) for q in qs]), axis=0)
    ref = 1.5 * gmax
    ref[3:] = np.maximum(ref[3:], 2.0)
    ref[0] = max(ref[0], ref[2])      # el eje 1 es vertical: sin par de gravedad; se toma el del eje 3
    ref.setflags(write=False)
    return ref


def _estado(valor, aviso, bloqueo, mayor=True):
    if mayor:
        return 'falla' if valor > bloqueo else 'aviso' if valor > aviso else 'ok'
    return 'falla' if valor < bloqueo else 'aviso' if valor < aviso else 'ok'


def _regla(nombre, estado, valor, limite, t, detalle):
    return Regla(nombre, estado, float(valor), float(limite), None if t is None else float(t), detalle)


def regla_sigma(m, tol=TOLERANCIAS):
    i = int(np.argmin(m.sigma))
    v = float(m.sigma[i])
    est = _estado(v, tol.sigma_aviso, tol.sigma_bloqueo, mayor=False)
    q5 = float(m.q[i, 4])
    donde = ' (J5 cerca de 0°)' if abs(q5) < 10. else ''
    lim = tol.sigma_bloqueo if est == 'falla' else tol.sigma_aviso
    return _regla('σ_min(J)', est, v, lim, m.t[i], f'σ_min = {fmt(v, 3)} en t = {fmt(m.t[i])} s{donde}')


def regla_cond(m, tol=TOLERANCIAS):
    c = np.where(np.isfinite(m.cond), m.cond, np.inf)
    i = int(np.argmax(c))
    v = float(c[i])
    est = _estado(v, tol.cond_aviso, tol.cond_bloqueo)
    lim = tol.cond_bloqueo if est == 'falla' else tol.cond_aviso
    return _regla('κ(J)', est, v, lim, m.t[i], f'κ = {fmt(v, 0)} en t = {fmt(m.t[i])} s')


def regla_margen(m, tol=TOLERANCIAS):
    lim = hito2()['dh'].JOINT_LIMITS_DEG
    marg = np.minimum(m.q - lim[:, 0], lim[:, 1] - m.q)          # N×6
    i, j = np.unravel_index(int(np.argmin(marg)), marg.shape)
    v = float(marg[i, j])
    est = _estado(v, tol.margen_aviso_deg, tol.margen_bloqueo_deg, mayor=False)
    umbral = tol.margen_bloqueo_deg if est == 'falla' else tol.margen_aviso_deg
    return _regla('Margen a los límites', est, v, umbral, m.t[i],
                  f'margen = {fmt(v, 1)}° en t = {fmt(m.t[i])} s (J{j + 1} en {fmt(m.q[i, j], 1)}°)')


def regla_velocidad(m, tol=TOLERANCIAS):
    vmax = np.rad2deg(hito2()['dh'].MAX_SPEED_RAD_S)
    r = np.abs(m.qd) / vmax
    i, j = np.unravel_index(int(np.argmax(r)), r.shape)
    v = float(r[i, j])
    est = _estado(v, tol.vel_aviso, tol.vel_bloqueo)
    umbral = tol.vel_bloqueo if est == 'falla' else tol.vel_aviso
    return _regla('Velocidad articular', est, v, umbral, m.t[i],
                  f'J{j + 1} al {fmt(100 * v, 0)} % de su máxima ({fmt(vmax[j], 0)} °/s) en t = {fmt(m.t[i])} s')


def regla_aceleracion(m, amax_deg_s2, tol=TOLERANCIAS, construido=False):
    """Aceleración frente a la del perfil. `construido`: el LSPB la respeta por construcción (articular),
    así que solo se bloquea si la supera; el aviso del 70 % no aplica."""
    r = np.abs(m.qdd) / np.asarray(amax_deg_s2)
    i, j = np.unravel_index(int(np.argmax(r)), r.shape)
    v = float(r[i, j])
    aviso = np.inf if construido else tol.acc_aviso
    est = _estado(v, aviso, tol.acc_bloqueo + (1e-6 if construido else 0.))
    umbral = tol.acc_bloqueo if est == 'falla' else tol.acc_aviso
    return _regla('Aceleración articular', est, v, umbral, m.t[i],
                  f'J{j + 1} al {fmt(100 * v, 0)} % de la aceleración del perfil en t = {fmt(m.t[i])} s')


def regla_par(m, tol=TOLERANCIAS):
    ref = tau_ref()
    r = np.abs(m.tau) / ref
    i, j = np.unravel_index(int(np.argmax(r)), r.shape)
    v = float(r[i, j])
    est = _estado(v, tol.par_aviso, tol.par_bloqueo)
    umbral = tol.par_bloqueo if est == 'falla' else tol.par_aviso
    return _regla('Par articular', est, v, umbral, m.t[i],
                  f'J{j + 1}: {fmt(abs(m.tau[i, j]), 1)} N·m = {fmt(100 * v, 0)} % de τ_ref ({fmt(ref[j], 1)} N·m) '
                  f'en t = {fmt(m.t[i])} s')


def regla_salto_rama(m, tol=TOLERANCIAS):
    d = np.abs(np.diff(m.q, axis=0))
    if d.size == 0:
        return _regla('Salto de rama', 'ok', 0., tol.salto_rama_deg, None, 'sin saltos entre muestras')
    i, j = np.unravel_index(int(np.argmax(d)), d.shape)
    v = float(d[i, j])
    est = 'falla' if v > tol.salto_rama_deg else 'ok'
    return _regla('Salto de rama', est, v, tol.salto_rama_deg, m.t[i + 1],
                  f'salto máximo de {fmt(v, 1)}° en J{j + 1} en t = {fmt(m.t[i + 1])} s'
                  + (' (cambio de configuración)' if est == 'falla' else ''))


def regla_altura(m, tol=TOLERANCIAS):
    i = int(np.argmin(m.tcp[:, 2]))
    v = float(m.tcp[i, 2])
    est = _estado(v, tol.z_aviso_mm, tol.z_bloqueo_mm, mayor=False)
    umbral = tol.z_bloqueo_mm if est == 'falla' else tol.z_aviso_mm
    return _regla('Altura del TCP', est, v, umbral, m.t[i],
                  f'z mínima = {fmt(v, 1)} mm en t = {fmt(m.t[i])} s')


def regla_ik_fk(nombre_punto, err_mm, err_deg, tol=TOLERANCIAS):
    est = 'falla' if (err_mm > tol.ik_mm or err_deg > tol.ik_deg) else 'ok'
    return _regla(f'IK→FK en «{nombre_punto}»', est, err_mm, tol.ik_mm, None, f'error {fmt(err_mm, 5)} mm y {fmt(err_deg, 5)}° al volver con FK')


def evaluar_muestras(m, amax_deg_s2, tol=TOLERANCIAS, lineal=False):
    """Todas las reglas que dependen de las muestras. El salto de rama solo aplica al tramo lineal."""
    reglas = [regla_sigma(m, tol), regla_cond(m, tol), regla_margen(m, tol), regla_velocidad(m, tol),
              regla_aceleracion(m, amax_deg_s2, tol, construido=not lineal), regla_par(m, tol),
              regla_altura(m, tol)]
    if lineal:
        reglas.append(regla_salto_rama(m, tol))
    return reglas
