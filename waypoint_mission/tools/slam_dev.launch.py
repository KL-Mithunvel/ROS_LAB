"""SLAM for development mode: Cartographer on the LiDAR only (no Nav2, no URDF, no workspace needed).

Prereqs (start them first, e.g. from the GUI Drivers box): LiDAR driver publishing /scan with frame
`lidar_link`. The motor bridge is NOT required for mapping; it is only needed to drive the robot.

    ros2 launch /tmp/acrux_tools/slam_dev.launch.py

Provides: static base_link -> lidar_link (same pose/180 deg yaw as the URDF's lidar_joint), Cartographer
(map -> odom -> base_link, scan matching only) and the occupancy-grid publisher (/map, 1 Hz).
Do not run it together with the demo stack: both would publish map -> odom.
"""
import os

from launch import LaunchDescription
from launch_ros.actions import Node

HERE = os.path.dirname(os.path.realpath(__file__))


def generate_launch_description():
    return LaunchDescription([
        # acrux.xacro lidar_joint: xyz 0.283 0 0.1599, yaw 3.1452 (LiDAR is mounted backwards)
        Node(package='tf2_ros', executable='static_transform_publisher', name='static_tf_base_lidar',
             arguments=['--x', '0.283', '--y', '0.0', '--z', '0.1599', '--yaw', '3.1452',
                        '--frame-id', 'base_link', '--child-frame-id', 'lidar_link']),
        Node(package='cartographer_ros', executable='cartographer_node', name='cartographer_node',
             output='screen',
             arguments=['-configuration_directory', os.path.join(HERE, 'slam_config'),
                        '-configuration_basename', 'lidar.lua']),
        Node(package='cartographer_ros', executable='cartographer_occupancy_grid_node',
             name='cartographer_occupancy_grid_node',
             arguments=['-resolution', '0.05', '-publish_period_sec', '1.0']),
    ])
