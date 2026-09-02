"""Fuente reproducible de estados articulares para la demostracion en RViz."""

from math import pi

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

from irb120_hito1.kinematics.dh import JOINT_NAMES


def _degrees(value: float) -> float:
    return value * pi / 180.0


# Rangos oficiales ABB IRB 120-3/0.6, convertidos de grados a radianes.
JOINT_LIMITS_RAD = (
    (_degrees(-165.0), _degrees(165.0)),
    (_degrees(-110.0), _degrees(110.0)),
    (_degrees(-110.0), _degrees(70.0)),
    (_degrees(-160.0), _degrees(160.0)),
    (_degrees(-120.0), _degrees(120.0)),
    (_degrees(-400.0), _degrees(400.0)),
)


class JointStateSource(Node):
    """Publish six ABB joints plus the two symmetric gripper fingers.

    A command can be sent in degrees to ``/irb120/joint_commands_deg`` as a
    Float64MultiArray with six values. A seventh optional value controls the
    opening of each gripper finger in metres (0 to 0.015 m).
    """

    def __init__(self) -> None:
        super().__init__("irb120_joint_state_source")
        self.declare_parameter("initial_positions_deg", [0.0] * 6)
        self.declare_parameter("gripper_opening_m", 0.0)
        self.declare_parameter("publish_rate_hz", 20.0)

        degrees = list(self.get_parameter("initial_positions_deg").value)
        if len(degrees) != 6:
            raise ValueError("initial_positions_deg debe contener exactamente 6 valores.")
        self._positions = self._clamp([_degrees(float(value)) for value in degrees])
        self._gripper_opening = self._clamp_gripper(
            float(self.get_parameter("gripper_opening_m").value)
        )

        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        if rate_hz <= 0.0:
            raise ValueError("publish_rate_hz debe ser positivo.")

        self._publisher = self.create_publisher(JointState, "/joint_states", 10)
        self.create_subscription(
            Float64MultiArray,
            "/irb120/joint_commands_deg",
            self._command_callback,
            10,
        )
        self.create_timer(1.0 / rate_hz, self._publish)
        self.get_logger().info(
            "Fuente articular lista. Comandos: /irb120/joint_commands_deg (grados)."
        )

    @staticmethod
    def _clamp(values: list[float]) -> list[float]:
        return [
            min(max(value, lower), upper)
            for value, (lower, upper) in zip(values, JOINT_LIMITS_RAD, strict=True)
        ]

    @staticmethod
    def _clamp_gripper(value: float) -> float:
        return min(max(value, 0.0), 0.015)

    def _command_callback(self, message: Float64MultiArray) -> None:
        if len(message.data) not in {6, 7}:
            self.get_logger().error("El comando debe contener 6 angulos y, opcionalmente, 1 apertura.")
            return
        requested = [_degrees(float(value)) for value in message.data[:6]]
        clamped = self._clamp(requested)
        if clamped != requested:
            self.get_logger().warning("Uno o mas angulos fueron limitados al rango oficial del robot.")
        self._positions = clamped
        if len(message.data) == 7:
            self._gripper_opening = self._clamp_gripper(float(message.data[6]))

    def _publish(self) -> None:
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.name = [*JOINT_NAMES, "gripper_left_joint", "gripper_right_joint"]
        message.position = [
            *self._positions,
            self._gripper_opening,
            self._gripper_opening,
        ]
        self._publisher.publish(message)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = JointStateSource()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
