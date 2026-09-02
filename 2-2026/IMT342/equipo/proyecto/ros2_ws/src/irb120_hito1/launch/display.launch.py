"""Lanza el gemelo, una pose reproducible, el validador DH y RViz."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    share_directory = Path(get_package_share_directory("irb120_hito1"))
    urdf_path = share_directory / "urdf" / "irb120_with_gripper.urdf"
    rviz_path = share_directory / "rviz" / "hito1.rviz"
    joint_config = share_directory / "config" / "joint_state_source.yaml"
    robot_description = urdf_path.read_text(encoding="utf-8")

    use_rviz = LaunchConfiguration("use_rviz")
    target_frame = LaunchConfiguration("target_frame")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Abrir RViz junto con la validacion.",
            ),
            DeclareLaunchArgument(
                "target_frame",
                default_value="tool0",
                description="Frame a comparar: tool0 o tcp_link.",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="irb120_robot_state_publisher",
                output="screen",
                parameters=[{"robot_description": robot_description}],
            ),
            Node(
                package="irb120_hito1",
                executable="joint_state_source",
                name="irb120_joint_state_source",
                output="screen",
                parameters=[str(joint_config)],
            ),
            Node(
                package="irb120_hito1",
                executable="fk_validator",
                name="irb120_fk_validator",
                output="screen",
                parameters=[
                    {
                        "base_frame": "base_link",
                        "target_frame": target_frame,
                        "position_tolerance_m": 1.0e-6,
                    }
                ],
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", str(rviz_path)],
                condition=IfCondition(use_rviz),
            ),
        ]
    )
