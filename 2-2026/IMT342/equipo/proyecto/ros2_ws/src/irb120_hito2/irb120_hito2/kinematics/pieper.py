"""Cinematica inversa analitica del ABB IRB 120 por el metodo de Pieper.

El IRB 120 tiene muneca esferica: los ejes 4, 5 y 6 se cortan en un punto, el
centro de muneca (origen de los marcos 4 y 5, pues a4 = a5 = d5 = 0). Pieper
desacopla el problema:

1. Posicion: p_wc = p_tool0 - d6 * z6 depende solo de q1, q2, q3.
   - q1 = atan2(y, x) (o + pi con el brazo "hacia atras").
   - En el plano vertical del brazo, hombro S = (0, d1), brazo L2 y antebrazo
     L3 = sqrt(d4^2 + a3^2) desplazado delta = atan2(a3, d4). La ley de cosenos
     da dos soluciones de codo.
2. Orientacion: R_3^6 = R_0^3^T R_0^6 = Rz(q4) Ry(-q5) Rz(q6 + pi), una
   descomposicion de Euler ZYZ que da dos soluciones de muneca (q5 > 0 / < 0).

Resultan hasta 8 soluciones; se filtran por limites articulares y se verifican
contra la cinematica directa DH. Sin MoveIt ni resolvedores numericos.
"""

from dataclasses import dataclass
from math import acos, asin, atan2, hypot, pi, sqrt

import numpy as np
from numpy.typing import NDArray

from irb120_hito1.kinematics.dh import (
    DH_PARAMETERS,
    dh_transform,
    forward_kinematics,
    position_error_m,
    rotation_error_rad,
    tcp_transform,
)

Matrix4 = NDArray[np.float64]

D1 = DH_PARAMETERS[0].d_m
L2 = DH_PARAMETERS[1].a_m
A3 = DH_PARAMETERS[2].a_m
D4 = DH_PARAMETERS[3].d_m
D6 = DH_PARAMETERS[5].d_m
L3 = sqrt(D4 * D4 + A3 * A3)
DELTA = atan2(A3, D4)

LIMITS_RAD = np.deg2rad(
    np.array(
        [
            [-165.0, 165.0],
            [-110.0, 110.0],
            [-110.0, 70.0],
            [-160.0, 160.0],
            [-120.0, 120.0],
            [-400.0, 400.0],
        ]
    )
)
SINGULARITY_EPS = 1.0e-9
FK_TOLERANCE_M = 1.0e-6


@dataclass(frozen=True)
class IKSolution:
    """Una solucion articular [rad] con su configuracion (brazo, codo, muneca)."""

    q: tuple[float, ...]
    arm: str  # "frente" o "atras"
    elbow: str  # "arriba" o "abajo"
    wrist: str  # "q5+" o "q5-"
    singular_wrist: bool = False


def _wrap_pi(angle: float) -> float:
    return (angle + pi) % (2.0 * pi) - pi


def _fit_to_limits(angle: float, lower: float, upper: float, reference: float) -> float | None:
    """Representante angle + 2*pi*k dentro de limites, el mas cercano a reference."""
    best = None
    for turns in range(-3, 4):
        candidate = angle + 2.0 * pi * turns
        if lower - 1e-9 <= candidate <= upper + 1e-9:
            if best is None or abs(candidate - reference) < abs(best - reference):
                best = candidate
    return best


def _arm_solutions(wrist_center: NDArray[np.float64]) -> list[tuple[str, str, float, float, float]]:
    """Soluciones (arm, elbow, q1, q2, q3) que colocan el centro de muneca."""
    x, y, z = wrist_center
    planar = hypot(x, y)
    height = z - D1
    results = []
    for arm, q1, radial in (
        ("frente", atan2(y, x), planar),
        ("atras", atan2(y, x) + pi, -planar),
    ):
        reach_sq = radial * radial + height * height
        cos_term = (reach_sq - L2 * L2 - L3 * L3) / (2.0 * L2 * L3)
        if abs(cos_term) > 1.0 + 1e-12:
            continue  # fuera del espacio de trabajo
        cos_term = max(-1.0, min(1.0, cos_term))
        # -sin(q3 - delta) = cos_term  ->  dos soluciones de codo
        base = asin(-cos_term)
        alpha = atan2(radial, height)  # angulo de S->W medido desde la vertical
        for elbow, q3_minus_delta in (("arriba", base), ("abajo", pi - base)):
            q3 = _wrap_pi(q3_minus_delta + DELTA)
            eta = pi / 2.0 + q3 - DELTA
            q2 = _wrap_pi(alpha - atan2(L3 * np.sin(eta), L2 + L3 * np.cos(eta)))
            results.append((arm, elbow, _wrap_pi(q1), q2, q3))
    return results


