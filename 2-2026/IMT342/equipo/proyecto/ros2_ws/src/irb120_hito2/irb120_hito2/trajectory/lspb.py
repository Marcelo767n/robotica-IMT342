"""Perfil LSPB (Linear Segment with Parabolic Blends) sincronizado en espacio articular.

Todas las juntas comparten el tiempo total tf y el tiempo de mezcla tb, de modo
que llegan a la vez. Para la junta i con desplazamiento D_i:

    V_i = D_i / (tf - tb)        a_i = V_i / tb

    0 <= t < tb         q = q0 + a t^2 / 2                 (arranque parabolico)
    tb <= t <= tf - tb  q = q0 + V (t - tb / 2)            (tramo lineal)
    tf - tb < t <= tf   q = qf - a (tf - t)^2 / 2          (frenado parabolico)

El menor tf factible respeta |V_i| <= vmax_i y |a_i| <= amax_i en todas las
juntas; se obtiene por biseccion porque la factibilidad es monotona en tf.
"""

from dataclasses import dataclass

import numpy as np
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
