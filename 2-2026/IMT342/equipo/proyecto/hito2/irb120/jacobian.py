"""Jacobiano geometrico del IRB 120 y analisis de la singularidad de muneca.

J(q) (6x6) relaciona q_dot con el twist [v; w] del TCP expresado en base_link.
Con el centro de muneca como punto de referencia, J es triangular por bloques:

    det J = det(Jp_brazo[3x3]) * det([z3 z4 z5]) = det(Jp_brazo) * (+-sin q5)

porque z3 y z4 son perpendiculares y z4 y z5 tambien, y el angulo entre z3 y
z5 es q5. Cuando q5 = 0 los ejes 4 y 6 quedan alineados (z3 = z5), J pierde un
rango y q_dot = J^-1 * twist diverge como 1/|sin q5|.

Criterio central de singularidad: el RANGO de J calculado con la SVD
(numero de valores singulares sigma_i > tol). El determinante solo se usa como
complemento porque J es cuadrada (6x6); no dice cuantas direcciones se pierden ni cuales.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from irb120.dh import DH_PARAMETERS, TCP_Z_M, dh_transform, forward_kinematics_tcp

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
        point = (flange @ np.array([0.0, 0.0, TCP_Z_M, 1.0]))[:3]
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
        raise SingularityError("Jacobiano singular (rango < 6): no existe q_dot = J^-1 v.")
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


# --------------------------------------------------------------------------- validacion del Jacobiano


def _vee(skew: Matrix) -> Matrix:
    return np.array([skew[2, 1], skew[0, 2], skew[1, 0]])


def numerical_jacobian(q: np.ndarray, step: float = 1.0e-6) -> Matrix:
    """Jacobiano del TCP por diferencias centrales de la FK (independiente de la formula z x (p - o)).

    Columna i:  v_i = (p(q + h e_i) - p(q - h e_i)) / 2h
                w_i = vee( (R(q + h e_i) - R(q - h e_i)) / 2h * R(q)^T )
    porque dR/dt R^T = [w]x (matriz antisimetrica de la velocidad angular).
    """
    q = np.asarray(q, dtype=float)
    rotation = forward_kinematics_tcp(q)[:3, :3]
    jacobian = np.zeros((6, 6))
    for index in range(6):
        delta = np.zeros(6)
        delta[index] = step
        plus, minus = forward_kinematics_tcp(q + delta), forward_kinematics_tcp(q - delta)
        jacobian[:3, index] = (plus[:3, 3] - minus[:3, 3]) / (2.0 * step)
        d_rotation = (plus[:3, :3] - minus[:3, :3]) / (2.0 * step)
        jacobian[3:, index] = _vee(d_rotation @ rotation.T)
    return jacobian


def tcp_twist(q: np.ndarray, q_dot: np.ndarray) -> Matrix:
    """Mapeo diferencial x_dot = [v; w] = J(q) q_dot."""
    return geometric_jacobian(q) @ np.asarray(q_dot, dtype=float)


# --------------------------------------------------------------------------- rango y direcciones

RANK_TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class RankAnalysis:
    """SVD de J = U diag(sigma) V^T y lo que dice sobre la movilidad local."""

    singular_values: Matrix
    rank: int
    tolerance: float
    lost_twist_directions: Matrix  # columnas de U con sigma ~ 0: twists [v; w] que el TCP NO puede generar
    null_joint_motions: Matrix  # columnas de V con sigma ~ 0: q_dot que NO mueven el TCP

    @property
    def max_rank(self) -> int:
        return len(self.singular_values)

    @property
    def is_singular(self) -> bool:
        return self.rank < self.max_rank

    @property
    def condition_number(self) -> float:
        smallest = float(self.singular_values[-1])
        return float("inf") if smallest == 0.0 else float(self.singular_values[0] / smallest)


def rank_analysis(jacobian: Matrix, tol: float = RANK_TOLERANCE) -> RankAnalysis:
    """Rango numerico de J por SVD con tolerancia absoluta tol."""
    u, sigma, vt = np.linalg.svd(np.asarray(jacobian, dtype=float))
    rank = int(np.sum(sigma > tol))
    return RankAnalysis(sigma, rank, tol, u[:, rank:], vt[rank:, :].T)


def weakest_directions(jacobian: Matrix) -> tuple[float, Matrix, Matrix]:
    """(sigma_min, u_min, v_min): la direccion cartesiana mas dificil y el q_dot asociado.

    J v_min = sigma_min u_min. Para generar un twist unitario en u_min hace falta
    q_dot = v_min / sigma_min: la amplificacion de velocidad articular es 1 / sigma_min.
    """
    u, sigma, vt = np.linalg.svd(np.asarray(jacobian, dtype=float))
    return float(sigma[-1]), u[:, -1], vt[-1, :]
