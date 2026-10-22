"""Bateria de pruebas DH contra URDF, compartida por verify_model y el panel.

No depende de ROS ni de la interfaz grafica para poder probarse con pytest.
"""

from dataclasses import dataclass
from math import atan2, degrees, hypot
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from irb120_hito1.kinematics.dh import (
    JOINT_NAMES,
    forward_kinematics,
    forward_kinematics_tcp,
    position_error_m,
    rotation_error_rad,
)
from irb120_hito1.kinematics.urdf_chain import chain_transform
from irb120_hito1.slider_controls import JOINT_SLIDERS


Matrix4 = NDArray[np.float64]
FRAMES = ("tool0", "gripper_tcp")
DEFAULT_TOLERANCE_M = 1.0e-6


@dataclass(frozen=True)
class ValidationPose:
    name: str
    joints_deg: tuple[float, ...]
    reason: str


VALIDATION_POSES = (
    ValidationPose(
        name="Cero - posición de calibración",
        joints_deg=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        reason="Pose de calibración ABB; permite comprobar a mano la tabla DH.",
    ),
    ValidationPose(
        name="A - postura de trabajo",
        joints_deg=(30.0, -20.0, 15.0, 40.0, -35.0, 60.0),
        reason=(
            "Activa los seis ejes, evita la simetría de q=0 y representa una "
            "postura elevada de aproximación dentro del espacio de trabajo."
        ),
    ),
    ValidationPose(
        name="B - postura plegada crítica",
        joints_deg=(90.0, -60.0, 60.0, 90.0, 60.0, 180.0),
        reason=(
            "Activa los seis ejes y acerca el efector al eje de la base; es útil para "
            "detectar signos/offsets y estudiar la proximidad a la base."
        ),
    ),
)


@dataclass(frozen=True)
class ValidationResult:
    case: str
    joints_deg: tuple[float, ...]
    frame: str
    position_dh_m: tuple[float, float, float]
    position_urdf_m: tuple[float, float, float]
    position_error_m: float
    rotation_error_rad: float
    passed: bool


def random_poses(count: int, seed: int = 342) -> list[ValidationPose]:
    """Posturas pseudoaleatorias reproducibles dentro de los limites oficiales."""
    if count < 0:
        raise ValueError("count no puede ser negativo.")
    generator = np.random.default_rng(seed)
    lower = np.array([spec.lower_deg for spec in JOINT_SLIDERS])
    upper = np.array([spec.upper_deg for spec in JOINT_SLIDERS])
    return [
        ValidationPose(
            name=f"Aleatoria {index + 1:03d}",
            joints_deg=tuple(float(round(value, 3)) for value in generator.uniform(lower, upper)),
            reason=f"Muestra uniforme dentro de los limites (semilla {seed}).",
        )
        for index in range(count)
    ]


def analytic_transform(joints_deg: tuple[float, ...] | list[float], frame: str) -> Matrix4:
    """Funcion analitica DH hasta tool0 o hasta el TCP de la pinza."""
    if frame not in FRAMES:
        raise ValueError(f"frame debe ser uno de {FRAMES}.")
    joints_rad = np.deg2rad(np.asarray(joints_deg, dtype=float))
    if frame == "gripper_tcp":
        return forward_kinematics_tcp(joints_rad)
    return forward_kinematics(joints_rad)


def evaluate_pose(
    urdf_path: Path,
    pose: ValidationPose,
    frame: str,
    tolerance_m: float = DEFAULT_TOLERANCE_M,
) -> ValidationResult:
    """Compara T_DH(q) con la cadena URDF evaluada de forma independiente."""
    analytic = analytic_transform(pose.joints_deg, frame)
    joint_map = dict(zip(JOINT_NAMES, np.deg2rad(pose.joints_deg), strict=True))
    urdf_matrix = chain_transform(urdf_path, joint_map, base_link="base_link", target_link=frame)
    error_m = position_error_m(analytic, urdf_matrix)
    return ValidationResult(
        case=pose.name,
        joints_deg=tuple(pose.joints_deg),
        frame=frame,
        position_dh_m=tuple(float(value) for value in analytic[:3, 3]),
        position_urdf_m=tuple(float(value) for value in urdf_matrix[:3, 3]),
        position_error_m=error_m,
        rotation_error_rad=rotation_error_rad(analytic, urdf_matrix),
        passed=error_m < tolerance_m,
    )


def run_suite(
    urdf_path: Path,
    random_count: int = 100,
    tolerance_m: float = DEFAULT_TOLERANCE_M,
    seed: int = 342,
) -> list[ValidationResult]:
    """Poses justificadas y aleatorias, cada una en tool0 y en gripper_tcp."""
    poses = [*VALIDATION_POSES, *random_poses(random_count, seed)]
    return [
        evaluate_pose(urdf_path, pose, frame, tolerance_m) for pose in poses for frame in FRAMES
    ]


def rpy_deg(transform: Matrix4) -> tuple[float, float, float]:
    """Angulos roll-pitch-yaw (convencion URDF/RViz, R = Rz Ry Rx) en grados."""
    rotation = transform[:3, :3]
    pitch = atan2(-rotation[2, 0], hypot(rotation[0, 0], rotation[1, 0]))
    roll = atan2(rotation[2, 1], rotation[2, 2])
    yaw = atan2(rotation[1, 0], rotation[0, 0])
    return degrees(roll), degrees(pitch), degrees(yaw)
