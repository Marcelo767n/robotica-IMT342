import unittest

import numpy as np

from irb120_hito2.kinematics.collision import CollisionChecker


class TestCollision(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.checker = CollisionChecker()

    def test_validation_poses_are_collision_free(self) -> None:
        for degrees in ([0] * 6, [30, -20, 15, 40, -35, 60], [90, -60, 60, 90, 60, 180]):
            self.assertFalse(self.checker.in_collision(np.deg2rad(degrees)), degrees)

    def test_arm_leaning_into_base_and_table_collides(self) -> None:
        pairs = self.checker.colliding_pairs(np.deg2rad([0, 100, 60, 0, 0, 0]))
        self.assertIn(("base_link", "link_4"), pairs)
        self.assertIn(("mesa", "gripper_link"), pairs)

    def test_wrist_folded_onto_the_arm_collides(self) -> None:
        self.assertTrue(self.checker.in_collision(np.deg2rad([0, -100, 70, 0, 120, 0])))

    def test_distances_are_nonnegative_and_cover_all_pairs(self) -> None:
        distances = self.checker.min_distances(np.zeros(6))
        self.assertGreater(len(distances), 20)
        self.assertTrue(all(value >= -1e-9 or pair[0] == "mesa" for pair, value in distances.items()))


if __name__ == "__main__":
    unittest.main()
