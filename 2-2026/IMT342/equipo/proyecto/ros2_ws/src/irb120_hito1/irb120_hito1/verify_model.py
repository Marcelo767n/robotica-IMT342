"""Verificación reproducible DH contra URDF: poses justificadas y aleatorias."""

import argparse
from pathlib import Path

import numpy as np

from irb120_hito1.kinematics.dh import GRIPPER_TCP_Z_M, TCP_VERIFIED_ON_ROBOT
from irb120_hito1.validation import (
    DEFAULT_TOLERANCE_M,
    FRAMES,
    VALIDATION_POSES,
    evaluate_pose,
    run_suite,
)


def default_urdf_path() -> Path:
    try:
        from ament_index_python.packages import get_package_share_directory

        share = Path(get_package_share_directory("irb120_hito1"))
        candidate = share / "urdf" / "irb120.urdf"
        if candidate.exists():
            return candidate
    except (ImportError, LookupError):
        pass

    source_candidate = Path(__file__).resolve().parents[1] / "urdf" / "irb120.urdf"
    if source_candidate.exists():
        return source_candidate
    raise FileNotFoundError("No se encontró irb120.urdf.")


def verify(urdf_path: Path, tolerance_m: float, random_count: int = 100) -> bool:
    print(f"URDF: {urdf_path}")
    print("Comparación: T_DH(q) contra T_URDF(q), de base_link a tool0 y a gripper_tcp")
    print(f"Tolerancia posicional: {tolerance_m:.1e} m")
    print(
        f"TCP tool0->gripper_tcp (config/tcp.yaml): {GRIPPER_TCP_Z_M:.4f} m "
        f"({'verificado' if TCP_VERIFIED_ON_ROBOT else 'NO verificado en el robot'})"
    )

    for pose in VALIDATION_POSES:
        print(f"\nPrueba {pose.name}")
        print(f"q [deg]: {list(pose.joints_deg)}")
        print(f"Motivo: {pose.reason}")
        for frame in FRAMES:
            result = evaluate_pose(urdf_path, pose, frame, tolerance_m)
            radial_distance = float(np.hypot(*result.position_dh_m[:2]))
            print(f"  [{frame}]")
            print(f"  p_DH [m]: {np.array2string(np.array(result.position_dh_m), precision=6)}")
            print(f"  p_URDF [m]: {np.array2string(np.array(result.position_urdf_m), precision=6)}")
            print(f"  Distancia radial a la base: {radial_distance:.6f} m")
            print(f"  Error posición ||p_DH-p_URDF||₂: {result.position_error_m:.12e} m")
            print(f"  Error orientación: {result.rotation_error_rad:.12e} rad")

    results = run_suite(urdf_path, random_count=random_count, tolerance_m=tolerance_m)
    worst_position_error = max(result.position_error_m for result in results)
    worst_rotation_error = max(result.rotation_error_rad for result in results)
    passed_count = sum(result.passed for result in results)
    passed = passed_count == len(results)
    print(
        f"\nBatería completa: {len(results)} comparaciones "
        f"({len(VALIDATION_POSES)} justificadas + {random_count} aleatorias, x{len(FRAMES)} frames); "
        f"{passed_count} dentro de tolerancia."
    )
    print(f"Máximo error posicional: {worst_position_error:.12e} m")
    print(f"Máximo error de orientación: {worst_rotation_error:.12e} rad")
    print("RESULTADO: APROBADO" if passed else "RESULTADO: NO APROBADO")
    print(
        "Nota: la prueba B acerca el efector al eje de la base; la autocolisión "
        "se evalúa con los meshes de colisión en irb120_hito2 (collision.py)."
    )
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urdf", type=Path, default=None, help="Ruta al URDF expandido.")
    parser.add_argument(
        "--tolerance", type=float, default=DEFAULT_TOLERANCE_M, help="Tolerancia en metros."
    )
    parser.add_argument(
        "--random", type=int, default=100, help="Número de posturas aleatorias (semilla 342)."
    )
    arguments = parser.parse_args(argv)
    if arguments.tolerance <= 0.0:
        parser.error("--tolerance debe ser positiva")
    if arguments.random < 0:
        parser.error("--random no puede ser negativo")
    urdf_path = arguments.urdf or default_urdf_path()
    return 0 if verify(urdf_path, arguments.tolerance, arguments.random) else 1


if __name__ == "__main__":
    raise SystemExit(main())
