"""Contratos de la verificacion de enlace sin hardware: no abren conexiones ni ejecutan ping."""
import importlib.util
import ipaddress
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "g1_verificar_enlace", Path(__file__).parents[1] / "g1_verificar_enlace.py")
g1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g1)

UP = {"operstate": "up", "carrier": "1"}
DOWN = {"operstate": "down", "carrier": "0"}
OWN = [ipaddress.ip_interface("192.168.125.2/24")]
ROUTE_OK = {"dev": "eth9", "dst": "192.168.125.1"}


def states(results):
    return {name: state for name, state, _, _ in results}


class EvaluateTests(unittest.TestCase):
    def test_everything_ok(self):
        r = states(g1.evaluate("eth9", UP, OWN, ROUTE_OK, [{"dev": "wlan0"}]))
        self.assertEqual(r, {"adaptador": "PASS", "cable": "PASS", "ip": "PASS", "ruta": "PASS"})

    def test_no_adapter_stops_first(self):
        self.assertEqual(states(g1.evaluate(None, {}, [], None, [])), {"adaptador": "FAIL"})

    def test_no_carrier_stops_before_ip_checks(self):
        r = states(g1.evaluate("eth9", DOWN, [], None, []))
        self.assertEqual(r, {"adaptador": "PASS", "cable": "FAIL"})

    def test_cable_but_no_service_network_address(self):
        r = states(g1.evaluate("eth9", UP, [ipaddress.ip_interface("10.0.0.5/24")], None, []))
        self.assertEqual(r["ip"], "FAIL")
        self.assertNotIn("ruta", r)

    def test_pc_must_not_use_the_controller_address(self):
        r = g1.evaluate("eth9", UP, [ipaddress.ip_interface("192.168.125.1/24")], ROUTE_OK, [])
        self.assertEqual(states(r)["ip"], "FAIL")

    def test_route_through_another_interface_is_a_failure(self):
        r = states(g1.evaluate("eth9", UP, OWN, {"dev": "wlan0"}, []))
        self.assertEqual(r["ruta"], "FAIL")

    def test_default_route_through_robot_interface_warns(self):
        r = states(g1.evaluate("eth9", UP, OWN, ROUTE_OK, [{"dev": "eth9"}]))
        self.assertEqual(r["internet"], "AVISO")


class SystemReadersTests(unittest.TestCase):
    def test_only_physical_wired_interfaces_are_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name, device, wireless in (("lo", False, False), ("docker0", False, False),
                                           ("wlan0", True, True), ("eth9", True, False)):
                (base / name).mkdir()
                if device:
                    (base / name / "device").mkdir()
                if wireless:
                    (base / name / "wireless").mkdir()
            self.assertEqual(g1.find_ethernet_interfaces(base), ["eth9"])

    def test_unreadable_carrier_is_reported_as_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "eth9").mkdir()
            (Path(tmp) / "eth9" / "operstate").write_text("down\n")
            self.assertEqual(g1.read_link("eth9", Path(tmp)), {"operstate": "down", "carrier": None})

    def test_ipv4_extraction_ignores_ipv6(self):
        data = [{"addr_info": [{"family": "inet6", "local": "fe80::1", "prefixlen": 64},
                               {"family": "inet", "local": "192.168.125.2", "prefixlen": 24}]}]
        self.assertEqual([str(a) for a in g1.ipv4_addresses(data)], ["192.168.125.2/24"])


if __name__ == "__main__":
    unittest.main()
