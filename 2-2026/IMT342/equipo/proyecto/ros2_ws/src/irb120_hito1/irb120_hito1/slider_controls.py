"""Datos y conversiones independientes de la interfaz grafica."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SliderSpec:
    """Descripcion de un control articular expresado en grados."""

    name: str
    label: str
    lower_deg: float
    upper_deg: float


JOINT_SLIDERS = (
    SliderSpec("joint_1", "J1 - Base", -165.0, 165.0),
    SliderSpec("joint_2", "J2 - Hombro", -110.0, 110.0),
    SliderSpec("joint_3", "J3 - Codo", -110.0, 70.0),
    SliderSpec("joint_4", "J4 - Giro de muneca", -160.0, 160.0),
    SliderSpec("joint_5", "J5 - Inclinacion de muneca", -120.0, 120.0),
    SliderSpec("joint_6", "J6 - Flange", -400.0, 400.0),
)

PRESETS_DEG = {
    "Cero": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    "Prueba A": (30.0, -20.0, 15.0, 40.0, -35.0, 60.0),
    "Prueba B": (90.0, -60.0, 60.0, 90.0, 60.0, 180.0),
}


def command_payload(joints_deg: list[float]) -> list[float]:
    """Construye un mensaje limitado a las seis juntas del ABB."""

    if len(joints_deg) != len(JOINT_SLIDERS):
        raise ValueError("Se requieren exactamente seis valores articulares.")
    clamped_joints = [
        min(max(float(value), spec.lower_deg), spec.upper_deg)
        for value, spec in zip(joints_deg, JOINT_SLIDERS, strict=True)
    ]
    return clamped_joints
