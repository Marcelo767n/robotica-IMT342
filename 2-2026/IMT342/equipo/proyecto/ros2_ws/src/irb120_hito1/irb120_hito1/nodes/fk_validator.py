"""Comparacion en vivo entre la cinematica DH analitica, el URDF y el TF de RViz."""

from pathlib import Path

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
from irb120_hito1.kinematics.urdf_chain import chain_transform


def _transform_to_matrix(transform) -> np.ndarray:
    """Convert a geometry_msgs TransformStamped into a 4x4 matrix."""
    t, q = transform.transform.translation, transform.transform.rotation
    x, y, z, w = q.x, q.y, q.z, q.w
    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]
    matrix[:3, 3] = (t.x, t.y, t.z)
    return matrix


class ForwardKinematicsValidator(Node):
    """Validate every JointState against the URDF chain and the TF seen by RViz.

    El pasaporte del Hito 1 exige que la pose [x, y, z] mostrada en RViz (el
    arbol TF de robot_state_publisher) coincida con la funcion analitica DH. Por
    eso cada JointState se compara con (1) la cadena URDF evaluada de forma
    independiente y (2) la transformada TF consultada en el mismo instante.
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
        if self._target_frame not in ("tool0", "gripper_tcp"):
            raise ValueError("target_frame debe ser tool0 o gripper_tcp.")
        if not self._urdf_path.is_file():
            raise FileNotFoundError(f"No se encontro el URDF expandido: {self._urdf_path}")

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._tf_error_publisher = self.create_publisher(
            Float64, "/irb120/fk_tf_position_error_m", 10
        )
        self._pending_tf_sample: tuple[Time, np.ndarray] | None = None
        self._last_tf_error_m: float | None = None
        self.create_timer(0.05, self._check_tf)
        self._last_state: bool | None = None
        self._report_counter = 0
        self.create_subscription(JointState, "/joint_states", self._joint_callback, 20)
        self._error_publisher = self.create_publisher(Float64, "/irb120/fk_position_error_m", 10)

    def _joint_callback(self, message: JointState) -> None:
        received = dict(zip(message.name, message.position))
        if any(name not in received for name in JOINT_NAMES):
            return
        joint_vector = [float(received[name]) for name in JOINT_NAMES]
        if self._target_frame == "gripper_tcp":
            analytic = forward_kinematics_tcp(joint_vector)
        else:
            analytic = forward_kinematics(joint_vector)
        joint_map = dict(zip(JOINT_NAMES, joint_vector, strict=True))
        urdf_matrix = chain_transform(
            self._urdf_path,
            joint_map,
            base_link=self._base_frame,
            target_link=self._target_frame,
        )
        error_m = position_error_m(analytic, urdf_matrix)
        orientation_error_rad = rotation_error_rad(analytic, urdf_matrix)
        self._pending_tf_sample = (Time.from_msg(message.header.stamp), analytic)
        tf_error_m = self._last_tf_error_m
        passed = error_m < self._tolerance and (
            tf_error_m is None or tf_error_m < self._tolerance
        )

        error_message = Float64()
        error_message.data = error_m
        self._error_publisher.publish(error_message)

        self._report_counter += 1
        if passed != self._last_state or self._report_counter >= 20:
            status = "APROBADO" if passed else "FUERA DE TOLERANCIA"
            self.get_logger().info(
                f"{status} | DH vs URDF | frame={self._target_frame} "
                f"| error_pos={error_m:.3e} m | error_rot={orientation_error_rad:.3e} rad "
                f"| error_TF={'n/d' if tf_error_m is None else f'{tf_error_m:.3e} m'} "
                f"| limite={self._tolerance:.1e} m"
            )
            self._last_state = passed
            self._report_counter = 0


    def _check_tf(self) -> None:
        """Compare the analytic pose with TF at the JointState stamp.

        robot_state_publisher publica el TF despues de recibir el JointState,
        por eso la consulta se hace en un temporizador y no dentro del callback.
        """
        if self._pending_tf_sample is None:
            return
        stamp, analytic = self._pending_tf_sample
        try:
            transform = self._tf_buffer.lookup_transform(
                self._base_frame, self._target_frame, stamp
            )
        except TransformException:
            return  # TF aun no disponible; se reintenta con la muestra siguiente.
        self._pending_tf_sample = None
        self._last_tf_error_m = position_error_m(analytic, _transform_to_matrix(transform))
        tf_message = Float64()
        tf_message.data = self._last_tf_error_m
        self._tf_error_publisher.publish(tf_message)


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
