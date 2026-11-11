"""Adquisición GET acotada: q_antes → robtarget(tool0, Base) → q_después.

No es una lectura atómica del controlador. El validador debe comprobar quietud.
"""
import math
import re
import time
from irb120_conexion.comunicacion import lectura_rws as rws

CONTEXT = {"tool": "tool0", "wobj": "wobj0", "coordinate": "Base"}


def require_ok(result):
    if result["http_status"] != 200:
        raise ValueError(f"{result['path']}: HTTP {result['http_status']}; ABB {result.get('controller_error', {})}")


def parse_pose(records):
    for row in records:
        if row.get("_type") != "ms-robtargets":
            continue
        try:
            values = [float(row[key]) for key in ("x", "y", "z", "q1", "q2", "q3", "q4")]
        except (KeyError, ValueError, TypeError):
            continue
        if all(math.isfinite(v) for v in values) and sum(v*v for v in values[3:]) > 1e-12:
            return {"xyz_mm": values[:3], "quaternion_wxyz": values[3:]}
    raise ValueError("robtarget no contiene una pose finita y un cuaternión válido")


def acquire(session, base, mechunit, q_before, started, timeout=1.0, ignore_joint_state=False):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", mechunit):
        raise ValueError("Unidad mecánica inválida")
    path = f"/rw/motionsystem/mechunits/{mechunit}"
    pose_result = rws.read_resource(session, base, path + "/robtarget", timeout)
    require_ok(pose_result)
    pose = parse_pose(pose_result["records"])
    after = rws.read_resource(session, base, path + "/jointtarget", timeout, ignore_joint_state=ignore_joint_state)
    require_ok(after)
    q_after = rws.robot_axes(after["records"])
    if q_after is None:
        raise ValueError("La segunda lectura articular no tiene seis ejes finitos")
    return {"ok": True, "q_before_deg": list(q_before), "q_after_deg": q_after,
            "controller_pose": pose, "context": dict(CONTEXT),
            "window_ms": (time.monotonic()-started)*1000,
            "ignore_joint_state": ignore_joint_state}
