"""Nodo del Hito 2: PoseStamped -> Pieper -> trayectoria LSPB -> comandos articulares.

Entrada : /irb120/target_pose (geometry_msgs/PoseStamped, pose del TCP en base_link)
Salidas : /irb120/joint_commands_deg (Float64MultiArray, grados, 50 Hz) que consume
          joint_state_source del Hito 1, /irb120/planned_trajectory
          (trajectory_msgs/JointTrajectory, plan completo) y /irb120/ik_status.
"""

import numpy as np
import rclpy
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import PoseStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from irb120_hito1.kinematics.dh import JOINT_NAMES, forward_kinematics_tcp, position_error_m
from irb120_hito2.kinematics.collision import CollisionChecker
from irb120_hito2.kinematics.pieper import inverse_kinematics_tcp
from irb120_hito2.kinematics.transforms import pose_matrix, quaternion_to_matrix
from irb120_hito2.trajectory.lspb import LspbTrajectory, plan_lspb

# Velocidades maximas ABB IRB 120 [grados/s].
MAX_SPEED_DEG_S = np.array([250.0, 250.0, 250.0, 320.0, 320.0, 420.0])


class IkTrajectoryNode(Node):
    def __init__(self) -> None:
        super().__init__("irb120_ik_trajectory")
        self.declare_parameter("speed_scale", 0.3)
        self.declare_parameter("max_accel_rad_s2", 3.0)
        self.declare_parameter("publish_rate_hz", 50.0)
        self.declare_parameter("check_collisions", True)
        self.declare_parameter("collision_margin_m", 0.005)
        self._speed_scale = float(self.get_parameter("speed_scale").value)
        self._max_accel = float(self.get_parameter("max_accel_rad_s2").value)
        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        if not 0.0 < self._speed_scale <= 1.0:
            raise ValueError("speed_scale debe estar en (0, 1].")
        if self._max_accel <= 0.0 or rate_hz <= 0.0:
            raise ValueError("max_accel_rad_s2 y publish_rate_hz deben ser positivos.")

        self._margin = float(self.get_parameter("collision_margin_m").value)
        self._checker = (
            CollisionChecker() if self.get_parameter("check_collisions").value else None
        )
        self._current_q: np.ndarray | None = None
        self._trajectory: LspbTrajectory | None = None
        self._start_time = None

        self.create_subscription(JointState, "/joint_states", self._joint_callback, 10)
        self.create_subscription(PoseStamped, "/irb120/target_pose", self._target_callback, 10)
        self._command_pub = self.create_publisher(Float64MultiArray, "/irb120/joint_commands_deg", 10)
        self._plan_pub = self.create_publisher(JointTrajectory, "/irb120/planned_trajectory", 10)
        self._status_pub = self.create_publisher(String, "/irb120/ik_status", 10)
        self.create_timer(1.0 / rate_hz, self._tick)
        self.get_logger().info("Esperando pose objetivo en /irb120/target_pose (TCP, base_link).")

    def _status(self, text: str, error: bool = False) -> None:
        if error:
            self.get_logger().error(text)
        else:
            self.get_logger().info(text)
        self._status_pub.publish(String(data=text))

    def _joint_callback(self, message: JointState) -> None:
        received = dict(zip(message.name, message.position))
        if all(name in received for name in JOINT_NAMES):
            self._current_q = np.array([received[name] for name in JOINT_NAMES], dtype=float)

    def _target_callback(self, message: PoseStamped) -> None:
        if self._current_q is None:
            self._status("Sin /joint_states todavia; se ignora la pose.", error=True)
            return
        if message.header.frame_id not in ("", "base_link"):
            self._status(f"frame_id '{message.header.frame_id}' no soportado; use base_link.", True)
            return
        p, o = message.pose.position, message.pose.orientation
        try:
            rotation = quaternion_to_matrix(o.x, o.y, o.z, o.w)
        except ValueError as error:
            self._status(f"Orientacion invalida: {error}", error=True)
            return
        target = pose_matrix((p.x, p.y, p.z), rotation)

        start = self._current_q.copy()
        solutions = inverse_kinematics_tcp(target, start)
        if not solutions:
            self._status(
                f"SIN SOLUCION para ({p.x:.3f}, {p.y:.3f}, {p.z:.3f}) m: fuera del alcance "
                "o de los limites articulares.",
                error=True,
            )
            return
        best = solutions[0]
        if self._checker is not None:
            free = [s for s in solutions if not self._checker.in_collision(np.array(s.q), self._margin)]
            if not free:
                pairs = self._checker.colliding_pairs(np.array(best.q), self._margin)
                self._status(
                    f"{len(solutions)} soluciones Pieper, todas en colision (p. ej. {pairs}); "
                    "no se mueve el robot.",
                    error=True,
                )
                return
            best = free[0]
        goal = np.array(best.q)
        fk_error = position_error_m(target, forward_kinematics_tcp(goal))
        trajectory = plan_lspb(
            start,
            goal,
            vmax=np.deg2rad(MAX_SPEED_DEG_S) * self._speed_scale,
            amax=self._max_accel,
        )
        self._publish_plan(trajectory)
        self._trajectory = trajectory
        self._start_time = self.get_clock().now()
        self._status(
            f"{len(solutions)} soluciones Pieper; elegida {best.arm}/{best.elbow}/{best.wrist} "
            f"q={np.rad2deg(goal).round(2).tolist()} deg | error FK={fk_error:.2e} m | "
            f"LSPB tf={trajectory.tf:.2f} s tb={trajectory.tb:.2f} s"
        )

    def _publish_plan(self, trajectory: LspbTrajectory, step_s: float = 0.05) -> None:
        plan = JointTrajectory()
        plan.header.stamp = self.get_clock().now().to_msg()
        plan.joint_names = list(JOINT_NAMES)
        for t in np.append(np.arange(0.0, trajectory.tf, step_s), trajectory.tf):
            q, v, a = trajectory.sample(float(t))
            point = JointTrajectoryPoint()
            point.positions, point.velocities, point.accelerations = q.tolist(), v.tolist(), a.tolist()
            seconds = int(t)
            point.time_from_start = Duration(sec=seconds, nanosec=int((t - seconds) * 1e9))
            plan.points.append(point)
        self._plan_pub.publish(plan)

    def _tick(self) -> None:
        if self._trajectory is None:
            return
        elapsed = (self.get_clock().now() - self._start_time).nanoseconds * 1e-9
        q, _, _ = self._trajectory.sample(elapsed)
        self._command_pub.publish(Float64MultiArray(data=np.rad2deg(q).tolist()))
        if elapsed >= self._trajectory.tf:
            self._trajectory = None
            self._status("Trayectoria completada.")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = IkTrajectoryNode()
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
