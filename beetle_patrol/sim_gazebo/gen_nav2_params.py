#!/usr/bin/env python3
"""Humble's default nav2_params.yaml, tuned for the small BeetleBot in the Gazebo warehouse -> nav2_params.yaml."""
import yaml

p = yaml.safe_load(open("/opt/ros/humble/share/nav2_bringup/params/nav2_params.yaml"))
P = lambda k: p[k]["ros__parameters"]
P("amcl")["base_frame_id"] = "base_link"
P("amcl")["set_initial_pose"] = True
P("amcl")["initial_pose"] = {"x": 1.5, "y": 1.5, "z": 0.0, "yaw": 0.0}
P("amcl")["update_min_d"] = 0.1
P("amcl")["update_min_a"] = 0.1
P("bt_navigator")["robot_base_frame"] = "base_link"
P("bt_navigator")["odom_topic"] = "/odometry/filtered"
P("velocity_smoother")["odom_topic"] = "/odometry/filtered"
P("velocity_smoother")["max_velocity"] = [0.3, 0.0, 1.0]
P("velocity_smoother")["min_velocity"] = [-0.3, 0.0, -1.0]
fp = P("controller_server")["FollowPath"]
fp["max_vel_x"], fp["max_speed_xy"], fp["max_vel_theta"] = 0.3, 0.3, 1.0
fp["min_speed_xy"] = 0.0
P("controller_server")["general_goal_checker"]["xy_goal_tolerance"] = 0.25
P("controller_server")["general_goal_checker"]["yaw_goal_tolerance"] = 6.3
for cm, extra in (("local_costmap", {"width": 3, "height": 3}), ("global_costmap", {})):
    c = p[cm][cm]["ros__parameters"]
    c["robot_base_frame"] = "base_link"
    c["robot_radius"] = 0.22
    c["inflation_layer"]["inflation_radius"] = 0.45
    c["inflation_layer"]["cost_scaling_factor"] = 4.0
    c.update(extra)
yaml.safe_dump(p, open("nav2_params.yaml", "w"), sort_keys=False)
print("wrote nav2_params.yaml")
