"""Publica una demostracion ciclica para observar el robot en movimiento."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

from irb120_hito1.motion import interpolate_demo


class MotionDemo(Node):
    """Animate all six joints and the provisional gripper."""

    def __init__(self) -> None:
        super().__init__("irb120_motion_demo")
        self.declare_parameter("segment_duration_s", 3.0)
        self.declare_parameter("publish_rate_hz", 20.0)

        self._segment_duration = float(self.get_parameter("segment_duration_s").value)
        publish_rate = float(self.get_parameter("publish_rate_hz").value)
        if self._segment_duration <= 0.0 or publish_rate <= 0.0:
            raise ValueError("Las duraciones y frecuencias deben ser positivas.")

        self._start_ns = self.get_clock().now().nanoseconds
        self._publisher = self.create_publisher(
            Float64MultiArray,
            "/irb120/joint_commands_deg",
            10,
        )
        self.create_timer(1.0 / publish_rate, self._publish)
        self.get_logger().info(
            "Demostracion automatica activa: seis ejes y pinza en movimiento."
        )

    def _publish(self) -> None:
        elapsed_s = (self.get_clock().now().nanoseconds - self._start_ns) / 1.0e9
        command = interpolate_demo(elapsed_s, self._segment_duration)
        message = Float64MultiArray()
        message.data = command.tolist()
        self._publisher.publish(message)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = MotionDemo()
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
