#!/usr/bin/env python3
"""Monitor local de RWS, JointState y TF. Solo suscribe ROS y sirve HTTP en 127.0.0.1.

Las columnas se comparan por la MISMA marca de tiempo. El ángulo del gemelo se
recupera de su TF relativo y del origin/axis del URDF, no se copia de JointState.
"""
import argparse
from collections import OrderedDict, deque
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
import xml.etree.ElementTree as ET

JOINT_NAMES = tuple(f"joint_{i}" for i in range(1, 7))
from irb120_conexion.rutas import PACKAGE
DEFAULT_URDF = PACKAGE / "urdf/irb120.urdf"


def quaternion_product(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return (w*X + x*W + y*Z - z*Y, w*Y - x*Z + y*W + z*X,
            w*Z + x*Y - y*X + z*W, w*W - x*X - y*Y - z*Z)


def origin_quaternion(rpy):
    r, p, y = (v / 2 for v in rpy)
    sr, cr, sp, cp, sy, cy = math.sin(r), math.cos(r), math.sin(p), math.cos(p), math.sin(y), math.cos(y)
    return (sr*cp*cy - cr*sp*sy, cr*sp*cy + sr*cp*sy,
            cr*cp*sy - sr*sp*cy, cr*cp*cy + sr*sp*sy)


def load_joint_geometry(path):
    joints = {j.attrib["name"]: j for j in ET.parse(path).getroot().findall("joint")}
    result = {}
    for name in JOINT_NAMES:
        joint = joints[name]
        origin, axis = joint.find("origin"), joint.find("axis")
        rpy = [float(v) for v in (origin.get("rpy", "0 0 0") if origin is not None else "0 0 0").split()]
        vector = [float(v) for v in (axis.get("xyz", "1 0 0") if axis is not None else "1 0 0").split()]
        norm = math.sqrt(sum(v*v for v in vector))
        if norm == 0 or len(vector) != 3 or len(rpy) != 3:
            raise ValueError(f"Origin/axis inválido para {name}")
        result[name] = {"parent": joint.find("parent").get("link"),
                        "child": joint.find("child").get("link"),
                        "origin": origin_quaternion(rpy), "axis": tuple(v/norm for v in vector)}
    return result


def angle_from_tf(geometry, quaternion):
    if len(quaternion) != 4 or not all(math.isfinite(v) for v in quaternion):
        raise ValueError("Cuaternión TF inválido")
    norm = math.sqrt(sum(v*v for v in quaternion))
    if norm < 1e-12:
        raise ValueError("Cuaternión TF nulo")
    q = tuple(v/norm for v in quaternion)
    x, y, z, w = geometry["origin"]
    relative = quaternion_product((-x, -y, -z, w), q)
    along = sum(v*a for v, a in zip(relative[:3], geometry["axis"]))
    residual = math.sqrt(sum((v - along*a)**2 for v, a in zip(relative[:3], geometry["axis"])))
    if residual > 1e-5:
        raise ValueError("TF no corresponde al eje/origin del URDF")
    return math.remainder(math.degrees(2*math.atan2(along, relative[3])), 360.0)


def ordered_degrees(names, positions):
    if len(names) != len(positions) or len(set(names)) != len(names):
        raise ValueError("JointState incompleto o con nombres duplicados")
    values = dict(zip(names, positions))
    q = [math.degrees(values[name]) for name in JOINT_NAMES]
    if not all(math.isfinite(v) for v in q):
        raise ValueError("JointState no finito")
    return q


class MonitorState:
    """Estado acotado; todas las llamadas se realizan en el hilo ROS salvo snapshot()."""

    def __init__(self, geometry, stale_seconds=1.0, writer=None):
        self.geometry, self.stale_seconds, self.writer = geometry, stale_seconds, writer
        self.samples = OrderedDict()
        self.times = {key: deque(maxlen=100) for key in ("rws", "ros", "tf")}
        self.counts = dict.fromkeys(self.times, 0)
        self.last_error = None
        self.invalid_messages = 0
        self.lock = threading.RLock()

    def _sample(self, stamp):
        key = (int(stamp["sec"]), int(stamp["nanosec"]))
        if key[0] < 0 or not 0 <= key[1] < 1_000_000_000:
            raise ValueError("Marca de tiempo inválida")
        if key not in self.samples:
            self.samples[key] = {"stamp": key, "tf_parts": {}, "logged": False}
            if len(self.samples) > 120:
                self.samples.popitem(last=False)
        return self.samples[key]

    def _received(self, sample, kind, now):
        if kind not in sample:
            self.times[kind].append(now)
            self.counts[kind] += 1
        sample[kind + "_at"] = now

    def raw(self, event, now):
        with self.lock:
            if event.get("ok") is not True:
                self.last_error = str(event.get("error", "Error RWS"))[:400]
                return
            axes = event["axes_deg"]
            if len(axes) != 6 or not all(math.isfinite(v) for v in axes):
                raise ValueError("RWS necesita seis ejes finitos")
            request_ms = float(event["request_ms"])
            if not math.isfinite(request_ms) or request_ms < 0:
                raise ValueError("Duración RWS inválida")
            sample = self._sample(event["stamp"])
            self._received(sample, "rws", now)
            sample.update(rws=list(axes), request_ms=request_ms, seq=event["seq"])
            sample["source"] = event.get("source", "")
            sample["mechunit"] = event.get("mechunit", "")
            sample["ignore_joint_state"] = bool(event.get("ignore_joint_state", False))
            self.last_error = None
            self._record(sample)

    def joints(self, stamp, names, positions, now):
        values = ordered_degrees(names, positions)
        with self.lock:
            sample = self._sample(stamp)
            self._received(sample, "ros", now)
            sample["ros"] = values
            self._record(sample)

    def transforms(self, transforms, now):
        with self.lock:
            touched = set()
            for stamp, parent, child, quaternion in transforms:
                for name, geometry in self.geometry.items():
                    if (parent.lstrip("/"), child.lstrip("/")) != (geometry["parent"], geometry["child"]):
                        continue
                    angle = angle_from_tf(geometry, quaternion)
                    sample = self._sample(stamp)
                    sample["tf_parts"][name] = angle
                    touched.add(sample["stamp"])
            for key in touched:
                sample = self.samples[key]
                if len(sample["tf_parts"]) == 6:
                    self._received(sample, "tf", now)
                    sample["tf"] = [sample["tf_parts"][name] for name in JOINT_NAMES]
                    self._record(sample)

    @staticmethod
    def comparison(sample):
        raw, ros, tf = sample.get("rws"), sample.get("ros"), sample.get("tf")
        # TF expresa orientación: para J6 se elige la vuelta equivalente más
        # próxima al JointState; TF por sí solo no puede contar vueltas completas.
        shown_tf = [r + math.remainder(t-r, 360.0) for t, r in zip(tf, ros)] if tf and ros else tf
        return {"rws": raw, "ros": ros, "tf": shown_tf,
                "delta_ros": [r-a for r, a in zip(ros, raw)] if raw and ros else None,
                "delta_tf": [math.remainder(t-r, 360.0) for t, r in zip(tf, ros)] if tf and ros else None}

    def _record(self, sample):
        if sample["logged"] or not all(k in sample for k in ("rws", "ros", "tf")):
            return
        sample["logged"] = True
        if self.writer:
            data = self.comparison(sample)
            self.writer([datetime.now(timezone.utc).isoformat(), *sample["stamp"], sample["seq"], sample["request_ms"],
                         *data["rws"], *data["ros"], *data["tf"], *data["delta_ros"], *data["delta_tf"],
                         sample.get("ignore_joint_state", False)])

    def snapshot(self, now):
        with self.lock:
            latest = next((s for s in reversed(list(self.samples.values())) if "rws" in s), None)
            complete = next((s for s in reversed(list(self.samples.values()))
                             if all(k in s for k in ("rws", "ros", "tf"))), None)
            # Preferir una muestra completa reciente. Si TF/ROS se detienen,
            # mostrar la lectura RWS nueva y columnas faltantes como pendientes.
            sample = complete if complete and (latest is None or latest["rws_at"] - complete["rws_at"] <= 0.35) else latest
            stats = {}
            for key, times in self.times.items():
                age = max(0.0, now-times[-1]) if times else None
                active = [t for t in times if now-t <= 3.0]
                hz = (len(active)-1)/(active[-1]-active[0]) if len(active) > 1 and active[-1] > active[0] else 0.0
                stats[key] = {"age_s": age, "hz": hz, "count": self.counts[key],
                              "fresh": age is not None and age < self.stale_seconds}
            data = self.comparison(sample) if sample else dict.fromkeys(("rws", "ros", "tf", "delta_ros", "delta_tf"))
            return {"stats": stats, "sample": data,
                    "seq": sample.get("seq") if sample else None,
                    "sample_age_s": max(0.0, now-sample["rws_at"]) if sample else None,
                    "request_ms": latest.get("request_ms") if latest else None,
                    "stamp": list(sample["stamp"]) if sample else None,
                    "error": self.last_error, "invalid_messages": self.invalid_messages,
                    "source": latest.get("source", "") if latest else "",
                    "mechunit": latest.get("mechunit", "") if latest else "",
                    "ignore_joint_state": latest.get("ignore_joint_state", False) if latest else False,
                    "stale_seconds": self.stale_seconds}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="/irb120/real/joint_states")
    parser.add_argument("--tf-topic", default="/irb120/real/tf")
    parser.add_argument("--urdf", type=Path, default=DEFAULT_URDF)
    parser.add_argument("--http-port", type=int, default=8765)
    parser.add_argument("--stale-seconds", type=float, default=1.0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.http_port <= 65535 or not math.isfinite(args.stale_seconds) or args.stale_seconds <= 0:
        parser.error("Puerto o umbral de antigüedad inválido")

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import JointState
    from std_msgs.msg import String
    from tf2_msgs.msg import TFMessage

    logfile = None
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        logfile = args.csv.open("x", newline="", encoding="utf-8")
        writer = csv.writer(logfile)
        writer.writerow(["received_at_utc", "stamp_sec", "stamp_nanosec", "seq", "request_ms"] +
                        [f"{kind}_j{i}_deg" for kind in ("rws", "ros", "tf", "delta_ros", "delta_tf") for i in range(1, 7)] +
                        ["ignore_joint_state"])
        def write_row(row):
            writer.writerow(row)
            logfile.flush()
    state = MonitorState(load_joint_geometry(args.urdf), args.stale_seconds, write_row if logfile else None)
    page = Path(__file__).with_name("panel.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/":
                body, mime = page, "text/html; charset=utf-8"
            elif self.path == "/estado":
                body, mime = json.dumps(state.snapshot(time.monotonic()), allow_nan=False).encode(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", args.http_port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    rclpy.init()
    node = Node("irb120_monitor_comunicacion")

    def guarded(callback):
        def receive(msg):
            try:
                callback(msg)
            except (ValueError, KeyError, TypeError, OverflowError) as exc:
                with state.lock:
                    state.invalid_messages += 1
                node.get_logger().warning(f"Muestra descartada: {exc}")
        return receive

    def stamp(s):
        return {"sec": s.sec, "nanosec": s.nanosec}

    node.create_subscription(String, args.topic.rstrip("/") + "/rws",
                             guarded(lambda m: state.raw(json.loads(m.data), time.monotonic())), 20)
    node.create_subscription(JointState, args.topic,
                             guarded(lambda m: state.joints(stamp(m.header.stamp), m.name, m.position, time.monotonic())), 20)
    node.create_subscription(TFMessage, args.tf_topic, guarded(lambda m: state.transforms([
        (stamp(t.header.stamp), t.header.frame_id, t.child_frame_id,
         (t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w))
        for t in m.transforms], time.monotonic())), qos_profile_sensor_data)
    url = f"http://127.0.0.1:{args.http_port}/"
    print(f"Panel de comunicación: {url}", flush=True)
    if not args.no_browser:
        # Abrir el navegador no debe bloquear la recepción ROS.
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
        if logfile:
            logfile.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
