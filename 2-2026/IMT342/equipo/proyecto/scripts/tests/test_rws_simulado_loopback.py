"""Ensayo general del lector RWS contra un controlador SIMULADO en 127.0.0.1.

Ejecuta de verdad `probe()` con `requests`: HTTP real por loopback, handshake HTTP Digest (RFC 2617)
y parseo de las respuestas. El servidor imita a RWS 1.0 con la estructura documentada por ABB
(`fuentes/rws_system.html`, `rws_jointtarget.html`, `rws_intro.html`): XHTML con `class`/`title` y JSON con
`_embedded._state[]`, `_type` y `_title`. Los recursos `mechunits` y `opmode` se modelan por analogia: ABB
no incluye un ejemplo de su respuesta en las fuentes guardadas.

NO es una prueba del controlador fisico ni de que el robot responda asi: solo demuestra que el codigo
funciona de punta a punta con un servidor que habla el protocolo.
"""
import hashlib
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import unittest
from urllib.parse import parse_qs, urlsplit

import requests
from requests.auth import HTTPDigestAuth

spec = importlib.util.spec_from_file_location(
    "abb_lectura_rws", Path(__file__).parents[1] / "abb_lectura_rws.py")
abb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abb)

USER, PASSWORD, REALM, NONCE = "operador", "clave-de-prueba-123", "RWS-simulado", "abc123nonce"
AXES = [10.5, -20.25, 30.0, 0.0, 45.0, 90.0]


def md5(text):
    return hashlib.md5(text.encode()).hexdigest()


def li(cls, title, **fields):
    spans = "".join(f'<span class="{k}">{v}</span>' for k, v in fields.items())
    return (f'<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
            f'<div class="state"><ul><li class="{cls}" title="{title}">{spans}</li></ul></div></body></html>')


def record(_type, _title, **fields):
    return {"_type": _type, "_title": _title, **fields}


def json_body(rec):
    return json.dumps({"_links": {"base": {"href": "http://localhost/rw/"}}, "_embedded": {"_state": [rec]}})


def routes(fmt):
    sys_fields = {"name": "120-SIM", "rwversion": "6.12.01.00"}
    joint_fields = {f"rax_{i + 1}": v for i, v in enumerate(AXES)}
    items = {
        "/rw/system": ("sys-system-li", "system", sys_fields),
        "/rw/panel/ctrlstate": ("pnl-ctrlstate", "ctrlstate", {"ctrlstate": "motoroff"}),
        "/rw/panel/opmode": ("pnl-opmode", "opmode", {"opmode": "MANR"}),
        "/rw/rapid/execution": ("rap-execution", "execution", {"ctrlexecstate": "stopped"}),
        "/rw/motionsystem/mechunits": ("ms-mechunit-li", "ROB_1", {"type": "TCPRobot"}),
        "/rw/motionsystem/mechunits/ROB_1/jointtarget": ("ms-jointtarget", "ROB_1", joint_fields),
    }
    return {path: (json_body(record(t, ti, **f)) if fmt == "json" else li(t, ti, **f))
            for path, (t, ti, f) in items.items()}


