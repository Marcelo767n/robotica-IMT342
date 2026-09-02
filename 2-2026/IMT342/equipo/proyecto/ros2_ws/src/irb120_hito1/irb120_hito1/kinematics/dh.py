"""Cinematica directa del ABB IRB 120 mediante Denavit-Hartenberg clasico.

La tabla se transcribio de Bahani et al. (2023), Tabla I. Las longitudes
publicadas en milimetros se expresan aqui en metros, que es la unidad de ROS.
Los angulos de entrada son los seis angulos articulares ABB en radianes; los
offsets de las filas 2 y 6 se aplican internamente.
"""

from dataclasses import dataclass
from math import cos, pi, sin
from typing import Iterable

import numpy as np
from numpy.typing import NDArray


Matrix4 = NDArray[np.float64]
JOINT_NAMES = tuple(f"joint_{index}" for index in range(1, 7))


@dataclass(frozen=True)
class DHParameter:
    """Una fila de la convencion DH clasica: theta, d, a, alpha."""

    d_m: float
    a_m: float
    alpha_rad: float
    theta_offset_rad: float = 0.0


DH_PARAMETERS = (
    DHParameter(d_m=0.290, a_m=0.000, alpha_rad=-pi / 2.0),
    DHParameter(d_m=0.000, a_m=0.270, alpha_rad=0.0, theta_offset_rad=-pi / 2.0),
    DHParameter(d_m=0.000, a_m=0.070, alpha_rad=-pi / 2.0),
    DHParameter(d_m=0.302, a_m=0.000, alpha_rad=pi / 2.0),
    DHParameter(d_m=0.000, a_m=0.000, alpha_rad=-pi / 2.0),
    DHParameter(d_m=0.072, a_m=0.000, alpha_rad=0.0, theta_offset_rad=pi),
)

# tool0 -> gripper_base_link (20 mm) -> tcp_link (140 mm).
TCP_OFFSET_M = 0.160


def dh_transform(theta_rad: float, parameter: DHParameter) -> Matrix4:
    """Return the classical DH matrix Rz(theta) Tz(d) Tx(a) Rx(alpha)."""
    theta = theta_rad + parameter.theta_offset_rad
    c_theta, s_theta = cos(theta), sin(theta)
    c_alpha, s_alpha = cos(parameter.alpha_rad), sin(parameter.alpha_rad)

    return np.array(
        [
            [
                c_theta,
                -s_theta * c_alpha,
                s_theta * s_alpha,
                parameter.a_m * c_theta,
            ],
            [
                s_theta,
                c_theta * c_alpha,
                -c_theta * s_alpha,
                parameter.a_m * s_theta,
            ],
            [0.0, s_alpha, c_alpha, parameter.d_m],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def _joint_vector(joint_positions_rad: Iterable[float]) -> NDArray[np.float64]:
    joints = np.asarray(tuple(joint_positions_rad), dtype=float)
    if joints.shape != (6,):
        raise ValueError(
            f"Se esperaban 6 angulos articulares y se recibio una forma {joints.shape}."
        )
    if not np.all(np.isfinite(joints)):
        raise ValueError("Todos los angulos articulares deben ser valores finitos.")
    return joints


def forward_kinematics(joint_positions_rad: Iterable[float]) -> Matrix4:
    """Compute base_link -> tool0 for the six ABB joint angles."""
    joints = _joint_vector(joint_positions_rad)
    transform = np.eye(4, dtype=float)
    for angle, parameter in zip(joints, DH_PARAMETERS, strict=True):
        transform = transform @ dh_transform(float(angle), parameter)
    return transform


def forward_kinematics_tcp(joint_positions_rad: Iterable[float]) -> Matrix4:
    """Compute base_link -> tcp_link for the provisional parallel gripper."""
    tool_to_tcp = np.eye(4, dtype=float)
    tool_to_tcp[2, 3] = TCP_OFFSET_M
    return forward_kinematics(joint_positions_rad) @ tool_to_tcp


def position_error_m(reference: Matrix4, measured: Matrix4) -> float:
    """Euclidean position error between two homogeneous transforms."""
    return float(np.linalg.norm(reference[:3, 3] - measured[:3, 3]))


def rotation_error_rad(reference: Matrix4, measured: Matrix4) -> float:
    """Geodesic angular distance between two rotation matrices."""
    relative_rotation = reference[:3, :3].T @ measured[:3, :3]
    cosine = (float(np.trace(relative_rotation)) - 1.0) / 2.0
    return float(np.arccos(np.clip(cosine, -1.0, 1.0)))
