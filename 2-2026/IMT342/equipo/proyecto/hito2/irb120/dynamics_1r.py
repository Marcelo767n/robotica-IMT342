"""Modelo dinamico reducido 1R del hombro (junta 2) del IRB 120.

Modelo trabajado en clase (pendulo 1R, angulo medido desde la vertical inferior):

    T = 1/2 J theta_dot^2        V = m g lc (1 - cos theta)
    Euler-Lagrange  ->  tau = J theta_ddot + m g lc sin(theta),     J = I_c + m lc^2

Reduccion aplicada al IRB 120:
- La junta 2 (hombro, eje horizontal) es el actuador del pendulo.
- Todo lo que cuelga de ella (eslabones 2 a 6 + pinza) se trata como UN cuerpo
  rigido: las juntas 3 a 6 se congelan en una configuracion de referencia q_ref.
- m, lc, I_c NO se inventan: se calculan con los parametros CAD por eslabon de
  Truc y Lam (2020) que ya usa `dynamics.py` (masa, centro de masa e inercia),
  mas la pinza SMC MHZ2-16D (115 g, hoja de datos).
- Con el cuerpo congelado, theta = q2 + phi0: girar la junta 2 gira el centro de
  masa del mismo angulo. phi0 depende de q_ref y se calcula aqui.

Lo que el modelo 1R deja fuera: el movimiento simultaneo de las juntas 3-6 y los
terminos de Coriolis/centrifugos del modelo completo (en un 1R no existen: la
energia cinetica no depende de theta, por eso theta_dot no aparece en tau).
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from irb120.dynamics import GRAVITY_M_S2, LINKS, LinkInertia
from irb120.jacobian import joint_frames

Vector = NDArray[np.float64]
SHOULDER = 1  # indice 0-based de la junta 2
DOWN = np.array([0.0, 0.0, -1.0])


@dataclass(frozen=True)
class OneRModel:
    """Parametros del pendulo equivalente del hombro."""

    mass_kg: float  # m: masa total que mueve la junta 2
    lc_m: float  # lc: distancia del eje 2 al centro de masa, perpendicular al eje
    inertia_com_kg_m2: float  # I_c: inercia respecto al eje paralelo por el centro de masa
    phi0_rad: float  # theta = q2 + phi0
    q_ref: tuple[float, ...]  # configuracion con la que se congelaron las juntas 3-6

    @property
    def inertia_kg_m2(self) -> float:
        """J = I_c + m lc^2 (Steiner): inercia respecto al eje de la junta 2."""
        return self.inertia_com_kg_m2 + self.mass_kg * self.lc_m**2

    def pendulum_angle(self, q2) -> Vector:
        """theta medido desde la vertical inferior (convencion de clase)."""
        return np.asarray(q2, dtype=float) + self.phi0_rad

    def torque_components(self, q2, q2_ddot) -> tuple[Vector, Vector, Vector]:
        """(tau_inercial, tau_gravedad, tau_total) [N m] para arreglos q2(t), q2_ddot(t)."""
        inertial = self.inertia_kg_m2 * np.asarray(q2_ddot, dtype=float)
        gravity = self.mass_kg * GRAVITY_M_S2 * self.lc_m * np.sin(self.pendulum_angle(q2))
        return inertial, gravity, inertial + gravity

    def torque(self, q2, q2_ddot) -> Vector:
        return self.torque_components(q2, q2_ddot)[2]

    @property
    def max_gravity_torque(self) -> float:
        """m g lc: torque gravitacional cuando el centro de masa queda horizontal (theta = 90 deg)."""
        return self.mass_kg * GRAVITY_M_S2 * self.lc_m


def shoulder_model(q_ref, links: tuple[LinkInertia, ...] = LINKS) -> OneRModel:
    """Construye el modelo 1R del hombro con las juntas 3-6 congeladas en q_ref."""
    q_ref = np.asarray(q_ref, dtype=float)
    frames = joint_frames(q_ref)
    axis = frames[SHOULDER][:3, 2]  # la junta 2 gira sobre z1
    origin = frames[SHOULDER][:3, 3]

    mass = 0.0
    first_moment = np.zeros(3)
    inertia_axis = 0.0
    for link_number in range(SHOULDER + 1, 7):  # eslabones 2..6 (el 6 ya incluye la pinza)
        link = links[link_number - 1]
        transform = frames[link_number]
        com = (transform @ np.array([*link.com_m, 1.0]))[:3]
        rotation = transform[:3, :3]
        offset = com - origin
        inertia_base = rotation @ link.inertia_kg_m2 @ rotation.T
        # inercia del eslabon respecto al eje 2: propia + m * (distancia perpendicular)^2
        inertia_axis += float(axis @ inertia_base @ axis)
        inertia_axis += link.mass_kg * float(offset @ offset - (offset @ axis) ** 2)
        mass += link.mass_kg
        first_moment += link.mass_kg * offset

    radius = first_moment / mass
    radius_perp = radius - (radius @ axis) * axis
    lc = float(np.linalg.norm(radius_perp))
    theta = float(np.arctan2(axis @ np.cross(DOWN, radius_perp), DOWN @ radius_perp))
    return OneRModel(
        mass_kg=mass,
        lc_m=lc,
        inertia_com_kg_m2=inertia_axis - mass * lc * lc,
        phi0_rad=theta - float(q_ref[SHOULDER]),
        q_ref=tuple(q_ref),
    )
