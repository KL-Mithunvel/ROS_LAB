"""
localization.launch.py — AMCL on a SAVED map, ON THE ROBOT (guide section 8, option A).

    ros2 launch localization.launch.py map:=$HOME/maps/lab.yaml
    ros2 launch localization.launch.py map:=$HOME/maps/lab.yaml use_sim_time:=True

Starts map_server + amcl + one lifecycle manager for both, using the amcl block
of Acrux's own nav2_params.yaml. Then give AMCL a start pose (RViz "2D Pose
Estimate", or `mission_node.py --set-initial-pose` with the robot on the home marker).

!! NOT run on the robot yet. Two things must be true or this will fight the
shipped stack - run lab_preflight.py first:
  * Do not start navigation.launch.py with exploration:=False at the same time:
    it launches its own map_server (two map servers on one name).
  * Cartographer publishes map->odom itself (`provide_odom_frame = true` in
    acrux_slam/config/lidar.lua). AMCL and Cartographer must not both own
    map->odom. Stop Cartographer, or switch it to pure localization, and make
    sure something still provides odom->base_link.
  * AMCL's base_frame_id in nav2_params.yaml is `base_footprint` while the
    costmaps use `base_link`; check both frames exist (`ros2 run tf2_tools view_frames`).

Run with `ros2 launch <full path to this file>`; it needs no colcon package.
"""

import os

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def _default_params_file():
    try:
        return os.path.join(get_package_share_directory("acrux_navigation"),
                            "config", "nav2_params.yaml")
    except PackageNotFoundError:
        return ""   # forces the user to pass params_file:= instead of failing obscurely


def generate_launch_description():
    map_file = LaunchConfiguration("map")
    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")

    # nav2_params.yaml hard-codes use_sim_time: True for amcl; override it from the argument.
    amcl_params = RewrittenYaml(
        source_file=params_file,
        root_key="",
        param_rewrites={"use_sim_time": use_sim_time},
        convert_types=True)

    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[{"yaml_filename": map_file, "use_sim_time": use_sim_time}])

    amcl = Node(
        package="nav2_amcl",
        executable="amcl",
        name="amcl",
        output="screen",
        emulate_tty=True,
        parameters=[amcl_params])

    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_localization",
        output="screen",
        parameters=[{"autostart": True,
                     "node_names": ["map_server", "amcl"],
                     "use_sim_time": use_sim_time}])

    return LaunchDescription([
        DeclareLaunchArgument("map", description="full path to the saved map .yaml"),
        DeclareLaunchArgument("params_file", default_value=_default_params_file(),
                              description="Nav2 params file containing an `amcl:` block"),
        DeclareLaunchArgument("use_sim_time", default_value="False"),
        map_server,
        amcl,
        lifecycle_manager,
    ])
