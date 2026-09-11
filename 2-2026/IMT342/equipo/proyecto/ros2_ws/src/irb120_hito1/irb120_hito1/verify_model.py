"""Verificación reproducible DH contra URDF para las dos poses del examen."""

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from irb120_hito1.kinematics.dh import (
    JOINT_NAMES,
    forward_kinematics,
    position_error_m,
    rotation_error_rad,
)
from irb120_hito1.kinematics.urdf_chain import chain_transform


@dataclass(frozen=True)
class ValidationPose:
    name: str
    joints_deg: tuple[float, ...]
    reason: str


VALIDATION_POSES = (
    ValidationPose(
        name="A - postura de trabajo",
        joints_deg=(30.0, -20.0, 15.0, 40.0, -35.0, 60.0),
        reason=(
            "Activa los seis ejes, evita la simetría de q=0 y representa una "
            "postura elevada de aproximación dentro del espacio de trabajo."
        ),
    ),
    ValidationPose(
        name="B - postura plegada crítica",
        joints_deg=(90.0, -60.0, 60.0, 90.0, 60.0, 180.0),
        reason=(
            "Activa los seis ejes y acerca tool0 al eje de la base; es útil para "
            "detectar signos/offsets y señalar una zona de posible colisión."
        ),
    ),
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


def verify(urdf_path: Path, tolerance_m: float) -> bool:
    worst_position_error = 0.0
    worst_rotation_error = 0.0
    print(f"URDF: {urdf_path}")
    print("Comparación: T_DH(q) contra T_URDF(q), ambas de base_link a tool0")
    print(f"Tolerancia posicional: {tolerance_m:.1e} m")

    for pose in VALIDATION_POSES:
        sample_rad = np.deg2rad(pose.joints_deg)
        joint_map = dict(zip(JOINT_NAMES, sample_rad, strict=True))
        analytic = forward_kinematics(sample_rad)
        urdf_transform = chain_transform(
            urdf_path,
            joint_map,
            base_link="base_link",
            target_link="tool0",
        )
        error_m = position_error_m(analytic, urdf_transform)
        error_rad = rotation_error_rad(analytic, urdf_transform)
        worst_position_error = max(worst_position_error, error_m)
        worst_rotation_error = max(worst_rotation_error, error_rad)

        radial_distance = float(np.hypot(analytic[0, 3], analytic[1, 3]))
        print(f"\nPrueba {pose.name}")
        print(f"q [deg]: {list(pose.joints_deg)}")
        print(f"Motivo: {pose.reason}")
        print(f"p_DH [m]: {np.array2string(analytic[:3, 3], precision=6)}")
        print(f"p_URDF [m]: {np.array2string(urdf_transform[:3, 3], precision=6)}")
        print(f"Distancia radial de tool0 a la base: {radial_distance:.6f} m")
        print(f"Error posición ||p_DH-p_URDF||₂: {error_m:.12e} m")
        print(f"Error orientación: {error_rad:.12e} rad")

    passed = worst_position_error < tolerance_m
    print(f"\nMáximo error posicional: {worst_position_error:.12e} m")
    print(f"Máximo error de orientación: {worst_rotation_error:.12e} rad")
    print("RESULTADO: APROBADO" if passed else "RESULTADO: NO APROBADO")
    print(
        "Nota: la prueba B identifica riesgo geométrico; la detección formal de "
        "colisiones requiere los meshes de colisión del CAD."
    )
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
