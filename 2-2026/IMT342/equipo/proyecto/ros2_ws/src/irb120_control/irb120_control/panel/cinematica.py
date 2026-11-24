"""Cinemática directa e inversa (Pieper) del Hito 2 aplicada al panel. Sin ROS."""
import math
import sys

from irb120_conexion.rutas import PROJECT
from irb120_control.rws_j6 import Refused
from irb120_control.rws_mover import MARGIN_DEG
from irb120_control.panel.limites import clean_target

# Punto cuya pose se muestra y se pide: el TCP del proyecto (150 mm sobre z de la brida) o la brida.
TOOLS = ('tcp', 'brida')


def kinematics():
    """Modelo DH y Pieper del Hito 2 (los mismos que usa supervisor.py); sin duplicar fórmulas."""
    import numpy as np
    path = str(PROJECT / 'hito2')
    if path not in sys.path:
        sys.path.insert(0, path)
    from irb120 import dh, pieper, transforms
    return np, dh, pieper, transforms


def clean_tool(tool):
    if tool not in TOOLS:
        raise Refused('Herramienta desconocida: usar «tcp» o «brida».')
    return tool


def pose_of(q_deg, tool='tcp'):
    """Cinemática directa: [x, y, z en mm, roll, pitch, yaw en grados], R = Rz(yaw) Ry(pitch) Rx(roll)."""
    np, dh, _, transforms = kinematics()
    forward = dh.forward_kinematics_tcp if clean_tool(tool) == 'tcp' else dh.forward_kinematics
    transform = forward(np.deg2rad(q_deg))
    return [float(v) for v in (*(transform[:3, 3] * 1000.), *transforms.matrix_to_rpy_deg(transform[:3, :3]))]


def solve_pose(pose, reference_deg, tool='tcp'):
    """Cinemática inversa de Pieper para una pose [x, y, z mm, roll, pitch, yaw °].

    Devuelve las 8 ramas con el criterio de selección del proyecto (rank_candidates) respecto a
    la postura de referencia, y marca cuáles caben además en los límites con margen del panel.
    """
    np, dh, pieper, transforms = kinematics()
    clean_tool(tool)
    if not isinstance(pose, (list, tuple)) or len(pose) != 6 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in pose):
        raise Refused('Se esperan seis números: X, Y, Z en mm y roll, pitch, yaw en grados.')
    if any(abs(v) > 2000. for v in pose[:3]) or any(abs(v) > 360. for v in pose[3:]):
        raise Refused('Pose fuera de rango: posición hasta ±2000 mm y ángulos hasta ±360°.')
    x, y, z = (v / 1000. for v in pose[:3])
    try:
        target = transforms.pose_from_xyz_rpy_deg(x, y, z, *pose[3:])
        if tool == 'brida':  # analyze_pose recibe la pose del TCP: T_tcp = T_brida · Tz(150 mm)
            target = target @ dh.tcp_transform()
        reference = np.deg2rad(reference_deg)
        report = pieper.analyze_pose(target, reference)
        decisions = pieper.rank_candidates(report, reference)
    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
        raise Refused(f'La cinemática inversa no pudo evaluar la pose: {exc}') from exc
    rows = []
    for decision in decisions:
        candidate = decision.candidate
        q = None if candidate.q is None else [float(v) for v in np.rad2deg(candidate.q)]
        usable, status = False, decision.status
        if decision.admissible:
            try:
                clean_target(q)
                usable = True
            except Refused as exc:
                status = f'fuera del margen de {MARGIN_DEG:g}° del panel: {exc}'
        rows.append({'rama': candidate.branch, 'brazo': candidate.arm, 'codo': candidate.elbow,
                     'muneca': candidate.wrist, 'q': q, 'estado': status, 'puesto': decision.rank,
                     'usable': usable, 'costo': decision.weighted_cost if usable else None,
                     'cambio_max': None if q is None else max(abs(a - b) for a, b in zip(q, reference_deg))})
    usable = [row for row in rows if row['usable']]
    ranked = sorted((row for row in usable if row['puesto'] is not None), key=lambda row: row['puesto'])
    chosen = (ranked or sorted(usable, key=lambda row: row['costo']) or [None])[0]
    verdict = report.verdict
    if report.reachable and chosen is None:
        verdict = f'NO UTILIZABLE: las ramas admisibles quedan a menos de {MARGIN_DEG:g}° de un límite articular.'
    return {'veredicto': verdict, 'ramas': rows, 'elegida': None if chosen is None else chosen['rama'],
            'pose': list(pose), 'herramienta': tool}


def convertir_herramienta(pose, de, a):
    """La misma pose vista desde otro punto de referencia: 'tcp' (150 mm sobre z de la brida) o 'brida'."""
    clean_tool(de), clean_tool(a)
    if de == a:
        return [float(v) for v in pose]
    np, dh, _, transforms = kinematics()
    T = transforms.pose_from_xyz_rpy_deg(*(v / 1000. for v in pose[:3]), *pose[3:])
    offset = dh.tcp_transform()
    T = T @ offset if (de, a) == ('brida', 'tcp') else T @ np.linalg.inv(offset)
    return [float(v) for v in (*(T[:3, 3] * 1000.), *transforms.matrix_to_rpy_deg(T[:3, :3]))]


def pose_desde_cuaternion(frame_id, xyz_m, quat_xyzw):
    """Pose de un mensaje ROS (metros, cuaternión x y z w) → [x, y, z mm, roll, pitch yaw °], Refused si no vale.

    Solo se acepta frame_id 'base_link' (no hay TF en el panel). El cuaternión se normaliza si es
    finito y no nulo."""
    if frame_id != 'base_link':
        raise Refused(f"Marco «{frame_id}» no admitido: la pose debe venir en «base_link» (sin TF por ahora).")
    values = [*xyz_m, *quat_xyzw]
    if len(values) != 7 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise Refused('La pose contiene valores no finitos.')
    norm = math.sqrt(sum(v * v for v in quat_xyzw))
    if norm < 1e-6:
        raise Refused('Cuaternión nulo: no se puede normalizar.')
    np, _, _, transforms = kinematics()
    x, y, z, w = (v / norm for v in quat_xyzw)
    rotation = transforms.quaternion_to_matrix(x, y, z, w)
    return [*(v * 1000. for v in xyz_m), *(float(v) for v in transforms.matrix_to_rpy_deg(rotation))]
