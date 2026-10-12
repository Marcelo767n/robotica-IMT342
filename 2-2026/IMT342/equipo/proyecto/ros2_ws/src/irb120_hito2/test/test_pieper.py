import unittest

import numpy as np

from irb120_hito1.kinematics.dh import (
    forward_kinematics,
    forward_kinematics_tcp,
    position_error_m,
    rotation_error_rad,
)
from irb120_hito2.kinematics.pieper import LIMITS_RAD, inverse_kinematics, inverse_kinematics_tcp


class TestPieper(unittest.TestCase):
    def test_recovers_original_joints_and_every_solution_reaches_the_pose(self) -> None:
        generator = np.random.default_rng(seed=2)
        for _ in range(200):
            q = generator.uniform(LIMITS_RAD[:, 0], LIMITS_RAD[:, 1])
            target = forward_kinematics(q)
            solutions = inverse_kinematics(target, q)
            self.assertTrue(solutions)
            np.testing.assert_allclose(solutions[0].q, q, atol=1e-6)
            for solution in solutions:
                reached = forward_kinematics(solution.q)
                self.assertLess(position_error_m(target, reached), 1e-9)
                self.assertLess(rotation_error_rad(target, reached), 1e-7)
                self.assertTrue(np.all(np.array(solution.q) >= LIMITS_RAD[:, 0] - 1e-9))
                self.assertTrue(np.all(np.array(solution.q) <= LIMITS_RAD[:, 1] + 1e-9))

    def test_generic_pose_has_up_to_eight_distinct_solutions(self) -> None:
        q = np.deg2rad([20.0, 10.0, -30.0, 15.0, 50.0, 30.0])
        solutions = inverse_kinematics(forward_kinematics(q), q)
        self.assertGreaterEqual(len(solutions), 2)
        self.assertLessEqual(len(solutions), 8)
        self.assertEqual(len({(s.arm, s.elbow, s.wrist) for s in solutions}), len(solutions))

    def test_tcp_target_accounts_for_gripper_offset(self) -> None:
        q = np.deg2rad([30.0, -20.0, 15.0, 40.0, -35.0, 60.0])
        target = forward_kinematics_tcp(q)
        solutions = inverse_kinematics_tcp(target, q)
        np.testing.assert_allclose(solutions[0].q, q, atol=1e-6)

    def test_unreachable_pose_returns_no_solution(self) -> None:
        target = np.eye(4)
        target[:3, 3] = [2.0, 0.0, 0.5]
        self.assertEqual(inverse_kinematics(target), [])

    def test_wrist_singularity_q5_zero_is_solved(self) -> None:
        q = np.deg2rad([10.0, 20.0, -10.0, 30.0, 0.0, 40.0])
        solutions = inverse_kinematics(forward_kinematics(q), q)
        self.assertTrue(solutions)
        self.assertTrue(solutions[0].singular_wrist)
        self.assertLess(position_error_m(forward_kinematics(q), forward_kinematics(solutions[0].q)), 1e-9)

    def test_invalid_input_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            inverse_kinematics(np.eye(3))
        with self.assertRaises(ValueError):
            inverse_kinematics(np.full((4, 4), np.nan))


if __name__ == "__main__":
    unittest.main()
