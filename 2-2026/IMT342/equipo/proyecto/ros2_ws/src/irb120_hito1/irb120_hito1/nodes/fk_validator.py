"""Comparacion en vivo entre TF/RViz y la cinematica DH analitica."""

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from tf2_ros import Buffer, TransformException, TransformListener

from irb120_hito1.kinematics.dh import (
    JOINT_NAMES,
    forward_kinematics,
    forward_kinematics_tcp,
    position_error_m,
    rotation_error_rad,
)


def _transform_matrix(transform) -> np.ndarray:
    translation = transform.transform.translation
    quaternion = transform.transform.rotation
    x, y, z, w = quaternion.x, quaternion.y, quaternion.z, quaternion.w
    norm = np.linalg.norm([x, y, z, w])
    if norm == 0.0:
        raise ValueError("TF entrego un cuaternion nulo.")
    x, y, z, w = np.asarray([x, y, z, w], dtype=float) / norm

    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = np.array(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ]
    )
    matrix[:3, 3] = [translation.x, translation.y, translation.z]
    return matrix


class ForwardKinematicsValidator(Node):
    """Validate robot_state_publisher TF against the independent DH model."""

    def __init__(self) -> None:
        super().__init__("irb120_fk_validator")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("target_frame", "tool0")
        self.declare_parameter("position_tolerance_m", 1.0e-6)

        self._base_frame = str(self.get_parameter("base_frame").value)
        self._target_frame = str(self.get_parameter("target_frame").value)
        self._tolerance = float(self.get_parameter("position_tolerance_m").value)
        if self._tolerance <= 0.0:
            raise ValueError("position_tolerance_m debe ser positiva.")
        if self._target_frame not in {"tool0", "tcp_link"}:
            raise ValueError("target_frame debe ser tool0 o tcp_link.")

        self._joints: dict[str, float] = {}
        self._last_state: bool | None = None
        self._report_counter = 0
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self.create_subscription(JointState, "/joint_states", self._joint_callback, 20)
        self._error_publisher = self.create_publisher(Float64, "/irb120/fk_position_error_m", 10)
        self.create_timer(0.25, self._validate)

    def _joint_callback(self, message: JointState) -> None:
        for name, position in zip(message.name, message.position):
            if name in JOINT_NAMES:
                self._joints[name] = float(position)

    def _validate(self) -> None:
        if any(name not in self._joints for name in JOINT_NAMES):
            return
        try:
            tf_message = self._tf_buffer.lookup_transform(
                self._base_frame,
                self._target_frame,
                Time(),
            )
        except TransformException as error:
            self.get_logger().debug(f"TF aun no disponible: {error}")
            return

        joint_vector = [self._joints[name] for name in JOINT_NAMES]
        analytic = (
            forward_kinematics_tcp(joint_vector)
            if self._target_frame == "tcp_link"
            else forward_kinematics(joint_vector)
        )
        tf_matrix = _transform_matrix(tf_message)
        error_m = position_error_m(analytic, tf_matrix)
        orientation_error_rad = rotation_error_rad(analytic, tf_matrix)
        passed = error_m < self._tolerance

        error_message = Float64()
        error_message.data = error_m
        self._error_publisher.publish(error_message)

        self._report_counter += 1
        if passed != self._last_state or self._report_counter >= 20:
            status = "APROBADO" if passed else "FUERA DE TOLERANCIA"
            self.get_logger().info(
                f"{status} | frame={self._target_frame} | error_pos={error_m:.3e} m "
                f"| error_rot={orientation_error_rad:.3e} rad | limite={self._tolerance:.1e} m"
            )
            self._last_state = passed
            self._report_counter = 0


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ForwardKinematicsValidator()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
