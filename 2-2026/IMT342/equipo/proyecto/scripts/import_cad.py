#!/usr/bin/env python3
"""Importa el CAD real del IRB 120 (ROS-Industrial) a los marcos del URDF del proyecto.

Fuente: https://github.com/ros-industrial/abb  (abb_irb120_support/meshes/irb120_3_58,
rama noetic-devel, licencia Apache-2.0). Los STL de ROS-Industrial estan en el marco
local de cada eslabon con la postura q = 0 alineada a los ejes del mundo; los marcos de
este URDF (derivados de DH) tienen otra orientacion y origen. Para cada eslabon se aplica

    v_proyecto = R0^T (v_ros + o_ros - t0)

donde (R0, t0) es la pose de nuestro eslabon en q = 0 (calculada con la cadena URDF) y
o_ros el origen del eslabon ROS-I en q = 0.

Uso:  python3 scripts/import_cad.py DIRECTORIO_CON_visual_Y_collision
"""

import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ros2_ws" / "src" / "irb120_hito1"
sys.path.insert(0, str(PACKAGE))

from irb120_hito1.kinematics.urdf_chain import chain_transform  # noqa: E402

# nuestro eslabon -> (STL ROS-I, origen del eslabon ROS-I en q = 0, en base_link)
LINKS = {
    "base_link": ("base_link", (0.0, 0.0, 0.0)),
    "link_1": ("link_1", (0.0, 0.0, 0.0)),
    "link_2": ("link_2", (0.0, 0.0, 0.290)),
    "link_3": ("link_3", (0.0, 0.0, 0.560)),
    "link_4": ("link_4", (0.0, 0.0, 0.630)),
    "link_5": ("link_5", (0.302, 0.0, 0.630)),
    "tool0": ("link_6", (0.374, 0.0, 0.630)),
}
DTYPE = np.dtype([("normal", "<3f4"), ("vertices", "<9f4"), ("attr", "<u2")])


def read_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    count = struct.unpack("<I", data[80:84])[0]
    records = np.frombuffer(data[84 : 84 + count * 50], dtype=DTYPE)
    return records["vertices"].reshape(-1, 3, 3).astype(float)


def write_stl(path: Path, triangles: np.ndarray, header: str) -> None:
    edge_a = triangles[:, 1] - triangles[:, 0]
    edge_b = triangles[:, 2] - triangles[:, 0]
    normals = np.cross(edge_a, edge_b)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)
    records = np.zeros(len(triangles), dtype=DTYPE)
    records["normal"] = normals
    records["vertices"] = triangles.reshape(-1, 9)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header.encode().ljust(80, b"\0") + struct.pack("<I", len(triangles)) + records.tobytes())


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    source = Path(sys.argv[1])
    urdf = PACKAGE / "urdf" / "irb120.urdf"
    header = "ABB IRB120 CAD (c) ROS-Industrial, Apache-2.0, re-framed for irb120_hito1"
    for ours, (theirs, origin) in LINKS.items():
        pose = chain_transform(urdf, {}, target_link=ours)  # q = 0
        rotation, translation = pose[:3, :3], pose[:3, 3]
        for kind in ("visual", "collision"):
            triangles = read_stl(source / kind / f"{theirs}.stl")
            moved = (triangles + np.asarray(origin) - translation) @ rotation  # R^T v
            write_stl(PACKAGE / "meshes" / kind / f"{ours}.stl", moved, header)
            low, high = moved.reshape(-1, 3).min(0), moved.reshape(-1, 3).max(0)
            print(f"{kind:9s} {ours:9s} <- {theirs:9s} bbox {low.round(3)} .. {high.round(3)}")


if __name__ == "__main__":
    main()
