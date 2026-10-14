# Acrux Bot: SSH, VNC and Demo/Development Mode Runbook

Scripts in this folder give you SSH control of the Acrux bot, a remote desktop, and a safe switch
between demo (autostart) and development mode. Run them from `waypoint_mission/tools/`.

| Item | Value |
| --- | --- |
| Robot IP | 192.168.0.110 (Wi-Fi `wlp0s20f3`) |
| Hostname | `acrux` (called "bot" in the lab) |
| Login user | `bot` |
| Autostart owner | `rigbetel-labs` (uid 1000) |
| ROS distro | Humble, Ubuntu 22.04 |
| Password | Given by the lab. Never stored in these scripts; type it when `ssh-copy-id` or `sudo` asks |

| File | Purpose |
| --- | --- |
| `setup-key.sh` | One-time: create an SSH key and install it on the robot |
| `acrux` | Everyday CLI: run commands, ROS commands, copy files, build, drive |
| `vnc.sh` | Start a VNC desktop on the robot and tunnel it to your PC |
| `dev-mode.sh` | Switch between autostart (demo) and development mode |
| `acrux.env` | Host, user and key path. Edit if the IP or user changes |
| `acrux_gui.py` | Control panel GUI for all of the above (section 0) |

---

## 0. Control panel (GUI)

```bash
./acrux_gui.py        # runs on the laptop; needs ROS 2 Humble sourced (it re-launches itself with it)
```

One window for the whole gift-greeter project: **E-STOP** (button or Space), camera, LiDAR, map with
robot pose (click-drag to set the initial pose or send a goal), drive pad (hold buttons or W A S D,
capped 0.2 m/s / 0.6 rad/s), mission start/stop plus Next/Skip/Retry/Pause/Home/Quit, and the
**Demo / Development switch, which reboots the robot and reconnects** when it is back. In development
mode the *Drivers* box starts/stops the motor bridge, LiDAR and camera (`sensor-test.sh`).

- **Robot jobs (ROS stacks)...** opens a window that runs background ROS commands on the robot as
  `rigbetel-labs` (detached, pid + log in `/tmp/acrux_jobs/`, survives closing the GUI): SLAM stack,
  navigation on a saved map, save map, AMCL localization, collision monitor, and a custom command.
  Commands are editable; status is polled; **Log** prints the tail. AMCL/safety presets push
  `practice/acrux_greeter/` to `/tmp/acrux_greeter` first. These presets are unverified on the robot
  (guide sections 7-8: check the `cmd_vel` chain and who owns `map -> odom`). **RViz2** starts on the laptop.
- Everything robot-side reuses `acrux`, `dev-mode.sh` and `sensor-test.sh`; IP/key stay in `acrux.env`.
- The robot's sudo password is asked once, kept in memory, never written to disk ("Forget sudo password" clears it).
- **E-STOP is software**: it latches, streams zero `/cmd_vel`, cancels Nav2 goals and repeats a zero over SSH.
  It depends on Wi-Fi and this laptop. Keep a person at the physical power switch.
- The mission program and its safety layer are as described in `learn/build/09-acrux-greeter-mission.md`
  (the collision monitor still runs on the robot).
- Status: rendering, teleop and E-stop latching were tested offline with fake topics; the mode switch +
  reboot + reconnect path has **not** been run against the robot yet.

---

## 1. SSH setup (once)

1. Be on the same network as the robot: `ping 192.168.0.110`.
2. Run `./setup-key.sh`.
3. Enter the robot password when `ssh-copy-id` asks. This is the only time it is needed.
4. Check: `./acrux status` prints hostname, uptime, workspace contents and running ROS nodes.

After this, plain `ssh bot@192.168.0.110` works without a password too.

### Everyday commands

| Command | What it does |
| --- | --- |
| `./acrux status` | Hostname, uptime, workspace, running nodes |
| `./acrux run '<cmd>'` | Run any shell command on the robot |
| `./acrux ros '<cmd>'` | Run with ROS 2 and the workspace sourced, e.g. `./acrux ros 'ros2 topic list'` |
| `./acrux shell` | Interactive shell on the robot |
| `./acrux push <src> <dst>` | Copy PC -> robot |
| `./acrux pull <src> <dst>` | Copy robot -> PC |
| `./acrux sync` | Mirror `bots/acrux` into `~/ros2_ws/src/acrux` on the robot |
| `./acrux build` | `colcon build --symlink-install` on the robot |
| `./acrux drive <lin> <ang> <sec>` | Short velocity pulse (max 0.2 m/s, 0.6 rad/s, 5 s), then zero |
| `./acrux teleop` | WASD keyboard control (see section 4) |
| `./acrux nodes` / `./acrux stop` | List nodes and topics / kill `ros2 launch` processes |