def _rotation_0_3(q1: float, q2: float, q3: float) -> NDArray[np.float64]:
    transform = np.eye(4)
    for angle, parameter in zip((q1, q2, q3), DH_PARAMETERS[:3], strict=True):
        transform = transform @ dh_transform(angle, parameter)
    return transform[:3, :3]


def _wrist_solutions(rotation_3_6: NDArray[np.float64], q4_reference: float):
    """Soluciones (wrist, q4, q5, q6, singular) de R36 = Rz(q4) Ry(-q5) Rz(q6+pi)."""
    sin_beta = hypot(rotation_3_6[0, 2], rotation_3_6[1, 2])
    if sin_beta < SINGULARITY_EPS:
        # q5 = 0: solo q4 + q6 es determinable; se conserva q4 de referencia.
        total = atan2(rotation_3_6[1, 0], rotation_3_6[0, 0])
        return [("q5+", q4_reference, 0.0, total - q4_reference - pi, True)]
    cos_beta = float(rotation_3_6[2, 2])
    solutions = []
    for wrist, sign in (("q5+", 1.0), ("q5-", -1.0)):
        beta = atan2(sign * sin_beta, cos_beta)
        alpha = atan2(sign * rotation_3_6[1, 2], sign * rotation_3_6[0, 2])
        gamma = atan2(sign * rotation_3_6[2, 1], -sign * rotation_3_6[2, 0])
        solutions.append((wrist, alpha, -beta, gamma - pi, False))
    return solutions


def inverse_kinematics(
    target_tool0: Matrix4,
    reference_q: np.ndarray | None = None,
) -> list[IKSolution]:
    """Todas las soluciones validas para la pose de tool0, ordenadas por cercania.

    `target_tool0` es base_link -> tool0 (4x4). Si no hay solucion (fuera del
    alcance o limites articulares) devuelve una lista vacia.
    """
    target = np.asarray(target_tool0, dtype=float)
    if target.shape != (4, 4) or not np.all(np.isfinite(target)):
        raise ValueError("target_tool0 debe ser una matriz 4x4 finita.")
    reference = np.zeros(6) if reference_q is None else np.asarray(reference_q, dtype=float)
    rotation = target[:3, :3]
    wrist_center = target[:3, 3] - D6 * rotation[:, 2]

    found: list[IKSolution] = []
    for arm, elbow, q1, q2, q3 in _arm_solutions(wrist_center):
        rotation_3_6 = _rotation_0_3(q1, q2, q3).T @ rotation
        for wrist, q4, q5, q6, singular in _wrist_solutions(rotation_3_6, reference[3]):
            raw = (q1, q2, q3, q4, q5, q6)
            fitted = [
                _fit_to_limits(angle, lower, upper, reference[index])
                for index, (angle, (lower, upper)) in enumerate(zip(raw, LIMITS_RAD, strict=True))
            ]
            if any(value is None for value in fitted):
                continue
            q = np.array(fitted, dtype=float)
            check = forward_kinematics(q)
            if position_error_m(target, check) > FK_TOLERANCE_M:
                continue
            if rotation_error_rad(target, check) > 1.0e-6:
                continue
            found.append(IKSolution(tuple(q), arm, elbow, wrist, singular))

    found.sort(key=lambda solution: float(np.linalg.norm(np.array(solution.q) - reference)))
    unique: list[IKSolution] = []
    for solution in found:
        if not any(np.allclose(solution.q, other.q, atol=1e-9) for other in unique):
            unique.append(solution)
    return unique


def inverse_kinematics_tcp(
    target_tcp: Matrix4,
    reference_q: np.ndarray | None = None,
) -> list[IKSolution]:
    """Igual que inverse_kinematics pero para la pose del TCP de la pinza."""
    tool0 = np.asarray(target_tcp, dtype=float) @ np.linalg.inv(tcp_transform())
    return inverse_kinematics(tool0, reference_q)
