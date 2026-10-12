"""Hito 2: gemelo del Hito 1 (sin sliders) + nodo IK/LSPB."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    hito1_launch = Path(get_package_share_directory("irb120_hito1")) / "launch" / "display.launch.py"
    return LaunchDescription(
        [
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("speed_scale", default_value="0.3"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(str(hito1_launch)),
                launch_arguments={
                    "use_slider_gui": "false",
                    "use_rviz": LaunchConfiguration("use_rviz"),
                }.items(),
            ),
            Node(
                package="irb120_hito2",
                executable="ik_trajectory_node",
                name="irb120_ik_trajectory",
                output="screen",
                parameters=[{"speed_scale": LaunchConfiguration("speed_scale")}],
            ),
        ]
    )
