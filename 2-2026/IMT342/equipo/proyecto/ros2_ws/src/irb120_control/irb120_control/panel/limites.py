"""Límites articulares del panel: los del IRB 120 con el margen de 2° que también aplica el RAPID."""
import math

from irb120_control.rws_j6 import LIMITS, Refused
from irb120_control.rws_mover import MARGIN_DEG

BOUNDS = [(lo + MARGIN_DEG, hi - MARGIN_DEG) for lo, hi in LIMITS]
EXT = [9e9] * 6           # ejes externos «sin usar» en un jointtarget


def clean_target(values):
    """Seis ángulos finitos en grados dentro de los límites con margen; si no, Refused."""
    if not isinstance(values, (list, tuple)) or len(values) != 6:
        raise Refused('Se esperan exactamente seis ángulos (J1..J6) en grados.')
    result = []
    for index, (value, (lo, hi)) in enumerate(zip(values, BOUNDS), start=1):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise Refused(f'J{index} no es un número válido.')
        if not lo <= value <= hi:
            raise Refused(f'J{index}={value:.3f}° fuera de [{lo:g}, {hi:g}]°.')
        result.append(float(value))
    return result
