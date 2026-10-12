import unittest

import numpy as np

from irb120_hito2.trajectory.lspb import plan_lspb


class TestLspb(unittest.TestCase):
    def setUp(self) -> None:
        self.q0 = np.zeros(6)
        self.qf = np.deg2rad([60.0, -40.0, 20.0, 90.0, 30.0, -120.0])
        self.vmax = np.deg2rad(np.full(6, 100.0))
        self.amax = np.full(6, 3.0)
        self.trajectory = plan_lspb(self.q0, self.qf, self.vmax, self.amax)

    def test_endpoints_and_rest_boundary_conditions(self) -> None:
        start = self.trajectory.sample(0.0)
        end = self.trajectory.sample(self.trajectory.tf)
        np.testing.assert_allclose(start[0], self.q0, atol=1e-12)
        np.testing.assert_allclose(end[0], self.qf, atol=1e-12)
        np.testing.assert_allclose(start[1], 0.0, atol=1e-12)
        np.testing.assert_allclose(end[1], 0.0, atol=1e-12)

    def test_limits_are_respected_and_one_joint_saturates(self) -> None:
        velocity = np.abs(self.trajectory.cruise_velocity)
        acceleration = np.abs(self.trajectory.blend_acceleration)
        self.assertTrue(np.all(velocity <= self.vmax + 1e-9))
        self.assertTrue(np.all(acceleration <= self.amax + 1e-9))
        self.assertTrue(
            np.isclose(velocity.max(), self.vmax[0]) or np.isclose(acceleration.max(), 3.0)
        )
        self.assertLessEqual(self.trajectory.tb, self.trajectory.tf / 2.0 + 1e-12)

    def test_profile_is_continuous_in_position_and_velocity(self) -> None:
        tb, tf = self.trajectory.tb, self.trajectory.tf
        for instant in (tb, tf - tb):
            before = self.trajectory.sample(instant - 1e-9)
            after = self.trajectory.sample(instant + 1e-9)
            np.testing.assert_allclose(before[0], after[0], atol=1e-6)
            np.testing.assert_allclose(before[1], after[1], atol=1e-6)

    def test_all_joints_move_synchronously(self) -> None:
        middle = self.trajectory.sample(self.trajectory.tf / 2.0)[0]
        np.testing.assert_allclose(middle, (self.q0 + self.qf) / 2.0, atol=1e-9)

    def test_numerical_integration_matches_position(self) -> None:
        times = np.linspace(0.0, self.trajectory.tf, 4001)
        velocities = np.array([self.trajectory.sample(t)[1] for t in times])
        integral = np.sum(0.5 * (velocities[1:] + velocities[:-1]) * np.diff(times)[:, None], axis=0)
        np.testing.assert_allclose(integral, self.qf - self.q0, atol=1e-5)

    def test_zero_motion_and_invalid_limits(self) -> None:
        still = plan_lspb(self.q0, self.q0, self.vmax, self.amax)
        np.testing.assert_allclose(still.sample(0.3)[0], self.q0)
        with self.assertRaises(ValueError):
            plan_lspb(self.q0, self.qf, -1.0, 1.0)


if __name__ == "__main__":
    unittest.main()
