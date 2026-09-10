"""Trayectoria articular sencilla para demostrar el Hito 1 en RViz."""

from math import cos, pi

import numpy as np
from numpy.typing import NDArray


# Seis angulos ABB en grados y apertura de cada dedo en metros.
DEMO_KEYFRAMES = np.array(
    [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.000],
        [30.0, -20.0, 15.0, 40.0, -35.0, 60.0, 0.012],
        [-35.0, 30.0, -40.0, -50.0, 45.0, -90.0, 0.004],
        [15.0, 50.0, -65.0, 80.0, 30.0, 120.0, 0.015],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.000],
    ],
    dtype=float,
)


def interpolate_demo(elapsed_s: float, segment_duration_s: float) -> NDArray[np.float64]:
    """Interpolate cyclic keyframes with zero velocity at each endpoint."""
    if elapsed_s < 0.0:
        raise ValueError("elapsed_s no puede ser negativo.")
    if segment_duration_s <= 0.0:
        raise ValueError("segment_duration_s debe ser positivo.")

    segment_count = len(DEMO_KEYFRAMES) - 1
    cycle_duration = segment_count * segment_duration_s
    cycle_time = elapsed_s % cycle_duration
    segment_index = min(int(cycle_time // segment_duration_s), segment_count - 1)
    local_time = (cycle_time - segment_index * segment_duration_s) / segment_duration_s
    blend = 0.5 - 0.5 * cos(pi * local_time)

    start = DEMO_KEYFRAMES[segment_index]
    end = DEMO_KEYFRAMES[segment_index + 1]
    return start + blend * (end - start)
