import unittest

import numpy as np

from irb120.dh import forward_kinematics_tcp
from irb120.validation import POSITION_TOL_M, fk_check, round_trip_test


class TestFKValidation(unittest.TestCase):
    def test_exact_joints_give_zero_error(self) -> None:
        q = np.deg2rad([30.0, -20.0, 15.0, 40.0, -35.0, 60.0])
        check = fk_check(forward_kinematics_tcp(q), q)
        self.assertTrue(check.accepted)
        self.assertLess(check.frobenius_error, 1e-12)

    def test_small_joint_error_is_rejected(self) -> None:
        q = np.deg2rad([30.0, -20.0, 15.0, 40.0, -35.0, 60.0])
        check = fk_check(forward_kinematics_tcp(q), q + np.array([1e-3, 0, 0, 0, 0, 0]))
        self.assertFalse(check.accepted)
        self.assertGreater(check.position_error_m, POSITION_TOL_M)

    def test_orientation_only_error_is_detected(self) -> None:
        q = np.deg2rad([30.0, -20.0, 15.0, 40.0, -35.0, 60.0])
        target = forward_kinematics_tcp(q)
        rotated = q.copy()
        rotated[5] += 0.01  # q6 gira sobre el eje del TCP: la posicion no cambia
        check = fk_check(target, rotated)
        self.assertLess(check.position_error_m, 1e-12)
        self.assertAlmostEqual(check.rotation_error_rad, 0.01, places=9)
        self.assertFalse(check.accepted)

    def test_round_trip_recovers_every_random_configuration(self) -> None:
        stats = round_trip_test(samples=300, seed=3)
        self.assertEqual(stats.solved, stats.samples)
        self.assertEqual(stats.recovered_original, stats.samples)
        self.assertLess(stats.max_position_error_m, 1e-9)
        self.assertLess(stats.max_rotation_error_rad, 1e-7)


if __name__ == "__main__":
    unittest.main()
