"""Cálculos del Hito 2 sobre la pose del panel. Puros: sin red ni interfaz.

Unidades de entrada/salida: grados, mm, s, N·m. Internamente el Hito 2 trabaja en rad y m.
"""
from functools import lru_cache
import math

import numpy as np

from irb120_control.analisis.modelo import hito2

TOL_MM = 1e-3          # criterio pedido: una milésima de milímetro
TOL_DEG = 1e-3
SINGULAR_SIGMA = 1e-2  # mismo umbral que rank_candidates del Hito 2
LSPB_MUESTRAS = 200
DINAMICA_MUESTRAS = 41
VELOCIDAD_HITO2_PCT = 25.  # default_limits(0.25) es el perfil presentado en el Hito 2


def _wrap(deg):
    return (deg + 180.) % 360. - 180.


def _pose_matrix(pose):
    t = hito2()['transforms']
    return t.pose_from_xyz_rpy_deg(pose[0] / 1000., pose[1] / 1000., pose[2] / 1000., *pose[3:])


def _fk(q_deg, tool):
    dh = hito2()['dh']
    q = np.deg2rad(q_deg)
    return dh.forward_kinematics_tcp(q) if tool == 'tcp' else dh.forward_kinematics(q)


def _errores(reference, measured):
    dh = hito2()['dh']
    return dh.position_error_m(reference, measured) * 1000., math.degrees(dh.rotation_error_rad(reference, measured))


def _a_tcp(T, tool):
    """La IK de Pieper del Hito 2 recibe la pose del TCP."""
    return T if tool == 'tcp' else T @ hito2()['dh'].tcp_transform()


def _pose_pedida(e):
    return _pose_matrix(e.pose_deseada) if e.pose_deseada is not None else _fk(e.objetivo, e.herramienta)


def _rama_mas_cercana(T_tcp, q_ref_deg):
    """IK de Pieper y la rama (real) más cercana a q_ref; devuelve (q_deg, candidato)."""
    pieper = hito2()['pieper']
    report = pieper.analyze_pose(T_tcp, np.deg2rad(q_ref_deg))
    best, best_cost = None, math.inf
    for candidate in report.candidates:
        q = candidate.q if candidate.q is not None else candidate.q_raw
        if q is None:
            continue
        q_deg = np.rad2deg(q)
        cost = max(abs(_wrap(a - b)) for a, b in zip(q_deg, q_ref_deg))
        if cost < best_cost:
            best, best_cost = (list(map(float, q_deg)), candidate), cost
    return best


def cinematica(e):
    """Ida y vuelta: q_IK → FK → T frente a T pedida; IK(FK(q_IK)) frente a q_IK; robot real."""
    T_pedida = _pose_pedida(e)
    T_fk = _fk(e.objetivo, e.herramienta)
    pos, rot = _errores(T_pedida, T_fk)
    rec = _rama_mas_cercana(_a_tcp(T_fk, e.herramienta), e.objetivo)
    ida_vuelta = []
    for i, q in enumerate(e.objetivo):
        q_rec = None if rec is None else rec[0][i]
        err = None if q_rec is None else _wrap(q_rec - q)
        ida_vuelta.append({'eje': i + 1, 'q_ik': q, 'q_recuperado': q_rec, 'error_deg': err,
                           'ok': err is not None and abs(err) <= TOL_DEG})
    base = e.inicio
    robot = []
    for i, (q_ik, q_med) in enumerate(zip(e.objetivo, e.medido)):
        err = q_med - q_ik
        travel = None if base is None else abs(q_ik - base[i])
        pct = abs(err) / travel * 100. if travel and travel >= .5 else None
        robot.append({'eje': i + 1, 'q_ik': q_ik, 'q_medido': q_med, 'error_deg': err, 'error_pct': pct,
                      'ok': abs(err) <= .1})
    T_med = _fk(e.medido, e.herramienta)
    pos_med, rot_med = _errores(T_pedida, T_med)
    return {'T_pedida': T_pedida, 'T_fk': T_fk, 'T_medida': T_med, 'origen': 'IK' if e.pose_deseada else 'ángulos',
            'fk': {'pos_mm': pos, 'rot_deg': rot, 'ok': pos <= TOL_MM and rot <= TOL_DEG},
            'ida_vuelta': ida_vuelta, 'rama_recuperada': None if rec is None else rec[1].branch,
            'robot': robot, 'robot_pose': {'pos_mm': pos_med, 'rot_deg': rot_med,
                                           'ok': pos_med <= .5 and rot_med <= .1}}


