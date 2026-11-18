"""Verificación del objetivo antes y durante el movimiento (lo que pidió el ingeniero).

  1 · IK → FK      FK(q_objetivo) frente a la pose deseada: comprueba la cinemática inversa.
  2 · Robot real   FK(q_medido) frente a la pose deseada: error en tiempo real hasta la llegada.
  3 · Controlador  FK propia de tool0 frente a la pose que informa el propio ABB (robtarget):
                   comprueba que nuestro modelo coincide con el brazo real.
El envío solo se permite si la pose es alcanzable, el objetivo respeta los límites y los
errores 1 y 3 están dentro de tolerancia. Sin ROS: se prueba solo.
"""
import functools
import math
import time

from irb120_control.rws_j6 import Refused
from irb120_control.panel.cinematica import kinematics, pose_of
from irb120_control.panel.limites import clean_target

TOLERANCIAS = {'ik_mm': 0.001, 'ik_deg': 0.001,         # criterio del Hito 2 (10⁻⁶ m); Pieper da ~1e-12
               'ida_vuelta_deg': 0.001,                 # IK(FK(q)) frente a q, eje por eje
               'llegada_mm': 0.5, 'llegada_deg': 0.1,   # 0,016° por eje a ~0,5 m ≈ 0,14 mm
               'modelo_mm': 0.5, 'modelo_deg': 0.1}     # FK propia frente al ABB (04/11: < 0,001 mm)
CONTROLLER_MAX_AGE_S = 5.
MIN_TRAVEL_DEG = 0.5       # por debajo, el error en % de ese eje no tiene sentido
MIN_TRAVEL_MM = 1.
ROBTARGET = '/rw/motionsystem/mechunits/ROB_1/robtarget'


def pose_error(a, b):
    """Error entre dos poses [mm, °]: distancia en mm y ángulo de la rotación relativa en grados."""
    np, _, _, transforms = kinematics()
    distance = math.dist(a[:3], b[:3])
    ra = transforms.rpy_to_matrix(*np.deg2rad(a[3:]))
    rb = transforms.rpy_to_matrix(*np.deg2rad(b[3:]))
    cosine = (np.trace(ra.T @ rb) - 1.) / 2.
    return distance, math.degrees(math.acos(max(-1., min(1., float(cosine)))))


def matriz(pose):
    """[x, y, z mm, roll, pitch, yaw °] → matriz homogénea 4×4 (metros)."""
    np, _, _, transforms = kinematics()
    return transforms.pose_from_xyz_rpy_deg(*(v / 1000. for v in pose[:3]), *pose[3:])


def fk_matriz(q_deg, tool):
    """FK del Hito 2: T base→TCP (150 mm) o base→brida, en metros."""
    np, dh, _, _ = kinematics()
    forward = dh.forward_kinematics_tcp if tool == 'tcp' else dh.forward_kinematics
    return forward(np.deg2rad(q_deg))


@functools.lru_cache(maxsize=64)
def _ida_vuelta(q, tool):
    np, dh, pieper, _ = kinematics()
    T = fk_matriz(list(q), tool)
    if tool != 'tcp':
        T = T @ dh.tcp_transform()
    report = pieper.analyze_pose(T, np.deg2rad(q))
    best, best_error = None, math.inf
    for candidate in report.candidates:
        values = candidate.q if candidate.q is not None else candidate.q_raw
        if values is None:
            continue
        recovered = [float(v) for v in np.rad2deg(values)]
        error = max(abs((r - g + 180.) % 360. - 180.) for r, g in zip(recovered, q))
        if error < best_error:
            best, best_error = recovered, error
    return best


def ida_vuelta(target, tool):
    """IK(FK(q)) frente a q, eje por eje (rama más cercana a q)."""
    recovered = _ida_vuelta(tuple(round(v, 9) for v in target), tool)
    rows = []
    for index, goal in enumerate(target):
        value = None if recovered is None else recovered[index]
        error = None if value is None else abs((value - goal + 180.) % 360. - 180.)
        rows.append({'eje': index + 1, 'q_ik': goal, 'q_recuperado': value, 'error_deg': error})
    ok = recovered is not None and all(r['error_deg'] <= TOLERANCIAS['ida_vuelta_deg'] for r in rows)
    return rows, ok


