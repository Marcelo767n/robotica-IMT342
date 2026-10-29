import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comparar_lectura_abb import abb_quaternion, load_axes, main, predict, quaternion_angle_deg  # noqa: E402
from irb120.dh import forward_kinematics  # noqa: E402


class TestCompararLecturaAbb(unittest.TestCase):
    def test_home_matches_datasheet_in_flexpendant_units(self):
        result = predict([0, 0, 0, 0, 0, 0])
        np.testing.assert_allclose(result["tool0_mm"], [374.0, 0.0, 630.0], atol=1e-9)
        np.testing.assert_allclose(result["tool0_quaternion_wxyz"], [np.sqrt(0.5), 0, np.sqrt(0.5), 0], atol=1e-9)
        self.assertTrue(result["near_singularity"])  # q5 = 0
        self.assertEqual(result["outside_limits"], [])

    def test_quaternion_has_nonnegative_w_and_unit_norm(self):
        rng = np.random.default_rng(3)
        for _ in range(50):
            q = rng.uniform(-1.5, 1.5, 6)
            w, x, y, z = abb_quaternion(forward_kinematics(q)[:3, :3])
            self.assertGreaterEqual(w, 0.0)
            self.assertAlmostEqual(w * w + x * x + y * y + z * z, 1.0, places=12)

    def test_limits_are_reported_per_axis(self):
        self.assertEqual(predict([170, 0, 0, 0, 0, 0])["outside_limits"], [1])
        self.assertEqual(predict([0, 0, 80, 0, 130, 0])["outside_limits"], [3, 5])

    def test_invalid_input_is_rejected(self):
        for bad in ([0] * 5, [0, 0, 0, 0, 0, float("nan")]):
            with self.assertRaises(ValueError):
                predict(bad)

    def test_load_axes_reads_a_valid_snapshot_and_refuses_a_failed_probe(self):
        good = {"controller_probe": {"state": "rws_joint_snapshot_observed",
                                     "joint_snapshot": {"rax_1_to_6": [1, 2, 3, 4, 5, 6]}}}
        bad = {"controller_probe": {"state": "http_reachable_authentication_or_permission_pending"}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ok.json").write_text(json.dumps(good))
            (Path(tmp) / "mal.json").write_text(json.dumps(bad))
            self.assertEqual(load_axes(Path(tmp) / "ok.json"), [1, 2, 3, 4, 5, 6])
            with self.assertRaises(ValueError):
                load_axes(Path(tmp) / "mal.json")
            self.assertEqual(main(["--json", str(Path(tmp) / "mal.json")]), 2)

    def test_cli_returns_zero_for_valid_axes(self):
        self.assertEqual(main(["--q", "10", "-20", "30", "0", "45", "90", "--flexpendant", "300", "50", "500"]), 0)

    def test_quaternion_angle(self):
        self.assertAlmostEqual(quaternion_angle_deg([1, 0, 0, 0], [1, 0, 0, 0]), 0.0, places=6)
        self.assertAlmostEqual(quaternion_angle_deg([1, 0, 0, 0], [-1, 0, 0, 0]), 0.0, places=6)  # misma rotacion
        half = np.sqrt(0.5)
        self.assertAlmostEqual(quaternion_angle_deg([1, 0, 0, 0], [half, 0, 0, half]), 90.0, places=6)
        with self.assertRaises(ValueError):
            quaternion_angle_deg([0, 0, 0, 0], [1, 0, 0, 0])

    def test_cli_compares_quaternion(self):
        self.assertEqual(main(["--q", "0", "0", "0", "0", "0", "0", "--flexpendant", "374", "0", "630",
                               "--flexpendant-quat", "0.70711", "0", "0.70711", "0"]), 0)


if __name__ == "__main__":
    unittest.main()
