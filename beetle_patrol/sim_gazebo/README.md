# sim_gazebo/ - BeetleBot patrol in a Gazebo warehouse

Runs the **unchanged** `patrol_node.py` and `beetle_gui.py` against a Gazebo Classic world instead of the fake
Python robot in `../sim/`. It has the same pieces as the real stack: LiDAR, camera, IMU, odometry, the arm/disarm
gate, Nav2 with AMCL on a map, and a walking intruder for the motion warning.

| File | Purpose |
|------|---------|
| `gen_world.py` | Writes `worlds/warehouse.world` **and** the matching `maps/warehouse.{pgm,yaml}` from one list of obstacles |
| `beetlebot.sdf` | Simplified BeetleBot: 0.375 x 0.36 m diff drive, 360-beam LiDAR, 320x240 camera, IMU. Same topic names as the real robot |
| `gate_node.py` | `/cmd_vel` -> `/cmd_vel_gated` only while armed; `/lyra/arm`, `/lyra/disarm`, `/lyra/armed` (starts DISARMED) |
| `scan_restamp.py` | `/scan_raw` -> `/scan` stamped 50 ms in the past, like the real driver (otherwise scans are newer than the odom tf and get skipped) |
| `intruder.py` | Walks the red box in through the east door and around the north half (triggers motion warnings) |
| `overview_recorder.py` | Records the virtual overview camera `/overview/image_raw` to PNG stills + mp4, independent of window focus |
| `gen_nav2_params.py` -> `nav2_params.yaml` | Humble's default Nav2 params tuned for the small robot |
| `patrol_gz.yaml`, `zones_gz.yaml` | Patrol settings and a 4 x 3 grid of 3 m zones over the 12 x 9 m floor |
| `run_gazebo_sim.sh`, `run_patrol_gz.sh` | Start the sim; start the patrol node + GUI |

## Run

```bash
sim_gazebo/run_gazebo_sim.sh              # Gazebo window, robot, Nav2, gate, intruder  (--headless for no window)
sim_gazebo/run_patrol_gz.sh               # patrol node + GUI (same environment)
# then arm and start (GUI buttons, or):
source /opt/ros/humble/setup.bash; export ROS_DOMAIN_ID=77 ROS_LOCALHOST_ONLY=1
ros2 topic pub --once /patrol/command std_msgs/msg/String "{data: arm}"
ros2 topic pub --once /patrol/command std_msgs/msg/String "{data: start}"
sim_gazebo/run_gazebo_sim.sh --stop       # stop the Gazebo side
```

Always ROS domain 77, localhost only; both scripts refuse domains 154/155 (the real robots). The patrol node runs
with `use_sim_time:=true`. `BEETLE_PATROL_YAML` / `BEETLE_ZONES_YAML` point the node and GUI at the warehouse
settings (default: the lab files). `INTRUDER_DELAY` / `INTRUDER_REPEAT` (seconds) control the intruder.

## Result (2026-11-09, about 8 minutes)

32 zone decisions, 15 moving-object warnings, no failed goals. The LiDAR carried every warning; the camera never
warned on its own, as designed. Captures are in `../../showcase/beetle_gazebo/`.

## Known limits

- Nav2 uses the pre-generated map (no SLAM, no explore_lite).
- Odometry comes from Gazebo's diff-drive plugin (no drift model).
- The GUI camera panel shows the real 3D scene, but camera motion confidence stays near 0 because the robot is
  moving almost all the time and the node ignores the camera while driving.
- Gazebo's own window is not reliable for screenshots while another window covers it; use `overview_recorder.py`.
