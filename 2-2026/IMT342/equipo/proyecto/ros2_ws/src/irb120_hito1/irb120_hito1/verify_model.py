"""Verificacion offline reproducible del pasaporte del Hito 1."""

import argparse
from pathlib import Path

import numpy as np

from irb120_hito1.kinematics.dh import (
    JOINT_NAMES,
    forward_kinematics,
    forward_kinematics_tcp,
    position_error_m,
    rotation_error_rad,
)
from irb120_hito1.kinematics.urdf_chain import chain_transform


SAMPLES_DEG = (
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (30.0, -20.0, 15.0, 40.0, -35.0, 60.0),
    (-90.0, 45.0, -60.0, -80.0, 50.0, -180.0),
    (160.0, -100.0, 65.0, 150.0, -110.0, 390.0),
)


def default_urdf_path() -> Path:
    try:
        from ament_index_python.packages import get_package_share_directory

        share = Path(get_package_share_directory("irb120_hito1"))
        candidate = share / "urdf" / "irb120_with_gripper.urdf"
        if candidate.exists():
            return candidate
    except (ImportError, LookupError):
        pass

    source_candidate = Path(__file__).resolve().parents[1] / "urdf" / "irb120_with_gripper.urdf"
    if source_candidate.exists():
        return source_candidate
    raise FileNotFoundError("No se encontro irb120_with_gripper.urdf.")


def verify(urdf_path: Path, tolerance_m: float) -> bool:
    worst_position_error = 0.0
    worst_rotation_error = 0.0
    print(f"URDF: {urdf_path}")
    print(f"Tolerancia del pasaporte: {tolerance_m:.1e} m")
    print("muestra  frame       error posicion [m]   error rotacion [rad]")

    for sample_index, sample_deg in enumerate(SAMPLES_DEG, start=1):
        sample_rad = np.deg2rad(sample_deg)
        joint_map = dict(zip(JOINT_NAMES, sample_rad, strict=True))
        for target, analytic in (
            ("tool0", forward_kinematics(sample_rad)),
            ("tcp_link", forward_kinematics_tcp(sample_rad)),
        ):
            urdf_transform = chain_transform(
                urdf_path,
                joint_map,
                base_link="base_link",
                target_link=target,
            )
            error_m = position_error_m(analytic, urdf_transform)
            error_rad = rotation_error_rad(analytic, urdf_transform)
            worst_position_error = max(worst_position_error, error_m)
            worst_rotation_error = max(worst_rotation_error, error_rad)
            print(f"{sample_index:>7}  {target:<10}  {error_m:>18.12e}   {error_rad:>18.12e}")

    passed = worst_position_error < tolerance_m
    print(f"Maximo error posicional: {worst_position_error:.12e} m")
    print(f"Maximo error de orientacion: {worst_rotation_error:.12e} rad")
    print("RESULTADO: APROBADO" if passed else "RESULTADO: NO APROBADO")
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urdf", type=Path, default=None, help="Ruta al URDF expandido.")
    parser.add_argument("--tolerance", type=float, default=1.0e-6, help="Tolerancia en metros.")
    arguments = parser.parse_args(argv)
    if arguments.tolerance <= 0.0:
        parser.error("--tolerance debe ser positiva")
    urdf_path = arguments.urdf or default_urdf_path()
    return 0 if verify(urdf_path, arguments.tolerance) else 1


if __name__ == "__main__":
    raise SystemExit(main())
