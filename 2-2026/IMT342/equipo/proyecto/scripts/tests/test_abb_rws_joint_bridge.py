"""Puente RWS -> ROS 2 sin ROS ni hardware: la logica de lectura contra el controlador SIMULADO en loopback."""
import importlib.util
import math
from pathlib import Path
from http.server import ThreadingHTTPServer
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

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
    def test_controller_400_is_not_silently_retried_and_explicit_ignore_reads_axes(self):
        class RequiresIgnore(sim.FakeRws):
            def do_GET(self):
                query = parse_qs(urlsplit(self.path).query)
                if "jointtarget" in self.path and query.get("ignore") != ["1"]:
                    self.server.log.append((self.command, self.path))
                    data = b'{"_embedded":{"status":{"code":-1073414145,"msg":"Unable to get jointtarget icode:-804"}}}'
                    self.send_response(400)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                super().do_GET()
        server = ThreadingHTTPServer(("127.0.0.1", 0), RequiresIgnore)
        server.mode, server.log = "json", []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        session = self.session()
        with self.assertRaisesRegex(bridge.BridgeError, "-1073414145.*icode:-804"):
            bridge.fetch_joints_deg(session, base)
        self.assertEqual(len(server.log), 1, "No debe activar ignore=1 automáticamente")
        self.assertEqual(bridge.fetch_joints_deg(session, base, ignore_joint_state=True), sim.AXES)
        self.assertTrue(all(method == "GET" for method, _ in server.log))
        self.assertEqual(parse_qs(urlsplit(server.log[-1][1]).query), {"json": ["1"], "ignore": ["1"]})

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
    def test_http_400_reports_the_controller_cause_without_publishing_values(self):
        response = {"http_status": 400, "records": [],
                    "controller_error": {"code": "-123", "message": "State not valid"}}
        with patch.object(bridge.abb, "read_resource", return_value=response):
            with self.assertRaisesRegex(bridge.BridgeError, "HTTP 400.*code=-123.*State not valid"):
                bridge.fetch_joints_deg(object(), "http://192.0.2.1")

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
        source = Path(bridge.__file__).read_text()
        for forbidden in (".post(", ".put(", ".delete(", ".patch(", "create_subscription", "create_service", "ActionServer"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
