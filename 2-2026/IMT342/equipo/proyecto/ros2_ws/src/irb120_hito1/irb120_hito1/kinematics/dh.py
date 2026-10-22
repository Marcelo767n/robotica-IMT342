"""Cinematica directa del ABB IRB 120 mediante Denavit-Hartenberg clasico.

La tabla se transcribio de Bahani et al. (2023), Tabla I. Las longitudes
publicadas en milimetros se expresan aqui en metros, que es la unidad de ROS.
Los angulos de entrada son los seis angulos articulares ABB en radianes; los
offsets de las filas 2 y 6 se aplican internamente.
"""

from dataclasses import dataclass
from math import atan2, cos, isfinite, pi, sin
from pathlib import Path
from typing import Iterable

import numpy as np
import yaml
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


TCP_CONFIG_NAME = "tcp.yaml"


def tcp_config_path() -> Path:
    """Locate config/tcp.yaml, the single source of the tool0 -> TCP offset.

    Se busca primero en el share instalado y luego en el arbol fuente, igual que
    verify_model.default_urdf_path; asi el URDF y la DH leen el mismo archivo.
    """
    try:
        from ament_index_python.packages import get_package_share_directory

        candidate = Path(get_package_share_directory("irb120_hito1")) / "config" / TCP_CONFIG_NAME
        if candidate.is_file():
            return candidate
    except (ImportError, LookupError):
        pass

    source_candidate = Path(__file__).resolve().parents[2] / "config" / TCP_CONFIG_NAME
    if source_candidate.is_file():
        return source_candidate
    raise FileNotFoundError(f"No se encontro config/{TCP_CONFIG_NAME}.")


def load_tcp_config(path: str | Path | None = None) -> dict:
    """Read and validate the TCP YAML (tool0_to_tcp_z_m, verified_on_robot)."""
    config_path = Path(path) if path is not None else tcp_config_path()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "tool0_to_tcp_z_m" not in data:
        raise ValueError(f"{config_path} debe definir tool0_to_tcp_z_m.")
    tcp_z_m = float(data["tool0_to_tcp_z_m"])
    if not isfinite(tcp_z_m) or tcp_z_m < 0.0:
        raise ValueError("tool0_to_tcp_z_m debe ser finito y no negativo.")
    return {
        "tool0_to_tcp_z_m": tcp_z_m,
        "verified_on_robot": bool(data.get("verified_on_robot", False)),
        "path": config_path,
    }


# Pinza neumatica: el TCP esta sobre el eje Z de tool0. El valor se lee de
# config/tcp.yaml (el mismo archivo que usa el xacro). Por defecto 0.150 m,
# igual que el Hito 2; NO esta verificado en el robot fisico.
_TCP_CONFIG = load_tcp_config()
GRIPPER_TCP_Z_M: float = _TCP_CONFIG["tool0_to_tcp_z_m"]
TCP_VERIFIED_ON_ROBOT: bool = _TCP_CONFIG["verified_on_robot"]


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


def tcp_transform(tool_to_tcp_z_m: float = GRIPPER_TCP_Z_M) -> Matrix4:
    """Fixed transform tool0 -> gripper_tcp (traslacion pura sobre Z)."""
    transform = np.eye(4, dtype=float)
    transform[2, 3] = tool_to_tcp_z_m
    return transform


def forward_kinematics_tcp(
    joint_positions_rad: Iterable[float], tool_to_tcp_z_m: float = GRIPPER_TCP_Z_M
) -> Matrix4:
    """Compute base_link -> gripper_tcp: T_DH(q) multiplicada por la pinza."""
    return forward_kinematics(joint_positions_rad) @ tcp_transform(tool_to_tcp_z_m)


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
