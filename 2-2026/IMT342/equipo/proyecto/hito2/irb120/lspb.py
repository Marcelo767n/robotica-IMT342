"""Perfil LSPB (Linear Segment with Parabolic Blends) sincronizado en espacio articular.

Todas las juntas comparten el tiempo total tf y el tiempo de mezcla tb, de modo
que llegan a la vez. Para la junta i con desplazamiento D_i:

    V_i = D_i / (tf - tb)        a_i = V_i / tb

    0 <= t < tb         q = q0 + a t^2 / 2                 (arranque parabolico)
    tb <= t <= tf - tb  q = q0 + V (t - tb / 2)            (tramo lineal)
    tf - tb < t <= tf   q = qf - a (tf - t)^2 / 2          (frenado parabolico)

El menor tf factible respeta |V_i| <= vmax_i y |a_i| <= amax_i en todas las
juntas; se obtiene por biseccion porque la factibilidad es monotona en tf.

Limites usados (ver `default_limits`): vmax sale del datasheet ABB por eje,
escalado por un factor de velocidad (como el "speed override" del controlador);
ABB no publica aceleraciones articulares, asi que amax = vmax / t_rampa con un
tiempo de rampa declarado como supuesto de diseno.
"""

from dataclasses import dataclass

import numpy as np

from irb120.dh import MAX_SPEED_RAD_S
from numpy.typing import NDArray

Vector = NDArray[np.float64]


@dataclass(frozen=True)
class LspbTrajectory:
    q0: Vector
    qf: Vector
    tf: float
    tb: float

    @property
    def displacement(self) -> Vector:
        return self.qf - self.q0

    @property
    def cruise_velocity(self) -> Vector:
        return self.displacement / (self.tf - self.tb)

    @property
    def blend_acceleration(self) -> Vector:
        return self.cruise_velocity / self.tb

    def sample(self, t: float) -> tuple[Vector, Vector, Vector]:
        """Posicion, velocidad y aceleracion en el instante t (saturado a [0, tf])."""
        t = min(max(float(t), 0.0), self.tf)
        v, a = self.cruise_velocity, self.blend_acceleration
        if t < self.tb:
            return self.q0 + 0.5 * a * t * t, a * t, a.copy()
        if t <= self.tf - self.tb:
            return self.q0 + v * (t - 0.5 * self.tb), v.copy(), np.zeros_like(v)
        remaining = self.tf - t
        return self.qf - 0.5 * a * remaining * remaining, a * remaining, -a

    def sample_many(self, times) -> tuple[Vector, Vector, Vector]:
        """q, q_dot, q_ddot para un arreglo de tiempos: cada uno de forma (N, n_juntas)."""
        samples = [self.sample(t) for t in np.asarray(times, dtype=float)]
        return tuple(np.array([s[k] for s in samples]) for k in range(3))

    def phase(self, t: float) -> str:
        """'acelera', 'crucero' o 'frena'."""
        if t < self.tb:
            return "acelera"
        return "crucero" if t <= self.tf - self.tb else "frena"


@dataclass(frozen=True)
class LspbCheck:
    """Comprobaciones numericas de un perfil LSPB."""

    start_position_error: float  # max |q(0) - q0|
    end_position_error: float  # max |q(tf) - qf|
    start_velocity: float  # max |q_dot(0)|
    end_velocity: float  # max |q_dot(tf)|
    position_jump: float  # max salto de q en tb y tf - tb
    velocity_jump: float  # max salto de q_dot en tb y tf - tb
    velocity_margin: float  # min (vmax - |V|): >= 0 si respeta limites
    acceleration_margin: float  # min (amax - |a|)

    @property
    def passed(self) -> bool:
        tol = 1e-6
        return (
            max(self.start_position_error, self.end_position_error, self.start_velocity, self.end_velocity) < tol
            and max(self.position_jump, self.velocity_jump) < tol
            and min(self.velocity_margin, self.acceleration_margin) > -1e-9
        )


def check_trajectory(trajectory: LspbTrajectory, vmax, amax, epsilon: float = 1e-9) -> LspbCheck:
    """Fronteras en reposo, continuidad de q y q_dot en las mezclas y respeto de limites."""
    q0, v0, _ = trajectory.sample(0.0)
    qf, vf, _ = trajectory.sample(trajectory.tf)
    position_jump = velocity_jump = 0.0
    for instant in (trajectory.tb, trajectory.tf - trajectory.tb):
        before = trajectory.sample(instant - epsilon)
        after = trajectory.sample(instant + epsilon)
        position_jump = max(position_jump, float(np.max(np.abs(before[0] - after[0]))))
        velocity_jump = max(velocity_jump, float(np.max(np.abs(before[1] - after[1]))))
    return LspbCheck(
        float(np.max(np.abs(q0 - trajectory.q0))),
        float(np.max(np.abs(qf - trajectory.qf))),
        float(np.max(np.abs(v0))),
        float(np.max(np.abs(vf))),
        position_jump,
        velocity_jump,
        float(np.min(np.asarray(vmax) - np.abs(trajectory.cruise_velocity))),
        float(np.min(np.asarray(amax) - np.abs(trajectory.blend_acceleration))),
    )


def default_limits(speed_scale: float = 0.25, ramp_time_s: float = 0.25) -> tuple[Vector, Vector]:
    """(vmax, amax) por junta [rad/s, rad/s^2].

    vmax = speed_scale * velocidad maxima del datasheet ABB.
    amax = vmax / ramp_time_s  (supuesto: la junta alcanza vmax en ramp_time_s).
    """
    if not 0.0 < speed_scale <= 1.0 or ramp_time_s <= 0.0:
        raise ValueError("speed_scale debe estar en (0, 1] y ramp_time_s ser positivo.")
    vmax = speed_scale * MAX_SPEED_RAD_S
    return vmax, vmax / ramp_time_s


def plan_lspb(q0, qf, vmax, amax) -> LspbTrajectory:
    """Planifica un LSPB sincronizado con limites de velocidad y aceleracion."""
    q0 = np.asarray(q0, dtype=float)
    qf = np.asarray(qf, dtype=float)
    vmax = np.broadcast_to(np.asarray(vmax, dtype=float), q0.shape)
    amax = np.broadcast_to(np.asarray(amax, dtype=float), q0.shape)
    if q0.shape != qf.shape or q0.ndim != 1:
        raise ValueError("q0 y qf deben ser vectores de la misma longitud.")
    if np.any(vmax <= 0.0) or np.any(amax <= 0.0):
        raise ValueError("vmax y amax deben ser positivos.")
    distance = np.abs(qf - q0)
    if float(distance.max()) == 0.0:
        return LspbTrajectory(q0, qf, tf=1.0, tb=0.5)  # sin movimiento

    accel_term = float(np.max(distance / amax))  # K: tb (tf - tb) >= K
    cruise_term = float(np.max(distance / vmax))  # tf - tb >= Dv

    def blend_time(tf: float) -> float:
        return 0.5 * (tf - np.sqrt(tf * tf - 4.0 * accel_term))

    def feasible(tf: float) -> bool:
        return tf * tf >= 4.0 * accel_term and blend_time(tf) <= tf - cruise_term + 1e-12

    low = max(2.0 * np.sqrt(accel_term), cruise_term)
    high = 2.0 * low + 1.0
    while not feasible(high):
        high *= 2.0
    if feasible(low):
        high = low
    else:
        for _ in range(100):
            middle = 0.5 * (low + high)
            low, high = (low, middle) if feasible(middle) else (middle, high)
    return LspbTrajectory(q0, qf, tf=float(high), tb=float(blend_time(high)))

