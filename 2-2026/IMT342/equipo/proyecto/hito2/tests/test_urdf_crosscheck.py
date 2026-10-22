import unittest
from pathlib import Path

import numpy as np

from irb120.dh import JOINT_LIMITS_RAD, forward_kinematics
from irb120.rosi_model import ROSI_LIMITS_RAD, rosi_forward_kinematics
from irb120.urdf_chain import chain_transform

URDF = Path(__file__).resolve().parents[1] / "datos" / "irb120.urdf"


class TestAgainstOfficialRosIndustrialModel(unittest.TestCase):
    """Verificacion INDEPENDIENTE: modelo oficial de ROS-Industrial (abb_irb120_support), no derivado de DH."""

    def test_full_pose_matches_official_model(self) -> None:
        generator = np.random.default_rng(seed=33)
        for _ in range(200):
            q = generator.uniform(JOINT_LIMITS_RAD[:, 0], JOINT_LIMITS_RAD[:, 1])
            np.testing.assert_allclose(forward_kinematics(q), rosi_forward_kinematics(q), atol=1e-12)

    def test_joint_limits_match_official_model(self) -> None:
        np.testing.assert_allclose(JOINT_LIMITS_RAD, ROSI_LIMITS_RAD, atol=1e-5)


class TestDhAgainstHito1Urdf(unittest.TestCase):
    """Verificacion de IMPLEMENTACION: el URDF del Hito 1 se derivo de la tabla DH, evaluado con otro codigo."""

    def test_full_pose_matches_for_random_configurations(self) -> None:
        generator = np.random.default_rng(seed=21)
        for _ in range(100):
            q = generator.uniform(JOINT_LIMITS_RAD[:, 0], JOINT_LIMITS_RAD[:, 1])
            urdf = chain_transform(URDF, {f"joint_{i + 1}": q[i] for i in range(6)})
            np.testing.assert_allclose(forward_kinematics(q), urdf, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
