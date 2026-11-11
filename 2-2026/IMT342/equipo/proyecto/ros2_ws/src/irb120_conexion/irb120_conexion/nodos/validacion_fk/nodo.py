#!/usr/bin/env python3
"""Nodo FK: recibe muestras ABB, evalúa FK propia, publica resultados y sirve panel local."""
import argparse
import csv
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import signal
import threading
import time
import webbrowser
from irb120_conexion.nodos.validacion_fk.comparacion import compare, model_identity, POSITION_TOL_MM, ORIENTATION_TOL_RAD


def format_comparison(result):
    """Expone en la terminal la cadena que se calculó para una misma muestra."""
    title = f"\n[FK muestra {result.get('seq', '—')}] {result['status']}"
    if 'q_input_rad' not in result:
        return title + '\n  ' + result['reason']
    def values(items, places=9):
        return '[' + ', '.join(f'{v:.{places}f}' for v in items) + ']'
    return '\n'.join([
        title,
        '  1. Ángulos ABB [deg]: ' + values(result['q_before_deg'], 6),
        '     Entrada FK [rad]: ' + values(result['q_input_rad']),
        '  2. Nuestra FK XYZ [mm]: ' + values(result['own_xyz_mm']),
        '     Nuestra FK RPY [deg]: ' + values(result['own_rpy_deg'], 6),
        '  3. Pose ABB   XYZ [mm]: ' + values(result['controller_xyz_mm']),
        '     Pose ABB   RPY [deg]: ' + values(result['controller_rpy_deg'], 6),
        '  4. ΔXYZ propia − ABB [mm]: ' + values(result['delta_xyz_mm']),
        f"     Error posición: {result['position_error_mm']:.9g} mm · "
        f"orientación: {result['orientation_error_deg']:.9g}° ({result['orientation_error_rad']:.9g} rad)",
        '     ' + result['reason'],
    ])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-topic", default="/irb120/real/joint_states/fk_sample")
    parser.add_argument("--http-port", type=int, default=8766)
    parser.add_argument("--position-tol-mm", type=float, default=POSITION_TOL_MM)
    parser.add_argument("--orientation-tol-rad", type=float, default=ORIENTATION_TOL_RAD)
    parser.add_argument("--motion-threshold-deg", type=float, default=0.01)
    parser.add_argument("--max-window-ms", type=float, default=500)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--print-every", type=float, default=1.0,
                        help="Segundos entre cálculos mostrados en terminal; 0 desactiva la impresión")
    parser.add_argument("--node-name", default="irb120_validacion_fk", help=argparse.SUPPRESS)
    parser.add_argument("--log-prefix", type=Path, required=True)
    args = parser.parse_args(argv)
    limits = [args.position_tol_mm, args.orientation_tol_rad, args.motion_threshold_deg, args.max_window_ms]
    if not all(math.isfinite(v) and v > 0 for v in limits) or not 1 <= args.http_port <= 65535:
        parser.error("Tolerancias, ventana o puerto inválidos")
    if not math.isfinite(args.print_every) or args.print_every < 0:
        parser.error("--print-every debe ser finito y no negativo")
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    args.log_prefix.parent.mkdir(parents=True, exist_ok=True)
    details_file = args.log_prefix.with_suffix(".jsonl").open("x", encoding="utf-8")
    csv_file = args.log_prefix.with_suffix(".csv").open("x", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow(["received_at_utc", "seq", "status", "accepted", "position_error_mm", "orientation_error_rad",
                     "position_tolerance_mm", "orientation_tolerance_rad", "window_ms", "ignore_joint_state"] +
                    [f"q_j{i}_deg" for i in range(1, 7)] +
                    [f"{prefix}_{axis}_mm" for prefix in ("own", "abb", "delta") for axis in "xyz"])
    identity = model_identity()
    state = {"result": None, "received": None, "count": 0, "pass": 0, "fail": 0, "skipped": 0}
    lock = threading.Lock()
    page = Path(__file__).with_name("panel.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/":
                body, mime = page, "text/html; charset=utf-8"
            elif self.path == "/estado":
                with lock:
                    payload = {**state, "age_s": None if state["received"] is None else time.monotonic()-state["received"],
                               "model": identity, "position_tolerance_mm": args.position_tol_mm,
                               "orientation_tolerance_rad": args.orientation_tol_rad}
                body, mime = json.dumps(payload, allow_nan=False).encode(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", args.http_port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    rclpy.init()
    node = Node(args.node_name)
    publisher = node.create_publisher(String, args.sample_topic + "/resultado", 10)
    last_print = 0.0

    def receive(message):
        nonlocal last_print
        try:
            sample = json.loads(message.data)
            result = compare(sample, args.position_tol_mm, args.orientation_tol_rad,
                             args.motion_threshold_deg, args.max_window_ms)
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            sample = None
            result = {"status": "LECTURA_INVALIDA", "reason": str(exc), "accepted": None}
        observed = datetime.now(timezone.utc).isoformat()
        with lock:
            state.update(result=result, received=time.monotonic(), count=state["count"]+1)
            key = "pass" if result["accepted"] is True else "fail" if result["accepted"] is False else "skipped"
            state[key] += 1
        details_file.write(json.dumps({"received_at_utc": observed, "sample": sample, "result": result,
                                       "model": identity}, ensure_ascii=False, allow_nan=False) + "\n")
        details_file.flush()
        writer.writerow([observed, result.get("seq"), result["status"], result["accepted"],
                         result.get("position_error_mm"), result.get("orientation_error_rad"),
                         args.position_tol_mm, args.orientation_tol_rad, result.get("window_ms"),
                         result.get("ignore_joint_state")] + result.get("q_before_deg", [None]*6) +
                        result.get("own_xyz_mm", [None]*3) + result.get("controller_xyz_mm", [None]*3) +
                        result.get("delta_xyz_mm", [None]*3))
        csv_file.flush()
        now = time.monotonic()
        if args.print_every > 0 and now-last_print >= args.print_every:
            last_print = now
            print(format_comparison(result), flush=True)
        response = String()
        response.data = json.dumps(result, allow_nan=False)
        publisher.publish(response)

    node.create_subscription(String, args.sample_topic, receive, 20)
    url = f"http://127.0.0.1:{args.http_port}/"
    print(f"Panel FK: {url}\nRegistro FK: {args.log_prefix}.csv / .jsonl", flush=True)
    if not args.no_browser:
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        server.shutdown()
        server.server_close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        details_file.close()
        csv_file.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
