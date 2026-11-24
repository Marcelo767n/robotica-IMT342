"""Planificador de trayectorias A → B → C → A: elige articular o lineal por tramo con las reglas del Hito 2.

Unidades de la interfaz: grados, mm, s, N·m. Dentro se usa rad y m (como el Hito 2).
"""
from dataclasses import dataclass, field
import math

import numpy as np

from irb120_control.analisis.modelo import hito2
from irb120_control.trayectorias.modelo import Trayectoria
from irb120_control.trayectorias.reglas import (TOLERANCIAS, Muestras, Regla, Tolerancias, evaluar_muestras, fmt,
                                                regla_ik_fk)

DT_S = 0.02                # muestreo objetivo
N_MIN, N_MAX = 50, 400
N_DINAMICA = 14            # la dinámica completa cuesta ~7 ms por muestra: se calcula en N_DINAMICA y se interpola
V_LINEAL_MM_S = 250.       # velocidad cartesiana al 100 %
RAMPA_S = 0.25             # mismo supuesto que default_limits del Hito 2
MM_POR_GRADO = 2.          # longitud equivalente de un giro puro (solo para dimensionar el perfil lineal)
UMBRAL_QUIETO_DEG = 0.01
ELEVACION_MM = 100.


@dataclass
class Evaluacion:
    tipo: str
    factible: bool
    duracion_s: float
    reglas: list = field(default_factory=list)
    muestras: Muestras | None = None

    def fallas(self):
        return [r for r in self.reglas if r.estado == 'falla']

    def avisos(self):
        return [r for r in self.reglas if r.estado == 'aviso']


@dataclass
class Tramo:
    indice: int
    desde: str
    hasta: str
    q0: list
    qf: list
    tipo: str                  # elegido
    motivo: str
    opciones: dict
    ok: bool
    sugerencias: list = field(default_factory=list)
    pose_tool0_fin: list = field(default_factory=list)   # [x, y, z mm, qw, qx, qy, qz] de la brida en base


@dataclass
class Plan:
    tramos: list
    ok: bool
    resumen: str
    q_puntos: list
    duracion_s: float
    tolerancias: Tolerancias


# ------------------------------------------------------------------ utilidades cinemáticas

def _fk(q_deg, tcp=True):
    dh = hito2()['dh']
    q = np.deg2rad(q_deg)
    return dh.forward_kinematics_tcp(q) if tcp else dh.forward_kinematics(q)


def _vec6(v, que):
    a = np.asarray(v, dtype=float) if isinstance(v, (list, tuple, np.ndarray)) else None
    if a is None or a.shape != (6,) or not np.all(np.isfinite(a)):
        raise ValueError(f'{que}: se esperan 6 ángulos finitos en grados.')
    return a


def _pose_tool0(q_deg):
    """[x, y, z mm, qw, qx, qy, qz] de la brida (tool0) en base_link."""
    T = _fk(q_deg, tcp=False)
    x, y, z, w = hito2()['transforms'].matrix_to_quaternion(T[:3, :3])
    return [float(v) for v in (*(T[:3, 3] * 1000.), w, x, y, z)]


def _errores_fk(T_pedida, q_deg):
    dh = hito2()['dh']
    T = _fk(q_deg)
    return dh.position_error_m(T_pedida, T) * 1000., math.degrees(dh.rotation_error_rad(T_pedida, T))


def _en_limites(q_deg):
    lim = hito2()['dh'].JOINT_LIMITS_DEG
    return [j + 1 for j in range(6) if not lim[j, 0] <= q_deg[j] <= lim[j, 1]]


def _resolver_puntos(tray, q_inicio, tol):
    """q de cada punto (rama de Pieper cercana al punto anterior). Devuelve (q_puntos, T_tcp, errores, fallos)."""
    h = hito2()
    pieper, transforms, dh = h['pieper'], h['transforms'], h['dh']
    q_puntos, Ts, errores, fallos = [], [], [], {}
    ref = np.asarray(q_inicio, dtype=float)
    for i, p in enumerate(tray.puntos):
        q, T, err = None, None, (0., 0.)
        if p.q is not None:
            fuera = _en_limites(p.q)
            if fuera:
                fallos[i] = f'Punto «{p.nombre}»: ángulos fuera de los límites en J{", J".join(map(str, fuera))}.'
            else:
                q, T = list(p.q), _fk(p.q)
        else:
            T = transforms.pose_from_xyz_rpy_deg(*(v / 1000. for v in p.pose[:3]), *p.pose[3:])
            if tray.herramienta == 'brida':
                T = T @ dh.tcp_transform()
            report = pieper.analyze_pose(T, np.deg2rad(ref))
            elegido = next((d for d in pieper.rank_candidates(
                report, np.deg2rad(ref), min_sigma=tol.sigma_bloqueo, min_margin_deg=tol.margen_bloqueo_deg)
                if d.rank == 1), None)
            if elegido is None:
                if not report.reachable:
                    fallos[i] = (f'Punto «{p.nombre}» fuera de alcance: la muñeca queda a '
                                 f'{fmt(report.shoulder_to_wrist_m * 1000, 0)} mm del hombro o la orientación no es '
                                 'alcanzable con ninguna rama.')
                else:
                    fallos[i] = f'Punto «{p.nombre}»: ninguna rama cabe en los límites articulares.'
            else:
                q = [float(v) for v in np.rad2deg(elegido.candidate.q)]
                err = _errores_fk(T, q)
        q_puntos.append(q)
        Ts.append(T)
        errores.append(err)
        if q is not None:
            ref = np.asarray(q)
    return q_puntos, Ts, errores, fallos


