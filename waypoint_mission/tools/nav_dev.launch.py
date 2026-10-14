"""Nav2 on the live Cartographer map (development mode). Start slam_dev.launch.py first.

    ros2 launch /tmp/acrux_tools/nav_dev.launch.py

Uses nav2_bringup's navigation_launch.py with nav2_dev_params.yaml. Final velocity goes to /cmd_vel via the
velocity smoother. Needs: /scan, /map (Cartographer), TF map->odom->base_link, and the motor bridge to move.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

HERE = os.path.dirname(os.path.realpath(__file__))


def generate_launch_description():
    nav2 = get_package_share_directory('nav2_bringup')
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav2, 'launch', 'navigation_launch.py')),
            launch_arguments={'params_file': os.path.join(HERE, 'nav2_dev_params.yaml'),
                              'use_sim_time': 'false', 'autostart': 'true'}.items()),
    ])
