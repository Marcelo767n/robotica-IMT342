import unittest
from pathlib import Path

import numpy as np

from irb120.dh import JOINT_LIMITS_RAD, forward_kinematics
from irb120.urdf_chain import chain_transform

URDF = Path(__file__).resolve().parents[1] / "datos" / "irb120.urdf"


class TestDhAgainstUrdf(unittest.TestCase):
    """Verificacion externa: la FK por DH coincide con el URDF del Hito 1 (otro modelo, otro codigo)."""

    def test_full_pose_matches_for_random_configurations(self) -> None:
        generator = np.random.default_rng(seed=21)
        for _ in range(100):
            q = generator.uniform(JOINT_LIMITS_RAD[:, 0], JOINT_LIMITS_RAD[:, 1])
            urdf = chain_transform(URDF, {f"joint_{i + 1}": q[i] for i in range(6)})
            np.testing.assert_allclose(forward_kinematics(q), urdf, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