# ------------------------------------------------------------------ muestras

def _muestras(t, q_deg, qd_deg, qdd_deg):
    """Calcula σ_min, κ, TCP y par (dinámica completa en pocos puntos, interpolada) de una trayectoria."""
    h = hito2()
    dh, jac, dyn = h['dh'], h['jacobian'], h['dynamics']
    n = len(t)
    qr = np.deg2rad(q_deg)
    sigma, cond, tcp = np.empty(n), np.empty(n), np.empty((n, 3))
    for k in range(n):
        s = np.linalg.svd(jac.geometric_jacobian(qr[k]), compute_uv=False)
        sigma[k], cond[k] = s[-1], (s[0] / s[-1] if s[-1] > 0 else np.inf)
        tcp[k] = dh.forward_kinematics_tcp(qr[k])[:3, 3] * 1000.
    idx = np.unique(np.linspace(0, n - 1, min(n, N_DINAMICA)).round().astype(int))
    qdr, qddr = np.deg2rad(qd_deg), np.deg2rad(qdd_deg)
    tau_sub = np.array([dyn.inverse_dynamics(qr[k], qdr[k], qddr[k]) for k in idx])
    tau = np.column_stack([np.interp(t, t[idx], tau_sub[:, j]) for j in range(6)])
    return Muestras(t, q_deg, qd_deg, qdd_deg, tau, sigma, cond, tcp)


def _n_muestras(duracion):
    return int(min(N_MAX, max(N_MIN, math.ceil(duracion / DT_S) + 1)))


def _articular(q0, qf, pct, tol):
    lspb = hito2()['lspb']
    vmax, amax = lspb.default_limits(pct / 100.)
    tr = lspb.plan_lspb(np.deg2rad(q0), np.deg2rad(qf), vmax, amax)
    t = np.linspace(0., tr.tf, _n_muestras(tr.tf))
    q, qd, qdd = (np.rad2deg(a) for a in tr.sample_many(t))
    m = _muestras(t, q, qd, qdd)
    return Evaluacion('articular', True, float(tr.tf), evaluar_muestras(m, np.rad2deg(amax), tol), m)


def _slerp(R0, Rf, u):
    tr = hito2()['transforms']
    a = np.array(tr.matrix_to_quaternion(R0))
    b = np.array(tr.matrix_to_quaternion(Rf))
    if a @ b < 0:
        b = -b
    om = math.acos(min(1., a @ b))
    if om < 1e-9:
        return [R0] * len(u)
    sa = math.sin(om)
    quats = [(math.sin((1 - s) * om) * a + math.sin(s * om) * b) / sa for s in u]
    return [tr.quaternion_to_matrix(*qq) for qq in quats]


