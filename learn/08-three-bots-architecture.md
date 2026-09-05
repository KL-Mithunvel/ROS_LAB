# 08 — BeetleBot / JetBot / Acrux: full architecture walkthrough

This file is the deep reference for the three robots vendored into this repo as git
submodules (`BeetleBot/`, `jetbot/`, `acrux/`). It explains, from the **actual checked-out
source** (not just each README): what each robot is, every package and file and what it's
for, the exact commands to set up and run each, and — the main event — **how localization,
SLAM, obstacle avoidance and navigation actually work and how they plug together** into one
pipeline. BeetleBot is the lab robot; JetBot and Acrux are comparison platforms (see
`.CLAUDE/CLAUDE.md` Architecture table).

Cross-links: `02-ros2-concepts.md` (ROS 2 basics, `colcon`, the reactive obstacle-avoidance
script line-by-line), `03-beetlebot-runbook.md` (the lab-day procedure for BeetleBot only).
This file goes wider (all three bots) and deeper (the Nav2/SLAM/localization internals that
`02`/`03` intentionally keep lab-exam-level).

---

## 1. The three robots at a glance

| | BeetleBot | Acrux | JetBot |
|---|---|---|---|
| Maker | VEEROBOT (Siliris Technologies) | VEEROBOT / rigbetellabs | NVIDIA-AI-IOT |
| Role in this repo | **the lab robot** | comparison AMR | comparison — non-ROS contrast |
| Drive | 4-wheel skid-steer | differential (2 driven wheels + casters) | differential (2 driven wheels) |
| Compute | Raspberry Pi 5 | Intel NUC i3 (10th gen) | Jetson Nano |
| Motor/IO controller | STM32F405 "Lyra" (FreeRTOS, UART) | DOIT-ESP32 Devkit V1 | Adafruit/SparkFun I2C motor HAT — no separate MCU |
| ROS version | ROS 2 **Jazzy** | ROS 2 **Humble** | **none** — plain Python |
| LiDAR | RPLiDAR C1 (360°, 12 m) | YDLidar (via `ydlidar_ros2_driver`) + optional RealSense D435i depth | none (camera only) |
| Mapping | SLAM Toolbox only | SLAM Toolbox **or** Cartographer **or** gmapping (3 configs shipped) | none (no map — camera-based reactive AI instead) |
| Navigation | Nav2 (AMCL + Regulated Pure Pursuit) | Nav2 (full `acrux_navigation` stack) | none |
| Simulation | Gazebo Harmonic (URDF+SDF) | Gazebo (`acrux_gazebo`) | none |
| What it teaches you | the full AMR autonomy stack, real robot | the *same* stack with different SLAM back-end choices, ESP32 firmware pattern | robot control **without** ROS — I2C, motor HAT, notebook-driven AI perception |

**Why JetBot is worth studying even though it has no ROS:** every ROS concept in this repo
(publish velocity commands, read a camera, run a control loop) exists in JetBot too, just
built from scratch in plain Python instead of using ROS's pub/sub + message types. Comparing
`jetbot/jetbot/robot.py`'s `Robot.forward()` against `lyra_bridge`'s `_cmd_vel_callback` +
`_motor_control_loop` shows you exactly what ROS is buying you: message types, topics,
timers, launch files, and interoperability — none of which JetBot has, and all of which it
re-implements ad hoc (a `traitlets`-based `Robot` singleton object instead of a `Twist`
message and a subscription).

---

## 2. BeetleBot — full package walkthrough

Source: `BeetleBot/lyra_ws/src/` (a normal ROS 2 workspace `src/` layout — see
`02-ros2-concepts.md` §3 for what a workspace/package/`colcon build` is).

```
lyra_ws/src/
├── beetlebot_description/   URDF, meshes, RViz configs — no nodes, just robot geometry
├── camera_ros/               vendored 3rd-party camera driver (C++, libcamera-based)
├── sllidar_ros2/              vendored 3rd-party RPLiDAR driver (C++)
├── lyra_bridge/               the STM32 UART bridge — motors, arm/disarm, telemetry
├── lyra_control/               cmd_vel priority mux + joystick teleop wrapper
├── lyra_cmd_vel_gate/          a second, simpler safety gate in front of cmd_vel
├── lyra_localization/           wheel odometry + EKF sensor fusion
├── lyra_slam/                   SLAM Toolbox launch/config
├── lyra_nav2/                    AMCL + Nav2 planner/controller/costmap launch/config
└── lyra_bringup/                 top-level launch files that wire everything above together
```

### `lyra_bridge` — the hardware boundary

The only package that talks to real hardware (over `/dev/ttyAMA0`, 115200 baud — see
Known Technical Debt #7 in `.CLAUDE/CLAUDE.md` for the `ttyACM0` vs `ttyAMA0` handout
conflict). Files, from `lyra_bridge/lyra_bridge/`:

| File | Role |
|---|---|
| `node.py` | the ROS node itself — see below |
| `protocol.py` | builds/parses the binary serial frames (`build_arm_command`, `build_set_wheel_vel_command`, etc.) — the wire format between Pi and STM32 |
| `transport.py` | `SerialTransport` — raw pyserial read/write wrapper, non-blocking (`timeout=0.0`) |
| `telemetry.py` | decodes the STM32's telemetry payload into a dict (`wheel_rpm`, `wheel_ticks`, `battery_v`, `accel_*`, `gyro_*`, `status_flags`) |

