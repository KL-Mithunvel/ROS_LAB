# 01 — BeetleBot lab-day runbook (consolidated)

One procedure, reconciled from the four handouts in `docs/`. Where they disagree, this file
picks the safest interpretation and flags it. **Confirm the starred (⚠️) values with the
instructor before you start.**

Source handouts:
- `docs/Beetlebot Manual.docx` — the phase-by-phase lab manual
- `docs/VEEROBOT BEETLE BOT LYRA.txt` — the Lyra operation manual + automated move commands + teleop guide
- `docs/BEETLEBOT  Obstacle_avoid.txt` — obstacle-avoidance task (v1)
- `docs/BEETLEBOT Updated _Obstacle_avoid.txt` — obstacle-avoidance task (v2, fuller — use this)

---

## Fixed facts (same across handouts)

| Thing | Value |
|---|---|
| ROS 2 version | **Jazzy** |
| SSH username | `veerobot` |
| SSH password | `veerobot` |
| Robot's ROS workspace | `~/lyra_ws` |
| Drive topic | **`/cmd_vel_nav`** (NOT `/cmd_vel` — the upstream repo uses `/cmd_vel`, the lab does not) |
| Arm service | `ros2 service call /lyra/arm std_srvs/srv/Trigger` |
| Disarm service | `ros2 service call /lyra/disarm std_srvs/srv/Trigger` |
| Bringup launch | `ros2 launch lyra_bringup robot.launch.py` |
| LiDAR topic | `/scan` (`sensor_msgs/msg/LaserScan`) |
| IMU topic | `/imu/data_raw` |

## ⚠️ Confirm these with the instructor

| Thing | Handout values | What to do |
|---|---|---|
| Your robot number | used as last octet of IP **and** `ROS_DOMAIN_ID` | get your assigned number |
| Robot IP | `192.168.0.128` / `.129` / `.<yourNumber>` | almost certainly `192.168.0.<yourNumber>` |
| Robot hostname | `beetlebot-124.local` | try `ssh veerobot@<hostname>` as a fallback to the IP |
| Wi-Fi SSID / password | `BEETLEBOT_5G` / `15619xxx` (truncated) | get the full password |
| Your workspace name | `~/ros2_ws` or `~/<registerNumber>_ws` | use your register number |

---

## Phase 0 — Local setup (once, on the lab PC, before the robot)

```bash
# make your own workspace
mkdir -p ~/<registerNumber>_ws/src
cd ~/<registerNumber>_ws
source /opt/ros/jazzy/setup.bash
colcon build                       # builds an empty ws — just to create install/
echo "source ~/<registerNumber>_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### Sanity-check ROS itself with turtlesim
```bash
sudo apt update && sudo apt install ros-jazzy-turtlesim
ros2 run turtlesim turtlesim_node                 # terminal 1
ros2 run turtlesim turtle_teleop_key              # terminal 2 — arrow keys move it
ros2 topic list                                   # terminal 3
ros2 topic echo /turtle1/cmd_vel
```
If the turtle moves and `echo` prints Twist messages, your ROS install is fine.

---

## Phase 1 — Connect the PC to the robot

1. Turn on the robot. Wait ~30–60 s for it to boot.
2. On the PC, connect to Wi-Fi **`BEETLEBOT_5G`** (password from instructor).
3. Confirm you're on the right subnet and the robot answers:
   ```bash
   ip a                          # your address should be 192.168.0.x
   ping 192.168.0.<robotNumber>  # Ctrl+C once you see replies
   ```
   Timeouts → power-cycle the robot, re-check Wi-Fi, re-check the number.

---

## Phase 2 — Terminal 1: robot bringup (leave running all session)

```bash
ssh veerobot@192.168.0.<robotNumber>        # password: veerobot
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<robotNumber>

# plain drive/teleop session:
ros2 launch lyra_bringup robot.launch.py

# OR, for the mapping task, with extra sensors:
ros2 launch lyra_bringup robot.launch.py mode:=slam camera:=true imu:=true
```

Leave this terminal alone. It's printing LiDAR + motor bridge logs. Closing it kills the robot's drivers.

---

## Phase 3 — Verify from the PC (new terminal, on the PC)

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=<robotNumber>          # MUST match Terminal 1

ros2 node list                              # should list lyra_* nodes
ros2 topic list                             # should include /scan /odom /cmd_vel_nav /imu/data_raw
ros2 topic echo /scan --once                # one LaserScan message
ros2 topic hz /scan                         # ~10 Hz
```

**If `ros2 topic list` is empty or missing the robot's topics:** domain ID mismatch, wrong
Wi-Fi, or `ROS_LOCALHOST_ONLY=1` is set. Fix before continuing — nothing downstream works.

---

## Phase 4 — Terminal 2: arm and drive (new SSH session)

```bash
ssh veerobot@192.168.0.<robotNumber>
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<robotNumber>

# 1. ARM (motors ignore all velocity until armed)
ros2 service call /lyra/arm std_srvs/srv/Trigger

# 2a. one-shot forward pulse (0.3 m/s):
ros2 topic pub --once /cmd_vel_nav geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 2b. OR keyboard teleop (default cmd_vel remapped to the robot's topic):
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=cmd_vel_nav
#   i = forward   , = back   j = left   l = right   k = stop
#   q/z = all speeds ±10%   w/x = linear ±10%   e/c = angular ±10%

# 3. DISARM when done
ros2 service call /lyra/disarm std_srvs/srv/Trigger
```

