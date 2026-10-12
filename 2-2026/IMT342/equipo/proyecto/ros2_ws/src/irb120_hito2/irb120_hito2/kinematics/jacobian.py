"""Jacobiano geometrico del IRB 120 y analisis de la singularidad de muneca.

J(q) (6x6) relaciona q_dot con el twist [v; w] del TCP expresado en base_link.
Con el centro de muneca como punto de referencia, J es triangular por bloques:

    det J = det(Jp_brazo[3x3]) * det([z3 z4 z5]) = det(Jp_brazo) * (+-sin q5)

porque z3 y z4 son perpendiculares y z4 y z5 tambien, y el angulo entre z3 y
z5 es q5. Cuando q5 = 0 los ejes 4 y 6 quedan alineados (z3 = z5), J pierde un
rango y q_dot = J^-1 * twist diverge como 1/|sin q5|.
"""

import numpy as np
from numpy.typing import NDArray

from irb120_hito1.kinematics.dh import DH_PARAMETERS, GRIPPER_TCP_Z_M, dh_transform

Matrix = NDArray[np.float64]


def joint_frames(q: np.ndarray) -> list[Matrix]:
    """Transformadas T_0^i para i = 0..6 (el indice 0 es la identidad)."""
    frames = [np.eye(4)]
    for angle, parameter in zip(np.asarray(q, dtype=float), DH_PARAMETERS, strict=True):
        frames.append(frames[-1] @ dh_transform(float(angle), parameter))
    return frames


def geometric_jacobian(q: np.ndarray, reference: str = "tcp") -> Matrix:
    """Jacobiano 6x6 respecto a `reference`: 'tcp', 'tool0' o 'wrist'."""
    frames = joint_frames(q)
    flange = frames[6]
    if reference == "tcp":
        point = (flange @ np.array([0.0, 0.0, GRIPPER_TCP_Z_M, 1.0]))[:3]
    elif reference == "tool0":
        point = flange[:3, 3]
    elif reference == "wrist":
        point = frames[4][:3, 3]
    else:
        raise ValueError("reference debe ser 'tcp', 'tool0' o 'wrist'.")
    jacobian = np.zeros((6, 6))
    for index in range(6):
        axis = frames[index][:3, 2]  # la junta i+1 gira sobre z del marco i
        origin = frames[index][:3, 3]
        jacobian[:3, index] = np.cross(axis, point - origin)
        jacobian[3:, index] = axis
    return jacobian


def determinant(q: np.ndarray) -> float:
    return float(np.linalg.det(geometric_jacobian(q)))


def smallest_singular_value(q: np.ndarray) -> float:
    return float(np.linalg.svd(geometric_jacobian(q), compute_uv=False)[-1])


def condition_number(q: np.ndarray) -> float:
    singular_values = np.linalg.svd(geometric_jacobian(q), compute_uv=False)
    if singular_values[-1] == 0.0:
        return float("inf")
    return float(singular_values[0] / singular_values[-1])


def arm_position_determinant(q: np.ndarray) -> float:
    """det del bloque 3x3 de posicion del centro de muneca (q1..q3)."""
    return float(np.linalg.det(geometric_jacobian(q, "wrist")[:3, :3]))


class SingularityError(np.linalg.LinAlgError):
    """J(q) no es invertible: q_dot = J^-1 twist no existe."""


SINGULAR_VALUE_TOLERANCE = 1.0e-9


def solve_with_jacobian(q: np.ndarray, rhs: np.ndarray, jacobian: Matrix | None = None) -> Matrix:
    """Resuelve J x = rhs; lanza SingularityError si sigma_min(J) es ~ 0."""
    matrix = geometric_jacobian(q) if jacobian is None else jacobian
    if float(np.linalg.svd(matrix, compute_uv=False)[-1]) < SINGULAR_VALUE_TOLERANCE:
        raise SingularityError("Jacobiano singular (q5 = 0): no existe q_dot = J^-1 v.")
    return np.linalg.solve(matrix, np.asarray(rhs, dtype=float))


def joint_velocity(q: np.ndarray, twist: np.ndarray) -> Matrix:
    """q_dot = J^-1 twist; diverge como 1/|sin q5| y no existe en q5 = 0."""
    return solve_with_jacobian(q, twist)


def jacobian_dot(q: np.ndarray, q_dot: np.ndarray, step: float = 1.0e-6) -> Matrix:
    """J_dot = sum_k dJ/dq_k q_dot_k por diferencias centrales a lo largo de q_dot."""
    q = np.asarray(q, dtype=float)
    q_dot = np.asarray(q_dot, dtype=float)
    speed = float(np.linalg.norm(q_dot))
    if speed == 0.0:
        return np.zeros((6, 6))
    direction = q_dot / speed
    plus = geometric_jacobian(q + step * direction)
    minus = geometric_jacobian(q - step * direction)
    return (plus - minus) / (2.0 * step) * speed