def _lineal(q0, qf, pct, tol):
    h = hito2()
    pieper, lspb = h['pieper'], h['lspb']
    T0, Tf = _fk(q0, tcp=False), _fk(qf, tcp=False)
    p0, pf = T0[:3, 3] * 1000., Tf[:3, 3] * 1000.
    ang = math.degrees(h['dh'].rotation_error_rad(T0, Tf))
    largo = max(float(np.linalg.norm(pf - p0)), MM_POR_GRADO * ang)
    v = V_LINEAL_MM_S * pct / 100.
    tr = lspb.plan_lspb([0.], [largo], [v], [v / RAMPA_S])
    n = _n_muestras(tr.tf)
    t = np.linspace(0., tr.tf, n)
    u = np.clip(np.array([tr.sample(x)[0][0] for x in t]) / largo, 0., 1.) if largo > 0 else np.zeros(n)
    Rs = _slerp(T0[:3, :3], Tf[:3, :3], u)
    q = np.empty((n, 6))
    q[0], q[-1] = np.deg2rad(q0), np.deg2rad(qf)
    w = pieper.DEFAULT_WEIGHTS
    amax_deg = np.rad2deg(lspb.default_limits(pct / 100.)[1])
    for k in range(1, n - 1):
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = Rs[k], (p0 + u[k] * (pf - p0)) / 1000.
        cands = [c for c in pieper.enumerate_candidates(T, q[k - 1]) if c.q is not None]
        if not cands:
            regla = Regla('Alcance', 'falla', None, None, float(t[k]),
                          f'fuera de alcance en t = {fmt(t[k])} s: ninguna rama de la IK cabe en los límites')
            return Evaluacion('lineal', False, float(tr.tf), [regla], None)
        q[k] = min((np.asarray(c.q) for c in cands), key=lambda c: float(np.linalg.norm(w * (c - q[k - 1]))))
    q_deg = np.rad2deg(q)
    qd = np.gradient(q_deg, t, axis=0)
    qdd = np.gradient(qd, t, axis=0)
    m = _muestras(t, q_deg, qd, qdd)
    return Evaluacion('lineal', True, float(tr.tf), evaluar_muestras(m, amax_deg, tol, lineal=True), m)


def _evaluar(tipo, q0, qf, pct, tol, extra):
    ev = (_articular if tipo == 'articular' else _lineal)(q0, qf, pct, tol)
    ev.reglas += extra
    ev.factible = ev.factible and not ev.fallas()
    return ev


# ------------------------------------------------------------------ elección y sugerencias

def _peor(ev):
    f = ev.fallas()
    return f[0].detalle if f else 'sin detalle'


def _sigma_min(ev):
    r = next((r for r in ev.reglas if r.nombre == 'σ_min(J)'), None)
    return -1. if r is None or r.valor is None else r.valor


def _hay_aviso_singular(ev):
    return any(r.nombre in ('σ_min(J)', 'κ(J)') and r.estado != 'ok' for r in ev.reglas)


def _elegir(ops, forzado):
    """(tipo, motivo, ok) según las reglas de elección del contrato."""
    art, lin = ops['articular'], ops['lineal']
    if forzado:
        ev = ops[forzado]
        if ev.factible:
            return forzado, f'Tipo {forzado} forzado por el punto ({fmt(ev.duracion_s)} s).', True
        return forzado, f'El tipo {forzado} forzado por el punto falla: {_peor(ev)}.', False
    fact = [ev for ev in (art, lin) if ev.factible]
    if not fact:
        return 'articular', (f'Ninguna opción es factible. Articular: {_peor(art)}. Lineal: {_peor(lin)}.'), False
    if len(fact) == 1:
        ev = fact[0]
        otra = lin if ev is art else art
        return ev.tipo, f'Solo {ev.tipo} es factible; {otra.tipo} falla: {_peor(otra)}.', True
    if _hay_aviso_singular(art) or _hay_aviso_singular(lin):
        ev = max(fact, key=_sigma_min)
        otra = lin if ev is art else art
        return ev.tipo, (f'{ev.tipo.capitalize()} se aleja más de la singularidad (σ_min mínimo '
                         f'{fmt(_sigma_min(ev), 3)} frente a {fmt(_sigma_min(otra), 3)}).'), True
    ev = min(fact, key=lambda e: (e.duracion_s, e.tipo != 'articular'))
    otra = lin if ev is art else art
    return ev.tipo, (f'Ambas son factibles; {ev.tipo} es más corta ({fmt(ev.duracion_s)} s frente a '
                     f'{fmt(otra.duracion_s)} s).'), True


def _sugerencias(ops, forzado, q0, qf, T_dest, nombre, pct, tol):
    sug = []
    if forzado and ops['lineal' if forzado == 'articular' else 'articular'].factible:
        otro = 'lineal' if forzado == 'articular' else 'articular'
        sug.append(f'Cambiar el tipo de movimiento de «{nombre}» a {otro} o a auto.')
    fallas = {r.nombre for ev in ops.values() for r in ev.fallas()}
    if fallas & {'Velocidad articular', 'Aceleración articular', 'Par articular'} and pct > 10:
        sug.append(f'Reducir la velocidad (ahora {fmt(pct, 0)} %).')
    medio = (_fk(q0)[:3, 3] + _fk(qf)[:3, 3]) * 500.
    sug.append('Añadir un punto intermedio en [%s] mm.' % ', '.join(
        fmt(v, 1) for v in (medio[0], medio[1], medio[2] + ELEVACION_MM)))
    if T_dest is not None:
        pieper = hito2()['pieper']
        ref = np.deg2rad(q0)
        report = pieper.analyze_pose(T_dest, ref)
        mejores = []
        for d in pieper.rank_candidates(report, ref, min_sigma=tol.sigma_bloqueo,
                                        min_margin_deg=tol.margen_bloqueo_deg):
            c = d.candidate
            if d.admissible and d.rank is not None and np.max(np.abs(np.rad2deg(np.asarray(c.q)) - qf)) > 1.:
                mejores.append(d)
        if mejores:
            c = min(mejores, key=lambda d: d.rank).candidate
            sug.append(f'Probar la rama codo {c.elbow} (brazo {c.arm}, muñeca {c.wrist}) para «{nombre}»: '
                       'q = [%s]°.' % ', '.join(fmt(v, 1) for v in np.rad2deg(c.q)))
    return sug


