"""Referencia independiente ROS-Industrial y contratos de adquisición/cartesiana."""
import copy
import json
import math
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from irb120_conexion.rutas import PROJECT
sys.path.insert(0, str(PROJECT / "hito2"))
from irb120.rosi_model import rosi_forward_kinematics
from irb120.transforms import matrix_to_quaternion
from irb120_conexion.nodos.validacion_fk.comparacion import compare, CONTEXT, model_identity
from irb120_conexion.comunicacion import muestra_fk, lectura_rws


def sample(q=None):
    q = q or [30, -20, 15, 40, -35, 60]
    T = rosi_forward_kinematics([math.radians(v) for v in q])
    x, y, z, w = matrix_to_quaternion(T[:3, :3])
    return {"ok": True, "q_before_deg": q[:], "q_after_deg": q[:], "context": dict(CONTEXT),
            "window_ms": 5, "seq": 1, "stamp": {"sec": 1, "nanosec": 0},
            "controller_pose": {"xyz_mm": (T[:3, 3]*1000).tolist(), "quaternion_wxyz": [w, x, y, z]}}


class FkComparisonTests(unittest.TestCase):
    def test_own_fk_matches_independent_geometry_in_regular_and_singular_poses(self):
        for q in ([30,-20,15,40,-35,60], [55.301,16.946,.643,-45.428,-63.668,9.132], [0]*6, [90,-60,60,90,60,370]):
            result = compare(sample(q))
            self.assertTrue(result["accepted"], result)
            self.assertLess(result["position_error_mm"], 1e-9)

    def test_position_error_is_measured_in_mm_and_threshold_can_fail(self):
        s = sample()
        s["controller_pose"]["xyz_mm"][0] += .02
        result = compare(s)
        self.assertEqual(result["status"], "FUERA")
        self.assertAlmostEqual(result["position_error_mm"], .02, places=10)
        self.assertTrue(compare(s, position_tol_mm=.03)["accepted"])

    def test_fk_depends_on_read_joints_independently_from_controller_pose(self):
        original = sample([30,-20,15,40,-35,60])
        first = compare(original)
        changed = copy.deepcopy(original)
        changed['q_before_deg'][0] += 1
        changed['q_after_deg'][0] += 1
        second = compare(changed)
        # La referencia ABB queda fija; cambiar la entrada a FK debe cambiar la pose propia y el error.
        self.assertEqual(first['controller_matrix_m'], second['controller_matrix_m'])
        self.assertNotEqual(first['own_matrix_m'], second['own_matrix_m'])
        self.assertFalse(second['accepted'])
        self.assertGreater(second['position_error_mm'], .1)
        self.assertAlmostEqual(second['orientation_error_deg'], 1, places=9)
        self.assertAlmostEqual(second['q_input_rad'][0], math.radians(31), places=12)

    def test_quaternion_sign_is_equivalent_but_orientation_error_is_not_ignored(self):
        s = sample([0]*6)
        s["controller_pose"]["quaternion_wxyz"] = [-v for v in s["controller_pose"]["quaternion_wxyz"]]
        self.assertTrue(compare(s)["accepted"])
        # Rotar el eje de la muñeca del controlador sin alterar nuestros ángulos.
        other = sample([0,0,0,0,0,1])
        s["controller_pose"]["quaternion_wxyz"] = other["controller_pose"]["quaternion_wxyz"]
        self.assertAlmostEqual(compare(s)["orientation_error_deg"], 1, places=9)
        self.assertFalse(compare(s)["accepted"])

    def test_moving_or_slow_acquisition_never_produces_a_pass_or_fail(self):
        s = sample(); s["q_after_deg"][0] += .1
        self.assertIsNone(compare(s)["accepted"])
        self.assertEqual(compare(s)["status"], "NO_EVALUABLE")
        s = sample(); s["window_ms"] = 1000
        self.assertIsNone(compare(s)["accepted"])

    def test_subtle_motion_below_joint_threshold_is_detected_by_strict_fk_span(self):
        s = sample(); s["q_after_deg"][0] += .001
        self.assertLess(.001, .01)
        self.assertIsNone(compare(s)["accepted"])

    def test_wrong_frame_or_tcp_prevents_comparison(self):
        for key, value in [("tool", "pinza"), ("coordinate", "World"), ("wobj", "tablero")]:
            s = sample(); s["context"][key] = value
            result = compare(s)
            self.assertEqual(result["status"], "MARCO_INVALIDO")
            self.assertNotIn("position_error_mm", result)

    def test_bad_pose_or_input_is_rejected(self):
        for invalid in ([0,0,0,0], [float("nan"),0,0,1], [10,0,0,0]):
            s = sample(); s["controller_pose"]["quaternion_wxyz"] = invalid
            with self.assertRaises(ValueError): compare(s)
        s = sample(); s["q_before_deg"][0] = float("inf")
        with self.assertRaises(ValueError): compare(s)
        for value in (0, -1, float("nan")):
            with self.assertRaises(ValueError): compare(sample(), position_tol_mm=value)

    def test_http_failure_never_counts_as_a_good_pose(self):
        result = compare({"ok": False, "error": "robtarget HTTP 400"})
        self.assertIsNone(result["accepted"])
        self.assertEqual(result["status"], "LECTURA_INVALIDA")
        self.assertEqual(len(model_identity()["sha256"]), 64)


class Session:
    def __init__(self, values):
        self.values, self.calls = values, []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return type("Response", (), {"status_code": 200, "text": json.dumps(self.values[len(self.calls)-1])})()


class AcquisitionTests(unittest.TestCase):
    def test_robtarget_uses_fixed_context_and_ignore_applies_only_to_jointtarget(self):
        s = sample()
        pose = s["controller_pose"]
        row = {"_type": "ms-robtargets", **dict(zip(("x","y","z","q1","q2","q3","q4"),
                                                   pose["xyz_mm"]+pose["quaternion_wxyz"]))}
        axes = {"_type": "ms-jointtarget", **{f"rax_{i+1}": v for i,v in enumerate(s["q_after_deg"])}}
        session = Session([{"_embedded":{"_state":[row]}}, {"_embedded":{"_state":[axes]}}])
        out = muestra_fk.acquire(session,"http://192.0.2.1","ROB_1",s["q_before_deg"],time.monotonic(),ignore_joint_state=True)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[0][1]["params"], {"json":"1", "tool":"tool0", "wobj":"wobj0", "coordinate":"Base"})
        self.assertEqual(session.calls[1][1]["params"], {"json":"1", "ignore":"1"})
        self.assertEqual(out["context"], CONTEXT)
        self.assertTrue(compare(out)["accepted"])

    def test_pose_path_injection_and_unsupported_actions_are_rejected(self):
        session = Session([])
        for path in ("/rw/motionsystem/mechunits/ROB_1/robtarget?action=set", "/rw/motionsystem/mechunits/../robtarget"):
            with self.assertRaises(ValueError): lectura_rws.read_resource(session, "http://192.0.2.1", path, 1)
        self.assertEqual(session.calls, [])


if __name__ == "__main__":
    unittest.main()