### Automated move recipes (from the Lyra manual)
`-r 10` = 10 Hz, `-t 50` = 50 messages (so `-t 50` at 10 Hz ≈ 5 s). Always chain a stop.

```bash
# forward 5 s then forced stop 1.5 s
ros2 topic pub -r 10 -t 50 /cmd_vel_nav geometry_msgs/msg/Twist \
  "{linear: {x: 0.3}, angular: {z: 0.0}}" && \
ros2 topic pub -r 10 -t 15 /cmd_vel_nav geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"

# spin in place: linear.x 0.0, angular.z 0.5
# emergency flood-stop: publish zeros at 20 Hz for 40 msgs
ros2 topic pub -r 20 -t 40 /cmd_vel_nav geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

---

## Phase 5 — Record and visualise (PC, more terminals — each `source` + `export`)

```bash
ros2 topic echo /scan > scan_output.txt         # text capture (Ctrl+C to stop)

ros2 bag record /scan                           # bag capture
ros2 bag record -o scan_data_bag /scan
ros2 bag record -o my_cmd_vel_bag /cmd_vel_nav
ros2 bag record -a                              # everything
ros2 bag info scan_data_bag                     # inspect
ros2 bag play scan_data_bag                     # replay

ros2 run rviz2 rviz2                            # add displays: LaserScan (/scan), Map, TF
rqt                                             # camera feed, topic monitor, etc.
ros2 run rqt_graph rqt_graph                    # node/topic graph
```

---

## Phase 6 — SLAM mapping and saving the map

1. Terminal 1 bringup with `mode:=slam camera:=true imu:=true` (Phase 2).
2. On the PC, open RViz (`ros2 run rviz2 rviz2`), add a **Map** display on `/map`.
3. Drive slowly (Phase 4 teleop, keep under ~0.5 m/s) to cover the area. Watch the map fill in.
4. Save it (on the robot, or wherever `/map` is visible — needs `nav2-map-server`):
   ```bash
   sudo apt install ros-jazzy-nav2-map-server           # once
   ros2 run nav2_map_server map_saver_cli -f ~/my_map
   ```
   Produces `~/my_map.pgm` (image) + `~/my_map.yaml` (metadata).
5. Copy the map to the PC:
   ```bash
   scp veerobot@192.168.0.<robotNumber>:'~/my_map.*' ./maps/
   ```

---

## Phase 7 — Autonomous navigation (if the lab covers it)

```bash
# Terminal 1 (robot): launch with the saved map
ros2 launch lyra_bringup robot.launch.py    # (nav variant / pass the map per instructor)
# PC: RViz -> "2D Pose Estimate" to set where the robot is
#            "2D Nav Goal"      to send it somewhere
# Terminal 2 (robot): ros2 service call /lyra/arm std_srvs/srv/Trigger
```
Upstream shortcut form (only if `lyra_commands.sh` is sourced): `lyra-launch-robot-nav ~/maps/house_map.yaml`.

---

## Emergency stops — know all of these cold

| Situation | Action |
|---|---|
| Normal stop of your node / a launch | **`Ctrl+C`** in that terminal (obstacle-avoidance node zeroes the wheels on the way out) |
| Wheels still spinning after `Ctrl+C` | `ros2 service call /lyra/disarm std_srvs/srv/Trigger` |
| Still moving | publish zero Twist repeatedly: `ros2 topic pub -r 20 -t 40 /cmd_vel_nav geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"` |
| Teleop: instant stop | press `k` |
| Nothing works / lost connection | physically pick up the robot and flip the power/toggle switches |
| Kill all ROS nodes on the robot | `Ctrl+C` Terminal 1; if stuck, from another SSH: `pkill -f ros2` |

---

## Common failures → fix

| Symptom | Cause | Fix |
|---|---|---|
| `ros2: command not found` | didn't `source /opt/ros/jazzy/setup.bash` | source it (every terminal) |
| `ros2 topic list` empty on PC | `ROS_DOMAIN_ID` mismatch / wrong Wi-Fi / localhost-only | `export ROS_DOMAIN_ID=<n>` to match; reconnect Wi-Fi |
| `ssh: connect ... timed out` | wrong IP, robot not booted, wrong network | `ping` first; power-cycle robot |
| Motors don't move after publishing | not armed | `ros2 service call /lyra/arm std_srvs/srv/Trigger` |
| Motors move then stop after ~0.5 s | `cmd_vel` timeout — you sent `--once` | publish continuously (`-r 10`) or use teleop |
| `ros2 run lyra_control obstacle_avoid` → "executable not found" | forgot to add the entry_point / rebuild / re-source | edit `setup.py`, `colcon build --packages-select lyra_control`, `source install/setup.bash` |
| Package builds but import fails | wrong `<depend>` in `package.xml` / didn't source overlay | add deps, re-source |
| `/scan` has `inf`/`nan` values | normal — beyond sensor range | filter with `range_min < r < range_max` (the node does this) |

---

## The 60-second mental checklist before you touch the robot

1. Same Wi-Fi? `ping` works?
2. `ROS_DOMAIN_ID` exported the same in **every** terminal, PC and robot?
3. Both `source` lines run in every ROS terminal?
4. Terminal 1 bringup running and left alone?
5. `ros2 topic list` on the PC shows the robot's topics?
6. **Armed** before expecting motion? Will **disarm** when done?
7. Know where the stop is (`Ctrl+C`, `k`, disarm, power switch)?

Next: `02-lab1-turtlesim-and-workspace.md` (or, for the "why" behind each command,
`../foundations/01-linux-and-shell.md` and `../foundations/02-ros2-concepts.md`).
