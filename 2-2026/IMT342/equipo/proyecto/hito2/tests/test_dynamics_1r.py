import unittest

import numpy as np

from irb120 import dynamics
from irb120.dynamics_1r import shoulder_model


class TestShoulderOneR(unittest.TestCase):
    def test_parameters_come_from_cad_links_and_gripper(self) -> None:
        model = shoulder_model(np.zeros(6))
        expected = sum(link.mass_kg for link in dynamics.LINKS[1:])
        self.assertAlmostEqual(model.mass_kg, expected, places=12)
        self.assertGreater(model.lc_m, 0.0)
        self.assertGreater(model.inertia_com_kg_m2, 0.0)

    def test_matches_full_model_for_joint_two(self) -> None:
        generator = np.random.default_rng(seed=4)
        for _ in range(30):
            q = generator.uniform(-1.5, 1.5, 6)
            model = shoulder_model(q)
            self.assertAlmostEqual(model.inertia_kg_m2, dynamics.mass_matrix(q)[1, 1], places=10)
            self.assertAlmostEqual(
                float(model.torque(q[1], 0.0)), dynamics.gravity_vector(q)[1], places=10
            )

    def test_components_add_up_and_cruise_torque_is_pure_gravity(self) -> None:
        model = shoulder_model(np.zeros(6))
        q2 = np.linspace(-0.5, 0.5, 5)
        inertial, gravity, total = model.torque_components(q2, np.zeros(5))
        np.testing.assert_allclose(inertial, 0.0)
        np.testing.assert_allclose(total, gravity)
        self.assertTrue(np.any(np.abs(gravity) > 0.1))  # velocidad constante no implica torque cero

    def test_hanging_down_needs_no_static_torque(self) -> None:
        model = shoulder_model(np.zeros(6))
        q2_down = -model.phi0_rad  # theta = 0: centro de masa bajo el eje
        self.assertAlmostEqual(float(model.torque(q2_down, 0.0)), 0.0, places=12)
        self.assertAlmostEqual(
            float(model.torque(q2_down + np.pi / 2, 0.0)), model.max_gravity_torque, places=12
        )


if __name__ == "__main__":
    unittest.main()
