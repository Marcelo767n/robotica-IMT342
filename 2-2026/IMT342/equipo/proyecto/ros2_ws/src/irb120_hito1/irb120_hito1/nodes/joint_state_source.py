"""Fuente reproducible de estados articulares para la demostracion en RViz."""

from math import pi

import rclpy
from rclpy.executors import ExternalShutdownException
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
    """Publica exclusivamente las seis juntas revolutas del ABB IRB 120."""

    def __init__(self) -> None:
        super().__init__("irb120_joint_state_source")
        self.declare_parameter("initial_positions_deg", [0.0] * 6)
        self.declare_parameter("publish_rate_hz", 20.0)

        degrees = list(self.get_parameter("initial_positions_deg").value)
        if len(degrees) != 6:
            raise ValueError("initial_positions_deg debe contener exactamente 6 valores.")
        self._positions = self._clamp([_degrees(float(value)) for value in degrees])
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

    def _command_callback(self, message: Float64MultiArray) -> None:
        if len(message.data) != 6:
            self.get_logger().error("El comando debe contener exactamente 6 angulos.")
            return
        requested = [_degrees(float(value)) for value in message.data]
        clamped = self._clamp(requested)
        if clamped != requested:
            self.get_logger().warning("Uno o mas angulos fueron limitados al rango oficial del robot.")
        self._positions = clamped
    def _publish(self) -> None:
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.name = list(JOINT_NAMES)
        message.position = self._positions
        self._publisher.publish(message)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = JointStateSource()
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