def ramas(e):
    """Las 8 ramas de Pieper para la pose pedida, ordenadas con el criterio del proyecto."""
    pieper = hito2()['pieper']
    T_tcp = _a_tcp(_pose_pedida(e), e.herramienta)
    reference = np.deg2rad(e.medido)
    report = pieper.analyze_pose(T_tcp, reference)
    decisions = {d.candidate.branch: d for d in pieper.rank_candidates(report, reference)}
    rows = []
    for c in report.candidates:
        check = report.checks[c.branch - 1]
        q = c.q if c.q is not None else c.q_raw
        d = decisions[c.branch]
        rows.append({'rama': c.branch, 'brazo': c.arm, 'codo': c.elbow, 'muneca': c.wrist, 'real': c.real,
                     'en_limites': c.within_limits, 'q': None if q is None else [float(v) for v in np.rad2deg(q)],
                     'e_p_mm': None if check is None else check.position_error_m * 1000.,
                     'e_R_deg': None if check is None else math.degrees(check.rotation_error_rad),
                     'sigma_min': None if not d.admissible else float(d.sigma_min),
                     'estado': d.status, 'puesto': d.rank})
    return {'veredicto': report.verdict, 'filas': rows,
            'elegida': next((r['rama'] for r in rows if r['puesto'] == 1), None)}


def trayectoria(e):
    """Perfil LSPB del Hito 2 de la postura medida al objetivo (escala de velocidad = % del panel)."""
    lspb = hito2()['lspb']
    vmax, amax = lspb.default_limits(e.velocidad_pct / 100.)
    q0, qf = np.deg2rad(e.medido), np.deg2rad(e.objetivo)
    traj = lspb.plan_lspb(q0, qf, vmax, amax)
    times = np.linspace(0., traj.tf, LSPB_MUESTRAS)
    q, qd, qdd = traj.sample_many(times)
    check = lspb.check_trajectory(traj, vmax, amax)
    return {'traj': traj, 't': times, 'q': np.rad2deg(q), 'qd': np.rad2deg(qd), 'qdd': np.rad2deg(qdd),
            'tf': traj.tf, 'tb': traj.tb, 'vmax': np.rad2deg(vmax), 'amax': np.rad2deg(amax),
            'check': {'paso': check.passed, 'error_final_deg': math.degrees(check.end_position_error),
                      'margen_vel_deg_s': math.degrees(check.velocity_margin),
                      'margen_acel_deg_s2': math.degrees(check.acceleration_margin)}}


def jacobiano(e, tray):
    jac = hito2()['jacobian']
    q = np.deg2rad(e.objetivo)
    J = jac.geometric_jacobian(q, 'tcp' if e.herramienta == 'tcp' else 'tool0')
    rank = jac.rank_analysis(J)
    sigma_t = np.array([jac.smallest_singular_value(np.deg2rad(qi)) for qi in tray['q'][::4]])
    return {'J': J, 'det': float(np.linalg.det(J)), 'sigma': rank.singular_values, 'sigma_min': float(rank.singular_values[-1]),
            'condicion': rank.condition_number, 'rango': rank.rank, 't_sigma': tray['t'][::4], 'sigma_t': sigma_t,
            'singular': float(sigma_t.min()) < SINGULAR_SIGMA}


def dinamica(e, tray):
    """Par en cada eje a lo largo de la LSPB: modelo completo y modelo 1R del hombro (J2)."""
    h = hito2()
    traj = tray['traj']
    times = np.linspace(0., traj.tf, DINAMICA_MUESTRAS)
    q, qd, qdd = traj.sample_many(times)
    tau = np.array([h['dynamics'].inverse_dynamics(a, b, c) for a, b, c in zip(q, qd, qdd)])
    model = h['dynamics_1r'].shoulder_model(traj.q0)
    inertial, gravity, total = model.torque_components(q[:, 1], qdd[:, 1])
    return {'t': times, 'tau': tau, 'tau_max': np.max(np.abs(tau), axis=0),
            'j2_1r': {'inercial': inertial, 'gravedad': gravity, 'total': total},
            'j2_1r_max': float(np.max(np.abs(total))), 'j2_completo_max': float(np.max(np.abs(tau[:, 1]))),
            'modelo_1r': {'m_kg': model.mass_kg, 'lc_m': model.lc_m, 'J_kg_m2': model.inertia_kg_m2}}


@lru_cache(maxsize=8)
def _pesado(key):
    """Ramas, LSPB, Jacobiano y dinámica: caché por clave redondeada (no cambian con el ruido de lectura)."""
    result = {'ramas': ramas(key), 'trayectoria': trayectoria(key)}
    result['jacobiano'] = jacobiano(key, result['trayectoria'])
    result['dinamica'] = dinamica(key, result['trayectoria'])
    return result


def analizar(e):
    """Todo junto. La cinemática (errores de 0,001 mm) se calcula SIEMPRE con los valores exactos;
    redondear solo sirve de clave de caché para la parte pesada."""
    return {**_pesado(redondear(e)), 'entrada': e, 'cinematica': cinematica(e)}


def redondear(e):
    """Clave de caché estable frente al ruido de lectura (milésimas de grado)."""
    r = lambda values, n=3: None if values is None else tuple(round(v, n) for v in values)
    return type(e)(r(e.medido, 2), r(e.objetivo), e.herramienta, r(e.pose_deseada), r(e.inicio, 2),
                   round(e.velocidad_pct, 1))
