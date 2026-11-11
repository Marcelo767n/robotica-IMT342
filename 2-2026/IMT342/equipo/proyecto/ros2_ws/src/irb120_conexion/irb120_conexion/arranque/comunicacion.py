#!/usr/bin/env python3
"""Prueba de lectura ABB → ROS → RViz con panel de ángulos y registro CSV.

Ejecutar mediante scripts/prueba_comunicacion.sh para cargar Jazzy y Python 3.12.
"""
import argparse
from datetime import datetime, timezone
import getpass
import math
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile

from irb120_conexion.nodos.lectura_articular import puente_rws as bridge
from irb120_conexion.modelo.preparar import prepare
from irb120_conexion.rutas import DEFAULT_OUTPUT, SOURCE_PACKAGE

HERE = Path(__file__).resolve().parent


class ChildStopped(RuntimeError):
    def __init__(self, name, code):
        super().__init__(f"{name} terminó (código {code}). Se detiene toda la prueba.")
        self.code = code


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="IPv4 del ABB; en el laboratorio: 192.168.125.1")
    parser.add_argument("--user", required=True, help="Usuario UAS; contraseña solicitada en la terminal")
    parser.add_argument("--rate", type=float, default=10.0, help="Consultas por segundo, máximo 10 (defecto 10)")
    parser.add_argument("--port", type=int, default=80, help="Puerto HTTP alternativo solo para simulación en loopback")
    parser.add_argument("--mechunit", default="ROB_1")
    parser.add_argument("--ignore-joint-state", action="store_true",
                        help="Consulta jointtarget con ignore=1; se indica en el panel y en el CSV")
    parser.add_argument("--topic", default=bridge.DEFAULT_TOPIC)
    parser.add_argument("--http-port", type=int, default=8765, help="Puerto del panel local")
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_OUTPUT / "prueba_comunicacion")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-rviz", action="store_true", help="Solo para ensayo de la cadena sin ventana RViz")
    parser.add_argument("--max-messages", type=int, default=0, help="Terminar tras N muestras; 0 = hasta Ctrl+C")
    parser.add_argument("--print-every", type=float, default=1.0)
    parser.add_argument("--validate-fk", action="store_true", help="Abre también la comparación FK frente a robtarget ABB")
    parser.add_argument("--fk-http-port", type=int, default=8766)
    parser.add_argument("--position-tol-mm", type=float, default=0.001)
    parser.add_argument("--orientation-tol-rad", type=float, default=1e-6)
    parser.add_argument("--motion-threshold-deg", type=float, default=0.01)
    parser.add_argument("--max-window-ms", type=float, default=500)
    args = parser.parse_args(argv)
    try:
        bridge.build_base_url(args.host, args.port)
    except ValueError as exc:
        parser.error(str(exc))
    if not math.isfinite(args.rate) or not 0 < args.rate <= bridge.MAX_RATE_HZ:
        parser.error("--rate debe ser mayor que cero y como máximo 10 Hz")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.mechunit):
        parser.error("Unidad mecánica inválida")
    if not re.fullmatch(r"/(?:[A-Za-z_][A-Za-z0-9_]*)(?:/[A-Za-z_][A-Za-z0-9_]*)*", args.topic):
        parser.error("--topic debe ser un nombre ROS absoluto, sin barra final")
    if not 1 <= args.http_port <= 65535 or args.max_messages < 0:
        parser.error("Puerto del panel o número de muestras inválido")
    if not math.isfinite(args.print_every) or args.print_every < 0:
        parser.error("--print-every debe ser finito y no negativo")
    if not 1 <= args.fk_http_port <= 65535 or (args.validate_fk and args.fk_http_port == args.http_port):
        parser.error("Los puertos de los paneles deben ser válidos y distintos")
    if not all(math.isfinite(v) and v > 0 for v in (args.position_tol_mm, args.orientation_tol_rad,
                                                   args.motion_threshold_deg, args.max_window_ms)):
        parser.error("Los límites de validación deben ser positivos y finitos")
    args.log_dir = args.log_dir.expanduser().resolve()
    return args


