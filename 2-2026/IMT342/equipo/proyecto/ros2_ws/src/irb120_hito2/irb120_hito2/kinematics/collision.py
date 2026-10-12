"""Deteccion de autocolision y de contacto con la mesa usando los meshes `collision` del CAD.

Cada STL de `irb120_hito1/meshes/collision` esta en el marco de su eslabon. Se muestrea su
superficie (vertices + puntos baricentricos de cada triangulo) y, para una postura q, se
llevan las nubes de puntos a base_link con la cadena URDF. Dos eslabones colisionan si la
distancia minima entre sus nubes es menor que `margin_m`. Se ignoran pares vecinos en la
cadena (comparten junta y siempre se tocan) y se agrega el plano de la mesa z = floor_z.

Es una prueba conservadora de proximidad superficial, no una prueba de interpenetracion
exacta: basta para descartar posturas que doblan el brazo contra la base o la mesa.
"""

import struct
from itertools import combinations
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from irb120_hito1.kinematics.urdf_chain import load_joints

LINK_ORDER = ("base_link", "link_1", "link_2", "link_3", "link_4", "link_5", "tool0", "gripper_link")
_RECORD = np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")])


def default_package_dir() -> Path:
    try:
        from ament_index_python.packages import get_package_share_directory

        share = Path(get_package_share_directory("irb120_hito1"))
        if (share / "meshes").is_dir():
            return share
    except (ImportError, LookupError):
        pass
    return Path(__file__).resolve().parents[3] / "irb120_hito1"


def _surface_points(path: Path, samples_per_triangle: int = 3) -> NDArray[np.float64]:
    data = path.read_bytes()
    count = struct.unpack("<I", data[80:84])[0]
    triangles = (
        np.frombuffer(data[84 : 84 + 50 * count], dtype=_RECORD)["v"].reshape(-1, 3, 3).astype(float)
    )
    generator = np.random.default_rng(0)  # muestreo reproducible
    weights = generator.dirichlet(np.ones(3), size=(len(triangles), samples_per_triangle))
    interior = np.einsum("tsk,tkd->tsd", weights, triangles).reshape(-1, 3)
    return np.vstack([triangles.reshape(-1, 3), interior])


class CollisionChecker:
    def __init__(self, package_dir: Path | None = None, floor_z: float = 0.0) -> None:
        root = Path(package_dir) if package_dir else default_package_dir()
        self._joints = load_joints(root / "urdf" / "irb120.urdf")
        self._points = {
            name: _surface_points(root / "meshes" / "collision" / f"{name}.stl")
            for name in LINK_ORDER
        }
        self._floor_z = floor_z
        # Se omiten pares vecinos (padre/hijo) y link_5-pinza, separados solo por la brida.
        self._pairs = [
            (a, b)
            for (i, a), (j, b) in combinations(enumerate(LINK_ORDER), 2)
            if j - i >= 2 and (a, b) != ("link_5", "gripper_link")
        ]

    def _link_clouds(self, q: np.ndarray) -> dict[str, NDArray[np.float64]]:
        from irb120_hito1.kinematics.dh import JOINT_NAMES
        from irb120_hito1.kinematics.urdf_chain import _joint_transform

        positions = dict(zip(JOINT_NAMES, np.asarray(q, dtype=float), strict=True))
        transforms = {"base_link": np.eye(4)}
        for name in LINK_ORDER[1:]:
            joint = self._joints[name]
            transforms[name] = transforms[joint.parent] @ _joint_transform(
                joint, positions.get(joint.name, 0.0)
            )
        return {
            name: self._points[name] @ transforms[name][:3, :3].T + transforms[name][:3, 3]
            for name in LINK_ORDER
        }

    def min_distances(self, q: np.ndarray) -> dict[tuple[str, str], float]:
        """Distancia minima entre cada par no vecino; ('mesa', link) para el plano."""
        clouds = self._link_clouds(q)
        result: dict[tuple[str, str], float] = {}
        for a, b in self._pairs:
            pa, pb = clouds[a], clouds[b]
            squared = (
                np.sum(pa * pa, axis=1)[:, None] + np.sum(pb * pb, axis=1)[None, :] - 2.0 * pa @ pb.T
            )
            result[(a, b)] = float(np.sqrt(max(float(squared.min()), 0.0)))
        for name in LINK_ORDER[1:]:
            result[("mesa", name)] = float(clouds[name][:, 2].min() - self._floor_z)
        return result

    def colliding_pairs(self, q: np.ndarray, margin_m: float = 0.005) -> list[tuple[str, str]]:
        return [pair for pair, distance in self.min_distances(q).items() if distance < margin_m]

    def in_collision(self, q: np.ndarray, margin_m: float = 0.005) -> bool:
        return bool(self.colliding_pairs(q, margin_m))
