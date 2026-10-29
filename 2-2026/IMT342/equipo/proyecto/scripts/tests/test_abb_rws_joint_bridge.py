"""Puente RWS -> ROS 2 sin ROS ni hardware: la logica de lectura contra el controlador SIMULADO en loopback."""
import importlib.util
import math
from pathlib import Path
from http.server import ThreadingHTTPServer
import threading
import unittest

import requests
from requests.auth import HTTPDigestAuth

HERE = Path(__file__).parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load("abb_rws_joint_bridge", HERE.parents[0] / "abb_rws_joint_bridge.py")
sim = load("test_rws_simulado_loopback_mod", HERE / "test_rws_simulado_loopback.py")


class BridgeLogicTests(unittest.TestCase):
    def serve(self, mode="json"):
        server = ThreadingHTTPServer(("127.0.0.1", 0), sim.FakeRws)
        server.mode, server.log = mode, []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server, f"http://127.0.0.1:{server.server_address[1]}"

    def session(self, password=sim.PASSWORD):
        s = requests.Session()
        s.trust_env = False
        s.auth = HTTPDigestAuth(sim.USER, password)
        self.addCleanup(s.close)
        return s

    def test_reads_six_axes_json_and_xhtml(self):
        for mode in ("json", "xhtml_only"):
            server, base = self.serve(mode)
            self.assertEqual(bridge.fetch_joints_deg(self.session(), base), sim.AXES)

    def test_each_cycle_is_exactly_one_get_of_the_jointtarget(self):
        server, base = self.serve()
        s = self.session()
        bridge.fetch_joints_deg(s, base)
        before = len(server.log)
        bridge.fetch_joints_deg(s, base)
        new = server.log[before:]
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0][0], "GET")
        self.assertIn("/rw/motionsystem/mechunits/ROB_1/jointtarget", new[0][1])

    def test_wrong_password_raises_bridge_error_and_does_not_continue(self):
        server, base = self.serve()
        with self.assertRaises(bridge.BridgeError):
            bridge.fetch_joints_deg(self.session("otra"), base)

    def test_bad_mechunit_name_is_rejected_before_any_request(self):
        server, base = self.serve()
        with self.assertRaises(bridge.BridgeError):
            bridge.fetch_joints_deg(self.session(), base, "ROB_1/../../x")
        self.assertEqual(server.log, [])

    def test_unreachable_controller_raises_a_request_exception(self):
        server, base = self.serve()
        server.shutdown()
        server.server_close()
        with self.assertRaises(requests.RequestException):
            bridge.fetch_joints_deg(self.session(), base, timeout=0.5)


class PureFunctionTests(unittest.TestCase):
    def test_degrees_to_radians_and_names(self):
        names, positions = bridge.joint_state_fields([180, 90, 0, -90, 45, 0])
        self.assertEqual(names, ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"])
        self.assertAlmostEqual(positions[0], math.pi)
        self.assertAlmostEqual(positions[3], -math.pi / 2)
        with self.assertRaises(ValueError):
            bridge.joint_state_fields([0, 0, 0, 0, 0])
        with self.assertRaises(ValueError):
            bridge.joint_state_fields([0, 0, 0, 0, 0, float("nan")])

    def test_limit_check(self):
        self.assertEqual(bridge.outside_limits([0, 0, 0, 0, 0, 0]), [])
        self.assertEqual(bridge.outside_limits([170, 0, 80, 0, 0, 0]), [1, 3])
        self.assertEqual(bridge.outside_limits([165.5, 0, 0, 0, 0, 0]), [])  # dentro del margen de 1 grado

    def test_base_url_rules(self):
        self.assertEqual(bridge.build_base_url("192.168.125.1"), "http://192.168.125.1")
        self.assertEqual(bridge.build_base_url("127.0.0.1", 8081), "http://127.0.0.1:8081")
        for bad in (("192.168.125.1", 8080), ("224.0.0.1", 80), ("0.0.0.0", 80), ("255.255.255.255", 80)):
            with self.assertRaises(ValueError):
                bridge.build_base_url(*bad)
        with self.assertRaises(Exception):
            bridge.build_base_url("http://192.168.125.1")

    def test_rate_is_capped(self):
        with self.assertRaises(SystemExit):
            bridge.main(["--host", "127.0.0.1", "--user", "u", "--rate", "50"])

    def test_the_bridge_has_no_write_path(self):
        source = (HERE.parents[0] / "abb_rws_joint_bridge.py").read_text()
        for forbidden in (".post(", ".put(", ".delete(", ".patch(", "create_subscription", "create_service", "ActionServer"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