class FakeRws(BaseHTTPRequestHandler):
    """Servidor de solo lectura: cualquier metodo distinto de GET se rechaza y queda registrado."""

    def log_message(self, *args):
        pass

    def _digest_ok(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Digest "):
            return False
        parts = dict(p.strip().split("=", 1) for p in header[7:].split(","))
        parts = {k: v.strip('"') for k, v in parts.items()}
        ha1 = md5(f"{USER}:{REALM}:{PASSWORD}")
        ha2 = md5(f"GET:{parts.get('uri')}")
        expected = md5(f"{ha1}:{parts['nonce']}:{parts['nc']}:{parts['cnonce']}:{parts['qop']}:{ha2}")
        return parts.get("username") == USER and parts.get("response") == expected

    def do_GET(self):
        server = self.server
        server.log.append(("GET", self.path))
        url = urlsplit(self.path)
        if server.mode == "no_rws":
            return self._send(200, "<html><body>Hola, esto no es un controlador</body></html>", "text/html")
        if not self._digest_ok():
            self.send_response(401)
            self.send_header("WWW-Authenticate",
                             f'Digest realm="{REALM}", qop="auth", nonce="{NONCE}", opaque="x"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        wants_json = parse_qs(url.query).get("json") == ["1"] and server.mode != "xhtml_only"
        table = routes("json" if wants_json else "xhtml")
        if server.mode == "no_mechunit" and url.path == "/rw/motionsystem/mechunits":
            table[url.path] = json_body(record("ms-mechunit-li", "ROB_9"))
        if url.path in table:
            self._send(200, table[url.path], "application/json" if wants_json else "application/xhtml+xml")
        else:
            self._send(404, "", "text/plain")

    def _send(self, status, body, ctype):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _reject(self):
        self.server.log.append((self.command, self.path))
        self.send_response(405)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = do_PUT = do_DELETE = do_PATCH = _reject


class SimulatedControllerTests(unittest.TestCase):
    def serve(self, mode="json"):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRws)
        server.mode, server.log = mode, []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server, f"http://127.0.0.1:{server.server_address[1]}"

    def session(self, password=PASSWORD):
        s = requests.Session()
        s.trust_env = False
        s.auth = HTTPDigestAuth(USER, password)
        self.addCleanup(s.close)
        return s

    def test_full_read_with_digest_json(self):
        server, base = self.serve("json")
        report = abb.probe(self.session(), base)
        self.assertEqual(report["state"], "rws_joint_snapshot_observed")
        self.assertEqual(report["joint_snapshot"]["rax_1_to_6"], AXES)
        self.assertFalse(report["movement_authorized"])

    def test_full_read_when_server_ignores_json_and_answers_xhtml(self):
        server, base = self.serve("xhtml_only")
        report = abb.probe(self.session(), base)
        self.assertEqual(report["state"], "rws_joint_snapshot_observed")
        self.assertEqual(report["joint_snapshot"]["rax_1_to_6"], AXES)

    def test_only_get_on_the_allowed_paths_and_never_a_write(self):
        server, base = self.serve("json")
        abb.probe(self.session(), base)
        paths = {urlsplit(path).path for _, path in server.log}
        self.assertEqual({method for method, _ in server.log}, {"GET"})
        self.assertTrue(paths <= abb.READ_PATHS | {"/rw/motionsystem/mechunits/ROB_1/jointtarget"})
        self.assertTrue(all("json=1" in path for _, path in server.log))

    def test_wrong_password_stops_after_identity_check(self):
        server, base = self.serve("json")
        report = abb.probe(self.session("otra-clave"), base)
        self.assertEqual(report["state"], "http_reachable_authentication_or_permission_pending")
        self.assertEqual({urlsplit(p).path for _, p in server.log}, {"/rw/system"})
        self.assertNotIn("joint_snapshot", report)

    def test_plain_web_server_is_not_accepted_as_abb(self):
        server, base = self.serve("no_rws")
        report = abb.probe(self.session(), base)
        self.assertEqual(report["state"], "rws_identity_not_verified")
        self.assertEqual(len(server.log), 1)

    def test_missing_mechanical_unit_never_reads_joints(self):
        server, base = self.serve("no_mechunit")
        report = abb.probe(self.session(), base)
        self.assertEqual(report["state"], "rws_system_observed")
        self.assertIsNone(report["joint_snapshot"])
        self.assertFalse(any("jointtarget" in path for _, path in server.log))

    def test_report_never_contains_the_password(self):
        server, base = self.serve("json")
        text = json.dumps(abb.probe(self.session(), base), ensure_ascii=False)
        self.assertNotIn(PASSWORD, text)
        self.assertNotIn("Authorization", text)

    def test_connection_refused_is_reported_without_crashing_the_flow(self):
        server, base = self.serve("json")
        server.shutdown()
        server.server_close()
        with self.assertRaises(requests.RequestException):
            abb.probe(self.session(), base, timeout=1.0)


if __name__ == "__main__":
    unittest.main()
