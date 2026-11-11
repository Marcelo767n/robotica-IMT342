"""Comparación independiente de TF, sincronización y pérdida de lectura, sin robot/ROS."""
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("monitor_comunicacion", Path(__file__).parents[1] / "monitor_comunicacion.py")
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def test_ignore_option_is_visible_and_recorded_in_csv(self):
        self.state.raw({"ok": True, "stamp": {"sec": 1, "nanosec": 0},
                        "seq": 1, "request_ms": 2, "axes_deg": self.q, "ignore_joint_state": True}, 10)
        self.ros(); self.tf()
        self.assertTrue(self.state.snapshot(10.04)["ignore_joint_state"])
        self.assertIs(self.rows[0][-1], True)

    def setUp(self):
        self.geometry = monitor.load_joint_geometry(monitor.DEFAULT_URDF)
        self.rows = []
        self.state = monitor.MonitorState(self.geometry, writer=self.rows.append)
        self.q = [30.0, -20.0, 15.0, 40.0, -35.0, 370.0]

    def raw(self, sec=1, now=10.0, q=None):
        self.state.raw({"ok": True, "stamp": {"sec": sec, "nanosec": 0},
                        "seq": sec, "request_ms": 2.3, "axes_deg": q or self.q}, now)

    def ros(self, sec=1, now=10.01, q=None):
        self.state.joints({"sec": sec, "nanosec": 0}, monitor.JOINT_NAMES,
                          [math.radians(v) for v in (q or self.q)], now)

    def tf(self, sec=1, now=10.02, q=None):
        transforms = []
        for name, deg in zip(monitor.JOINT_NAMES, q or self.q):
            g = self.geometry[name]
            half = math.radians(deg)/2
            rotation = (*[a*math.sin(half) for a in g["axis"]], math.cos(half))
            quat = monitor.quaternion_product(g["origin"], rotation)
            transforms.append(({"sec": sec, "nanosec": 0}, g["parent"], g["child"], quat))
        self.state.transforms(transforms, now)

    def test_actual_urdf_origins_are_removed_and_j6_winding_is_preserved_for_display(self):
        self.raw(); self.ros(); self.tf()
        data = self.state.snapshot(10.03)["sample"]
        for raw, tf in zip(self.q, data["tf"]):
            self.assertAlmostEqual(raw, tf, places=10)
        self.assertLess(max(map(abs, data["delta_tf"])), 1e-10)
        self.assertEqual(len(self.rows), 1)

    def test_tf_disagreement_is_visible_instead_of_copying_received_angles(self):
        self.raw(); self.ros(); self.tf(q=[31, -20, 15, 40, -35, 370])
        self.assertAlmostEqual(self.state.snapshot(10.03)["sample"]["delta_tf"][0], 1.0)

    def test_ros_degree_conversion_error_is_visible(self):
        self.raw(); self.ros(q=[30, -18, 15, 40, -35, 370]); self.tf()
        self.assertAlmostEqual(self.state.snapshot(10.03)["sample"]["delta_ros"][1], 2.0)

    def test_different_timestamps_are_never_compared(self):
        self.raw(sec=2); self.ros(sec=1); self.tf(sec=1)
        data = self.state.snapshot(10.04)["sample"]
        self.assertIsNone(data["ros"])
        self.assertIsNone(data["delta_ros"])
        self.assertIsNone(data["tf"])
        self.assertEqual(self.rows, [])

    def test_arrival_order_can_be_tf_before_ros_before_raw(self):
        self.tf(now=10); self.ros(now=10.01); self.raw(now=10.02)
        self.assertIsNotNone(self.state.snapshot(10.03)["sample"]["delta_tf"])
        self.assertEqual(len(self.rows), 1)

    def test_no_data_is_distinct_from_six_zero_angles(self):
        data = self.state.snapshot(20)
        self.assertIsNone(data["sample"]["rws"])
        self.assertFalse(data["stats"]["rws"]["fresh"])
        self.raw(q=[0]*6)
        self.assertEqual(self.state.snapshot(10.1)["sample"]["rws"], [0]*6)

    def test_stale_stream_retains_last_values_and_recovery_clears_error(self):
        self.raw(); self.ros(); self.tf()
        self.state.raw({"ok": False, "error": "HTTP 503"}, 11.1)
        data = self.state.snapshot(11.2)
        self.assertEqual(data["sample"]["rws"], self.q)
        self.assertFalse(any(s["fresh"] for s in data["stats"].values()))
        self.assertEqual(data["error"], "HTTP 503")
        self.raw(sec=2, now=12)
        self.assertIsNone(self.state.snapshot(12.1)["error"])
        self.assertTrue(self.state.snapshot(12.1)["stats"]["rws"]["fresh"])

    def test_ros_or_tf_stall_does_not_hide_new_raw_angles(self):
        self.raw(); self.ros(); self.tf()
        self.raw(sec=2, now=10.5, q=[35]*6)
        data = self.state.snapshot(10.6)
        self.assertEqual(data["sample"]["rws"], [35]*6)
        self.assertIsNone(data["sample"]["tf"])

    def test_duplicate_tf_does_not_duplicate_csv_rows(self):
        self.raw(); self.ros(); self.tf(); self.tf(now=10.03)
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(self.state.snapshot(10.04)["stats"]["tf"]["count"], 1)

    def test_joint_names_are_mapped_by_name_and_bad_samples_rejected(self):
        deg = monitor.ordered_degrees(list(reversed(monitor.JOINT_NAMES)), list(reversed([math.radians(v) for v in self.q])))
        self.assertAlmostEqual(deg[1], -20)
        for names, values in [(["joint_1"]*6, [0]*6), (monitor.JOINT_NAMES, [0]*5),
                              (monitor.JOINT_NAMES, [0]*5+[float("nan")])]:
            with self.assertRaises(ValueError):
                monitor.ordered_degrees(names, values)

    def test_invalid_quaternions_and_wrong_axes_are_not_accepted(self):
        for q in [(0,0,0,0), (0,0,0,float("nan")), (1,0,0,0)]:
            with self.assertRaises(ValueError):
                monitor.angle_from_tf(self.geometry["joint_1"], q)

    def test_history_is_bounded(self):
        for i in range(1, 501):
            self.raw(sec=i, now=i/10)
        self.assertEqual(len(self.state.samples), 120)
        self.assertEqual(len(self.state.times["rws"]), 100)


if __name__ == "__main__":
    unittest.main()
