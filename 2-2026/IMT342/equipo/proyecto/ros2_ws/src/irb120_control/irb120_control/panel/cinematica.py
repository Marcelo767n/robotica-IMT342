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
