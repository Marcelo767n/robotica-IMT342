import unittest

import numpy as np

from irb120_hito1.kinematics.dh import forward_kinematics, forward_kinematics_tcp


class TestDirectKinematics(unittest.TestCase):
    def test_zero_pose_matches_paper_geometry(self) -> None:
        transform = forward_kinematics([0.0] * 6)
        np.testing.assert_allclose(transform[:3, 3], [0.374, 0.0, 0.630], atol=1.0e-15)

    def test_tcp_is_160_mm_along_tool_z(self) -> None:
        tool = forward_kinematics([0.0] * 6)
        tcp = forward_kinematics_tcp([0.0] * 6)
        expected_tcp = tool[:3, 3] + 0.160 * tool[:3, 2]
        np.testing.assert_allclose(tcp[:3, 3], expected_tcp, atol=1.0e-15)

    def test_rotation_is_orthonormal(self) -> None:
        transform = forward_kinematics(np.deg2rad([23.0, -41.0, 11.0, 87.0, -33.0, 205.0]))
        rotation = transform[:3, :3]
        np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1.0e-14)
        self.assertAlmostEqual(float(np.linalg.det(rotation)), 1.0, places=14)

    def test_rejects_wrong_joint_count(self) -> None:
        with self.assertRaises(ValueError):
            forward_kinematics([0.0] * 5)


if __name__ == "__main__":
    unittest.main()
