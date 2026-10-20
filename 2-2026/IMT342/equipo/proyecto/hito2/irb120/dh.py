"""Cinematica directa del ABB IRB 120 mediante Denavit-Hartenberg clasico.

La tabla se transcribio de Bahani et al. (2023), Tabla I. Las longitudes
publicadas en milimetros se expresan aqui en metros, que es la unidad de ROS.
Los angulos de entrada son los seis angulos articulares ABB en radianes; los
offsets de las filas 2 y 6 se aplican internamente.
"""

from dataclasses import dataclass
from math import atan2, cos, pi, sin
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


# TCP del Hito 2: punto sobre el eje Z de tool0 (brida) a 0.150 m de ella.
TCP_Z_M = 0.150
GRIPPER_TCP_Z_M = TCP_Z_M  # nombre anterior, se conserva por compatibilidad

# Datos del fabricante (ABB, Product specification IRB 120, rango y velocidad por eje).
JOINT_LIMITS_DEG = np.array(
    [
        [-165.0, 165.0],
        [-110.0, 110.0],
        [-110.0, 70.0],
        [-160.0, 160.0],
        [-120.0, 120.0],
        [-400.0, 400.0],
    ]
)
JOINT_LIMITS_RAD = np.deg2rad(JOINT_LIMITS_DEG)
# Pose inicial por defecto: posicion de calibracion / sincronizacion ABB (todos los ejes en 0 grados).
# Se elige porque es la postura de referencia de ABB para sincronizar (MoveAbsJ a un jointtarget de ceros).
# Nota: en ella q5 = 0, asi que es una singularidad de muneca (ejes 4 y 6 alineados).
HOME_Q = np.zeros(6)

MAX_SPEED_DEG_S = np.array([250.0, 250.0, 250.0, 320.0, 320.0, 420.0])
MAX_SPEED_RAD_S = np.deg2rad(MAX_SPEED_DEG_S)


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


def tcp_transform(tool_to_tcp_z_m: float = TCP_Z_M) -> Matrix4:
    """Transformada fija tool0 -> TCP (traslacion pura sobre Z)."""
    transform = np.eye(4, dtype=float)
    transform[2, 3] = tool_to_tcp_z_m
    return transform


def forward_kinematics_tcp(joint_positions_rad: Iterable[float]) -> Matrix4:
    """Compute base_link -> TCP: T_DH(q) multiplicada por Tz(TCP_Z_M)."""
    return forward_kinematics(joint_positions_rad) @ tcp_transform()


def position_error_m(reference: Matrix4, measured: Matrix4) -> float:
    """Euclidean position error between two homogeneous transforms."""
    return float(np.linalg.norm(reference[:3, 3] - measured[:3, 3]))


def rotation_error_rad(reference: Matrix4, measured: Matrix4) -> float:
    """Geodesic angular distance between two rotation matrices."""
    relative_rotation = reference[:3, :3].T @ measured[:3, :3]
    cosine = (float(np.trace(relative_rotation)) - 1.0) / 2.0
    skew_vector = np.array(
        [
            relative_rotation[2, 1] - relative_rotation[1, 2],
            relative_rotation[0, 2] - relative_rotation[2, 0],
            relative_rotation[1, 0] - relative_rotation[0, 1],
        ]
    )
    sine = float(np.linalg.norm(skew_vector)) / 2.0
    return atan2(sine, float(np.clip(cosine, -1.0, 1.0)))
