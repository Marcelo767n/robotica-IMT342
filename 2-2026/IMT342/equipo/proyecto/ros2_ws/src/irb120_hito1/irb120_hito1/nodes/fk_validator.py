"""Comparacion en vivo entre la cadena URDF y la cinematica DH analitica."""

from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

from irb120_hito1.kinematics.dh import (
    JOINT_NAMES,
    forward_kinematics,
    forward_kinematics_tcp,
    position_error_m,
    rotation_error_rad,
)
from irb120_hito1.kinematics.urdf_chain import chain_transform


class ForwardKinematicsValidator(Node):
    """Validate every JointState through two independent kinematic paths.

    RViz and robot_state_publisher consume the same URDF and JointState used by
    this node. Evaluating the expanded URDF directly avoids comparing samples
    from different instants while the robot is moving continuously.
    """

    def __init__(self) -> None:
        super().__init__("irb120_fk_validator")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("target_frame", "tool0")
        self.declare_parameter("position_tolerance_m", 1.0e-6)
        self.declare_parameter("urdf_path", "")

        self._base_frame = str(self.get_parameter("base_frame").value)
        self._target_frame = str(self.get_parameter("target_frame").value)
        self._tolerance = float(self.get_parameter("position_tolerance_m").value)
        self._urdf_path = Path(str(self.get_parameter("urdf_path").value))
        if self._tolerance <= 0.0:
            raise ValueError("position_tolerance_m debe ser positiva.")
        if self._target_frame not in {"tool0", "tcp_link"}:
            raise ValueError("target_frame debe ser tool0 o tcp_link.")
        if not self._urdf_path.is_file():
            raise FileNotFoundError(f"No se encontro el URDF expandido: {self._urdf_path}")

        self._last_state: bool | None = None
        self._report_counter = 0
        self.create_subscription(JointState, "/joint_states", self._joint_callback, 20)
        self._error_publisher = self.create_publisher(Float64, "/irb120/fk_position_error_m", 10)

    def _joint_callback(self, message: JointState) -> None:
        received = dict(zip(message.name, message.position))
        if any(name not in received for name in JOINT_NAMES):
            return
        joint_vector = [float(received[name]) for name in JOINT_NAMES]
        analytic = (
            forward_kinematics_tcp(joint_vector)
            if self._target_frame == "tcp_link"
            else forward_kinematics(joint_vector)
        )
        joint_map = dict(zip(JOINT_NAMES, joint_vector, strict=True))
        urdf_matrix = chain_transform(
            self._urdf_path,
            joint_map,
            base_link=self._base_frame,
            target_link=self._target_frame,
        )
        error_m = position_error_m(analytic, urdf_matrix)
        orientation_error_rad = rotation_error_rad(analytic, urdf_matrix)
        passed = error_m < self._tolerance

        error_message = Float64()
        error_message.data = error_m
        self._error_publisher.publish(error_message)

        self._report_counter += 1
        if passed != self._last_state or self._report_counter >= 20:
            status = "APROBADO" if passed else "FUERA DE TOLERANCIA"
            self.get_logger().info(
                f"{status} | DH vs URDF | frame={self._target_frame} "
                f"| error_pos={error_m:.3e} m | error_rot={orientation_error_rad:.3e} rad "
                f"| limite={self._tolerance:.1e} m"
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
