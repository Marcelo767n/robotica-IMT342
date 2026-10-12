"""Publica una pose objetivo del TCP: ros2 run irb120_hito2 send_target X Y Z [R P Y deg]."""

import argparse
from math import radians

import rclpy
from geometry_msgs.msg import PoseStamped

from irb120_hito2.kinematics.transforms import matrix_to_quaternion, rpy_to_matrix


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("x", type=float, help="metros en base_link")
    parser.add_argument("y", type=float)
    parser.add_argument("z", type=float)
    parser.add_argument(
        "rpy_deg", nargs="*", type=float, default=[0.0, 180.0, 0.0],
        help="roll pitch yaw en grados (por defecto 0 180 0: pinza hacia abajo)",
    )
    parsed = parser.parse_args(rclpy.utilities.remove_ros_args(args)[1:] if args else None)
    if len(parsed.rpy_deg) != 3:
        parser.error("rpy_deg requiere exactamente tres valores o ninguno")

    rclpy.init(args=args)
    node = rclpy.create_node("irb120_send_target")
    publisher = node.create_publisher(PoseStamped, "/irb120/target_pose", 10)
    message = PoseStamped()
    message.header.frame_id = "base_link"
    message.header.stamp = node.get_clock().now().to_msg()
    message.pose.position.x, message.pose.position.y, message.pose.position.z = (
        parsed.x, parsed.y, parsed.z,
    )
    qx, qy, qz, qw = matrix_to_quaternion(rpy_to_matrix(*(radians(v) for v in parsed.rpy_deg)))
    message.pose.orientation.x, message.pose.orientation.y = qx, qy
    message.pose.orientation.z, message.pose.orientation.w = qz, qw
    for _ in range(20):  # esperar al suscriptor y publicar una vez
        if publisher.get_subscription_count() > 0:
            break
        rclpy.spin_once(node, timeout_sec=0.1)
    publisher.publish(message)
    rclpy.spin_once(node, timeout_sec=0.2)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
