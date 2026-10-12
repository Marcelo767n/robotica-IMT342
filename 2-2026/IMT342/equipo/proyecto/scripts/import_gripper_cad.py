#!/usr/bin/env python3
"""Importa el CAD de la pinza (STL exportado del fabricante) al marco tool0 del URDF.

El STL de SMC se obtiene en https://www.smcworld.com/cad3d (serie MHZ2, modelo MHZ2-16D,
formato STL; requiere cuenta de SMC). El marco tool0 tiene +Z saliendo de la brida del robot,
asi que la cara de montaje de la pinza debe quedar en z = 0 y los dedos hacia +Z.

    v_tool0 = scale * R(rpy) v_cad + offset

Uso:
    python3 scripts/import_gripper_cad.py MHZ2-16D.stl --scale 0.001 \\
        [--rpy-deg R P Y] [--offset X Y Z] [--tcp-z 0.100]

Escribe meshes/visual/gripper_link.stl y meshes/collision/gripper_link.stl (la misma malla)
e imprime el cuadro delimitador resultante para comprobar la orientacion y el TCP.
"""

import argparse
import re
import struct
from math import radians
from pathlib import Path

import numpy as np

PACKAGE = Path(__file__).resolve().parents[1] / "ros2_ws" / "src" / "irb120_hito1"
DTYPE = np.dtype([("normal", "<3f4"), ("vertices", "<9f4"), ("attr", "<u2")])


def read_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:1000]:  # STL ASCII
        numbers = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)
        return np.array(numbers, dtype=float).reshape(-1, 3, 3)
    count = struct.unpack("<I", data[80:84])[0]
    return np.frombuffer(data[84 : 84 + 50 * count], dtype=DTYPE)["vertices"].reshape(-1, 3, 3).astype(float)


def rotation(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr, cp, sp, cy, sy = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
    return (
        np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
        @ np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
        @ np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    )


def write_stl(path: Path, triangles: np.ndarray) -> None:
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)
    records = np.zeros(len(triangles), dtype=DTYPE)
    records["normal"], records["vertices"] = normals, triangles.reshape(-1, 9)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = b"gripper CAD re-framed to tool0 for irb120_hito1".ljust(80, b"\0")
    path.write_bytes(header + struct.pack("<I", len(triangles)) + records.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stl", type=Path)
    parser.add_argument("--scale", type=float, default=0.001, help="unidades CAD -> m (mm: 0.001)")
    parser.add_argument("--rpy-deg", type=float, nargs=3, default=[0.0, 0.0, 0.0])
    parser.add_argument("--offset", type=float, nargs=3, default=[0.0, 0.0, 0.0], help="metros, marco tool0")
    arguments = parser.parse_args()

    triangles = read_stl(arguments.stl)
    matrix = rotation(*(radians(v) for v in arguments.rpy_deg))
    moved = arguments.scale * triangles @ matrix.T + np.asarray(arguments.offset)
    for kind in ("visual", "collision"):
        write_stl(PACKAGE / "meshes" / kind / "gripper_link.stl", moved)
    points = moved.reshape(-1, 3)
    print(f"{len(triangles)} triangulos | bbox min {points.min(0).round(4)} max {points.max(0).round(4)} m")
    print("Compruebe: cara de montaje en z=0, dedos hacia +Z; ajuste gripper_tcp_z en el xacro si hace falta.")


if __name__ == "__main__":
    main()
