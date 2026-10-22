"""Contratos de diagnóstico sin hardware: no abrir conexiones de red."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "abb_lectura_rws", Path(__file__).parents[1] / "abb_lectura_rws.py")
abb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abb)


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        path = url.removeprefix("http://192.0.2.1")
        status, payload = self.responses[path]
        return type("Response", (), {
            "status_code": status, "text": json.dumps(payload)})()


def payload(records):
    return {"_embedded": {"_state": records}}


class ReadOnlyDiagnosticTests(unittest.TestCase):
    def test_json_and_namespaced_xhtml_axes(self):
        row = {f"rax_{i}": str(i) for i in range(1, 7)}
        self.assertEqual(abb.robot_axes(abb.state_records(json.dumps(payload([row])))),
                         [1, 2, 3, 4, 5, 6])
        spans = "".join(f'<span class="{k}">{v}</span>' for k, v in row.items())
        xml = f'<html xmlns="http://www.w3.org/1999/xhtml"><li class="ms-jointtarget" title="ROB_1">{spans}</li></html>'
        self.assertEqual(abb.robot_axes(abb.state_records(xml)), [1, 2, 3, 4, 5, 6])

    def test_rejects_missing_non_numeric_and_non_finite_axes(self):
        valid = {f"rax_{i}": i for i in range(1, 7)}
        for bad in (None, "NaN", "inf", "not-a-number"):
            with self.subTest(bad=bad):
                self.assertIsNone(abb.robot_axes([{**valid, "rax_3": bad}]))
        del valid["rax_3"]
        self.assertIsNone(abb.robot_axes([valid]))

    def test_auth_failure_stops_before_state_reads(self):
        for code in (401, 403):
            session = FakeSession({"/rw/system": (code, {})})
            report = abb.probe(session, "http://192.0.2.1")
            self.assertEqual(len(session.calls), 1)
            self.assertIn("permission_pending", report["state"])

    def test_arbitrary_http_page_does_not_count_as_abb(self):
        session = FakeSession({"/rw/system": (200, {"hello": "world"})})
        self.assertEqual(abb.probe(session, "http://192.0.2.1")["state"],
                         "rws_identity_not_verified")
        self.assertEqual(len(session.calls), 1)

    def test_missing_mechanical_unit_never_reads_jointtarget(self):
        responses = {path: (200, payload([])) for path in abb.READ_PATHS}
        responses["/rw/system"] = (200, payload([{"_type": "sys-system-li"}]))
        session = FakeSession(responses)
        report = abb.probe(session, "http://192.0.2.1")
        self.assertIsNone(report["joint_snapshot"])
        self.assertEqual(len(session.calls), 5)

    def test_valid_snapshot_uses_only_bounded_gets_without_redirects(self):
        responses = {path: (200, payload([])) for path in abb.READ_PATHS}
        responses["/rw/system"] = (200, payload([{"_type": "sys-system-li"}]))
        responses["/rw/motionsystem/mechunits"] = (200, payload([
            {"_type": "ms-mechunit-li", "_title": "ROB_1"}]))
        responses["/rw/motionsystem/mechunits/ROB_1/jointtarget"] = (
            200, payload([{f"rax_{i}": i for i in range(1, 7)}]))
        session = FakeSession(responses)
        report = abb.probe(session, "http://192.0.2.1", timeout=2)
        self.assertEqual(report["state"], "rws_joint_snapshot_observed")
        self.assertFalse(report["movement_authorized"])
        self.assertFalse(report["joint_snapshot"]["physical_controller_identity_confirmed"])
        self.assertEqual(len(session.calls), 6)
        for _, kwargs in session.calls:
            self.assertFalse(kwargs["allow_redirects"])
            self.assertEqual(kwargs["timeout"], 2)

    def test_unlisted_resources_and_path_injection_are_rejected(self):
        session = FakeSession({})
        for path in ("/rw/panel/ctrlstate?action=setctrlstate", "/fileservice/a", "/rw/rapid/symbol/data"):
            with self.assertRaises(ValueError):
                abb.read_resource(session, "http://192.0.2.1", path, 2)
        with self.assertRaises(ValueError):
            abb.probe(session, "http://192.0.2.1", "../bad")
        self.assertEqual(session.calls, [])

    def test_no_host_is_local_inventory_only(self):
        with patch.object(abb, "local_inventory", return_value={}), \
             patch.object(abb, "probe", side_effect=AssertionError("Network forbidden")), \
             patch("builtins.print"):
            self.assertEqual(abb.main([]), 0)


if __name__ == "__main__":
    unittest.main()
