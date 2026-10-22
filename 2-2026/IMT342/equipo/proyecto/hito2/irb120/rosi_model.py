"""Modelo cinematico OFICIAL del IRB 120 publicado por ROS-Industrial (paquete abb_irb120_support).

Fuente: https://github.com/ros-industrial/abb/blob/kinetic-devel/abb_irb120_support/urdf/irb120_3_58_macro.xacro
Es una fuente geometrica INDEPENDIENTE de nuestra tabla DH (Bahani 2023): ROS-Industrial la construyo a partir de
los planos de ABB, con otra convencion (traslaciones puras + ejes de giro, sin parametros DH). Se usa solo para
VERIFICAR la cinematica directa.

Cada junta: origen fijo (traslacion) y luego giro q_i alrededor de su eje. tool0 = link_6 * Ry(90 deg).
"""

import numpy as np
from numpy.typing import NDArray

SOURCE_URL = (
    "https://github.com/ros-industrial/abb/blob/kinetic-devel/abb_irb120_support/urdf/irb120_3_58_macro.xacro"
)

# (origen xyz [m], eje de giro) de joint_1 ... joint_6, tal como aparecen en el xacro oficial.
ROSI_JOINTS = (
    ((0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ((0.0, 0.0, 0.29), (0.0, 1.0, 0.0)),
    ((0.0, 0.0, 0.27), (0.0, 1.0, 0.0)),
    ((0.0, 0.0, 0.07), (1.0, 0.0, 0.0)),
    ((0.302, 0.0, 0.0), (0.0, 1.0, 0.0)),
    ((0.072, 0.0, 0.0), (1.0, 0.0, 0.0)),
)
# Limites del xacro oficial [rad] (coinciden con el datasheet ABB).
ROSI_LIMITS_RAD = np.array(
    [[-2.87979, 2.87979], [-1.91986, 1.91986], [-1.91986, 1.22173],
     [-2.79253, 2.79253], [-2.094395, 2.094395], [-6.98132, 6.98132]]
)


def _axis_rotation(axis, angle: float) -> NDArray[np.float64]:
    """Rodrigues: rotacion de `angle` alrededor del eje unitario `axis`."""
    x, y, z = axis
    k = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + np.sin(angle) * k + (1.0 - np.cos(angle)) * k @ k


def rosi_forward_kinematics(q) -> NDArray[np.float64]:
    """base_link -> tool0 segun el modelo oficial de ROS-Industrial."""
    transform = np.eye(4)
    for (xyz, axis), angle in zip(ROSI_JOINTS, np.asarray(q, dtype=float), strict=True):
        step = np.eye(4)
        step[:3, 3] = xyz
        step[:3, :3] = _axis_rotation(axis, float(angle))
        transform = transform @ step
    tool = np.eye(4)
    tool[:3, :3] = _axis_rotation((0.0, 1.0, 0.0), np.pi / 2.0)  # link_6 -> tool0: rpy (0, 90 deg, 0)
    return transform @ tool
