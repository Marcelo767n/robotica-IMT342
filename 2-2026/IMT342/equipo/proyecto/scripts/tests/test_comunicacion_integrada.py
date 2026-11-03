"""Ensayo opcional de la cadena real de procesos ROS contra HTTP simulado.

IRB120_RUN_ROS_TEST=1, entorno Jazzy/Python 3.12 y permisos de sockets locales.
No requiere RViz ni contacta al robot: todos los servicios se enlazan a loopback.
"""
import csv
from http.server import ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen

import test_rws_simulado_loopback as sim


@unittest.skipUnless(os.environ.get("IRB120_RUN_ROS_TEST") == "1", "Ensayo ROS opcional: IRB120_RUN_ROS_TEST=1")
class IntegratedCommunicationTests(unittest.TestCase):
    def test_moving_axes_match_tf_and_loss_is_visible_then_recovers(self):
        sys.path.insert(0, str(Path(__file__).parents[1]))
        import prueba_comunicacion as launch

        started = time.monotonic()
        original_routes = sim.routes

        def moving_routes(fmt):
            t = time.monotonic() - started
            sim.AXES[:] = [30*math.sin(t), -20+8*math.sin(t), 15, 40, -35, 370]
            return original_routes(fmt)

        class InterruptedRws(sim.FakeRws):
            def do_GET(self):
                elapsed = time.monotonic() - started
                if 2.2 < elapsed < 4.6:
                    self.server.log.append((self.command, self.path))
                    self.send_response(503)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                super().do_GET()

        server = ThreadingHTTPServer(("127.0.0.1", 0), InterruptedRws)
        server.mode, server.log = "json", []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            panel_port = sock.getsockname()[1]
        samples, stop, probe_errors = [], threading.Event(), []

        def observe():
            while not stop.wait(0.08):
                try:
                    with urlopen(f"http://127.0.0.1:{panel_port}/estado", timeout=0.5) as response:
                        samples.append(json.load(response))
                except OSError:
                    continue
                except Exception as exc:
                    probe_errors.append(repr(exc))

        observer = threading.Thread(target=observe, daemon=True)
        observer.start()
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(sim, "routes", moving_routes), \
                    patch.object(launch.getpass, "getpass", return_value=sim.PASSWORD):
                code = launch.main(["--host", "127.0.0.1", "--port", str(server.server_address[1]),
                                    "--user", sim.USER, "--http-port", str(panel_port),
                                    "--log-dir", directory, "--no-browser", "--no-rviz",
                                    "--max-messages", "65", "--print-every", "0"])
                self.assertEqual(code, 0)
                files = list(Path(directory).glob("*.csv"))
                self.assertEqual(len(files), 1)
                with files[0].open() as csvfile:
                    rows = list(csv.DictReader(csvfile))
                self.assertGreater(len(rows), 25)
                delta_fields = [key for key in rows[0] if key.startswith("delta_")]
                maximum = max(abs(float(row[key])) for row in rows for key in delta_fields)
                self.assertLess(maximum, 1e-8)
                self.assertGreater(max(float(r["rws_j1_deg"]) for r in rows) - min(float(r["rws_j1_deg"]) for r in rows), 20)
        finally:
            stop.set()
            observer.join(timeout=2)
        self.assertFalse(probe_errors)
        healthy = [i for i, s in enumerate(samples) if all(k["fresh"] for k in s["stats"].values())]
        stale = [i for i, s in enumerate(samples) if s["error"] and not s["stats"]["rws"]["fresh"]]
        self.assertTrue(healthy, "Nunca hubo RWS + ROS + TF frescos")
        self.assertTrue(stale, "La interrupción de lectura no se detectó")
        self.assertGreater(max(healthy), max(stale), "No se recuperó la cadena tras el fallo")
        self.assertTrue(all(method == "GET" for method, _ in server.log))
        self.assertTrue(all("jointtarget" in path for _, path in server.log))
        print(f"\nEnsayo integrado: {len(rows)} muestras CSV; máximo error {maximum:.3g}°; "
              f"{len(samples)} estados del panel; pérdida y recuperación verificadas.", flush=True)


if __name__ == "__main__":
    unittest.main()