---

## 2. VNC (remote desktop)

```bash
./vnc.sh            # start session, open tunnel, launch viewer
./vnc.sh status     # tunnel state and running VNC sessions
./vnc.sh stop       # close tunnel and kill the robot's VNC session
```

- VNC listens on the robot's **localhost only**; you reach it through an SSH tunnel on `localhost:5901`.
- **First run:** installs TigerVNC and XFCE on the robot (about 400 MB). `sudo` asks for the robot
  password in your terminal. You are also asked to choose a VNC password (6 to 8 characters), stored
  hashed in `~/.vnc/passwd` on the robot.
- **Viewer on your PC:** `sudo apt install tigervnc-viewer` (or Remmina). If none is found, the script
  prints the address; connect any viewer to `localhost:5901`.
- Options: `VNC_GEOMETRY=1920x1080 ./vnc.sh`, `VNC_DISPLAY=2`, `VNC_LOCAL_PORT=5905`.
- The VNC desktop is separate from the robot's physical screen. Run `rviz2` from the XFCE terminal in it.

> Status: `vnc.sh` has been syntax-checked but not yet run end to end on the robot. The first run is the real test.

---

## 3. Demo mode vs development mode

| Mode | Meaning |
| --- | --- |
| **Demo** | `robot_bringup.service` (user unit of `rigbetel-labs`) starts the whole stack at boot via `start.sh`: micro-ROS agent, lidar, cartographer, nav2, joystick teleop |
| **Development** | That service is disabled and stopped. Nothing starts at boot; you launch only what you want |

The lab's `development.sh` / `demo.sh` act on the *calling* user's systemd, so running them as `bot`
does nothing to the `rigbetel-labs` service. `dev-mode.sh` does the equivalent for the right user.

```bash
./dev-mode.sh status   # enabled? active? linger?
./dev-mode.sh on       # development mode: disable + stop service, disable linger
./dev-mode.sh off      # back to demo mode: enable + start service, enable linger
```

- Run it from a **real terminal** as your normal user, **not** with `sudo` on your PC (the script refuses,
  since root has no SSH key). `sudo` on the *robot* asks for the robot password and needs a TTY.
- `status` in development mode shows "user manager down"; that is the expected state, not an error.
- Turning linger off ends that user's systemd manager, so the stack stops immediately. You may see
  "Failed to connect to bus" afterwards; that is expected.
- Verify the stack is down: `./acrux ros 'ros2 node list'` returns nothing.
- Restore with `./dev-mode.sh off`, or run the repo's `demo.sh` as `rigbetel-labs`.

---

## 4. WASD keyboard teleop

```bash
./acrux teleop
```

Run from a real terminal. It opens an SSH session and runs `wasd_teleop.py` on the robot, publishing `/cmd_vel`.

| Key | Action |
| --- | --- |
| `w` / `s` | Forward / back |
| `a` / `d` | Turn left / right in place |
| `q` `e` `z` `c` | Arcs: forward-left, forward-right, back-left, back-right |
| `space` or `x` | Stop immediately |
| `+` / `-` | Speed up / down (default 0.10 m/s and 0.40 rad/s; capped 0.20 m/s and 0.60 rad/s) |
| `p` or `Ctrl-C` | Quit (sends zero) |

- **Deadman:** hold a key to move. The command expires 0.6 s after the last keypress, then one zero is sent.
- **Safe exit:** quitting, Ctrl-C or a dropped SSH session all send zero. The script stays silent while idle so it does not fight other `/cmd_vel` publishers.
- **Needs the motor bridge:** the micro-ROS agent must be running (section 5), and the autostart stack down (section 3) so nothing else publishes `/cmd_vel`.

---

## 5. First movement test (development mode)

With the stack down, the motor bridge (micro-ROS agent on `/dev/esp`) must be started. `bot` is not in
the `dialout` group and the agent lives in `rigbetel-labs`' workspace, so run it as that user:

```bash
./acrux run 'sudo -u rigbetel-labs bash -c "source /home/rigbetel-labs/ros2_ws/install/setup.bash; \
  ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/esp -b 921600"'
```

(Use a second terminal or `setsid -f ... &` to keep it running; it asks for the sudo password.)

Then check and move:

