"""Validacion por cinematica directa (FK) de candidatos de cinematica inversa.

Un candidato q^(k) de Pieper solo se acepta si al reinyectarlo en la FK
reproduce la pose deseada completa (posicion Y orientacion):

    e_p = || p(q) - p_d ||                       [m]
    e_R = angulo de R_d^T R(q)  (distancia geodesica en SO(3))   [rad]
    e_F = || T(q) - T_d ||_F                     (indicador global, sin unidad)

Criterio de aceptacion: e_p < POSITION_TOL_M  y  e_R < ROTATION_TOL_RAD.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from irb120.dh import (
    JOINT_LIMITS_RAD,
    forward_kinematics,
    forward_kinematics_tcp,
    position_error_m,
    rotation_error_rad,
)

Matrix4 = NDArray[np.float64]

POSITION_TOL_M = 1.0e-6  # 1 micrometro: muy por debajo de la repetibilidad del IRB 120 (0.01 mm)
ROTATION_TOL_RAD = 1.0e-6


@dataclass(frozen=True)
class FKCheck:
    """Resultado de comparar T(q) con T_d."""

    position_error_m: float
    rotation_error_rad: float
    frobenius_error: float

    @property
    def accepted(self) -> bool:
        return self.position_error_m < POSITION_TOL_M and self.rotation_error_rad < ROTATION_TOL_RAD


def fk_check(target: Matrix4, q, tcp: bool = True) -> FKCheck:
    """Reinyecta q en la FK (al TCP o a tool0) y mide el error frente a target."""
    reached = forward_kinematics_tcp(q) if tcp else forward_kinematics(q)
    target = np.asarray(target, dtype=float)
    return FKCheck(
        position_error_m(target, reached),
        rotation_error_rad(target, reached),
        float(np.linalg.norm(reached - target)),
    )


@dataclass(frozen=True)
class RoundTripStats:
    """Resumen de la prueba de ida y vuelta q -> FK -> IK -> FK sobre poses aleatorias."""

    samples: int
    solved: int
    recovered_original: int
    max_position_error_m: float
    max_rotation_error_rad: float


def round_trip_test(samples: int = 1000, seed: int = 0) -> RoundTripStats:
    """Genera q aleatorios dentro de limites, calcula T = FK(q), resuelve IK y vuelve a verificar.

    Cuenta cuantas veces aparece el q original entre las soluciones y el peor error FK
    de todas las soluciones aceptadas.
    """
    from irb120.pieper import inverse_kinematics_tcp  # import local: pieper depende de este modulo

    generator = np.random.default_rng(seed)
    solved = recovered = 0
    worst_position = worst_rotation = 0.0
    for _ in range(samples):
        q = generator.uniform(JOINT_LIMITS_RAD[:, 0], JOINT_LIMITS_RAD[:, 1])
        target = forward_kinematics_tcp(q)
        solutions = inverse_kinematics_tcp(target, q)
        if not solutions:
            continue
        solved += 1
        if any(np.allclose(solution.q, q, atol=1e-6) for solution in solutions):
            recovered += 1
        for solution in solutions:
            check = fk_check(target, solution.q)
            worst_position = max(worst_position, check.position_error_m)
            worst_rotation = max(worst_rotation, check.rotation_error_rad)
    return RoundTripStats(samples, solved, recovered, worst_position, worst_rotation)
