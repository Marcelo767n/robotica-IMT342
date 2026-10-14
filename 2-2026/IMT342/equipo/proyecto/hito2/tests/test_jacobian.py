import unittest

import numpy as np

from irb120.dh import forward_kinematics_tcp
from irb120.jacobian import (
    geometric_jacobian,
    numerical_jacobian,
    rank_analysis,
    tcp_twist,
    weakest_directions,
)
from irb120.pieper import DELTA

Q = np.deg2rad([30.0, -20.0, 15.0, 40.0, -35.0, 60.0])


class TestJacobian(unittest.TestCase):
    def test_matches_finite_differences_of_fk(self) -> None:
        generator = np.random.default_rng(seed=11)
        for _ in range(30):
            q = generator.uniform(-2.0, 2.0, 6)
            np.testing.assert_allclose(geometric_jacobian(q), numerical_jacobian(q), atol=1e-8)

    def test_twist_predicts_tcp_displacement(self) -> None:
        q_dot = np.array([0.3, -0.2, 0.1, 0.5, -0.4, 0.2])
        dt = 1e-6
        moved = forward_kinematics_tcp(Q + q_dot * dt)[:3, 3] - forward_kinematics_tcp(Q)[:3, 3]
        np.testing.assert_allclose(moved / dt, tcp_twist(Q, q_dot)[:3], atol=1e-5)

    def test_hand_column_at_zero_pose(self) -> None:
        # q = 0: eje 1 = z0 = (0,0,1), TCP en (0.374 + 0.150, 0, 0.630): J1 = z0 x p = (0, 0.524, 0)
        column = geometric_jacobian(np.zeros(6))[:, 0]
        np.testing.assert_allclose(column, [0.0, 0.524, 0.0, 0.0, 0.0, 1.0], atol=1e-12)

    def test_regular_configuration_has_full_rank(self) -> None:
        analysis = rank_analysis(geometric_jacobian(Q))
        self.assertEqual(analysis.rank, 6)
        self.assertFalse(analysis.is_singular)

    def test_wrist_singularity_loses_one_rank_with_q4_minus_q6_null_motion(self) -> None:
        q = Q.copy()
        q[4] = 0.0
        analysis = rank_analysis(geometric_jacobian(q))
        self.assertEqual(analysis.rank, 5)
        null = analysis.null_joint_motions[:, 0]
        self.assertLess(np.abs(null[:3]).max(), 1e-9)  # el brazo no participa
        self.assertAlmostEqual(abs(null[3]), abs(null[5]), places=9)
        self.assertAlmostEqual(null[3], -null[5], places=9)  # q4_dot = -q6_dot

    def test_elbow_singularity_when_arm_is_stretched(self) -> None:
        q = Q.copy()
        q[2] = DELTA - np.pi / 2.0
        self.assertEqual(rank_analysis(geometric_jacobian(q)).rank, 5)

    def test_velocity_amplification_is_inverse_of_sigma_min(self) -> None:
        q = Q.copy()
        q[4] = 1e-3
        sigma, u_min, _ = weakest_directions(geometric_jacobian(q))
        q_dot = np.linalg.solve(geometric_jacobian(q), u_min)
        self.assertAlmostEqual(np.linalg.norm(q_dot), 1.0 / sigma, delta=1e-6 / sigma)


if __name__ == "__main__":
    unittest.main()
