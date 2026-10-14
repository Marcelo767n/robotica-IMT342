"""Analiza si una pose del TCP es alcanzable por el IRB 120 y muestra las 8 ramas de Pieper.

Uso (desde hito2/):
    python analizar_pose.py X Y Z ROLL PITCH YAW          # metros y grados (R = Rz(yaw) Ry(pitch) Rx(roll))
    python analizar_pose.py 0.40 0.10 0.35 0 180 0
"""

import argparse

import numpy as np

from irb120.dh import HOME_Q, TCP_Z_M
from irb120.pieper import REACH_MAX_M, REACH_MIN_M, analyze_pose, select_solution
from irb120.transforms import pose_from_xyz_rpy_deg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("x", "y", "z"):
        parser.add_argument(name, type=float, help=f"{name} del TCP [m]")
    for name in ("roll", "pitch", "yaw"):
        parser.add_argument(name, type=float, help=f"{name} [grados]")
    args = parser.parse_args()

    target = pose_from_xyz_rpy_deg(args.x, args.y, args.z, args.roll, args.pitch, args.yaw)
    report = analyze_pose(target)
    np.set_printoptions(precision=4, suppress=True)
    print(f"T_d (TCP a {TCP_Z_M:.3f} m de tool0):\n{target}")
    print(f"Centro de muneca p_wc = {report.wrist_center} m")
    print(
        f"Distancia hombro-muneca = {report.shoulder_to_wrist_m:.4f} m "
        f"(rango alcanzable [{REACH_MIN_M:.4f}, {REACH_MAX_M:.4f}] m)\n"
    )
    header = f"{'rama':>4} {'brazo':>6} {'codo':>6} {'muneca':>6} {'real':>5} {'limites':>13}  q [deg]{'':40} {'e_p [m]':>9} {'e_R [rad]':>9}  acepta"
    print(header)
    for row in report.table():
        q = "-" if row["q_deg"] is None else " ".join(f"{v:7.2f}" for v in row["q_deg"])
        e_p = "-" if row["e_p_m"] is None else f"{row['e_p_m']:.1e}"
        e_r = "-" if row["e_R_rad"] is None else f"{row['e_R_rad']:.1e}"
        limits = "si" if row["en_limites"] else ("-" if not row["real"] else f"no {row['fuera_de_limites']}")
        print(
            f"{row['rama']:>4} {row['brazo']:>6} {row['codo']:>6} {row['muneca']:>6} "
            f"{'si' if row['real'] else 'no':>5} {limits:>13}  {q:47} {e_p:>9} {e_r:>9}  "
            f"{'SI' if row['aceptada'] else 'no'}"
        )
    print("\n" + report.verdict)
    chosen = select_solution(report, HOME_Q)
    if chosen is not None:
        print(f"Rama seleccionada desde la pose inicial (calibracion ABB, q = 0): {chosen.branch} -> q = {np.rad2deg(chosen.q)} deg")


if __name__ == "__main__":
    main()
