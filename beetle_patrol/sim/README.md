# sim/ - fake BeetleBot for laptop-only testing

Lets `patrol_node.py` (and later the GUI) run with NO robot, so the real robot only meets code that has
already run. Every real data source has a simulated twin with the same message shape.

| File | Purpose |
|------|---------|
| `world.py` | Pure numpy (no ROS): room + ray-cast LiDAR, diff-drive kinematics, scripted intruder, synthetic camera. Deterministic with `seed`. Tests: `tests/test_sim_world.py` |
| `fake_robot.py` | ROS 2 node publishing the topics named in `../patrol.yaml` (`topics:`) |
| `sim.yaml` | All simulator numbers (room, lidar, robot limits, laser mount flag, intruder script, nav server) |
| `run_sim.sh` | Starts the sim with the safe environment (domain 77, localhost only) |

## What it publishes / serves

`/scan` (best-effort, frame `laser`, 508 beams, 0.15-12 m, ~9 Hz, noise + inf/nan returns),
`/odometry/filtered` (50 Hz), `/imu/data` (50 Hz, gyro z follows the turning), camera (jpeg CompressedImage,
5 Hz; topic = `topics.camera` in patrol.yaml), `/lyra/armed` (10 Hz), services `/lyra/arm`, `/lyra/disarm`,
tf `odom->base_link`, `base_link->laser` (yaw 180 deg when `mount.laser_flipped: true`, the laser-mount bug
class). Scans are stamped 50 ms in the past, like a driver stamping at acquisition.

The robot moves ONLY from `/cmd_vel_nav` and ONLY while armed (starts DISARMED). A command older than
`cmd_timeout_s` (0.5 s) counts as zero, so keep publishing. Disarm stops it (with the accel limit).

Modes:
* `fake_nav` - also `map->odom` tf (optional small offset in `sim.yaml tf.map_odom_offset`), a static `/map`
  (transient-local), and a `NavigateToPose` action server at `/navigate_to_pose` that turns toward the goal and drives
  straight (no planning, no obstacle avoidance). It publishes on `/cmd_vel_nav`, so it obeys the arm gate. Succeeds
  within `xy_tolerance`; aborts for goals within `margin_m` of / outside the walls, after `goal_timeout_s`, or if
  disarmed for `disarmed_abort_s`; honours cancel (action cancel service).
* `base` - sensors, odom, `odom->base_link->laser`, arm/disarm only. No map tf, no action server, no `/map`, so
  slam_toolbox / nav2 can be layered on top later (their `map->odom` and `/map` then do not clash).

The intruder (`intruder:` in sim.yaml) is a 0.3 m box that walks `path` at constant speed between `t_start` and
`t_end` seconds after the sim starts (defaults 30-60 s). It only exists in the scan while inside the room, and the
camera image changes only while it is in view.

## How to run sim + patrol node + GUI together

Every terminal that talks to the sim needs the SAME environment:

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=77 ROS_LOCALHOST_ONLY=1      # NEVER 154 / 155: those are the real robots
```

Terminal 1 - simulator (sets the env itself; exits with code 2 if you had ROS_DOMAIN_ID=154/155 exported):
```bash
cd beetle_patrol
sim/run_sim.sh --mode fake_nav          # or --mode base
```

Terminal 2 - patrol node (system python, with the env above):
```bash
cd beetle_patrol
source /opt/ros/humble/setup.bash; export ROS_DOMAIN_ID=77 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 patrol_node.py
```

Terminal 3 - GUI (when it exists), again with the same env exported before launching it.
Command it through `/patrol/command` (`start`, `arm`, ... as supported by the node) and arm the robot with the
GUI button or `ros2 service call /lyra/arm std_srvs/srv/Trigger`. Then watch `/patrol/status`.

If a terminal does not have the env, it sits in a different ROS graph and sees nothing. Do not use
`ros2 topic hz` to check rates (unreliable here); use a small rclpy counter.

## Tests

```bash
cd beetle_patrol
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/python -m pytest -q tests/test_sim_world.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /usr/bin/python3 -m pytest -q tests/test_sim_world.py   # also works
```

## Known limits

No collision physics beyond clamping the robot inside the walls; fake Nav2 ignores boxes; odometry is perfect
(no drift or wheel slip); one intruder. Note the patrol node recording a bag writes into `beetle_patrol/runs/`.
