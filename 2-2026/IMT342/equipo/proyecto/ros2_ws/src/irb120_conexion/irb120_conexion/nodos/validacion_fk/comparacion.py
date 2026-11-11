"""FK propia del Hito 1 frente a robtarget ABB en Base, tool0 y wobj0.

No usa TF/RViz como referencia: la referencia proviene del controlador.
"""
import hashlib
from pathlib import Path
import numpy as np
from irb120_conexion import rutas  # configura la importación del modelo fuente
from irb120_hito1.kinematics import dh

POSITION_TOL_MM = 0.001  # 1e-6 m: criterio numérico estricto, no tolerancia oficial física
ORIENTATION_TOL_RAD = 1e-6
CONTEXT = {"tool": "tool0", "wobj": "wobj0", "coordinate": "Base"}


def model_identity():
    path = Path(dh.__file__).resolve()
    return {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "model": "FK DH propia irb120_hito1", "base": "base_link", "end_frame": "tool0"}


def vector(value, length):
    result = np.asarray(value, dtype=float)
    if result.shape != (length,) or not np.all(np.isfinite(result)):
        raise ValueError(f"Se requieren {length} valores finitos")
    return result


def abb_transform(pose):
    xyz = vector(pose["xyz_mm"], 3)
    q = vector(pose["quaternion_wxyz"], 4)
    norm = float(np.linalg.norm(q))
    if abs(norm-1) > 1e-3:
        raise ValueError("Cuaternión ABB no unitario")
    w, x, y, z = q/norm
    T = np.eye(4)
    T[:3, 3] = xyz/1000
    T[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                 [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                 [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    return T


def rpy_deg(T):
    R = T[:3, :3]
    cp = np.hypot(R[0, 0], R[1, 0])
    pitch = np.arctan2(-R[2, 0], cp)
    roll = np.arctan2(R[2, 1], R[2, 2]) if cp > 1e-12 else np.arctan2(-R[1, 2], R[1, 1])
    yaw = np.arctan2(R[1, 0], R[0, 0]) if cp > 1e-12 else 0
    return np.rad2deg([roll, pitch, yaw]).tolist()


def compare(sample, position_tol_mm=POSITION_TOL_MM, orientation_tol_rad=ORIENTATION_TOL_RAD,
            motion_threshold_deg=0.01, max_window_ms=500.0):
    thresholds = vector([position_tol_mm, orientation_tol_rad, motion_threshold_deg, max_window_ms], 4)
    if np.any(thresholds <= 0):
        raise ValueError("Tolerancias y límites temporales deben ser positivos")
    if sample.get("ok") is not True:
        return {"status": "LECTURA_INVALIDA", "reason": sample.get("error", "Sin lectura válida"), "accepted": None}
    if sample.get("context") != CONTEXT:
        return {"status": "MARCO_INVALIDO", "reason": "Se exige tool0 / wobj0 / Base", "accepted": None}
    before, after = vector(sample["q_before_deg"], 6), vector(sample["q_after_deg"], 6)
    duration = float(sample["window_ms"])
    if not np.isfinite(duration) or duration < 0:
        raise ValueError("Duración de adquisición inválida")
    # Los únicos datos de entrada a nuestra FK son los seis ejes leídos del ABB.
    q_input_rad = np.deg2rad(before)
    own = dh.forward_kinematics(q_input_rad)
    end = dh.forward_kinematics(np.deg2rad(after))
    reference = abb_transform(sample["controller_pose"])
    ep = dh.position_error_m(reference, own)*1000
    er = dh.rotation_error_rad(reference, own)
    position_span = dh.position_error_m(own, end)*1000
    rotation_span = dh.rotation_error_rad(own, end)
    moving = (float(np.max(np.abs(after-before))) > motion_threshold_deg or
              position_span > position_tol_mm or rotation_span > orientation_tol_rad)
    reasons = []
    if moving:
        reasons.append("Los ángulos cambiaron durante q → pose → q: no son medidas simultáneas")
    if duration > max_window_ms:
        reasons.append("Ventana de adquisición demasiado larga")
    accepted = None if reasons else bool(ep <= position_tol_mm and er <= orientation_tol_rad)
    return {"status": "NO_EVALUABLE" if reasons else ("DENTRO" if accepted else "FUERA"),
            "reason": "; ".join(reasons) if reasons else "Comparación de FK propia frente a pose del controlador",
            "accepted": accepted, "position_error_mm": ep, "orientation_error_rad": er,
            "orientation_error_deg": float(np.rad2deg(er)),
            "position_tolerance_mm": position_tol_mm, "orientation_tolerance_rad": orientation_tol_rad,
            "orientation_tolerance_deg": float(np.rad2deg(orientation_tol_rad)),
            "motion_threshold_deg": motion_threshold_deg, "max_window_ms": max_window_ms,
            "q_before_deg": before.tolist(), "q_after_deg": after.tolist(), "q_input_rad": q_input_rad.tolist(),
            "joint_span_deg": float(np.max(np.abs(after-before))), "position_span_mm": position_span,
            "orientation_span_rad": rotation_span, "window_ms": duration,
            "own_xyz_mm": (own[:3, 3]*1000).tolist(), "controller_xyz_mm": (reference[:3, 3]*1000).tolist(),
            "delta_xyz_mm": ((own[:3, 3]-reference[:3, 3])*1000).tolist(),
            "own_rpy_deg": rpy_deg(own), "controller_rpy_deg": rpy_deg(reference),
            "own_matrix_m": own.tolist(), "controller_matrix_m": reference.tolist(),
            "seq": sample.get("seq"), "stamp": sample.get("stamp"), "context": dict(CONTEXT),
            "source": sample.get("source", ""),
            "ignore_joint_state": bool(sample.get("ignore_joint_state", False))}
