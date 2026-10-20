import unittest

import numpy as np

from irb120.dh import (
    forward_kinematics,
    forward_kinematics_tcp,
    position_error_m,
    rotation_error_rad,
)
from irb120.pieper import (
    LIMITS_RAD,
    REACH_MAX_M,
    analyze_pose,
    enumerate_candidates,
    inverse_kinematics,
    inverse_kinematics_tcp,
    rank_candidates,
    select_solution,
)
from irb120.transforms import pose_matrix, rpy_to_matrix


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


class TestEightBranches(unittest.TestCase):
    def test_always_eight_candidates_in_fixed_order(self) -> None:
        q = np.deg2rad([20.0, 10.0, -30.0, 15.0, 50.0, 30.0])
        candidates = enumerate_candidates(forward_kinematics(q), q)
        self.assertEqual(len(candidates), 8)
        self.assertEqual([c.branch for c in candidates], list(range(1, 9)))
        self.assertEqual(len({(c.arm, c.elbow, c.wrist) for c in candidates}), 8)

    def test_every_real_branch_reproduces_the_pose_even_outside_limits(self) -> None:
        generator = np.random.default_rng(seed=7)
        for _ in range(100):
            q = generator.uniform(LIMITS_RAD[:, 0], LIMITS_RAD[:, 1])
            report = analyze_pose(forward_kinematics_tcp(q), q)
            for candidate, check in zip(report.candidates, report.checks):
                if candidate.real:
                    self.assertTrue(check.accepted, msg=f"rama {candidate.branch}")
            self.assertTrue(report.reachable)

    def test_unreachable_pose_has_no_real_branch(self) -> None:
        target = pose_matrix((1.0, 0.0, 0.5), np.eye(3))
        report = analyze_pose(target)
        self.assertFalse(report.geometrically_reachable)
        self.assertGreater(report.shoulder_to_wrist_m, REACH_MAX_M)
        self.assertIn("fuera de", report.verdict)
        self.assertEqual(report.admissible, [])

    def test_pose_that_exists_only_outside_joint_limits(self) -> None:
        q = np.deg2rad([-106.8, -85.6, 90.1, -79.1, -5.3, 173.1])  # q3 = 90.1 > 70 deg
        report = analyze_pose(forward_kinematics_tcp(q))
        self.assertTrue(report.geometrically_reachable)
        self.assertFalse(report.reachable)
        self.assertIn("limites", report.verdict)

    def test_pose_from_xyz_rpy_is_reachable(self) -> None:
        target = pose_matrix((0.40, 0.10, 0.35), rpy_to_matrix(0.0, np.pi, 0.0))
        report = analyze_pose(target)
        self.assertTrue(report.reachable)
        for candidate in report.admissible:
            reached = forward_kinematics_tcp(candidate.q)
            self.assertLess(position_error_m(target, reached), 1e-9)

    def test_home_pose_is_calibration_position_and_is_recovered(self) -> None:
        from irb120.dh import HOME_Q
        target = forward_kinematics_tcp(HOME_Q)
        np.testing.assert_allclose(target[:3, 3], [0.374 + 0.150, 0.0, 0.630], atol=1e-12)
        report = analyze_pose(target, HOME_Q)
        self.assertTrue(report.reachable)
        chosen = select_solution(report, HOME_Q)
        np.testing.assert_allclose(chosen.q, HOME_Q, atol=1e-12)
        self.assertTrue(chosen.singular_wrist)  # q5 = 0: el home es singularidad de muneca

    def test_selection_prefers_closest_admissible_branch(self) -> None:
        q = np.deg2rad([30.0, -20.0, 15.0, 40.0, -35.0, 60.0])
        report = analyze_pose(forward_kinematics_tcp(q), q)
        chosen = select_solution(report, q)
        np.testing.assert_allclose(chosen.q, q, atol=1e-9)


class TestInputAndSelection(unittest.TestCase):
    def test_rejects_matrices_that_are_not_rigid_poses(self) -> None:
        good = forward_kinematics_tcp(np.zeros(6))
        scaled = good.copy(); scaled[:3, :2] *= 2.0            # det(R) = 4
        bad_row = good.copy(); bad_row[3, 3] = 2.0              # ultima fila invalida
        mirror = good.copy(); mirror[:3, 0] *= -1.0             # det(R) = -1 (reflexion)
        for matrix in (scaled, bad_row, mirror):
            with self.assertRaises(ValueError):
                analyze_pose(matrix)

    def test_wrist_labels_match_the_sign_of_q5(self) -> None:
        generator = np.random.default_rng(seed=9)
        for _ in range(50):
            q = generator.uniform(LIMITS_RAD[:, 0], LIMITS_RAD[:, 1])
            for c in analyze_pose(forward_kinematics_tcp(q), q).candidates:
                if c.real and not c.singular_wrist:
                    self.assertEqual(c.wrist == "q5+", c.q_raw[4] > 0, msg=f"rama {c.branch}")

    def test_ranking_covers_eight_branches_and_picks_one(self) -> None:
        q = np.deg2rad([30.0, -20.0, 15.0, 40.0, -35.0, 60.0])
        report = analyze_pose(forward_kinematics_tcp(q), q)
        decisions = rank_candidates(report, q)
        self.assertEqual(len(decisions), 8)
        chosen = [d for d in decisions if d.rank == 1]
        self.assertEqual(len(chosen), 1)
        self.assertTrue(chosen[0].status.startswith("ELEGIDA"))
        np.testing.assert_allclose(chosen[0].candidate.q, q, atol=1e-9)
        for d in decisions:
            if not d.admissible:
                self.assertIsNone(d.rank)
                self.assertTrue(d.status.startswith("descartada"))


if __name__ == "__main__":
    unittest.main()
