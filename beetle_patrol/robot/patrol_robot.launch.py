"""Robot-side patrol stack: slam_toolbox + Nav2 (our params) + explore_lite + camera throttle.

Does NOT start the base stack (~/patrol_logs/start_base.sh does that).
No map_server / amcl: slam_toolbox provides /map and map->odom.

explore:=false (default): the explore node is started but immediately paused
by publishing Bool False on `explore/resume` (m-explore-ros2 convention: the
node subscribes to explore/resume; True resumes, False pauses). It also
waits for the navigate_to_pose server, so it cannot move before Nav2 is up.
Resume later with:  ros2 topic pub --once /explore/resume std_msgs/msg/Bool "{data: true}"
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node

HERE = os.path.dirname(os.path.abspath(__file__))


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    explore = LaunchConfiguration('explore')
    params_file = LaunchConfiguration('params_file')
    explore_params = os.path.join(HERE, 'explore.yaml')
    slam_params = os.path.join(get_package_share_directory('lyra_slam'),
                               'config', 'slam_toolbox.yaml')
    sim = {'use_sim_time': use_sim_time}

    slam = Node(
        package='slam_toolbox', executable='async_slam_toolbox_node',
        name='slam_toolbox', output='screen',
        parameters=[slam_params, sim],
        remappings=[('scan', '/scan'), ('odom', '/odometry/filtered')])
    # same lifecycle approach as the vendor slam.launch.py
    slam_lifecycle = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='slam_lifecycle_manager', output='screen',
        parameters=[{'autostart': True, 'node_names': ['slam_toolbox'],
                     'bond_timeout': 0.0, **sim}])

    def nav(pkg, exe, name, remap=False):
        return Node(package=pkg, executable=exe, name=name, output='screen',
                    parameters=[params_file, sim],
                    remappings=[('/cmd_vel', '/cmd_vel_nav')] if remap else [])

    nav_nodes = [
        nav('nav2_planner', 'planner_server', 'planner_server'),
        nav('nav2_controller', 'controller_server', 'controller_server', remap=True),
        nav('nav2_behaviors', 'behavior_server', 'behavior_server', remap=True),
        nav('nav2_bt_navigator', 'bt_navigator', 'bt_navigator'),
        nav('nav2_waypoint_follower', 'waypoint_follower', 'waypoint_follower'),
    ]
    nav_lifecycle = TimerAction(period=5.0, actions=[Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_navigation', output='screen',
        parameters=[{'use_sim_time': use_sim_time, 'autostart': True,
                     'node_names': ['planner_server', 'controller_server',
                                    'behavior_server', 'bt_navigator',
                                    'waypoint_follower']}])])

    explore_node = Node(
        package='explore_lite', executable='explore', name='explore',
        output='screen', parameters=[explore_params, sim])
    # start paused unless explore:=true
    pause_explore = TimerAction(
        period=4.0, condition=UnlessCondition(PythonExpression(["'", explore, "' == 'true'"])),
        actions=[ExecuteProcess(
            cmd=['ros2', 'topic', 'pub', '--once', '/explore/resume',
                 'std_msgs/msg/Bool', '{data: false}'], output='screen')])

    throttle = ExecuteProcess(
        cmd=['/usr/bin/python3', os.path.join(HERE, 'image_throttle.py')],
        name='image_throttle', output='screen')

    watchdog = ExecuteProcess(
        cmd=['/usr/bin/python3', os.path.join(HERE, 'patrol_watchdog.py')],
        name='patrol_watchdog', output='screen')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('explore', default_value='false',
                              description='true = explore_lite starts exploring immediately'),
        DeclareLaunchArgument('params_file',
                              default_value=os.path.join(HERE, 'nav2_patrol_params.yaml')),
        slam, slam_lifecycle, *nav_nodes, nav_lifecycle,
        explore_node, pause_explore, throttle, watchdog,
    ])
