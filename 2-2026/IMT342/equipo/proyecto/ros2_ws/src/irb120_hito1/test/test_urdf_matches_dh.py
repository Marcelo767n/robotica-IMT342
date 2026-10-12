import unittest
from pathlib import Path
from xml.etree import ElementTree

import numpy as np

from irb120_hito1.kinematics.dh import (
    JOINT_NAMES,
    forward_kinematics,
    forward_kinematics_tcp,
    position_error_m,
    rotation_error_rad,
)
from irb120_hito1.kinematics.urdf_chain import chain_transform


URDF_PATH = Path(__file__).resolve().parents[1] / "urdf" / "irb120.urdf"


class TestUrdfMatchesDh(unittest.TestCase):
    def test_expanded_urdf_is_well_formed_and_has_unique_names(self) -> None:
        root = ElementTree.parse(URDF_PATH).getroot()
        link_names = [element.attrib["name"] for element in root.findall("link")]
        joints = root.findall("joint")
        joint_names = [element.attrib["name"] for element in joints]
        movable = [j.attrib["name"] for j in joints if j.attrib["type"] == "revolute"]
        fixed = [j.attrib["name"] for j in joints if j.attrib["type"] == "fixed"]
        self.assertEqual(len(link_names), len(set(link_names)))
        self.assertEqual(len(joint_names), len(set(joint_names)))
        self.assertEqual(movable, list(JOINT_NAMES))
        self.assertEqual(fixed, ["gripper_mount", "gripper_tcp_joint"])
        self.assertEqual(
            link_names,
            [
                "base_link", "link_1", "link_2", "link_3", "link_4", "link_5",
                "tool0", "gripper_link", "gripper_tcp",
            ],
        )
        self.assertEqual(len(movable), 6)
        self.assertEqual(root.findall(".//inertial"), [])

    def test_one_origin_per_degree_of_freedom(self) -> None:
        root = ElementTree.parse(URDF_PATH).getroot()
        for joint in root.findall("joint"):
            origins = joint.findall("origin")
            if joint.attrib["type"] == "revolute":
                self.assertEqual(len(origins), 1, joint.attrib["name"])
        # Los visuales no llevan origin: los meshes ya estan en el marco del eslabon.
        self.assertEqual(root.findall("link/visual/origin"), [])
        self.assertEqual(root.findall("link/collision/origin"), [])
        self.assertEqual(len(root.findall(".//origin")), 7)  # 6 juntas + offset del TCP

    def test_visual_and_collision_meshes_exist(self) -> None:
        root = ElementTree.parse(URDF_PATH).getroot()
        for kind in ("visual", "collision"):
            meshes = root.findall(f"link/{kind}/geometry/mesh")
            self.assertEqual(len(meshes), 8, kind)
            for mesh in meshes:
                filename = mesh.attrib["filename"]
                self.assertTrue(filename.startswith(f"package://irb120_hito1/meshes/{kind}/"))
                path = URDF_PATH.parents[1] / filename.split("irb120_hito1/", 1)[1]
                self.assertTrue(path.is_file(), path)
                self.assertGreater(path.stat().st_size, 80, path)

    def test_cad_meshes_fit_the_kinematic_skeleton(self) -> None:
        """El origen de la siguiente junta debe quedar dentro del cuadro del mesh CAD."""
        import struct

        def vertices(name: str) -> np.ndarray:
            data = (URDF_PATH.parents[1] / "meshes" / "visual" / f"{name}.stl").read_bytes()
            count = struct.unpack("<I", data[80:84])[0]
            record = np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")])
            return np.frombuffer(data[84 : 84 + 50 * count], dtype=record)["v"].reshape(-1, 3)

        # eslabon -> origen de la siguiente junta expresado en el marco del eslabon
        # (joint_5 sale a d4 = 0.302 m sobre el eje del antebrazo).
        for link, point in (
            ("link_1", (0.0, 0.0, 0.290)),
            ("link_2", (0.270, 0.0, 0.0)),
            ("link_4", (0.0, 0.0, 0.302)),
        ):
            points = vertices(link)
            low, high = points.min(axis=0) - 0.01, points.max(axis=0) + 0.01
            self.assertTrue(np.all(np.array(point) >= low) and np.all(np.array(point) <= high), link)

    def test_urdf_position_matches_dh_below_milestone_tolerance(self) -> None:
        generator = np.random.default_rng(seed=342)
        lower_deg = np.array([-165.0, -110.0, -110.0, -160.0, -120.0, -400.0])
        upper_deg = np.array([165.0, 110.0, 70.0, 160.0, 120.0, 400.0])
        worst_error_m = 0.0
        worst_rotation_error_rad = 0.0

        for joints_deg in generator.uniform(lower_deg, upper_deg, size=(100, 6)):
            joints_rad = np.deg2rad(joints_deg)
            joint_map = dict(zip(JOINT_NAMES, joints_rad, strict=True))
            urdf_transform = chain_transform(URDF_PATH, joint_map)
            analytic_transform = forward_kinematics(joints_rad)
            worst_error_m = max(
                worst_error_m,
                position_error_m(analytic_transform, urdf_transform),
            )
            worst_rotation_error_rad = max(
                worst_rotation_error_rad,
                rotation_error_rad(analytic_transform, urdf_transform),
            )

        self.assertLess(worst_error_m, 1.0e-6)
        self.assertLess(worst_rotation_error_rad, 1.0e-9)

    def test_package_does_not_depend_on_moveit(self) -> None:
        package_xml = (URDF_PATH.parents[1] / "package.xml").read_text(encoding="utf-8")
        self.assertNotIn("moveit", package_xml.lower())


if __name__ == "__main__":
    unittest.main()
