"""G2: que predice nuestro modelo para los seis ejes que reporta el robot real.

Toma los ejes leidos (grados, convencion jointtarget de RAPID) y calcula con la FK del Hito 2 donde deberia
estar `tool0` en el marco base, en las unidades del FlexPendant: mm y cuaternion (w, x, y, z). Asi se puede
contrastar lado a lado con la posicion cartesiana que muestra el FlexPendant.

No contacta al robot ni a la red: solo calcula. Uso (desde hito2/, con el entorno del proyecto):

    .venv/bin/python comparar_lectura_abb.py --json ../docs/conexion_abb/evidencias/g1_rws_AAAA-MM-DD.json
    .venv/bin/python comparar_lectura_abb.py --q 10.5 -20.25 30 0 45 90
    .venv/bin/python comparar_lectura_abb.py --q 0 0 0 0 0 0 --flexpendant 374 0 630
    .venv/bin/python comparar_lectura_abb.py --json ARCHIVO.json --flexpendant X Y Z --flexpendant-quat Q1 Q2 Q3 Q4

Se compara `tool0` (la brida) y no el TCP de 0.150 m, porque el TCP fisico todavia no esta verificado en el robot.
"""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from irb120.dh import JOINT_LIMITS_DEG, forward_kinematics, forward_kinematics_tcp
from irb120.jacobian import condition_number, smallest_singular_value
from irb120.transforms import matrix_to_quaternion

SINGULAR_SIGMA = 1.0e-2


def load_axes(path):
    """Seis ejes [deg] de un JSON de abb_lectura_rws.py; ValueError si no hay una lectura valida."""
    data = json.loads(Path(path).read_text())
    snapshot = (data.get("controller_probe") or {}).get("joint_snapshot")
    if not snapshot:
        state = (data.get("controller_probe") or {}).get("state", "sin lectura")
        raise ValueError(f"El archivo no contiene una lectura de ejes (estado: {state}).")
    return [float(v) for v in snapshot["rax_1_to_6"]]


def abb_quaternion(rotation):
    """Cuaternion en el orden de ABB (w, x, y, z), con w >= 0 (q y -q son la misma rotacion)."""
    x, y, z, w = matrix_to_quaternion(rotation)
    sign = -1.0 if w < 0 else 1.0
    return (sign * w, sign * x, sign * y, sign * z)


def quaternion_angle_deg(a, b):
    """Angulo [deg] de la rotacion que lleva el cuaternion `a` al `b` (q y -q son la misma rotacion)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != (4,) or b.shape != (4,) or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("Cada cuaternion necesita cuatro valores finitos.")
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0.0 or nb == 0.0:
        raise ValueError("El cuaternion no puede ser nulo.")
    dot = min(1.0, abs(float(a @ b)) / (na * nb))
    return float(np.rad2deg(2.0 * np.arccos(dot)))


def predict(q_deg):
    """Prediccion del modelo para unos ejes [deg]: dict con tool0 [mm], cuaternion, TCP y avisos."""
    q_deg = np.asarray(q_deg, dtype=float)
    if q_deg.shape != (6,) or not np.all(np.isfinite(q_deg)):
        raise ValueError("Se necesitan seis ejes finitos en grados.")
    q = np.deg2rad(q_deg)
    flange = forward_kinematics(q)
    sigma = smallest_singular_value(q)
    return {
        "q_deg": q_deg.tolist(),
        "outside_limits": [i + 1 for i, (v, (lo, hi)) in enumerate(zip(q_deg, JOINT_LIMITS_DEG))
                           if not lo - 1e-9 <= v <= hi + 1e-9],
        "tool0_mm": (flange[:3, 3] * 1000.0).tolist(),
        "tool0_quaternion_wxyz": list(abb_quaternion(flange[:3, :3])),
        "tcp_mm_model_0150": (forward_kinematics_tcp(q)[:3, 3] * 1000.0).tolist(),
        "sigma_min": sigma,
        "condition_number": condition_number(q),
        "near_singularity": sigma < SINGULAR_SIGMA,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", type=Path, help="JSON producido por scripts/abb_lectura_rws.py")
    source.add_argument("--q", type=float, nargs=6, metavar="DEG", help="Seis ejes en grados")
    parser.add_argument("--flexpendant", type=float, nargs=3, metavar=("X", "Y", "Z"),
                        help="Posicion de tool0 que muestra el FlexPendant [mm], para ver la diferencia")
    parser.add_argument("--flexpendant-quat", type=float, nargs=4, metavar=("Q1", "Q2", "Q3", "Q4"),
                        help="Orientacion de tool0 que muestra el FlexPendant (q1 q2 q3 q4 = w x y z)")
    args = parser.parse_args(argv)
    try:
        q_deg = load_axes(args.json) if args.json else args.q
        result = predict(q_deg)
    except (ValueError, OSError, KeyError) as exc:
        print(f"No se pudo calcular: {exc}")
        return 2

    print("Ejes leidos [deg]      :", "  ".join(f"{v:9.3f}" for v in result["q_deg"]))
    if result["outside_limits"]:
        print(f"AVISO: ejes fuera de los limites del datasheet: {result['outside_limits']}")
    x, y, z = result["tool0_mm"]
    print(f"tool0 segun el modelo  : x={x:9.2f}  y={y:9.2f}  z={z:9.2f} mm   (marco base, tool0, wobj0)")
    print("cuaternion (w x y z)   :", "  ".join(f"{v:8.5f}" for v in result["tool0_quaternion_wxyz"]))
    print(f"TCP del modelo (0.150) : x={result['tcp_mm_model_0150'][0]:9.2f}  y={result['tcp_mm_model_0150'][1]:9.2f}"
          f"  z={result['tcp_mm_model_0150'][2]:9.2f} mm   (no verificado en el robot)")
    print(f"sigma_min(J) = {result['sigma_min']:.4f}   cond(J) = {result['condition_number']:.3g}"
          + ("   << cerca de una singularidad" if result["near_singularity"] else ""))
    if args.flexpendant:
        diff = np.array(args.flexpendant) - np.array(result["tool0_mm"])
        print(f"FlexPendant - modelo   : dx={diff[0]:7.2f}  dy={diff[1]:7.2f}  dz={diff[2]:7.2f} mm   "
              f"|d| = {np.linalg.norm(diff):.2f} mm")
    if args.flexpendant_quat:
        try:
            angle = quaternion_angle_deg(result["tool0_quaternion_wxyz"], args.flexpendant_quat)
        except ValueError as exc:
            print(f"No se pudo comparar el cuaternion: {exc}")
            return 2
        print(f"FlexPendant - modelo   : giro entre las dos orientaciones = {angle:.4f} deg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
