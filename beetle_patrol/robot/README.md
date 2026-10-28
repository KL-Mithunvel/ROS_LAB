# Robot-side patrol stack (BeetleBot, ROS 2 Jazzy)

Files only; nothing here has been run on the robot.

| File | Purpose |
|---|---|
| `nav2_patrol_params.yaml` | Our Nav2 params (copy of vendor, every change commented). No amcl/map_server: slam_toolbox provides map and `map->odom`. |
| `explore.yaml` | explore_lite params for a 3x3 m room. |
| `patrol_robot.launch.py` | slam_toolbox (vendor `lyra_slam` config) + Nav2 (our params, `/cmd_vel` -> `/cmd_vel_nav`) + explore_lite + image throttle + watchdog. Args: `use_sim_time`, `explore` (default false), `params_file`. Does not start the base stack. |
| `image_throttle.py`, `throttle_logic.py` | `/pi_camera/image_raw/compressed` -> `/patrol/camera/compressed` at max 5 Hz (`max_hz` param). |
| `watchdog_logic.py`, `patrol_watchdog.py` | If armed and `/patrol/status` heartbeat is silent > 2 s: cancel Nav2 goals, publish False on `/explore/resume`, call `/lyra/disarm`. Once per outage. Never arms. |
| `deploy.sh` | rsync only, to `~/patrol_ws/beetle_patrol_robot/`. Dry run by default; `--go` transfers. |

Tests (laptop): `cd beetle_patrol && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/python -m pytest -q tests`

## Explore pause convention
explore_lite subscribes to `explore/resume` (std_msgs/Bool): True resumes, False pauses.
With `explore:=false` the launch starts the node and, 4 s later, publishes False once (the node also
waits for the `navigate_to_pose` server, so it cannot drive before Nav2 is active).

## Commands for the human (GATED: need the user present)
1. Preview: `./deploy.sh` (dry run). Transfer: `./deploy.sh --go`.
2. On robot, after `~/patrol_logs/start_base.sh`:
   `source /opt/ros/jazzy/setup.bash; source ~/lyra_ws/install/setup.bash; source ~/patrol_ws/install/setup.bash`
   `ros2 launch ~/patrol_ws/beetle_patrol_robot/patrol_robot.launch.py` (add `explore:=true` to explore at once)
3. Resume/pause exploring: `ros2 topic pub --once /explore/resume std_msgs/msg/Bool "{data: true}"`

## Humble twin (laptop sim)
- Nav2 params: the `behavior_server` block carries both Humble keys (`costmap_topic`, `footprint_topic`) and Jazzy keys; Humble ignores the extra ones (it may warn).
- `use_sim_time:=true` for the sim. `lyra_slam` must be installed in that workspace, or pass another slam config.
- explore_lite must be built from m-explore-ros2 for Humble too; the topic names are identical.
- Python files use only rclpy/std_msgs/std_srvs/action_msgs/sensor_msgs, so they run on both.

## Unverified items
- explore_lite parameter names (`min_frontier_size`, `costmap_updates_topic`, `orientation_scale`, `return_to_init`) are from memory; check with `ros2 param list /explore` on the robot. Unknown params are ignored but would silently not apply.
- Footprint assumes base_link is at the body centre.