def main(argv=None):
    args = parse_args(argv)
    args.wait_for_monitor = True
    try:
        import rclpy  # noqa: F401: verificar dependencias antes de pedir contraseña
        from sensor_msgs.msg import JointState  # noqa: F401
        from std_msgs.msg import String  # noqa: F401
        from tf2_msgs.msg import TFMessage  # noqa: F401
    except ImportError as exc:
        print(f"Entorno ROS incompleto: {exc}. Usa scripts/prueba_comunicacion.sh.", file=sys.stderr)
        return 2
    rsp = Path("/opt/ros/jazzy/lib/robot_state_publisher/robot_state_publisher")
    if not rsp.exists() or (not args.no_rviz and shutil.which("rviz2") is None):
        print("Falta robot_state_publisher o rviz2 en el entorno Jazzy.", file=sys.stderr)
        return 2
    args.log_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.log_dir / ("comunicacion_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%fZ") + ".csv")
    try:
        password = getpass.getpass("Contraseña UAS (solo para lectura): ")
    except (KeyboardInterrupt, EOFError):
        print("\nPrueba cancelada.")
        return 130
    children = []

    def health_check():
        for name, child in children:
            if child.poll() is not None:
                raise ChildStopped(name, child.returncode)

    def stop(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        with tempfile.TemporaryDirectory(prefix="irb120_comunicacion_") as directory:
            out = prepare(directory)
            scope = args.topic.rsplit("/", 1)[0] or "/irb120/real"
            tf_topic = scope + "/tf"
            tf_static_topic = scope + "/tf_static"
            description_topic = scope + "/robot_description"
            remaps = ["--ros-args", "-r", f"/tf:={tf_topic}", "-r", f"/tf_static:={tf_static_topic}",
                      "-r", f"/robot_description:={description_topic}"]
            commands = [("robot_state_publisher", [str(rsp), "--ros-args", "--params-file",
                         str(out / "robot_state_publisher.yaml"), "-r", f"joint_states:={args.topic}",
                         "-p", "publish_frequency:=20.0", *remaps[1:]]),
                        ("monitor", [sys.executable, "-m", "irb120_conexion.nodos.monitor_comunicacion.monitor",
                         "--topic", args.topic, "--tf-topic", tf_topic,
                         "--http-port", str(args.http_port), "--csv", str(csv_path)])]
            if args.no_browser:
                commands[1][1].append("--no-browser")
            if not args.no_rviz:
                commands.append(("RViz", ["rviz2", "-d", str(out / "gemelo.rviz"), *remaps]))
            if args.validate_fk:
                fk_command = [sys.executable, "-m", "irb120_conexion.nodos.validacion_fk.nodo",
                              "--sample-topic", args.topic + "/fk_sample", "--http-port", str(args.fk_http_port),
                              "--position-tol-mm", str(args.position_tol_mm),
                              "--orientation-tol-rad", str(args.orientation_tol_rad),
                              "--motion-threshold-deg", str(args.motion_threshold_deg),
                              "--max-window-ms", str(args.max_window_ms),
                              "--print-every", str(args.print_every),
                              "--log-prefix", str(csv_path.with_name(csv_path.stem + "_fk"))]
                if args.no_browser:
                    fk_command.append("--no-browser")
                commands.append(("validación FK", fk_command))
            for name, command in commands:
                import os
                environment = os.environ.copy()
                environment["PYTHONPATH"] = str(SOURCE_PACKAGE.parent) + os.pathsep + environment.get("PYTHONPATH", "")
                children.append((name, subprocess.Popen(command, env=environment)))
            print(f"\nPanel: http://127.0.0.1:{args.http_port}/\nRegistro: {csv_path}\n"
                  "Solo lectura. Mueve el brazo con el FlexPendant bajo el protocolo del laboratorio.\n"
                  "Ctrl+C detiene RViz, monitor y puente.\n", flush=True)
            if args.validate_fk:
                print(f"Validación FK: http://127.0.0.1:{args.fk_http_port}/ · tool0 / wobj0 / Base\n"
                      f"Criterio estricto propuesto: {args.position_tol_mm} mm, {args.orientation_tol_rad} rad.\n"
                      "Dejar el brazo quieto para evaluar cada postura.", flush=True)
            bridge.run(args, password, health_check=health_check)
    except KeyboardInterrupt:
        pass
    except ChildStopped as exc:
        print(str(exc), flush=True)
        return 0 if exc.code == 0 else 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"No se pudo iniciar la prueba: {exc}", file=sys.stderr)
        return 2
    finally:
        for _, child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for _, child in reversed(children):
            try:
                child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        print(f"Prueba detenida. Registro de muestras comparadas: {csv_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