`node.py` (`LyraBridge`, node name `lyra_bridge`) — what it does, concretely:
- **Subscribes** `/cmd_vel` (`geometry_msgs/Twist`) → stores it with a timestamp (thread-safe, behind `cmd_lock`).
- **Publishes**: `/wheel_rpm` (`Float32MultiArray`), `/wheel_ticks` (`Int32MultiArray`), `/battery_voltage` (`Float32`), `/imu/data_raw` (`sensor_msgs/Imu`), `/lyra/armed` (`Bool`) — all sourced from decoded STM32 telemetry.
- **Services**: `/lyra/arm`, `/lyra/disarm`, `/lyra/emergency_stop` (all `std_srvs/Trigger`) — each just builds the matching binary command and writes it over serial; the response's `success`/`message` reflects whether the write succeeded, not whether the STM32 actually armed (that confirmation comes back asynchronously as the `armed` bit in telemetry).
- **Two background loops**:
  - `_motor_control_loop` (a `create_timer(0.05, ...)` → **20 Hz**, matching the STM32's own 20 Hz PID rate): if disarmed, or no `cmd_vel` ever received, or the last `cmd_vel` is older than `control.cmd_vel_timeout_s` (default 0.5 s), it sends an all-zero wheel-velocity command — this is the software deadman switch that stops the robot if teleop/Nav2 stalls or the network drops. Otherwise it runs `_inverse_kinematics(vx, wz)` (skid-steer differential-drive math: `v_left = vx - wz*track/2`, `v_right = vx + wz*track/2`, then `/wheel_radius` to get rad/s, clamped to `max_wheel_speed_rad_s`) and sends `[FL, BL, BR, FR]` wheel speeds.
  - `_rx_loop` (a separate daemon `threading.Thread`, not a ROS timer, because it has to block on serial I/O) polls the transport, parses complete frames out of the buffer, and on a telemetry frame (`CMD_GET_TELEMETRY = 0x85`) publishes all five topics above.
- Also runs a `_request_telemetry` timer (rate = `control.telemetry_rate_hz`, default 10 Hz) and a `_send_heartbeat` timer (`control.heartbeat_rate_hz`, default 1 Hz) — the heartbeat is what lets the STM32's own watchdog detect "the Pi died" and fail safe independently of the 20 Hz command loop.
- On `destroy_node()` (SIGINT/Ctrl+C via the launch system) it joins the RX thread and closes the serial port cleanly.

This is the node that makes Development Rule "Linux cannot do real-time motor control" concrete: `lyra_bridge` never computes a PID output itself — it only computes *desired* wheel speeds and ships them to the STM32, which runs the actual 20 Hz deterministic PID loop in FreeRTOS.

### `lyra_control` — arbitrating who gets to drive

| File | Role |
|---|---|
| `cmd_vel_mux.py` | priority-based multiplexer, output `/cmd_vel_raw` |
| `joy_teleop_wrapper.py` | turns joystick input into a `Twist` on `/cmd_vel_joy` |
| `config/joystick.yaml` | axis/button mapping |

`CmdVelMux` (node `cmd_vel_mux`) subscribes three inputs and picks **one** to forward, by priority, each output tick (20 Hz timer):

| Source topic | Priority | Timeout | Meaning |
|---|---|---|---|
| `/cmd_vel_joy` | 10 (highest) | 0.2 s | joystick — a human always overrides autonomy, and releasing the deadman stops the robot almost immediately |
| `/cmd_vel_nav` | 5 | 1.0 s | Nav2's output — tolerant of brief planner hiccups |
| `/cmd_vel_manual` | 1 (lowest) | 0.5 s | e.g. `teleop_twist_keyboard` remapped here for manual driving without Nav2 |

Each tick it finds the **highest-priority source that has published within its timeout** and republishes that message on `/cmd_vel_raw`; if *no* source is currently active it deliberately **publishes nothing** (the file's own comment calls this "NO ZERO SPAM mode" — earlier versions apparently flooded `/cmd_vel_raw` with zero `Twist`s when idle, which is why `lyra_bridge`'s own 0.5 s timeout deadman switch in §above still exists as a second, independent safety net downstream of the mux).

### `lyra_cmd_vel_gate`

A thin additional safety layer between the mux output and the bridge (single `node.py` — a place to add e-stop/bumper/battery-based command gating without touching `lyra_bridge` or `lyra_control`). Treat it as the same architectural idea as the mux's timeout logic, one layer further downstream.

### `lyra_localization` — turning sensors into a pose

| File | Role |
|---|---|
| `wheel_odom_node.py` | reads `/wheel_ticks` (from `lyra_bridge`) → integrates differential-drive kinematics → publishes `/wheel/odom` (`nav_msgs/Odometry`) |
| `odom_node.py` | general odometry helper node |
| `config/ekf.yaml` | `robot_localization` EKF — the one actually used |
| `config/ekf_adaptive.yaml` | an alternate/experimental EKF tuning |
| `config/imu_filter.yaml` | IMU pre-filtering (e.g. Madgwick/complementary filter before EKF) |

This is **Localization step 1** in the pipeline (§5 below). See §5.1 for what the EKF actually does with these inputs.

### `lyra_slam` and `lyra_nav2`

Both are launch/config-only packages (no custom nodes) that wrap upstream ROS 2 packages:

- `lyra_slam/config/slam_toolbox.yaml` configures **`slam_toolbox`** (an upstream package, not written for this robot) — see §5.2.
- `lyra_nav2/config/amcl.yaml` + `nav2_params.yaml` configure upstream **Nav2** (`amcl`, `map_server`, `bt_navigator`, `controller_server`, `planner_server`, `behavior_server`, `waypoint_follower`, plus `local_costmap`/`global_costmap`) — see §5.1 (AMCL) and §5.4 (Nav2).
- `launch/slam_bringup.launch.py`, `launch/full_nav.launch.py`, `launch/nav2_amcl.launch.py` are the entry points `lyra_bringup` calls into.

### `lyra_bringup` — wiring it all together

`launch/robot.launch.py` is the one command from the README/runbook:
```bash
ros2 launch lyra_bringup robot.launch.py                          # base + lidar only
ros2 launch lyra_bringup robot.launch.py mode:=slam camera:=true imu:=true
```
It composes the smaller launch files (`base.launch.py` — description + `lyra_bridge` +
`lyra_control`; `lidar.launch.py` — `sllidar_ros2`; `odom_ekf.launch.py` /
`odom_ekf_imu.launch.py` — `lyra_localization`) and, depending on the `mode:=` argument,
also brings in `lyra_slam` or `lyra_nav2`'s launch files. This is the practical meaning of
"launch file" from `02-ros2-concepts.md`: one process starts a dozen nodes with consistent
parameters instead of you running each `ros2 run` by hand.

### `beetlebot_description`

Pure data: `urdf/beetlebot.urdf` (link/joint geometry — chassis, 4 wheels, LiDAR mount),
`meshes/*.STL` (visual/collision shapes referenced by the URDF), `rviz/*.rviz` (five saved
RViz layouts: `beetlebot.rviz` general, `odom_only.rviz`, `slam_with_cam.rviz`,
`nav2.rviz`/`nav2_amcl.rviz` for the two navigation modes). No nodes — `robot_state_publisher`
(a stock ROS 2 package, launched by `lyra_bringup`) reads the URDF and publishes the static
part of the TF tree from it.

### Firmware: `STM32F405RGTx/`

The FreeRTOS/C source for "Lyra" itself — outside ROS entirely (it's what `lyra_bridge`
talks to *over* the serial link). Not something you rebuild/reflash during the lab; it's here
for completeness/reference only.

### Setup & run — BeetleBot

```bash
# On the robot (SSH) — one-time, per new terminal:
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<robot-number>

# Bring up hardware + LiDAR (Terminal 1, leave running)
ros2 launch lyra_bringup robot.launch.py                       # lyra-launch-robot-teleop (alias)
ros2 launch lyra_bringup robot.launch.py mode:=slam camera:=true imu:=true   # lyra-launch-robot-slam

# Terminal 2 — arm, then drive
ros2 service call /lyra/arm std_srvs/srv/Trigger                # lyra-arm
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=cmd_vel_manual
ros2 service call /lyra/disarm std_srvs/srv/Trigger              # lyra-disarm

# Rebuild after any Python source change:
cd ~/lyra_ws && colcon build --packages-select <pkg> && source install/setup.bash
```
Raw-vs-alias per Development Rule 4: `lyra-*` aliases only exist after
`source ~/lyra_ws/lyra_commands.sh` (or `docs_ros2/lyra_commands.sh` in the submodule) is
run on the robot; they wrap exactly the raw commands above. Full reconciled procedure incl.
the IP/topic-name technical debt: `03-beetlebot-runbook.md`.

---

## 3. Acrux — full package walkthrough

Source: `acrux/` top level (this submodule's packages sit at the repo root, not under a
`src/` subfolder like BeetleBot — you'd `git clone` it *into* `~/ros2_ws/src/acrux` per its
own README). ROS 2 **Humble**, not Jazzy — same concepts, different distro.

```
acrux/
├── acrux_bringup/       top-level launch: bringup.launch.py, autobringup.launch.py
├── acrux_description/    URDF/xacro + meshes + RViz + display/state-publisher launch
├── acrux_firmware/        ESP32 bridge params, LiDAR/RealSense/joystick launch
├── acrux_gazebo/           Gazebo worlds + spawn launch
├── acrux_navigation/        Nav2 config/launch + map_saver
└── acrux_slam/               THREE interchangeable SLAM back-ends
```

### `acrux_slam` — three ways to build a map

Unlike BeetleBot (SLAM Toolbox only), Acrux ships config for three different SLAM
algorithms, launched independently — a good place to *compare* approaches:

| Config file | Algorithm | Launch file |
|---|---|---|
| `config/slam_toolbox_params.yaml` | SLAM Toolbox (pose-graph, same family as BeetleBot's) | `launch/slam_toolbox.launch.py` |
| `config/lidar.lua` | **Cartographer** (Google's submap + branch-and-bound scan matcher) | `launch/cartographer.launch.py` |
| `config/gmapping.yaml` | **gmapping** (particle-filter/Rao-Blackwellized SLAM, the oldest of the three) | (older/ROS1-style config kept for reference) |

See §5.2 for how Cartographer's actual mechanics (`lidar.lua`) differ from SLAM Toolbox's.
`config/ekf.yaml` here plays the same role as BeetleBot's `lyra_localization/config/ekf.yaml`
— see §5.1; Acrux's fuses `wheel/odometry` position (x, y, yaw) plus a `bno055/imu` (note:
its IMU fusion fields are all `false` in the shipped config — meaning as checked in, IMU data
is *not* actually being fused, only wheel odometry; a good "spot the config bug" exercise).

### `acrux_firmware` — the ESP32 boundary

Equivalent role to BeetleBot's `lyra_bridge`, but the microcontroller is a DOIT-ESP32
(not STM32) and sensor drivers are launched from here rather than embedded in one node:

| Launch file | Brings up |
|---|---|
| `rplidar_a3.launch.py` (+ the YDLidar driver from the separate `ydlidar_ros2_driver-humble` repo, `config/x2_params.yaml`) | the 2D LiDAR |
| `realsense_d435i.launch.py` | Intel RealSense D435i depth camera |
| `merge_scan.launch.py` | `pointcloud_to_laserscan` (turns the depth camera's point cloud into a 2D scan) + `ira_laser_tools` merges that with the LiDAR scan into one combined scan — useful when the LiDAR alone has blind spots the depth camera covers |
| `auto_joy_teleop.launch.py` | joystick control **plus waypoint storage/navigation via joy buttons** (from the separate `joy_with_waypoint_nav` repo) |
| `hubble_scripts.launch.py` | closed-source (`freezed binaries`) network/goal-status publisher nodes feeding Acrux's LED status indicators |

Low-level topics (from the README, ROS 1-style names kept in ROS 2 for compatibility):
`/battery/percentage`, `/battery/voltage`, `/cmd_vel`, `/pid/control` (publish `0`-`3` to
stop/fast/smooth/supersmooth PID modes — an operator-tunable version of what BeetleBot's
STM32 firmware fixes at 20 Hz internally), `/wheel/ticks`, `/wheel/vel` (both `[lf, lb, rf,
rb]` arrays — note Acrux is nominally differential-drive but reports **four** wheel values,
implying skid-steer-style redundant wheel encoders same as BeetleBot).

### `acrux_navigation`, `acrux_description`, `acrux_gazebo`

- `acrux_navigation/config/nav2_params.yaml` — Nav2 stack config (see §5.4; same node set as BeetleBot's `lyra_nav2` — `bt_navigator`, `controller_server`, `planner_server`, costmaps — different tuning for a 100 kg-payload NUC-class robot vs BeetleBot's 300 mm/2.2 kg chassis). `launch/navigation.launch.py` + `launch/map_saver.launch.py`.
- `acrux_description` — `urdf/acrux.xacro` (xacro = URDF with macros/variables, more maintainable than BeetleBot's plain `.urdf`), `display.launch.py` (Gazebo + RViz + state publishers together), `rviz.launch.py`, `state_publisher.launch.py`.
- `acrux_gazebo` — `gazebo.launch.py` (world only), `spawn_robot.launch.py` (world + spawn the robot model with controllers) — `worlds/no_roof_small_warehouse.world`, `worlds/room2.sdf`.

### `acrux_bringup` — the top-level entry points

| Launch file | Does |
|---|---|
| `bringup.launch.py` | sensors + hardware + microROS + LiDAR + RealSense + Hubble scripts — **no navigation** |
| `autobringup.launch.py` | everything `bringup` does, **plus** navigation, exploration/SLAM, localization, RViz, simulation |

Key `autobringup.launch` arguments (from the README's own table): `use_sim_time` (Gazebo
vs real), `joy` (enable joystick), `exploration` (`True` = SLAM/mapping mode, `False` =
localize + navigate on an existing `map_file`), `realsense`, `merge_scan`.

### Setup & run — Acrux

```bash
# Clone into a workspace (their README's own convention — note ros2_ws here)
cd ~/ros2_ws/src && git clone -b ros2-humble https://github.com/rigbetellabs/acrux.git
cat acrux/requirements.txt | xargs sudo apt-get install -y      # installs Nav2, cartographer, xacro, teleop, etc.
cd ~/ros2_ws && colcon build --symlink-install

# On the robot, dev mode (stops the auto-start production service)
cd ~/ros2_ws/src/acrux && ./development.sh

# Simulation
ros2 launch acrux_gazebo spawn_robot.launch.py

# Real robot — SLAM/exploration mode
ros2 launch acrux_bringup autobringup.launch.py exploration:=True
ros2 launch acrux_navigation map_saver.launch.py map_file_path:=/your/map/directory

# Real robot — navigate a saved map
ros2 launch acrux_bringup autobringup.launch.py exploration:=False map_file:=/your/map/directory

# Restore the on-boot production service when done
cd ~/ros2_ws/src/acrux && ./demo.sh
```

---

## 4. JetBot — the non-ROS contrast case

Source: `jetbot/jetbot/` — a plain installable Python package (`setup.py` → `pip install`),
not a ROS workspace. Structure:

| File/dir | Role |
|---|---|
| `robot.py` | `Robot` class (a `traitlets.SingletonConfigurable`) — `forward()`, `backward()`, `left()`, `right()`, `stop()`, `set_motors(l, r)`. Detects which motor HAT is attached (`qwiic.scan()` for an I2C address: `96` = Adafruit HAT, `93` = SparkFun HAT) and defines the driver methods **inline in the `__init__`/class body** per-branch — an unusual pattern (branching on hardware at class-definition time) that only works because it runs once at import. |
| `motor.py` | `Motor` — one motor's PWM/direction logic, wrapped in a `traitlets.HasTraits` so `motor.value = 0.5` triggers a hardware write via an `@observe` callback (this is JetBot's rough equivalent of a ROS topic callback — a value-changed event instead of a message-received event). |
| `camera/camera_base.py`, `opencv_gst_camera.py`, `zmq_camera.py` | camera abstraction — GStreamer pipeline for the CSI camera, or a ZMQ-streamed camera for remote setups. No `sensor_msgs/Image`; frames are raw numpy arrays passed directly between Python objects. |
| `object_detection.py`, `tensorrt_model.py`, `ssd_tensorrt/` | the collision-avoidance / object-following AI models — a TensorRT-accelerated SSD detector (`ssd_tensorrt.py` + a compiled C++/CUDA `.so` built by the `CMakeLists.txt` you already saw — that's what `setup.py`'s `build_libs()` compiles before `pip install`). |
| `apps/wander.py`, `apps/stats.py` | example standalone scripts. |
| `heartbeat.py` | a watchdog: stops the robot if it hasn't heard from the controlling Jupyter cell recently — functionally the same *idea* as `lyra_bridge`'s `cmd_vel` timeout, implemented from scratch with a `traitlets` observer + `time`, no ROS timer involved. |
| `notebooks/{basic_motion, teleoperation, object_following, road_following, collision_avoidance}` | the actual "programs" — Jupyter notebooks that import `jetbot.Robot`/`jetbot.Camera` and call methods directly, with `ipywidgets` sliders as the human interface (there's no RViz, no `ros2 topic pub` — the notebook cell *is* the CLI). |

**How JetBot does obstacle avoidance (`collision_avoidance` notebook), for direct
comparison with §5.3 below:** it is not reactive geometry at all — it's a binary image
classifier (a small CNN, trained on "free" vs "blocked" labeled photos from the robot's own
camera) run on every camera frame; a "blocked" prediction stops/turns the robot. No LaserScan,
no windowing, no costmap — perception replaces geometry entirely. This is the single clearest
side-by-side in this repo of two different philosophies for the same problem: BeetleBot's
`obstacle_avoidance.py` (geometry: measure distance, threshold, turn) vs JetBot's
`collision_avoidance` (learned perception: classify the image, act on the label).

### Setup & run — JetBot

```bash
# On the Jetson Nano itself (JetBot's own README/docs — not reproduced on the robot in this lab)
python3 setup.py install                 # runs cmake+make for ssd_tensorrt, then pip-installs jetbot
# Then open one of the notebooks/ under Jupyter and run cells — no launch file, no colcon.
```
There is no PC/robot split like the ROS bots — the Jetson runs the code *and* serves the
Jupyter UI over the network to a browser.

---

## 5. How the autonomy stack actually works, end to end

This section is BeetleBot/Acrux-specific (both run the same architecture: Nav2 + a
`robot_localization` EKF + a swappable SLAM back-end). It walks the pipeline **in the order
data actually flows** — sensors in, wheel motion out — then shows the one diagram that ties
every stage together. Everything named here is a real node/topic you saw in §2/§3, with the
real config values from `lyra_localization/config/ekf.yaml`, `lyra_nav2/config/*.yaml`,
`lyra_slam/config/slam_toolbox.yaml`, and Acrux's equivalents.

### 5.1 Localization — turning raw sensors into "where am I"

Localization runs in **two layers**, continuously, whether or not a map exists:

**Layer 1 — wheel + IMU fusion (always running).** `lyra_bridge` publishes raw
`/wheel_ticks`; `wheel_odom_node.py` integrates differential-drive kinematics on those ticks
into `/wheel/odom` (position + velocity, but **drifts** over distance/time — skid-steer
wheels slip, and ticks alone can't sense yaw error from wheel slip). The IMU
(`/imu/data_raw` from `lyra_bridge`, filtered by `lyra_localization/config/imu_filter.yaml`)
gives an independent yaw-rate/orientation signal that doesn't drift the same way wheels do.
`robot_localization`'s `ekf_filter_node` (`lyra_localization/config/ekf.yaml`) fuses both
in a **2D Extended Kalman Filter**:
- `odom0: /wheel/odom`, `odom0_config` selects only `x, y, vx` from it (position + forward
  velocity — trusts wheels for translation, not rotation).
- `imu0: /imu/data`, `imu0_config` selects only `vyaw` (yaw rate) — trusts the IMU for
  rotation, not the wheels' differential-slip-prone yaw estimate.
- `frequency: 20.0` — outputs a fused estimate at 20 Hz, matching the bridge's control loop.
- `world_frame: odom`, `publish_tf: true` — the EKF is what actually **broadcasts the
  `odom → base_footprint` transform** on `/tf`; nothing downstream (SLAM, AMCL, Nav2) can
  work without this, since they all reason in terms of TF frames, not raw topics.
- Output: `/odometry/filtered` (`nav_msgs/Odometry`) — this is the topic every other
  component in this section actually consumes, not `/wheel/odom` directly.

Acrux runs the identical pattern with `acrux_slam/config/ekf.yaml` (`wheel/odometry` +
`bno055/imu`) — though as noted in §3, its shipped config has `imu0_config` all-`false`,
so in practice only wheel odometry is fused there; a live-robot debugging exercise is to
notice `/odometry/filtered` drifting on turns and trace it back to that config.

**Layer 2 — global correction against a map (only in navigation mode, not mapping mode).**
Wheel+IMU fusion alone still drifts unboundedly over a long run (no absolute reference).
Once a map exists, **AMCL** (`lyra_nav2/config/amcl.yaml`) adds the missing global anchor:
- Maintains a **particle filter** — 500–2000 weighted pose guesses (`min/max_particles`) —
  each representing "the robot might be here, facing this way."
- On each `/scan` (subject to `update_min_d`/`update_min_a` — don't recompute for
  sub-15cm/~8.6° motion) it moves every particle per the `differential` motion model, then
  reweights each particle by how well *that* hypothetical scan would match the real LiDAR
  hit pattern against the static `/map` (`laser_model_type: likelihood_field`, tuned by
  `z_hit`/`z_short`/`z_max`/`z_rand`/`sigma_hit` — essentially "how much do I trust a clean
  hit vs. noise vs. a max-range miss").
- Resamples (keeps likely particles, drops unlikely ones) and publishes the best estimate as
  the **`map → odom`** transform correction — note this is a *different* TF edge than the
  EKF's `odom → base_footprint`; together `map → odom → base_footprint` is the complete
  chain Nav2 needs, and it's why `global_frame_id: map` / `odom_frame_id: odom` /
  `base_frame_id` all have to be configured consistently across the EKF, AMCL, and the URDF.
- `set_initial_pose: false` here means AMCL starts globally uncertain (particles spread
  across the whole map) rather than assuming the robot is exactly at the map origin — you
  either set an initial pose in RViz ("2D Pose Estimate") or let it globally localize.

**In one sentence:** wheel+IMU EKF answers "how have I moved since I started" (relative,
drifts); AMCL answers "where am I on this specific map" (absolute, needs a map, corrects
the drift). Nav2 needs both — the EKF for smooth, high-rate local motion estimates between
scans, AMCL for not being lost after ten minutes of driving.

### 5.2 SLAM — building the map that AMCL will later use

SLAM only runs in **mapping mode** (you have no map yet, or are deliberately re-mapping);
it is mutually exclusive with AMCL's map-based localization above, because SLAM Toolbox
*replaces* the "what is `map`" question — it publishes the `map → odom` transform itself,
based on scan matching rather than particles against a fixed map.

**SLAM Toolbox** (both bots' primary/default SLAM, `lyra_slam/config/slam_toolbox.yaml`):
- Inputs: `/scan` and `/odometry/filtered` (the same EKF output from §5.1 — SLAM still
  needs a good short-term motion estimate to know how far the robot moved between scans
  before it tries to correct that estimate with scan matching).
- **Scan matching**: for each new scan, searches a small window of candidate poses near the
  odometry prediction (`correlation_search_space_dimension: 0.5` m,
  `correlation_search_space_resolution: 0.01` m) and picks the pose that makes the new scan
  line up best against previously-seen structure — this correction is what keeps the map
  from smearing as odometry drifts.
- **Pose graph + loop closure**: internally, SLAM Toolbox is a graph of robot poses
  connected by scan-match constraints; `do_loop_closing: true` +
  `loop_search_maximum_distance: 3.0` means when the robot returns near a place it's been
  before, it searches for a match and — if found — adds a constraint that lets it
  retroactively correct the *entire* accumulated path (fixing drift globally, not just
  locally), then republishes a corrected `/map`.
- Runs in `mode: mapping`; only moves/updates the map when the robot has moved
  `minimum_travel_distance: 0.15` m or turned `minimum_travel_heading: 0.35` rad since the
  last update — this is a compute-saving throttle, not a limitation of the algorithm.
- Output: `/map` (`nav_msgs/OccupancyGrid`) at up to `map_update_interval: 0.5` s, plus the
  `map → odom` TF.
- You then **save** it: `ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map` (writes a
  `.pgm` image + a `.yaml` with resolution/origin) — this saved map is exactly what AMCL
  loads back via `map_server` in navigation mode.

**Cartographer** (Acrux alternative, `acrux_slam/config/lidar.lua`) — same job, different
mechanism, worth contrasting directly since Acrux ships both:
- Builds small **submaps** (`TRAJECTORY_BUILDER_2D`) instead of one continuous map, each
  built from a short run of consecutive scans (`num_accumulated_range_data: 1` here — one
  scan per submap-update step at this LiDAR's rate).
- Matches each new scan against the *current* submap using a **real-time correlative scan
  matcher** (`use_online_correlative_scan_matching: true`, searching a
  `linear_search_window: 0.1` m — much tighter than SLAM Toolbox's, because this pass is
  meant to be cheap/fast, done every scan) for local consistency.
- Separately, a background **pose graph optimizer** (`POSE_GRAPH`) periodically
  (`optimize_every_n_nodes: 35`) does the heavier global consistency pass, finding
  constraints between submaps (`constraint_builder.min_score: 0.65` = how confident a match
  must be to accept it) and adjusting the whole graph — Cartographer's version of loop
  closure, done less often but over a richer submap-vs-submap comparison than SLAM
  Toolbox's scan-vs-scan.
- `use_imu_data: false` here — this particular config trusts scan matching alone, not IMU,
  for local consistency (contrast with BeetleBot's EKF, which does fuse IMU one layer down
  in the odometry it feeds in).
- Net effect for you as an operator: functionally the same output (`/map`), different
  internal trade-off — Cartographer's submap approach scales better to large/complex spaces,
  SLAM Toolbox is simpler to tune and is what's actually used across both robots by default.

**gmapping** (`acrux_slam/config/gmapping.yaml`) — the oldest of the three, a
Rao-Blackwellized particle filter (conceptually: like AMCL's particle filter, but each
particle *also* carries its own candidate map, not just a pose) — kept in Acrux mostly for
historical/comparison reference; SLAM Toolbox has superseded it in current Nav2 setups.

### 5.3 Obstacle avoidance — two genuinely different mechanisms in this repo

Don't conflate these; they solve overlapping problems in incompatible ways and only one
runs at a time in practice:

**(A) Reactive, no map, no Nav2 — the handout's own node.** Fully detailed already in
`02-ros2-concepts.md` §5 (windowing, the reverse state machine, the SIGINT stop-20-times
safety handler) — summary for how it fits *here*: it subscribes `/scan` directly and
publishes straight to `/cmd_vel_nav`, with **no localization, no map, no costmap** in the
loop at all. It only knows "something is 0.45 m in front of me right now"; it has no memory
of where obstacles were a second ago and no notion of a goal to reach. This is what Lab 3
runs standalone (`ros2 run lyra_control obstacle_avoid`), *instead of* Nav2, not alongside it.

**(B) Costmap-based, inside Nav2 — what actually protects the robot during navigation.**
This is not a separate node you run; it's built into the Nav2 pipeline itself, via two
costmaps (`lyra_nav2/config/nav2_params.yaml`, `local_costmap`/`global_costmap` sections):
- Each costmap is a grid (`resolution: 0.05` m/cell) built from layered sources
  (`plugins: [static_layer, obstacle_layer, inflation_layer]`):
  - `static_layer` — the fixed occupied/free cells from the saved SLAM map.
  - `obstacle_layer` — marks cells hit by the live `/scan` as occupied
    (`marking: true`, up to `obstacle_max_range`) and **clears** cells the laser saw *through*
    as free (`clearing: true`, via raytracing out to `raytrace_max_range`) — this is how a
    person who walked through and left gets un-marked automatically, unlike the static layer.
  - `inflation_layer` — expands every occupied cell outward by `inflation_radius`
    (0.25 m local / 0.3 m global here) with a cost that decays by `cost_scaling_factor`,
    so the planner is discouraged from planning a path that grazes an obstacle even if the
    exact `robot_radius` (0.15 m) circle would technically clear it — a safety margin, not a
    hard wall.
- The **local costmap** is a small (`5 m × 5 m`), robot-centered, `rolling_window: true`
  grid recomputed at `update_frequency: 10.0` Hz — this is what the controller (§5.4) checks
  every control cycle to react to obstacles *right now*, including ones the static map never
  knew about (a chair someone moved).
- The **global costmap** is the full map-sized (`100 × 100` cells at 5 cm = 10 m × 10 m
  here), fixed-position (`rolling_window: false`) grid the *planner* uses to find a path
  that avoids known obstacles over the whole environment, not just nearby ones.
- The controller's own collision check (`FollowPath.use_collision_detection: true`,
  `max_allowed_time_to_collision_up_to_carrot: 1.0`) additionally refuses to execute a
  velocity command that would run into the local costmap within the next second, even if
  the planned path looked clear a moment ago.

Net difference: (A) is a single node reacting to raw geometry with no goal; (B) is an
integrated part of "drive to this goal without hitting anything," using two costmaps + a
controller-level collision check, all built from the same `/scan` topic (A) reads directly.

### 5.4 Navigation (Nav2) — the goal-directed layer that ties it together

Nav2 is a set of cooperating servers, orchestrated by a **behavior tree** (`bt_navigator`),
not one monolithic node:

1. You (or a waypoint follower) send a **goal pose** (via RViz's "Nav2 Goal" or the
   `NavigateToPose` action) to `bt_navigator`.
2. `bt_navigator` runs its behavior tree, which (in the default tree) calls the
   **`planner_server`** to compute a global path: `GridBased` here is
   `nav2_navfn_planner::NavfnPlanner` — a Dijkstra/A*-family search over the **global
   costmap** (§5.3) from current pose to goal (`use_astar: false` = plain Dijkstra in this
   config; `allow_unknown: true` lets it plan through not-yet-seen cells, useful mid-SLAM).
3. The path is handed to the **`controller_server`**, which runs `FollowPath` —
   `nav2_regulated_pure_pursuit_controller` here: it picks a "carrot" point on the path
   `lookahead_dist` ahead (dynamically between `min`/`max_lookahead_dist` based on speed),
   steers toward it, and **regulates speed down** (`use_regulated_linear_velocity_scaling`)
   when approaching sharp turns (`regulated_linear_scaling_min_radius: 0.9` m) or the goal
   (`approach_velocity_scaling_dist`) — this is the node that actually publishes
   `/cmd_vel_nav` at `controller_frequency: 10.0` Hz, checking the **local costmap** (§5.3)
   for imminent collisions every cycle.
4. `bt_navigator` also watches a `progress_checker` (has the robot moved
   `required_movement_radius` in `movement_time_allowance` seconds? if not, it's stuck) and
   a `goal_checker` (`xy_goal_tolerance: 0.15` m, `yaw_goal_tolerance: 0.2` rad — when to
   declare success).
5. On failure/stuck conditions, the tree calls into the **`behavior_server`**'s recovery
   plugins — `spin`, `backup`, `drive_on_heading`, `wait` — to try to get unstuck before
   giving up or retrying the planner.

`/cmd_vel_nav` is exactly the topic `lyra_control`'s mux (§2) treats as priority-5 — so
Nav2's output is always subordinate to a human on the joystick, by design.

### 5.5 The whole pipeline, plugged together

```
                         ┌────────────────────────────────────────────┐
                         │              SENSORS                       │
                         │  RPLiDAR /scan     IMU /imu/data_raw        │
                         │  wheel ticks (via lyra_bridge, 20 Hz)       │
                         └───────┬───────────────────┬────────────────┘
                                 │                    │
                    wheel_odom_node.py         imu_filter (lyra_localization)
                                 │                    │
                                 v                    v
                         ┌─────────────────────────────────┐
                         │   EKF  (robot_localization)      │  §5.1 Layer 1
                         │   fuses wheel xy/vx + IMU vyaw    │
                         └───────────────┬───────────────────┘
                                          │ /odometry/filtered  +  odom→base_footprint TF
                     ┌────────────────────┼─────────────────────────┐
                     │ MAPPING MODE       │        NAVIGATION MODE   │
                     v                     │                          v
           ┌──────────────────┐            │                ┌───────────────────┐
           │ SLAM Toolbox /    │            │                │  AMCL              │  §5.1 L2 / §5.2
           │ Cartographer      │            │                │  (needs a saved     │
           │ builds /map,       │            │                │  /map from SLAM)    │
           │ publishes map→odom │            │                │  publishes map→odom │
           └────────┬──────────┘            │                └─────────┬───────────┘
                    │ save with map_saver ───┘                          │
                    │ (produces the .pgm/.yaml AMCL loads)              │
                    v                                                   v
           (map artifact on disk)                          ┌─────────────────────────┐
                                                             │ Nav2 costmaps            │  §5.3(B)
                                                             │ local (5x5m, rolling) +   │
                                                             │ global (full map)         │
                                                             └────────────┬──────────────┘
                                                                          │
                                                             ┌────────────v──────────────┐
                                                             │ planner_server (global path)│  §5.4
                                                             │ controller_server (FollowPath)│
                                                             │ behavior_server (recovery)   │
                                                             └────────────┬──────────────┘
                                                                          │ /cmd_vel_nav
                                                                          v
                                                             ┌─────────────────────────┐
             /cmd_vel_joy (joystick, prio 10) ──────────────>│  cmd_vel_mux             │  §2
             /cmd_vel_manual (keyboard, prio 1) ────────────>│  (priority arbitration)   │
                                                             └────────────┬──────────────┘
                                                                          │ /cmd_vel_raw
                                                                          v
                                                             ┌─────────────────────────┐
                                                             │  lyra_bridge              │
                                                             │  20 Hz motor loop,        │
                                                             │  cmd_vel timeout deadman  │
                                                             └────────────┬──────────────┘
                                                                          │ UART binary frames
                                                                          v
                                                             ┌─────────────────────────┐
                                                             │  STM32F405 "Lyra"         │
                                                             │  20 Hz real-time PID       │
                                                             └────────────┬──────────────┘
                                                                          v
                                                                     4× DC motors

     ── reactive path (mutually exclusive with the whole Nav2 branch above) ──
     RPLiDAR /scan ──> obstacle_avoidance.py (windowing + state machine) ──> /cmd_vel_nav
```

Reading the diagram top to bottom is the whole answer to "how does it plug together": raw
sensors feed **one** shared EKF that every downstream consumer trusts for short-term pose;
that pose feeds **either** SLAM (to build a map you save for later) **or** AMCL (to localize
against a map you already have) — never both at once; AMCL/the map feed Nav2's two costmaps;
the costmaps feed the planner and controller; the controller's `/cmd_vel_nav` output is just
one more input into the same priority mux that also takes joystick and manual input; and
every path — Nav2's, the joystick's, or the manual teleop's — funnels through the identical
`lyra_bridge` deadman-switch-protected motor loop before it ever reaches a wheel.

---

## 6. Cross-repo comparison — SLAM/localization/nav choices

| Capability | BeetleBot | Acrux | JetBot |
|---|---|---|---|
| Wheel+IMU fusion | `robot_localization` EKF (`ekf.yaml`) | `robot_localization` EKF (`ekf.yaml`, IMU fusion left off in shipped config) | none — no fused pose estimate at all |
| Map-based localization | AMCL | AMCL (`acrux_navigation/config/nav2_params.yaml`) | none |
| SLAM options | SLAM Toolbox | SLAM Toolbox, Cartographer, gmapping (3 configs, pick one) | none |
| Obstacle avoidance | reactive LaserScan node (Lab 3) **or** Nav2 costmaps (mutually exclusive, §5.3) | Nav2 costmaps; can also fuse a RealSense depth scan into the LiDAR scan (`merge_scan.launch.py`) for a wider sensed field | camera + CNN classifier (`collision_avoidance` notebook) — perception, not geometry |
| Navigation framework | Nav2 (Regulated Pure Pursuit + Navfn planner) | Nav2 (same node types, different tuning + more launch flexibility via `autobringup` args) | none — teleoperation/notebook-driven only |
| Simulation | Gazebo Harmonic | Gazebo (`acrux_gazebo`, includes a warehouse world) | none |

Next: nothing further in this repo's `learn/` set walks all three robots at once — for
ROS 2 concepts applied to *other kinds* of robots entirely (arms, legged, aerial), see
`09-ros2-across-robot-types.md`.
