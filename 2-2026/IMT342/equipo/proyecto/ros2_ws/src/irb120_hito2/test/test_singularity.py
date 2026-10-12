import unittest

import numpy as np

from irb120_hito2 import dynamics
from irb120_hito2.kinematics import jacobian

Q = np.deg2rad([30.0, -20.0, 15.0, 40.0, -35.0, 60.0])
TWIST = np.array([0.10, 0.05, 0.02, 0.30, 0.20, 0.10])
ACCEL = np.array([0.20, 0.10, 0.10, 0.50, 0.40, 0.30])


def with_q5(value: float) -> np.ndarray:
    q = Q.copy()
    q[4] = value
    return q


class TestWristSingularity(unittest.TestCase):
    def test_determinant_factorizes_as_sin_q5_times_arm_determinant(self) -> None:
        generator = np.random.default_rng(seed=5)
        for _ in range(50):
            q = generator.uniform(-1.0, 1.0, 6)
            expected = -np.sin(q[4]) * jacobian.arm_position_determinant(q)
            self.assertAlmostEqual(jacobian.determinant(q), expected, places=10)

    def test_jacobian_loses_rank_at_q5_zero(self) -> None:
        self.assertLess(jacobian.smallest_singular_value(with_q5(0.0)), 1e-12)
        self.assertAlmostEqual(jacobian.determinant(with_q5(0.0)), 0.0, places=12)
        with self.assertRaises(jacobian.SingularityError):
            jacobian.joint_velocity(with_q5(0.0), TWIST)

    def test_joint_velocity_diverges_as_inverse_sin_q5(self) -> None:
        norms = [np.linalg.norm(jacobian.joint_velocity(with_q5(e), TWIST)) for e in (1e-1, 1e-2, 1e-3)]
        self.assertGreater(norms[1] / norms[0], 7.0)
        self.assertGreater(norms[2] / norms[1], 9.0)  # ~ factor 10 por decada

    def test_condition_number_grows_toward_singularity(self) -> None:
        values = [jacobian.condition_number(with_q5(e)) for e in (1e-1, 1e-2, 1e-3)]
        self.assertLess(values[0], values[1])
        self.assertLess(values[1], values[2])

    def test_mass_matrix_is_symmetric_positive_definite(self) -> None:
        matrix = dynamics.mass_matrix(Q)
        np.testing.assert_allclose(matrix, matrix.T, atol=1e-12)
        self.assertGreater(np.linalg.eigvalsh(matrix).min(), 0.0)

    def test_gripper_mass_is_merged_into_link_six(self) -> None:
        with_gripper, paper = dynamics.LINKS, dynamics.LINKS_NO_GRIPPER
        self.assertAlmostEqual(
            with_gripper[-1].mass_kg - paper[-1].mass_kg, dynamics.GRIPPER_MASS_KG, places=12
        )
        self.assertEqual(with_gripper[:5], paper[:5])
        heavier = dynamics.gravity_vector(Q)
        lighter = dynamics.gravity_vector(Q, dynamics.LINKS_NO_GRIPPER)
        self.assertGreater(abs(heavier[1]) + abs(heavier[2]), abs(lighter[1]) + abs(lighter[2]))
        self.assertGreater(
            np.linalg.eigvalsh(dynamics.mass_matrix(Q, dynamics.LINKS_NO_GRIPPER)).min(), 0.0
        )

    def test_coriolis_is_zero_at_rest_and_energy_consistent(self) -> None:
        np.testing.assert_allclose(dynamics.coriolis_vector(Q, np.zeros(6)), 0.0, atol=1e-12)
        q_dot = np.array([0.3, -0.2, 0.1, 0.5, -0.4, 0.2])
        # q_dot^T (M_dot - 2C) q_dot = 0  =>  q_dot^T c = 1/2 q_dot^T M_dot q_dot
        step = 1e-6
        m_dot = (dynamics.mass_matrix(Q + step * q_dot) - dynamics.mass_matrix(Q - step * q_dot)) / (2 * step)
        self.assertAlmostEqual(
            float(q_dot @ dynamics.coriolis_vector(Q, q_dot)), 0.5 * float(q_dot @ m_dot @ q_dot), places=6
        )

    def test_dynamic_torque_demand_diverges_near_singularity(self) -> None:
        def inertial(e: float) -> float:
            _, _, tau = dynamics.cartesian_demand(with_q5(e), TWIST, ACCEL)
            return float(np.linalg.norm(tau - dynamics.gravity_vector(with_q5(e))))

        # El torque de la junta 4 crece ~ 1/sin^2(q5): factor ~100 por decada.
        values = [inertial(e) for e in (1e-3, 1e-4, 1e-5)]
        self.assertGreater(values[1] / values[0], 50.0)
        self.assertGreater(values[2] / values[1], 50.0)


if __name__ == "__main__":
    unittest.main()