def pose_controlador(mover):
    """Pose de tool0 que informa el ABB (Base/tool0/wobj0) en [mm, °] y los ejes leídos justo antes.

    Debe llamarse con mover.lock tomado. El simulador devuelve su propia FK."""
    if hasattr(mover, 'controller_pose'):
        return mover.controller_pose()
    from irb120_conexion.comunicacion.lectura_rws import read_resource
    from irb120_conexion.comunicacion.muestra_fk import parse_pose
    np, _, _, transforms = kinematics()
    q = mover.joints()[0]
    result = read_resource(mover.session, mover.base, ROBTARGET, mover.timeout)
    if result['http_status'] != 200:
        raise Refused(f"robtarget: HTTP {result['http_status']}")
    pose = parse_pose(result['records'])
    w, x, y, z = pose['quaternion_wxyz']
    rotation = transforms.quaternion_to_matrix(x, y, z, w)
    return q, [*pose['xyz_mm'], *transforms.matrix_to_rpy_deg(rotation)]


def _fila(distance, angle, mm, deg):
    return {'pos_mm': distance, 'rot_deg': angle, 'ok': distance <= mm and angle <= deg}


def ejes(target, measured, start):
    """Error de cada eje en grados y en % del recorrido de la última orden (null si no aplica)."""
    rows = []
    for index, goal in enumerate(target):
        value = None if measured is None else measured[index]
        error = None if value is None else value - goal
        travel = None if start is None else abs(goal - start[index])
        pct = (abs(error) / travel * 100.) if error is not None and travel and travel >= MIN_TRAVEL_DEG else None
        rows.append({'eje': index + 1, 'objetivo': goal, 'medido': value, 'error_deg': error, 'error_pct': pct})
    return rows


def evaluar(target, measured, desired, tool, abb=None, busy=False, simulated=False, now=None,
            reachable=True, start=None):
    """Construye el bloque «verificacion» del estado. desired = pose pedida por IK o None."""
    t = TOLERANCIAS
    if target is None:
        return None
    origin = 'ik' if desired is not None else 'angulos'
    try:
        clean_target(target)
        limits_ok, limits_reason = True, None
    except Refused as exc:
        limits_ok, limits_reason = False, str(exc)
    target_pose = pose_of(target, tool)
    wanted = desired if desired is not None else target_pose
    ik = _fila(*pose_error(target_pose, wanted), t['ik_mm'], t['ik_deg'])
    robot = None
    if measured is not None:
        real = pose_of(measured, tool)
        robot = _fila(*pose_error(real, wanted), t['llegada_mm'], t['llegada_deg'])
        robot['ejes_deg'] = [m - g for m, g in zip(measured, target)]
        robot['max_eje_deg'] = max(abs(v) for v in robot['ejes_deg'])
        robot['dx_mm'], robot['dy_mm'], robot['dz_mm'] = (r - w for r, w in zip(real[:3], wanted[:3]))
        travel = None if start is None else math.dist(pose_of(start, tool)[:3], wanted[:3])
        robot['pos_pct'] = robot['pos_mm'] / travel * 100. if travel and travel >= MIN_TRAVEL_MM else None
    controller = None
    if abb is not None:
        q_abb, abb_pose, read_at = abb
        age = (now if now is not None else time.monotonic()) - read_at
        controller = _fila(*pose_error(pose_of(q_abb, 'brida'), abb_pose), t['modelo_mm'], t['modelo_deg'])
        controller.update(edad_s=age, fuente='simulado' if simulated else 'RWS robtarget',
                          valida=not busy and age <= CONTROLLER_MAX_AGE_S)
    reasons = []
    if not reachable:
        reasons.append('la pose pedida no es alcanzable')
    if not limits_ok:
        reasons.append('fuera de límites: ' + limits_reason)
    if not ik['ok']:
        reasons.append(f"IK→FK con error {ik['pos_mm']:.4f} mm / {ik['rot_deg']:.4f}°")
    if busy:
        reasons.append('hay una orden en curso')
    elif controller is None or not controller['valida']:
        reasons.append('sin comparación reciente con el controlador ABB')
    elif not controller['ok']:
        reasons.append(f"modelo y controlador difieren {controller['pos_mm']:.3f} mm / {controller['rot_deg']:.3f}°")
    round_trip, round_trip_ok = ida_vuelta(target, tool)
    if not round_trip_ok:
        reasons.append('la ida y vuelta IK(FK(q)) no recupera los ángulos')
    matrices = {'T_pedida': matriz(wanted).tolist(), 'T_fk': fk_matriz(target, tool).tolist()}
    return {'origen': origin, 'herramienta': tool, 'pose_deseada': wanted, 'ik_fk': ik, 'robot': robot,
            'ejes': ejes(target, measured, start), 'inicio': start, 'ida_vuelta': round_trip,
            'ida_vuelta_ok': round_trip_ok, 'matrices': matrices,
            'controlador': controller, 'limites_ok': limits_ok, 'alcanzable': reachable,
            'envio_permitido': not reasons, 'motivo': '; '.join(reasons) or None, 'tolerancias': dict(t)}
