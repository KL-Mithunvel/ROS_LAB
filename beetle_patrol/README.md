# beetle_patrol — warehouse security patrol for the BeetleBot

Laptop-side app for the BeetleBot ("Lyra", ROS 2 Jazzy, Pi 5). The robot maps a small area, then patrols it:
every zone has a "last visited" age shown as a **heatmap** (a box turns green when the robot enters it and
fades to red), stale zones are prioritised by a **weighted score** and visited with Nav2, and moving objects
raise a **warning** (LiDAR + camera + IMU + wheel-odometry fusion). The GUI shows the decision-making; every
run can be recorded to a **rosbag**.

**Status (2026-10-28):** logic, node, GUI, simulator, robot-side stack and tools are written and unit-tested
(244 tests). Verified on the real robot: comms, arm/disarm, drive, watchdog, node + GUI running together,
boxes turning green on entry. **Not yet verified on hardware:** a Nav2 goal reaching its target, autonomous
mapping (`explore_lite`), a full patrol, moving-object warnings (the scan-to-map tf lookup is skipping scans),
wheel-level E-STOP latency, odometry scale. The virtual boundary (geofence) is **not built yet**. See `../TODO.md`.

**Test area:** a 3 m × 3 m lab floor, a fixed 3 × 3 grid of 1 m zones (`zones.yaml`, `dynamic.enabled: false`).

## Layout

| Path | Purpose |
|------|---------|
| `patrol/heatmap.py` | Zone grid + last-visit / alert times → heatmap data (entering a box = visited, any mode) |
| `patrol/priority.py` | Weighted next-zone score; returns each term so the GUI can explain a choice |
| `patrol/motion.py`, `fusion.py` | LiDAR scan-differencing + camera frame-differencing; fused into one warning |
| `patrol/engine.py` | Modes (idle / mapping / patrol / estop), goals, goal-status classification, timeouts (no ROS imports) |
| `patrol/protocol.py` | JSON schemas v1 for `/patrol/status`, `/decision`, `/warning`, `/command` + validators |
| `patrol/discovery.py` | Optional dynamic zones that grow from `/map` (off by default; GUI part unfinished) |
| `patrol/bag.py`, `bagstats.py`, `overlay.py` | `ros2 bag record` wrapper; bag summary; map ↔ zone overlay |
| `patrol_node.py` | ROS node (laptop): Nav2 goals, tf, E-STOP, status topics, bag start/stop |
| `beetle_gui.py`, `gui/view_model.py` | Tkinter control panel (+ pure view-model) |
| `sim/` | Fake 3 × 3 m robot + intruder on an isolated domain (77, localhost only) |
| `robot/` | Robot-side files: our Nav2 params, `explore_lite` params, launch file, camera throttle, watchdog, `deploy.sh` |
| `tools/` | `bag_check.py` (PASS/FAIL per topic), `zone_overlay.py` (suggests the grid origin from a saved map) |
| `patrol.yaml`, `zones.yaml` | All settings; unknown YAML keys are rejected |
| `secrets.env` (gitignored) | Robot host / user / password / key. Template: `secrets.env.example` |
| `runs/` (gitignored) | Recorded bags |

## How the algorithm decides

`score = 0.5·age + 0.2·risk + 0.2·closeness + 0.1·alert` (weights in `patrol.yaml`, normalised, adjustable
from the GUI sliders). A zone visited in the last `min_revisit_s` (15 s) or that Nav2 just failed to reach is
skipped. Motion: `fused = 0.7·lidar + 0.3·camera`; the camera can never warn alone and is ignored while the
robot drives; LiDAR is halved while it turns (IMU gyro / odometry decide); a warning needs 3 hits in the last
5 updates. Goal completion is read from `/navigate_to_pose/_action/status` (the Humble laptop cannot decode
Jazzy's result message) with a 90 s timeout.

## Tests

```bash
cd beetle_patrol
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/python -m pytest -q    # venv
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /usr/bin/python3 -m pytest -q       # the interpreter the node runs on
```
The env var is required when ROS Humble is sourced (its pytest plugins need `lark`).

## Run it

**Simulator (no robot):** `sim/run_sim.sh --mode fake_nav` (forces domain 77 + localhost-only; refuses 154/155),
then in other terminals with the same env: `/usr/bin/python3 patrol_node.py` and `./beetle_gui.py`.

**Real robot** (192.168.0.154, user `veerobot`, key `~/.ssh/beetlebot_ed25519`, see `secrets.env`):
```bash
# robot: base stack, then (optional) SLAM + Nav2 + explore_lite (paused) + throttle + watchdog
~/patrol_logs/start_base.sh          # robot.launch.py mode:=teleop imu:=true camera:=true
bash robot/deploy.sh --go            # laptop -> ~/patrol_ws/beetle_patrol_robot/ (dry run without --go)
~/patrol_logs/start_patrol.sh        # patrol_robot.launch.py explore:=false
# laptop (Humble), SAME private domain as the robot:
source /opt/ros/humble/setup.bash; export ROS_DOMAIN_ID=154 RMW_IMPLEMENTATION=rmw_fastrtps_cpp
/usr/bin/python3 patrol_node.py &  ./beetle_gui.py
```
GUI: Arm → hold W/A/S/D (≤ 0.15 m/s, 0.5 rad/s) to drive in `idle` mode; Space = E-STOP (latched in both the
node and the GUI — release in the GUI window). Start/Pause/Explore/Record/Save-map buttons publish to `/patrol/command`.
Use `setsid nohup` for background jobs; plain `&` dies when the shell call ends.

## Robot setup done (192.168.0.154)

- OpenCV fixed: user-site NumPy 2.5.3 moved to `~/.local/numpy2_backup`.
- `explore_lite` built from source in `~/patrol_ws` (separate from `~/lyra_ws`); `ros-jazzy-compressed-image-transport` installed.
- The robot rebooted twice on 2026-10-28 (the second time unexplained: clean shutdown, power OK).

## Findings and gotchas

- **Use a private ROS domain (154).** Domain 155 is shared with another BeetleBot on the lab Wi-Fi: every node
  appeared twice and arm/disarm calls may have reached the other robot.
- **Nav2 result vs Humble/Jazzy:** goals are accepted but the result message never decodes on the Humble laptop
  → completion is taken from the status topic. Not yet proven on the real robot.
- **Robot-side Nav2 aborted both test goals** ("failed to plan") with the robot lifted and a nearly empty map; retest on the floor.
- `cmd_vel_gate` has `auto_arm_for_nav: true`, so it forwards `/cmd_vel_nav` even when disarmed; stopping relies on the
  bridge/STM32 refusing commands while disarmed (not yet measured at the wheels).
- Odometry reported ~52 % of the commanded distance (0.155 m for 0.30 m) with the wheels lifted — needs a floor test with a tape.
- `/etc/systemd/system/lyra_base.service` has a mangled `ExecStart` and restarts every 2 s (untouched).
- Robot Nav2 vendor values: `robot_radius` 0.15 (real half-diagonal ≈ 0.26), cruise 0.4 m/s — our copy in `robot/` uses a 0.375 × 0.36 m footprint and 0.15 m/s.
- Humble CLI prints `sequence size exceeds remaining buffer` against Jazzy; use rclpy scripts, not `ros2 topic hz`.
- Camera streams ~56 Hz × 29 KB raw; the robot-side throttle republishes `/patrol/camera/compressed` at ~5 Hz.
