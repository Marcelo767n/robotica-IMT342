#!/usr/bin/env python3
"""Genera el mesh parametrico de la pinza neumatica (visual y collision).

El STL ya esta expresado en el marco de su eslabon, por lo que el URDF no necesita
ningun `<origin>` en `<visual>` ni en `<collision>`: los unicos `origin` del modelo
son los de las articulaciones. El brazo usa el CAD real (scripts/import_cad.py).

Uso:  python3 scripts/generate_meshes.py
"""

from math import cos, pi, sin
from pathlib import Path
import struct

import numpy as np

OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "ros2_ws" / "src" / "irb120_hito1" / "meshes"
)
SEGMENTS = 32


def box(size, center=(0.0, 0.0, 0.0)):
    sx, sy, sz = (value / 2.0 for value in size)
    corners = np.array(
        [[x, y, z] for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    ) + np.asarray(center)
    # Indices: bit 2 -> x, bit 1 -> y, bit 0 -> z. Caras con normal hacia afuera.
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    triangles = []
    for a, b, c, d in quads:
        triangles += [(corners[a], corners[b], corners[c]), (corners[a], corners[c], corners[d])]
    return triangles


def cylinder(radius, length, center=(0.0, 0.0, 0.0), axis="z"):
    """Cilindro cerrado con eje `axis` (x, y o z) centrado en `center`."""
    half = length / 2.0
    ring = [(radius * cos(2 * pi * i / SEGMENTS), radius * sin(2 * pi * i / SEGMENTS))
            for i in range(SEGMENTS + 1)]
    triangles = []
    for (x0, y0), (x1, y1) in zip(ring[:-1], ring[1:]):
        bottom0, bottom1 = (x0, y0, -half), (x1, y1, -half)
        top0, top1 = (x0, y0, half), (x1, y1, half)
        triangles += [(bottom0, bottom1, top1), (bottom0, top1, top0)]
        triangles += [((0, 0, half), top0, top1), ((0, 0, -half), bottom1, bottom0)]
    order = {"z": (0, 1, 2), "x": (2, 0, 1), "y": (1, 2, 0)}[axis]
    return [
        tuple(np.asarray(vertex, dtype=float)[list(order)] + np.asarray(center) for vertex in tri)
        for tri in triangles
    ]


def write_stl(path, triangles):
    with open(path, "wb") as handle:
        handle.write(b"irb120_hito1 provisional mesh".ljust(80, b"\0"))
        handle.write(struct.pack("<I", len(triangles)))
        for a, b, c in triangles:
            a, b, c = (np.asarray(v, dtype=float) for v in (a, b, c))
            normal = np.cross(b - a, c - a)
            norm = np.linalg.norm(normal)
            normal = normal / norm if norm > 0.0 else normal
            handle.write(struct.pack("<12fH", *normal, *a, *b, *c, 0))


# El CAD real del brazo se importa con scripts/import_cad.py; aqui solo se genera la
# pinza neumatica (modelo parametrico, aun sin CAD del fabricante) en el marco tool0.
MESHES = {
    "gripper_link": (
        cylinder(0.030, 0.015, (0, 0, 0.0075))
        + box((0.060, 0.040, 0.050), (0, 0, 0.040))
        + box((0.020, 0.008, 0.050), (0, 0.014, 0.090))
        + box((0.020, 0.008, 0.050), (0, -0.014, 0.090))
    ),
}


def main():
    for kind in ("visual", "collision"):
        (OUTPUT_DIR / kind).mkdir(parents=True, exist_ok=True)
        for name, triangles in MESHES.items():
            write_stl(OUTPUT_DIR / kind / f"{name}.stl", triangles)
            print(f"{kind}/{name}.stl: {len(triangles)} triangulos")


if __name__ == "__main__":
    main()