def _resumen(ok, tramos, dur):
    if ok:
        return f'Plan apto: {len(tramos)} tramos, {fmt(dur, 1)} s.'
    malos = [t for t in tramos if not t.ok]
    t = malos[0]
    return f'Plan NO apto: el tramo {t.indice + 1} ({t.desde} → {t.hasta}) falla. {t.motivo}'


# ------------------------------------------------------------------ API

def planificar(tray: Trayectoria, q_inicio: list, velocidad_pct: float, tol: Tolerancias = TOLERANCIAS) -> Plan:
    """Planifica una vuelta de la trayectoria desde la postura medida `q_inicio` [°]."""
    if isinstance(velocidad_pct, bool) or not isinstance(velocidad_pct, (int, float)) \
            or not 1. <= velocidad_pct <= 100.:
        raise ValueError('velocidad_pct debe estar entre 1 y 100.')
    q_inicio = [float(v) for v in _vec6(q_inicio, 'q_inicio')]
    if not tray.puntos:
        raise ValueError('La trayectoria no tiene puntos.')
    q_pts, Ts, errores, fallos = _resolver_puntos(tray, q_inicio, tol)
    n = len(tray.puntos)
    # destinos: cada punto y, si se cierra, el primero otra vez
    destinos = list(range(n)) + ([0] if tray.cerrar else [])
    tramos, previo, prev_nombre = [], q_inicio, 'Inicio'
    for i, d in enumerate(destinos):
        p = tray.puntos[d]
        cierre = i >= n
        forzado = None if cierre or p.tipo == 'auto' else p.tipo
        if q_pts[d] is None:
            tramos.append(Tramo(i, prev_nombre, p.nombre, list(previo), [], forzado or 'articular',
                                fallos[d], {}, False, ['Corregir el punto o acercarlo al espacio de trabajo.']))
            continue
        qf = q_pts[d]
        T_dest = Ts[d] if p.q is None else None
        pose_fin = _pose_tool0(qf)
        if max(abs(a - b) for a, b in zip(previo, qf)) < UMBRAL_QUIETO_DEG:
            ev = Evaluacion(forzado or 'articular', True, 0.)
            ops = {'articular': Evaluacion('articular', True, 0.), 'lineal': Evaluacion('lineal', True, 0.)}
            tramos.append(Tramo(i, prev_nombre, p.nombre, list(previo), list(qf), ev.tipo,
                                'Ya está en el punto: sin movimiento.', ops, True, [], pose_fin))
        else:
            extra = [regla_ik_fk(p.nombre, *errores[d], tol)]
            ops = {t: _evaluar(t, previo, qf, velocidad_pct, tol, [Regla(**r.__dict__) for r in extra])
                   for t in ('articular', 'lineal')}
            tipo, motivo, ok = _elegir(ops, forzado)
            sug = [] if ok else _sugerencias(ops, forzado, previo, qf, T_dest, p.nombre, velocidad_pct, tol)
            tramos.append(Tramo(i, prev_nombre, p.nombre, list(previo), list(qf), tipo, motivo, ops, ok, sug,
                                pose_fin))
        previo, prev_nombre = qf, p.nombre
    ok = all(t.ok for t in tramos)
    dur = sum(t.opciones[t.tipo].duracion_s for t in tramos if t.opciones)
    return Plan(tramos, ok, _resumen(ok, tramos, dur), [q if q is not None else [] for q in q_pts], dur, tol)


def a_ordenes(plan: Plan) -> list:
    """Órdenes JSON para el panel, una por tramo. Solo de un plan apto."""
    if not plan.ok:
        raise ValueError('El plan no es apto: no se generan órdenes.')
    return [{'tramo': t.indice, 'tipo': t.tipo, 'q': [float(v) for v in t.qf],
             'pose_tool0': [float(v) for v in t.pose_tool0_fin]} for t in plan.tramos]
