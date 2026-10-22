import unittest
from math import pi
from pathlib import Path

import numpy as np

from irb120_hito1.kinematics.dh import forward_kinematics, forward_kinematics_tcp
from irb120_hito1.slider_controls import JOINT_SLIDERS
from irb120_hito1.validation import (
    DEFAULT_TOLERANCE_M,
    FRAMES,
    VALIDATION_POSES,
    analytic_transform,
    random_poses,
    rpy_deg,
    run_suite,
)
from irb120_hito1.verify_model import main as verify_main


URDF_PATH = Path(__file__).resolve().parents[1] / "urdf" / "irb120.urdf"


class TestValidationSuite(unittest.TestCase):
    def test_suite_passes_for_justified_and_random_poses(self) -> None:
        results = run_suite(URDF_PATH, random_count=50)
        self.assertEqual(len(results), (len(VALIDATION_POSES) + 50) * len(FRAMES))
        self.assertTrue(all(result.passed for result in results))
        self.assertLess(max(r.position_error_m for r in results), DEFAULT_TOLERANCE_M)
        self.assertLess(max(r.rotation_error_rad for r in results), 1.0e-9)

    def test_random_poses_are_reproducible_and_within_limits(self) -> None:
        first = random_poses(20, seed=7)
        self.assertEqual(first, random_poses(20, seed=7))
        self.assertNotEqual(first, random_poses(20, seed=8))
        for pose in first:
            for value, spec in zip(pose.joints_deg, JOINT_SLIDERS, strict=True):
                self.assertGreaterEqual(value, spec.lower_deg)
                self.assertLessEqual(value, spec.upper_deg)

    def test_analytic_transform_selects_frame(self) -> None:
        q_deg = VALIDATION_POSES[1].joints_deg
        q_rad = np.deg2rad(q_deg)
        np.testing.assert_allclose(analytic_transform(q_deg, "tool0"), forward_kinematics(q_rad))
        np.testing.assert_allclose(
            analytic_transform(q_deg, "gripper_tcp"), forward_kinematics_tcp(q_rad)
        )
        with self.assertRaises(ValueError):
            analytic_transform(q_deg, "link_3")

    def test_rpy_matches_urdf_convention(self) -> None:
        roll, pitch, yaw = 0.3, -0.4, 1.1
        cr, sr = np.cos(roll), np.sin(roll)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)
        transform = np.eye(4)
        transform[:3, :3] = (
            np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
            @ np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
            @ np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
        )
        np.testing.assert_allclose(rpy_deg(transform), np.rad2deg([roll, pitch, yaw]))

    def test_zero_pose_tool0_points_along_base_x(self) -> None:
        # En la pose de calibracion el eje Z de tool0 apunta a +X de la base: pitch = 90 deg.
        transform = analytic_transform((0.0,) * 6, "tool0")
        np.testing.assert_allclose(transform[:3, 3], [0.374, 0.0, 0.630], atol=1e-12)
        self.assertAlmostEqual(rpy_deg(transform)[1], 90.0, places=9)

    def test_verify_model_cli_returns_success(self) -> None:
        self.assertEqual(verify_main(["--urdf", str(URDF_PATH), "--random", "10"]), 0)
        self.assertEqual(
            verify_main(["--urdf", str(URDF_PATH), "--random", "0", "--tolerance", "1e-30"]), 1
        )


if __name__ == "__main__":
    unittest.main()
