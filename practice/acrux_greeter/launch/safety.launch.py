"""
safety.launch.py — start Nav2's collision monitor ON THE ROBOT.

    ros2 launch safety.launch.py                       # defaults
    ros2 launch safety.launch.py cmd_vel_in:=cmd_vel_smoothed cmd_vel_out:=cmd_vel

The collision monitor must sit BETWEEN Nav2's final velocity output and the
topic the base listens on. The default names assume Nav2's velocity smoother
publishes `cmd_vel_smoothed` and the Acrux base listens on `/cmd_vel`. Acrux's
wiring has NOT been confirmed on the robot - find the real names with
`ros2 topic info /cmd_vel -v` and pass them as arguments. See
learn/build/09-acrux-greeter-mission.md section 7.

Run with `ros2 launch <full path to this file>`; it needs no colcon package.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

PARAMS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "collision_monitor.yaml")


def generate_launch_description():
    cmd_vel_in = LaunchConfiguration("cmd_vel_in")
    cmd_vel_out = LaunchConfiguration("cmd_vel_out")
    use_sim_time = LaunchConfiguration("use_sim_time")

    collision_monitor = Node(
        package="nav2_collision_monitor",
        executable="collision_monitor",
        name="collision_monitor",
        output="screen",
        emulate_tty=True,
        parameters=[PARAMS_FILE, {
            "cmd_vel_in_topic": cmd_vel_in,
            "cmd_vel_out_topic": cmd_vel_out,
            "use_sim_time": use_sim_time,
        }],
    )

    # collision_monitor is a lifecycle node: something must activate it.
    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_collision_monitor",
        output="screen",
        emulate_tty=True,
        parameters=[{
            "autostart": True,
            "node_names": ["collision_monitor"],
            "use_sim_time": use_sim_time,
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument("cmd_vel_in", default_value="cmd_vel_smoothed",
                              description="topic Nav2 publishes its final velocity on"),
        DeclareLaunchArgument("cmd_vel_out", default_value="cmd_vel",
                              description="topic the robot base listens on"),
        DeclareLaunchArgument("use_sim_time", default_value="False"),
        collision_monitor,
        lifecycle_manager,
    ])
