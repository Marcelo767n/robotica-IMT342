"""Modelo dinamico Lagrangiano del IRB 120: M(q), c(q, q_dot), g(q) y torques.

Los parametros inerciales (masa, centro de masa e inercia por eslabon) son las
aproximaciones por CAD de Truc y Lam (Turk J Elec Eng & Comp Sci, vol. 28, 2020, ec. 18),
expresadas en los marcos DH clasicos de los eslabones 1 a 6. Por defecto se suma
la pinza SMC MHZ2-16D (115 g, hoja de datos del fabricante) al eslabon 6 con el
teorema de ejes paralelos; `links=LINKS_NO_GRIPPER` reproduce el paper tal cual.
Se usan para evidenciar tendencias (divergencia en singularidad), no como
identificacion del robot real.

tau = M(q) q_ddot + c(q, q_dot) + g(q), con
c = M_dot q_dot - 1/2 grad_q(q_dot^T M q_dot) calculada por diferencias finitas.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from irb120.jacobian import (
    geometric_jacobian,
    jacobian_dot,
    joint_frames,
    solve_with_jacobian,
)

Matrix = NDArray[np.float64]
GRAVITY_M_S2 = 9.81


@dataclass(frozen=True)
class LinkInertia:
    mass_kg: float
    com_m: tuple[float, float, float]
    inertia_kg_m2: Matrix


def _diag(ixx: float, iyy: float, izz: float, scale: float) -> Matrix:
    return np.diag([ixx, iyy, izz]) * scale


_LINK3_INERTIA = np.array(
    [[17.562, 0.0, -1.993], [0.0, 23.140, 0.0], [-1.993, 0.0, 11.589]]
) * 1.0e-3

_PAPER_LINKS = (
    LinkInertia(4.248, (0.0, 0.054, 0.0), _diag(19.699, 14.484, 19.952, 1.0e-3)),
    LinkInertia(5.412, (-0.169, 0.0, 0.0), _diag(35.942, 83.522, 57.569, 1.0e-3)),
    LinkInertia(4.077, (-0.012, 0.0, 0.023), _LINK3_INERTIA),
    LinkInertia(1.832, (0.0, -0.007, 0.0), _diag(7.247, 3.919, 5.551, 1.0e-3)),
    LinkInertia(0.755, (0.0, 0.0, 0.0), _diag(1.120, 1.227, 0.559, 1.0e-3)),
    LinkInertia(0.019, (0.0, 0.0, -0.007), _diag(2.347, 2.347, 4.123, 1.0e-6)),
)


GRIPPER_MASS_KG = 0.115  # SMC MHZ2-16D
GRIPPER_COM_M = (0.0, 0.0, 0.040)  # en el marco tool0 (aprox.: cuerpo de la pinza)


def _parallel_axis(inertia: Matrix, mass: float, offset: np.ndarray) -> Matrix:
    return inertia + mass * (float(offset @ offset) * np.eye(3) - np.outer(offset, offset))


def _with_gripper(links: tuple[LinkInertia, ...]) -> tuple[LinkInertia, ...]:
    """Fusiona la pinza (masa puntual) con el eslabon 6."""
    wrist = links[-1]
    mass = wrist.mass_kg + GRIPPER_MASS_KG
    com = (wrist.mass_kg * np.array(wrist.com_m) + GRIPPER_MASS_KG * np.array(GRIPPER_COM_M)) / mass
    inertia = _parallel_axis(wrist.inertia_kg_m2, wrist.mass_kg, np.array(wrist.com_m) - com)
    inertia = _parallel_axis(inertia, GRIPPER_MASS_KG, np.array(GRIPPER_COM_M) - com)
    return (*links[:-1], LinkInertia(mass, tuple(com), inertia))


LINKS_NO_GRIPPER = _PAPER_LINKS
LINKS = _with_gripper(_PAPER_LINKS)


def _com_jacobians(q: np.ndarray, links: tuple[LinkInertia, ...] = LINKS):
    """Por eslabon: (Jv, Jw, R) del centro de masa en base_link."""
    frames = joint_frames(q)
    result = []
    for link_index, link in enumerate(links, start=1):
        transform = frames[link_index]
        point = (transform @ np.array([*link.com_m, 1.0]))[:3]
        jv = np.zeros((3, 6))
        jw = np.zeros((3, 6))
        for joint in range(link_index):
            axis = frames[joint][:3, 2]
            jv[:, joint] = np.cross(axis, point - frames[joint][:3, 3])
            jw[:, joint] = axis
        result.append((jv, jw, transform[:3, :3]))
    return result


def mass_matrix(q: np.ndarray, links: tuple[LinkInertia, ...] = LINKS) -> Matrix:
    matrix = np.zeros((6, 6))
    for link, (jv, jw, rotation) in zip(links, _com_jacobians(q, links), strict=True):
        inertia_base = rotation @ link.inertia_kg_m2 @ rotation.T
        matrix += link.mass_kg * jv.T @ jv + jw.T @ inertia_base @ jw
    return 0.5 * (matrix + matrix.T)


def gravity_vector(q: np.ndarray, links: tuple[LinkInertia, ...] = LINKS) -> Matrix:
    torque = np.zeros(6)
    for link, (jv, _, _) in zip(links, _com_jacobians(q, links), strict=True):
        torque += link.mass_kg * GRAVITY_M_S2 * jv[2, :]
    return torque


def coriolis_vector(
    q: np.ndarray,
    q_dot: np.ndarray,
    step: float = 1.0e-6,
    links: tuple[LinkInertia, ...] = LINKS,
) -> Matrix:
    """c(q, q_dot) = M_dot q_dot - 1/2 grad_q(q_dot^T M q_dot)."""
    q = np.asarray(q, dtype=float)
    q_dot = np.asarray(q_dot, dtype=float)
    d_mass = np.zeros((6, 6, 6))  # d_mass[k] = dM/dq_k
    for k in range(6):
        delta = np.zeros(6)
        delta[k] = step
        d_mass[k] = (mass_matrix(q + delta, links) - mass_matrix(q - delta, links)) / (2.0 * step)
    m_dot_q_dot = sum(q_dot[k] * d_mass[k] @ q_dot for k in range(6))
    gradient = np.array([q_dot @ d_mass[k] @ q_dot for k in range(6)])
    return m_dot_q_dot - 0.5 * gradient


def inverse_dynamics(
    q: np.ndarray,
    q_dot: np.ndarray,
    q_ddot: np.ndarray,
    links: tuple[LinkInertia, ...] = LINKS,
) -> Matrix:
    return (
        mass_matrix(q, links) @ np.asarray(q_ddot, dtype=float)
        + coriolis_vector(q, q_dot, links=links)
        + gravity_vector(q, links)
    )


def cartesian_demand(
    q: np.ndarray, twist: np.ndarray, accel: np.ndarray, links: tuple[LinkInertia, ...] = LINKS
):
    """(q_dot, q_ddot, tau) que exige seguir un twist/aceleracion cartesianos.

    q_dot = J^-1 v ;  q_ddot = J^-1 (a - J_dot q_dot) ;  tau = inverse_dynamics.
    Cerca de q5 = 0 los tres crecen sin cota.
    """
    jacobian = geometric_jacobian(q)
    q_dot = solve_with_jacobian(q, twist, jacobian)
    q_ddot = solve_with_jacobian(
        q, np.asarray(accel, dtype=float) - jacobian_dot(q, q_dot) @ q_dot, jacobian
    )
    return q_dot, q_ddot, inverse_dynamics(q, q_dot, q_ddot, links)
