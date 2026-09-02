"""Evaluador pequeno e independiente de cadenas URDF para verificar el modelo.

No reemplaza a robot_state_publisher. Se usa como implementacion independiente
en las pruebas para detectar discrepancias entre la tabla DH y el URDF entregado.
"""

from dataclasses import dataclass
from math import cos, sin
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
from numpy.typing import NDArray


Matrix4 = NDArray[np.float64]


@dataclass(frozen=True)
class Joint:
    name: str
    joint_type: str
    parent: str
    child: str
    xyz: NDArray[np.float64]
    rpy: NDArray[np.float64]
    axis: NDArray[np.float64]


def _vector(element: ElementTree.Element | None, key: str, default: str) -> NDArray[np.float64]:
    text = default if element is None else element.attrib.get(key, default)
    return np.fromstring(text, sep=" ", dtype=float)


def _rpy_rotation(rpy: NDArray[np.float64]) -> NDArray[np.float64]:
    roll, pitch, yaw = rpy
    cr, sr = cos(roll), sin(roll)
    cp, sp = cos(pitch), sin(pitch)
    cy, sy = cos(yaw), sin(yaw)
    rotation_x = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
    rotation_y = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    rotation_z = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    return rotation_z @ rotation_y @ rotation_x


def _axis_angle(axis: NDArray[np.float64], angle: float) -> NDArray[np.float64]:
    norm = float(np.linalg.norm(axis))
    if norm == 0.0:
        raise ValueError("El eje de una articulacion no puede ser nulo.")
    x, y, z = axis / norm
    c, s = cos(angle), sin(angle)
    one_minus_c = 1.0 - c
    return np.array(
        [
            [c + x * x * one_minus_c, x * y * one_minus_c - z * s, x * z * one_minus_c + y * s],
            [y * x * one_minus_c + z * s, c + y * y * one_minus_c, y * z * one_minus_c - x * s],
            [z * x * one_minus_c - y * s, z * y * one_minus_c + x * s, c + z * z * one_minus_c],
        ]
    )


def load_joints(urdf_path: str | Path) -> dict[str, Joint]:
    root = ElementTree.parse(urdf_path).getroot()
    joints: dict[str, Joint] = {}
    for element in root.findall("joint"):
        parent_element = element.find("parent")
        child_element = element.find("child")
        if parent_element is None or child_element is None:
            raise ValueError(f"La articulacion {element.attrib.get('name')} no tiene padre o hijo.")
        origin = element.find("origin")
        axis = element.find("axis")
        joint = Joint(
            name=element.attrib["name"],
            joint_type=element.attrib["type"],
            parent=parent_element.attrib["link"],
            child=child_element.attrib["link"],
            xyz=_vector(origin, "xyz", "0 0 0"),
            rpy=_vector(origin, "rpy", "0 0 0"),
            axis=_vector(axis, "xyz", "1 0 0"),
        )
        if joint.child in joints:
            raise ValueError(f"El enlace {joint.child} tiene mas de un padre.")
        joints[joint.child] = joint
    return joints


def _joint_transform(joint: Joint, position: float) -> Matrix4:
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = _rpy_rotation(joint.rpy)
    transform[:3, 3] = joint.xyz

    motion = np.eye(4, dtype=float)
    if joint.joint_type in {"revolute", "continuous"}:
        motion[:3, :3] = _axis_angle(joint.axis, position)
    elif joint.joint_type == "prismatic":
        motion[:3, 3] = (joint.axis / np.linalg.norm(joint.axis)) * position
    elif joint.joint_type != "fixed":
        raise ValueError(f"Tipo de articulacion URDF no soportado: {joint.joint_type}")
    return transform @ motion


def chain_transform(
    urdf_path: str | Path,
    joint_positions: dict[str, float],
    base_link: str = "base_link",
    target_link: str = "tool0",
) -> Matrix4:
    """Evaluate one serial path in the expanded URDF."""
    by_child = load_joints(urdf_path)
    reverse_chain: list[Joint] = []
    link = target_link
    visited: set[str] = set()
    while link != base_link:
        if link in visited:
            raise ValueError("Se detecto un ciclo en la cadena URDF.")
        visited.add(link)
        if link not in by_child:
            raise ValueError(f"No existe una cadena desde {base_link} hasta {target_link}.")
        joint = by_child[link]
        reverse_chain.append(joint)
        link = joint.parent

    transform = np.eye(4, dtype=float)
    for joint in reversed(reverse_chain):
        position = float(joint_positions.get(joint.name, 0.0))
        transform = transform @ _joint_transform(joint, position)
    return transform
