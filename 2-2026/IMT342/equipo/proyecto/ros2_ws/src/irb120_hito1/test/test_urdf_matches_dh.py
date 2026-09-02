import unittest
from pathlib import Path
from xml.etree import ElementTree

import numpy as np

from irb120_hito1.kinematics.dh import JOINT_NAMES, forward_kinematics, position_error_m
from irb120_hito1.kinematics.urdf_chain import chain_transform


URDF_PATH = Path(__file__).resolve().parents[1] / "urdf" / "irb120_with_gripper.urdf"


class TestUrdfMatchesDh(unittest.TestCase):
    def test_expanded_urdf_is_well_formed_and_has_unique_names(self) -> None:
        root = ElementTree.parse(URDF_PATH).getroot()
        link_names = [element.attrib["name"] for element in root.findall("link")]
        joint_names = [element.attrib["name"] for element in root.findall("joint")]
        self.assertEqual(len(link_names), len(set(link_names)))
        self.assertEqual(len(joint_names), len(set(joint_names)))
        self.assertTrue(set(JOINT_NAMES).issubset(joint_names))
        self.assertIn("tool0", link_names)
        self.assertIn("tcp_link", link_names)

    def test_urdf_position_matches_dh_below_milestone_tolerance(self) -> None:
        generator = np.random.default_rng(seed=342)
        lower_deg = np.array([-165.0, -110.0, -110.0, -160.0, -120.0, -400.0])
        upper_deg = np.array([165.0, 110.0, 70.0, 160.0, 120.0, 400.0])
        worst_error_m = 0.0

        for joints_deg in generator.uniform(lower_deg, upper_deg, size=(100, 6)):
            joints_rad = np.deg2rad(joints_deg)
            joint_map = dict(zip(JOINT_NAMES, joints_rad, strict=True))
            urdf_transform = chain_transform(URDF_PATH, joint_map)
            analytic_transform = forward_kinematics(joints_rad)
            worst_error_m = max(
                worst_error_m,
                position_error_m(analytic_transform, urdf_transform),
            )

        self.assertLess(worst_error_m, 1.0e-6)

    def test_package_does_not_depend_on_moveit(self) -> None:
        package_xml = (URDF_PATH.parents[1] / "package.xml").read_text(encoding="utf-8")
        self.assertNotIn("moveit", package_xml.lower())


if __name__ == "__main__":
    unittest.main()
