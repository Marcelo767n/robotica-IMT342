#!/usr/bin/env python3
"""Escucha un tema sensor_msgs/JointState y muestra los ejes en grados (solo suscribe; no publica nada).

Sirve para comprobar el lado ROS del puente sin usar la CLI `ros2`, que no funciona con el Python 3.14 de esta PC.

    source /opt/ros/jazzy/setup.bash
    ~/ros_py312/bin/python scripts/escuchar_joint_states.py --seconds 10
"""
import argparse
import math
import sys
import time


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", default="/irb120/real/joint_states")
    parser.add_argument("--seconds", type=float, default=10.0, help="Duracion de la escucha")
    parser.add_argument("--print-every", type=float, default=1.0, help="Segundos entre impresiones")
    args = parser.parse_args(argv)
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState

    rclpy.init()
    node = Node("escuchar_joint_states")
    got = []
    node.create_subscription(JointState, args.topic, lambda m: got.append((time.monotonic(), m)), 10)
    start = time.monotonic()
    last = 0.0
    while time.monotonic() - start < args.seconds and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.1)
        if got and time.monotonic() - last >= args.print_every:
            last = time.monotonic()
            print("ejes [deg]: " + "  ".join(f"{math.degrees(p):9.3f}" for p in got[-1][1].position), flush=True)
    print(f"mensajes recibidos en {args.topic}: {len(got)}")
    if len(got) >= 2:
        print(f"frecuencia observada: {(len(got) - 1) / (got[-1][0] - got[0][0]):.2f} Hz")
    node.destroy_node()
    rclpy.shutdown()
    return 0 if got else 2


if __name__ == "__main__":
    sys.exit(main())