```bash
./acrux ros 'ros2 node list'                  # expect /micro_ros_acrux_node
./acrux ros 'ros2 topic info /cmd_vel'        # one subscriber (the ESP)
./acrux drive 0.1 0 1.5                       # 0.1 m/s forward for 1.5 s, then zero
./acrux ros 'ros2 topic echo --once /wheel/ticks'
```

Clear space around the robot (or lift the wheels) first. Expected: both wheel tick counts rise by a
similar amount (about 194 / 193 in the lab test), then stay flat after the stop.

---

## 6. Sensor tests (lidar, camera)

```bash
./sensor-test.sh preflight        # read-only: USB, device nodes, free ports, temperatures
./sensor-test.sh run              # start drivers -> warm up -> check -> stop
./sensor-test.sh start lidar      # or: camera | all
./sensor-test.sh check            # PASS / LOW / FAIL per topic, plus content sanity
./sensor-test.sh stop
```

Drivers run as `rigbetel-labs`, so `start`/`stop` ask for the robot's sudo password (real terminal).
Options: `SENSOR_IMU=true` also enables the D435i IMU; `SENSOR_RESET=true` hardware-resets the camera on start.

Checks: `/scan` rate and valid-beam percentage; `/camera/color/image_raw`, `/camera/depth/image_rect_raw`,
`/camera/depth/color/points`, `/camera/imu` rates; depth value at image centre; colour brightness; IMU
gravity magnitude.

## 7. Troubleshooting and known issues

| Symptom | Cause / fix |
| --- | --- |
| Topics listed but no data (`NO DATA` on `ros2 topic hz`) | FastDDS shared memory fails between different Linux users. `./acrux ros` uses `~/fastdds_udp.xml` (UDP only) automatically; for manual shells run `export FASTRTPS_DEFAULT_PROFILES_FILE=$HOME/fastdds_udp.xml` |
| `sudo: a terminal is required` | Add `-t` to `ssh`, or run the script from a real terminal |
| `Permission denied` on `/dev/ttyUSB0`, `/dev/video*` | `bot` is not in `dialout` / `video`. Fix: `sudo usermod -aG dialout,video bot`, then log in again |
| `ros2 pkg prefix acrux_*` not found as `bot` | `~/ros2_ws/install` is a stub overlay. The built stack is in `/home/rigbetel-labs/ros2_ws` (not readable by `bot`) |
| `/odom` has no publisher but nav2 subscribes | `acrux_odometry` exists in the `rigbetel-labs` workspace but was not part of the running launch. Check `autobringup.launch.py` |
| `ira_laser_tools` shows as missing in `dpkg` | It is built from source in `rigbetel-labs`' workspace; only needed for the `merge_scan` option |
| RealSense node dies: `librealsense2.so.2.55: cannot open shared object file` | Partial upgrade: camera 4.55.1 needed `librealsense2` 2.55 but 2.54.1 was installed. Fixed 2026-10-12 by upgrading `ros-humble-librealsense2`, `-realsense2-camera`, `-realsense2-camera-msgs` together to 2.58.4 / 4.58.4 and `ros-humble-diagnostic-updater` to 4.0.7 |
| RealSense topics are `/camera/camera/...` | camera 4.58 default namespace. Existing launch files (`realsense_d435i.launch.py` remap, `merge_scan`) assume `/camera/...`; use `camera_namespace:=` or update the remaps |
| RealSense `Left MIPI error` / no frames after restarts | Sensor stuck after a forced kill. Start once with `SENSOR_RESET=true` (`initial_reset:=true`) |
| RealSense IMU: `Failed to open scan_element ... Hid device is busy` | No udev rules for non-root access to the HID/IIO IMU. Install the librealsense `99-realsense-libusb.rules`, or run with the IMU disabled (default in `sensor-test.sh`) |
| `ros2 topic hz` shows NO DATA for images/point clouds | Large messages over UDP-only DDS; use the Python probe (`sensor_probe.sh`) or bump `net.core.rmem_max` |
| `apt update`: `EXPKEYSIG F42ED6FBAB17C654 Open Robotics` | Expired ROS apt key. Fixed 2026-10-12: replaced `/usr/share/keyrings/ros-archive-keyring.gpg` with the current `ros.key` from `ros/rosdistro` (backup: `ros-archive-keyring.gpg.bak-20261012`) |
| Command line wraps and breaks when pasted | Use the scripts above instead of long one-liners |

Safety: never edit the lab's `development.sh` / `demo.sh` (they carry a warning). `acrux drive` is clamped
and always ends with a zero command, but keep clear of the robot during tests.
