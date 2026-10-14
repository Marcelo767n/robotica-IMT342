"""Utilidades de rotaciones y poses homogeneas en NumPy (sin tf_transformations)."""

from math import cos, sin

import numpy as np
from numpy.typing import NDArray

Matrix4 = NDArray[np.float64]


def rpy_to_matrix(roll: float, pitch: float, yaw: float) -> NDArray[np.float64]:
    """Rotacion ROS: R = Rz(yaw) Ry(pitch) Rx(roll)."""
    cr, sr, cp, sp, cy, sy = cos(roll), sin(roll), cos(pitch), sin(pitch), cos(yaw), sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=float)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=float)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=float)
    return rz @ ry @ rx


def quaternion_to_matrix(x: float, y: float, z: float, w: float) -> NDArray[np.float64]:
    """Matriz de rotacion de un cuaternion (x, y, z, w); se normaliza antes."""
    norm = float(np.sqrt(x * x + y * y + z * z + w * w))
    if norm == 0.0:
        raise ValueError("El cuaternion no puede ser nulo.")
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=float,
    )


def matrix_to_quaternion(rotation: NDArray[np.float64]) -> tuple[float, float, float, float]:
    """Cuaternion (x, y, z, w) de una matriz de rotacion."""
    trace = float(np.trace(rotation))
    if trace > 0.0:
        s = 2.0 * np.sqrt(trace + 1.0)
        w = 0.25 * s
        x = (rotation[2, 1] - rotation[1, 2]) / s
        y = (rotation[0, 2] - rotation[2, 0]) / s
        z = (rotation[1, 0] - rotation[0, 1]) / s
    else:
        i = int(np.argmax(np.diag(rotation)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = 2.0 * np.sqrt(1.0 + rotation[i, i] - rotation[j, j] - rotation[k, k])
        q = np.zeros(4)
        q[i] = 0.25 * s
        q[j] = (rotation[j, i] + rotation[i, j]) / s
        q[k] = (rotation[k, i] + rotation[i, k]) / s
        w = (rotation[k, j] - rotation[j, k]) / s
        x, y, z = q[0], q[1], q[2]
    return float(x), float(y), float(z), float(w)


def pose_matrix(position: tuple[float, float, float], rotation: NDArray[np.float64]) -> Matrix4:
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = rotation
    transform[:3, 3] = position
    return transform


def pose_from_xyz_rpy_deg(
    x: float, y: float, z: float, roll_deg: float, pitch_deg: float, yaw_deg: float
) -> Matrix4:
    """T_d a partir de posicion [m] y angulos roll-pitch-yaw [grados] (R = Rz Ry Rx)."""
    rotation = rpy_to_matrix(*np.deg2rad([roll_deg, pitch_deg, yaw_deg]))
    return pose_matrix((x, y, z), rotation)


def matrix_to_rpy_deg(rotation: NDArray[np.float64]) -> tuple[float, float, float]:
    """(roll, pitch, yaw) en grados tales que R = Rz(yaw) Ry(pitch) Rx(roll); pitch en [-90, 90]."""
    rotation = np.asarray(rotation, dtype=float)
    pitch = np.arctan2(-rotation[2, 0], np.hypot(rotation[0, 0], rotation[1, 0]))
    if np.hypot(rotation[0, 0], rotation[1, 0]) < 1e-12:  # gimbal lock: yaw = 0 por convencion
        roll, yaw = np.arctan2(-rotation[1, 2], rotation[1, 1]), 0.0
    else:
        roll = np.arctan2(rotation[2, 1], rotation[2, 2])
        yaw = np.arctan2(rotation[1, 0], rotation[0, 0])
    return tuple(float(v) for v in np.rad2deg([roll, pitch, yaw]))
