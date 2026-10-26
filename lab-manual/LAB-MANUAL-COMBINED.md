# Autonomous Mobile Robots — Lab Manual

**Course:** BMHA314E Autonomous Mobile Robots (practical component)
**Platforms:** VEEROBOT BeetleBot "Lyra" (Experiments 2–4, ROS 2 Jazzy, Raspberry Pi 5), VEEROBOT Acrux (Experiment 5, Nav2), a plain computer (Experiment 6, Python) and the UNO Smart Robot Car Kit (Experiment 7, Arduino — no ROS)
**Author:** kl mithunvel

---

## How to use this manual

Each experiment has the same layout so you can write the record straight from it:

1. **Aim** · 2. **Learning outcomes** · 3. **Apparatus** · 4. **Theory** · 5. **Pre-lab questions** ·
6. **Procedure** · 7. **Observations** · 8. **Result** · 9. **Viva questions**

Background and deeper explanations live in the study guides under `learn/`; this manual links
to them instead of repeating them. Commands are marked **[PC]** (lab computer) or **[Robot]**
(inside an SSH session) — mixing these up is the most common lab mistake.

## Experiment list

| # | Experiment | Platform | Syllabus experiment it serves* | Guide |
|---|---|---|---|---|
| 1 | Workspace setup and turtlesim publish/subscribe | PC only | 1 — Set up ROS, fundamentals | `learn/lab/02-…` |
| 2 | Connecting to BeetleBot and movement commands | BeetleBot | 1 (fundamentals on real hardware) | `learn/lab/03-…` |
| 3 | LiDAR obstacle avoidance | BeetleBot | 3–4 (perception → control loop) | `learn/lab/04-…` |
| 4 | Colour-based control with the camera | BeetleBot | 5 — Object detection (OpenCV) | `learn/lab/05-…` |
| 5 | Waypoint navigation mission | Acrux | 3–4 — SLAM and path planning (Nav2) | `waypoint_mission/` |
| 6 | Mobile-robot mechatronics calculations | PC (Python) | Locomotion, kinematics and dynamics (course Module 2) | `robot_calc/` |
| 7 | UNO car: PID line following + obstacle avoidance | UNO Smart Robot Car | Reactive control and sensing (non-ROS contrast to 3–5) | `uno_car/` |

\*The syllabus lists six indicative experiments in ROS 1 vocabulary (`move_base`, `actionlib`).
Map them to ROS 2 as: `move_base` → **Nav2**, `actionlib` → **ROS 2 actions**, `catkin` →
**`colcon`**, `roscore` → **DDS discovery** (`learn/foundations/04-ros1-vs-ros2.md`).
Syllabus experiments 2 (Gazebo simulation of a TurtleBot-class robot) and 6 (multi-robot
communication) are not covered by a robot experiment here; study material is
`learn/build/05-simulation-gazebo.md` and `learn/build/02-ros2-across-robot-types.md`.

## Ground rules and safety

1. **Robot on a stand or in clear floor space** (≥1 m around it) before arming. Never test a new node with the wheels on the floor and people in reach.
2. **Arm only when ready, disarm when done** (`/lyra/arm`, `/lyra/disarm`). BeetleBot boots disarmed on purpose.
3. **Know every way to stop before you start**: `Ctrl+C` the node → zero-Twist flood (`ros2 topic pub -r 20 -t 40 /cmd_vel_nav … zeros`) → `/lyra/disarm` → power switch. Someone must always be within reach of the power switch.
4. **One person drives, one person watches the robot.** Say "stop" out loud.
5. **Speed limits**: stay at or below 0.3 m/s for first runs (BeetleBot max is 1.0 m/s; Acrux navigation is capped at 0.3 m/s).
6. **Never edit the robot's own packages casually.** Build your code in your own workspace (`~/<registerNumber>_ws`) unless the experiment explicitly says to extend `lyra_control`.
7. **Passwords and Wi-Fi keys come from the instructor.** Do not write them in your record.

## Values to confirm with the instructor

The handouts disagree on these (see `learn/lab/01-lab-day-runbook.md`). Write the confirmed value on the day:

| Item | Handout values | Confirmed on the day |
|---|---|---|
| Robot number (last IP octet and `ROS_DOMAIN_ID`) | `192.168.0.<n>` | |
| Robot hostname | `beetlebot-124.local` | |
| Wi-Fi SSID | `BEETLEBOT_5G` | |
| Drive topic | `/cmd_vel_nav` (lab) vs `/cmd_vel` (upstream) | |

## Standard session header

Every BeetleBot session begins with these lines in **every** terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash        # on the robot only
export ROS_DOMAIN_ID=<robotNumber>         # same number on PC and robot
```

## How to write the lab record

For each experiment submit: aim, apparatus, a short theory paragraph in your own words, the
procedure you actually followed (past tense), your observation tables, any plots/screenshots
(`rqt_graph`, RViz, terminal output), the result, and answers to the viva questions.
**Record observations, not expectations**: if something failed, write what failed and what you
changed. Worked lab records (with blank result tables to fill from the bench) are in `waypoint_mission/LAB-RECORD.md`, `robot_calc/LAB-RECORD.md` and `uno_car/LAB-RECORD.md`.

## Appendix A — Command quick reference

| Task | Command |
|---|---|
| List nodes / topics / services | `ros2 node list` · `ros2 topic list` · `ros2 service list` |
| Inspect a topic | `ros2 topic info <t>` · `ros2 topic echo <t>` · `ros2 topic hz <t>` |
| Publish once / repeatedly | `ros2 topic pub --once <t> <type> "<yaml>"` · `-r 10` (Hz) · `-t 50` (count) |
| Call a service | `ros2 service call <s> <type>` |
| Run / launch | `ros2 run <pkg> <exe>` · `ros2 launch <pkg> <file>` |
| Build | `colcon build --packages-select <pkg>` then `source install/setup.bash` |
| Record / replay | `ros2 bag record -o <name> <topics>` · `ros2 bag play <name>` · `ros2 bag info <name>` |
| Graphs / visualisation | `ros2 run rqt_graph rqt_graph` · `ros2 run rviz2 rviz2` · `rqt` |
| Copy map to PC | `scp veerobot@192.168.0.<n>:'~/my_map.*' ./maps/` |

## Appendix B — Common failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `ping` times out | Wrong Wi-Fi, robot not booted, wrong IP | Check SSID, wait 60 s after power-on, confirm number |
| `ros2 topic list` on PC lacks robot topics | `ROS_DOMAIN_ID` mismatch, different subnet, `ROS_LOCALHOST_ONLY=1` | Export the same ID in every terminal; unset `ROS_LOCALHOST_ONLY` |
| Robot does not move | Not armed; wrong topic; bringup not running | `ros2 service call /lyra/arm …`; publish to `/cmd_vel_nav`; check Terminal 1 |
| Robot moves once then stops | `cmd_vel` timeout in the motor bridge | Publish repeatedly (`-r 10`) or use teleop |
| `ros2 run` says executable not found | Missing `entry_points` line, or build/source skipped | Edit `setup.py`, `colcon build`, `source install/setup.bash` |
| Node cannot import `cv_bridge`/`cv2` | Package missing on the robot | `sudo apt install ros-jazzy-cv-bridge python3-opencv` |

## Appendix C — Where to read more

`learn/README.md` is the index. Foundations: Linux and shell (`learn/foundations/01`), ROS 2
concepts (`02`), official docs index (`03`), ROS 1 vs ROS 2 (`04`). Lab-day procedure:
`learn/lab/01-lab-day-runbook.md`.

<div style="page-break-after: always"></div>

# Experiment 1 — Workspace setup and turtlesim publish/subscribe

## 1. Aim
To set up a ROS 2 (Jazzy) workspace and demonstrate the publish/subscribe model by driving the simulated turtle in `turtlesim`.

## 2. Learning outcomes
After this experiment you can: create and build a colcon workspace; explain underlay vs overlay; start nodes and inspect topics with the `ros2` CLI; identify publisher and subscriber in a running system; record topic data to a bag.

## 3. Apparatus
- Linux PC (Ubuntu 22.04/24.04) with ROS 2 Jazzy, **or** `docker run -it ros:jazzy`
- Packages: `ros-jazzy-turtlesim`, `ros-jazzy-teleop-twist-keyboard`
- No robot needed.

## 4. Theory
ROS 2 is a set of **nodes** (processes) that exchange typed messages over **topics** using DDS.
A **publisher** writes messages to a named topic; every **subscriber** to that topic receives
them through a callback. Nodes do not know each other — they agree only on topic name and
message type. Here, `turtle_teleop_key` publishes `geometry_msgs/msg/Twist` (linear velocity in
m/s, angular velocity in rad/s) on `/turtle1/cmd_vel`; `turtlesim_node` subscribes and moves the
turtle, and publishes its pose on `/turtle1/pose`.

A **workspace** is a folder with `src/` where packages are built by `colcon`, producing
`install/`. Sourcing `install/setup.bash` adds it as an **overlay** on top of the system
**underlay** (`/opt/ros/jazzy`). See `learn/foundations/02-ros2-concepts.md`.

## 5. Pre-lab questions
1. What is the difference between a topic and a service?
2. What fields of `Twist` matter for a differential-drive robot?
3. Why build an empty workspace before you have any code?

## 6. Procedure
**[PC]** — all steps.

1. Create and build the workspace:
   ```bash
   mkdir -p ~/<registerNumber>_ws/src
   cd ~/<registerNumber>_ws
   source /opt/ros/jazzy/setup.bash
   colcon build
   echo "source ~/<registerNumber>_ws/install/setup.bash" >> ~/.bashrc
   source ~/.bashrc
   ```
2. Install and start turtlesim (Terminal 1):
   ```bash
   sudo apt update && sudo apt install ros-jazzy-turtlesim
   ros2 run turtlesim turtlesim_node
   ```
3. Drive it with the keyboard (Terminal 2):
   ```bash
   ros2 run turtlesim turtle_teleop_key
   ```
4. Inspect from Terminal 3:
   ```bash
   ros2 node list
   ros2 topic list
   ros2 topic info /turtle1/cmd_vel
   ros2 topic echo /turtle1/cmd_vel
   ros2 topic hz /turtle1/pose
   ros2 run rqt_graph rqt_graph
   ```
5. Drive without the keyboard node:
   ```bash
   ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
     "{linear: {x: 2.0}, angular: {z: 1.8}}"
   ```
6. Try the general teleop with a remap:
   ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=turtle1/cmd_vel
   ```
7. Record and replay:
   ```bash
   ros2 bag record -o my_cmd_vel_bag /turtle1/cmd_vel      # Ctrl+C to stop
   ros2 bag info my_cmd_vel_bag
   ros2 bag play my_cmd_vel_bag                             # with turtlesim running
   ```

## 7. Observations

| Item | Observed |
|---|---|
| `ros2 node list` output | |
| `ros2 topic list` output | |
| `ros2 topic info /turtle1/cmd_vel` — publisher count / subscriber count | |
| Type of `/turtle1/cmd_vel` | |
| Publish rate of `/turtle1/pose` (`topic hz`) | |
| `Twist` values seen when pressing ↑ / ← | |
| Effect of `topic pub --once` with `{linear: {x: 2.0}, angular: {z: 1.8}}` | |
| Bag: duration, message count (`bag info`) | |
| Screenshot of `rqt_graph` | (attach) |

## 8. Result
☐ State that the workspace built, turtlesim ran, which node was publisher and which subscriber, and that the bag replayed the motion.

## 9. Viva questions
1. Which node is the publisher and which the subscriber in step 3? How do you prove it from the CLI?
2. What happens if two nodes publish to `/turtle1/cmd_vel` at once?
3. Explain `--remap cmd_vel:=turtle1/cmd_vel`.
4. Underlay vs overlay — what happens if you forget to `source` your workspace?
5. What replaced `roscore` in ROS 2?

<div style="page-break-after: always"></div>

# Experiment 2 — Connecting to BeetleBot and movement commands

## 1. Aim
To connect to the BeetleBot over Wi-Fi/SSH, arm its motor controller, and drive it using single messages, timed message streams and keyboard teleoperation.

## 2. Learning outcomes
Connect and verify a ROS 2 network between PC and robot; explain why the controller is disarmed by default; build `Twist` commands for a skid-steer robot; use `-r`/`-t` to publish timed motions; stop the robot safely in several independent ways.

## 3. Apparatus
- BeetleBot "Lyra": 4-wheel skid-steer, Raspberry Pi 5 (ROS 2 Jazzy), STM32F405 motor controller, RPLiDAR C1, max 1.0 m/s
- Lab PC with ROS 2 Jazzy on the `BEETLEBOT_5G` network
- Clear floor area (≥2 m × 2 m)

## 4. Theory
**Architecture.** The Pi runs the ROS 2 stack; `lyra_bridge` talks to the STM32 over UART. The
STM32 (FreeRTOS) runs the real-time PID wheel control. ROS-side code never has deterministic
motor timing.

**Skid-steer kinematics.** Wheels on a side turn together; turning is done by a speed
difference, so the robot is non-holonomic: only `linear.x` (m/s, forward +) and `angular.z`
(rad/s, left +) are meaningful. For a differential model with track width *b*:
v_left = v − ω·b/2, v_right = v + ω·b/2 (see `robot_calc/`, set `dd_kinematics`).

**Safety interlocks.** The controller boots **disarmed**; `/lyra/arm` (`std_srvs/srv/Trigger`)
enables motion. The bridge also has a `cmd_vel` **timeout**: if no fresh command arrives soon,
wheels are zeroed.

**DDS discovery.** PC and robot nodes find each other only on the same subnet **and** same
`ROS_DOMAIN_ID`.

## 5. Pre-lab questions
1. Why only two of the six `Twist` fields matter here?
2. Why does a single `topic pub --once` move the robot only briefly?
3. Why is a service (not a topic) used to arm?

## 6. Procedure
1. **[PC]** Connect to Wi-Fi, then:
   ```bash
   ip a                                   # address should be 192.168.0.x
   ping 192.168.0.<robotNumber>
   ```
2. **[Robot] Terminal 1 — bring-up (leave running):**
   ```bash
   ssh veerobot@192.168.0.<robotNumber>
   source /opt/ros/jazzy/setup.bash
   source ~/lyra_ws/install/setup.bash
   export ROS_DOMAIN_ID=<robotNumber>
   ros2 launch lyra_bringup robot.launch.py
   ```
3. **[PC]** Verify discovery:
   ```bash
   source /opt/ros/jazzy/setup.bash
   export ROS_DOMAIN_ID=<robotNumber>
   ros2 node list
   ros2 topic list
   ros2 topic hz /scan
   ```
4. **[Robot] Terminal 2** (new SSH, same three source/export lines) — arm:
   ```bash
   ros2 service call /lyra/arm std_srvs/srv/Trigger
   ```
5. Single pulse:
   ```bash
   ros2 topic pub --once /cmd_vel_nav geometry_msgs/msg/Twist \
     "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
   ```
6. Timed motion (5 s forward then stop):
   ```bash
   ros2 topic pub -r 10 -t 50 /cmd_vel_nav geometry_msgs/msg/Twist "{linear: {x: 0.3}, angular: {z: 0.0}}" && \
   ros2 topic pub -r 10 -t 15 /cmd_vel_nav geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
   ```
7. Repeat for: backward (`x: -0.3`), spin in place (`x: 0.0, z: 0.5`), and a square path (drive → stop → turn → stop, ×4).
8. Keyboard teleop:
   ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=cmd_vel_nav
   ```
   `i` forward · `,` back · `j`/`l` turn · `k` stop · `q`/`z` speed ±10%.
9. **[PC]** Watch the commands: `ros2 topic echo /cmd_vel_nav`.
10. Practise the stops: flood-stop `ros2 topic pub -r 20 -t 40 /cmd_vel_nav … zeros`, then
    **disarm**: `ros2 service call /lyra/disarm std_srvs/srv/Trigger`.

## 7. Observations

| Test | Command (v, ω, rate, count) | Expected duration (count/rate) | Measured distance / angle | Remarks |
|---|---|---|---|---|
| Single pulse | `x: 0.3`, once | — | | |
| Forward 5 s | 0.3 m/s, 10 Hz, 50 | 5 s | | |
| Backward 5 s | −0.3 m/s | 5 s | | |
| Spin in place | ω = 0.5 rad/s, 10 Hz, ___ | | angle turned: | |
| Square path | | | closing error: | |

| Check | Result |
|---|---|
| `ping` round-trip time | |
| `/scan` rate (`topic hz`) | |
| Does the robot move **before** arming? | |
| Stop methods tried and time to stop | |

## 8. Result
☐ State that the robot was armed, driven by pulses, timed streams and teleop, and compare expected vs measured distance (explain the difference: wheel slip, ramping, timeout).

## 9. Viva questions
1. Why is the controller disarmed at boot? What does arming change?
2. Explain `-r 10 -t 50`. How long does the robot move?
3. Why chain a zero-velocity stop with `&&`?
4. Why `/cmd_vel_nav` and not `/cmd_vel`? (handouts vs upstream repo)
5. What do `ROS_DOMAIN_ID` and the subnet do for discovery?
6. List four independent ways to stop the robot.
7. Why can the PC be Linux while the real-time motor loop is on an STM32?

<div style="page-break-after: always"></div>

# Experiment 3 — LiDAR obstacle avoidance

## 1. Aim
To deploy a Python `rclpy` node on the BeetleBot that reads the LiDAR `/scan` and steers the robot around obstacles, and to compare the simple (v1) and improved (v2) versions.

## 2. Learning outcomes
Write/deploy a node into a ROS 2 package; register it as an `entry_points` console script; build with `colcon`; explain LaserScan windowing and a reactive state machine; implement safe shutdown.

## 3. Apparatus
BeetleBot with RPLiDAR C1 (360°, 12 m); lab PC; obstacles (boxes, walls); source files `docs/BEETLEBOT  Obstacle_avoid.txt` (v1) and `docs/BEETLEBOT Updated _Obstacle_avoid.txt` (v2).

## 4. Theory
`sensor_msgs/LaserScan` holds `ranges[]` at evenly spaced angles; invalid readings (`inf`, `nan`, 0) must be filtered. The node takes **windows** of the array — v1: one front window (~60°); v2: front (~30°), left and right (~60° each) — and uses the minimum valid range in each window.

**Reactive control** (no map, no planning): if the front is clear, drive forward; if
closer than `safe_distance` (0.5 m) stop and turn; v2 additionally has `front_distance` (0.45 m)
below which it **reverses for 0.8 s** and then turns toward the side with more free space.
This is a behaviour-based (Braitenberg-style) controller — fast and simple, but it can get
trapped in local minima because it has no memory or global view.

**Safe shutdown.** A `SIGINT` handler publishes a zero `Twist` 20 times (50 ms apart) so the
last command the motors hear is "stop". Details: `learn/foundations/02-ros2-concepts.md` §5.

## 5. Pre-lab questions
1. Why filter `inf`/`nan` ranges before taking the minimum?
2. What would happen in v1 in a corridor if the fixed turn direction is blocked?
3. Why publish zero velocity several times at shutdown rather than once?

## 6. Procedure
1. **[Robot] Terminal 1** — bring-up (as Experiment 2, step 2). Leave running.
2. **[Robot] Terminal 2** — create the node:
   ```bash
   ssh veerobot@192.168.0.<robotNumber>
   cd ~/lyra_ws/src/lyra_control/lyra_control/
   nano obstacle_avoidance.py        # paste v1 or v2; Ctrl+O, Enter, Ctrl+X
   chmod +x obstacle_avoidance.py
   ```
3. Register the entry point in `~/lyra_ws/src/lyra_control/setup.py`, inside `console_scripts`:
   ```python
   'obstacle_avoid = lyra_control.obstacle_avoidance:main',
   ```
4. Build and source:
   ```bash
   cd ~/lyra_ws
   colcon build --packages-select lyra_control
   source install/setup.bash
   ```
5. Arm and run (robot on the floor, clear area, someone at the power switch):
   ```bash
   ros2 service call /lyra/arm std_srvs/srv/Trigger
   ros2 run lyra_control obstacle_avoid
   ```
6. Place a box ahead, then to one side, then a corridor of two boxes. Observe log lines (`Front | Left | Right`).
7. Stop with `Ctrl+C` **in the node's terminal**, then `ros2 service call /lyra/disarm std_srvs/srv/Trigger`.
8. Repeat steps 2–7 with the other version (v1 ↔ v2).

## 7. Observations

| Scenario | v1 behaviour | v2 behaviour |
|---|---|---|
| Obstacle directly ahead at 1 m | | |
| Obstacle ahead at < 0.45 m | | |
| Obstacle on the left only | | |
| Two-box corridor | | |
| Stuck / oscillated? time to escape | | |

| Parameter | v1 | v2 |
|---|---|---|
| Zones | | |
| `safe_distance` / `front_distance` | | |
| Linear and turn speeds used | | |

## 8. Result
☐ State which version avoided obstacles more reliably and why, and that the robot stopped cleanly on `Ctrl+C`.

## 9. Viva questions
1. Why is the `setup.py` `entry_points` edit required before `ros2 run` works?
2. Why `--packages-select`, and why re-`source` after building?
3. Explain v2's reverse-then-turn state machine.
4. Why compare left and right distances instead of always turning one way?
5. What are the limits of reactive avoidance vs Nav2? (local minima, no map)
6. How does the node behave if `/scan` stops arriving?

<div style="page-break-after: always"></div>

# Experiment 4 — Colour-based control with the camera

## 1. Aim
To deploy a vision node that segments the dominant colour in the centre of the Pi Camera image using OpenCV and drives the BeetleBot accordingly (green = forward, red = stop, blue = backward).

## 2. Learning outcomes
Use `cv_bridge` to convert ROS images to OpenCV; apply HSV thresholding; explain why hue-based segmentation beats RGB under changing light; handle the red hue wrap-around; build a perception→control node with a safe shutdown.

## 3. Apparatus
BeetleBot with Pi Camera V1.3; lab PC; green, red and blue cards/objects; source `docs/color_detection_beetlebot`.

## 4. Theory
**HSV** separates colour (hue) from brightness (value) and saturation, so a threshold on hue is
more robust to lighting than one on R, G, B. OpenCV hue is 0–179, so **red wraps around** and
needs two ranges (near 0 and near 179).

The node: subscribes to `sensor_msgs/Image` on `/pi_camera/image_raw`; converts BGR→HSV;
crops the **centre 50 %** region of interest; masks green, red (two ranges) and blue;
whichever mask covers **> 20 %** of the ROI wins (checked green → red → blue). If none
qualifies it **keeps the previous command**, so a one-frame dropout does not jerk the robot.
It publishes `Twist` on `/cmd_vel_nav`: green `linear.x = 0.2`, red zero (also the initial
state), blue `linear.x = -0.15`.

**Shutdown:** `try/except KeyboardInterrupt` around `rclpy.spin()` and a `finally` that
publishes zero `Twist` 10 times — not a `SIGINT` handler as in Experiment 3.

## 5. Pre-lab questions
1. Why two hue ranges for red?
2. Why crop to a central ROI?
3. What is the risk of "keep the previous command" when the camera is blocked?

## 6. Procedure
1. **[Robot] Terminal 1** — bring-up with the camera:
   ```bash
   ssh veerobot@192.168.0.<robotNumber>
   source /opt/ros/jazzy/setup.bash && source ~/lyra_ws/install/setup.bash
   export ROS_DOMAIN_ID=<robotNumber>
   ros2 launch lyra_bringup robot.launch.py camera:=true
   ```
   Check: `ros2 topic list | grep pi_camera` and `ros2 topic hz /pi_camera/image_raw`.
2. If imports fail later: `sudo apt install ros-jazzy-cv-bridge python3-opencv`.
3. **[Robot] Terminal 2** — place the node:
   ```bash
   cd ~/lyra_ws/src/lyra_control/lyra_control/
   nano color_control.py             # paste docs/color_detection_beetlebot
   chmod +x color_control.py
   ```
4. Register in `setup.py` → `console_scripts`:
   ```python
   'color_control = lyra_control.color_control:main',
   ```
5. Build and source:
   ```bash
   cd ~/lyra_ws && colcon build --packages-select lyra_control && source install/setup.bash
   ```
6. Arm and run:
   ```bash
   ros2 service call /lyra/arm std_srvs/srv/Trigger
   ros2 run lyra_control color_control
   ```
7. Hold a green, red, then blue object to fill about a quarter or more of the centre of the frame. Record the response and the log lines.
8. **[PC]** Optional: view the camera in `rqt` (Image View) and `ros2 topic echo /cmd_vel_nav`.
9. `Ctrl+C` the node, then disarm.

## 7. Observations

| Object shown | Fraction of ROI (approx.) | Command seen on `/cmd_vel_nav` | Robot action |
|---|---|---|---|
| Green | | | |
| Red | | | |
| Blue | | | |
| Nothing / white wall | | | |
| Object at the frame edge (outside ROI) | | | |
| Under dim light | | | |

Threshold ranges used (from the source): green ______ red ______ / ______ blue ______.

## 8. Result
☐ State which colours were reliably detected, the effect of lighting, and the minimum object size that triggered a command.

## 9. Viva questions
1. Why HSV rather than RGB? Why does red need two ranges?
2. What does the 20 % threshold do? What if you lower it to 5 %?
3. How does this node stop on `Ctrl+C`, compared with Experiment 3?
4. What are the latency sources between camera and wheels?
5. Name the ROS perception libraries named in the syllabus (OpenCV, PCL) and when each is used.

<div style="page-break-after: always"></div>

# Experiment 5 — Waypoint navigation mission (Acrux, Nav2)

## 1. Aim
To make the Acrux robot navigate autonomously through up to four pre-surveyed waypoints on a map, stop and wait at each until the operator confirms, avoid unexpected obstacles, and return home.

## 2. Learning outcomes
Build a map with SLAM; survey poses in the `map` frame; send goals to Nav2 through `nav2_simple_commander`; design a testable mission state machine; add a collision-monitor safety layer; test a depth camera as an obstacle sensor.

## 3. Apparatus
- VEEROBOT Acrux (≈0.76 × 0.80 m, LiDAR, Intel RealSense, micro-ROS base), ROS 2 Humble (confirm)
- Laptop with ROS 2 and `nav2_simple_commander` on the same Wi-Fi/`ROS_DOMAIN_ID`
- Project folder `waypoint_mission/` (mission code, config, tools, GUIDE, LAB-RECORD)
- Cardboard boxes as test obstacles; tape for floor markers

## 4. Theory
**Navigation pipeline.** Localisation (`map → odom → base_link` TF chain), global planner
(route on the global costmap), local controller (DWB, follows the path and avoids obstacles on
the local costmap), behaviour tree (retries and recovery). `learn/build/07` and `08`.

**Costmaps.** Obstacles from `/scan` and `/camera/points` are painted into a grid and
**inflated** by the robot's radius plus margin (0.55 m on Acrux), which is why waypoints need
a standoff and lanes ≥ ~1.5 m wide.

**Mission layer.** A ROS-free **finite-state machine** (`mission.py`) decides what happens next:

```
IDLE ─y─► NAVIGATING ─arrived─► AT_WAYPOINT ─y─► NAVIGATING … ─► RETURNING_HOME ─► DONE
           fail → auto-retry → BLOCKED (r retry · s skip · h home)      p pause · q quit
```
Keeping it free of ROS lets `pytest` test every path (60 tests).

**Layered safety.** Costmap re-planning → speed cap (0.3 m/s) → collision monitor (stop box /
slow-down box, runs *on the robot* so Wi-Fi loss cannot disable it) → operator commands →
physical e-stop.

## 5. Pre-lab questions
1. Why does the mission logic run on the laptop but the collision monitor on the robot?
2. Why is `--count` mandatory with no default?
3. What happens if a waypoint lies inside the inflated obstacle region?
4. What breaks if nothing publishes `map → odom`?

## 6. Procedure
Full detail: `waypoint_mission/GUIDE.md` §9–§12.

**A. Preparation**
1. Unit tests **[PC]**: `cd waypoint_mission && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt && pytest` → expect 60 passed.
2. Connect and check **[PC]** (from `waypoint_mission/tools/`): `./acrux status`; then `./acrux ros 'printenv ROS_DISTRO'`.
3. Switch the robot to development mode: `./dev-mode.sh on`; verify `./acrux ros 'ros2 node list'` is empty.
4. Start the micro-ROS agent and do a first movement test: `./acrux drive 0.1 0 1.5` (wheels lifted first).

**B. Sensors, map and survey**
5. LiDAR: `./acrux ros 'ros2 topic hz /scan'`.
6. RealSense: `ros2 topic hz /camera/points`; check stability, CPU load, and whether it sees a table edge the LiDAR misses.
7. SLAM: drive slowly (`./acrux teleop`), close loops, save the map (`map_saver_cli`).
8. Survey home + 4 waypoints (RViz 2D Goal Pose + `ros2 topic echo /goal_pose`, or `/amcl_pose`), enter them in `waypoints.yaml` (robot **centre**, ≥ 0.8 m from the target), set `surveyed: true`.

**C. Safety layer**
9. Find the real velocity chain: `ros2 topic info /cmd_vel -v`; `ros2 topic list | grep cmd_vel`.
10. Launch `launch/safety.launch.py cmd_vel_in:=<nav2 output> cmd_vel_out:=cmd_vel`. Test: while teleoperating forward, put a cardboard box in front — the robot must stop.

**D. Mission test ladder** (stop at the first failure)
11. Gazebo (`--sim`) → robot with wheels lifted → robot with cardboard obstacles → rehearsal with 3 then 4 waypoints.
12. Run **[PC]**: `python3 mission_node.py --count N`. Press `y`/Enter to start and at each waypoint. Other commands: `s` skip · `r` retry · `p` pause/resume · `h` home · `q` quit.
13. During one run, step a box into the path and note the response.

## 7. Observations

**Open-item checks**

| Check | Observed |
|---|---|
| ROS distro | |
| What provides `map → odom`? | |
| `cmd_vel` chain | |
| Collision-monitor parameters accepted? | |
| RealSense rate / CPU / extra obstacles seen | |

**Surveyed poses (map frame)**

| Point | x (m) | y (m) | yaw (rad) |
|---|---|---|---|
| Home | | | |
| Waypoint 1 | | | |
| Waypoint 2 | | | |
| Waypoint 3 | | | |
| Waypoint 4 | | | |

**Runs**

| Run | Environment | N | All reached? | Time (s) | Position error at each waypoint (m) | Obstacle response | Remarks |
|---|---|---|---|---|---|---|---|
| 1 | Gazebo | | | | | | |
| 2 | Wheels lifted | | | | | | |
| 3 | Floor + obstacle | | | | | | |
| 4 | Rehearsal N=3 | | | | | | |
| 5 | Rehearsal N=4 | | | | | | |

## 8. Result
☐ State whether every waypoint was reached, whether the safety stop worked, position accuracy, and the main failure modes.

## 9. Viva questions
1. Describe the mission state machine and what each operator key does.
2. Why wait for a human "yes" rather than a timer?
3. Name the five safety layers and which run on the robot.
4. Why must the stop polygon be front-only?
5. What is inflation, and how does it constrain waypoint placement?
6. What is AMCL, and why does its absence matter on a saved map?
7. Why is a 2D LiDAR not sufficient alone? What does the RealSense add?
8. Why does `mission_node.py` refuse to run when `surveyed: false`?
9. `move_base` (ROS 1) vs Nav2 — what changed?

<div style="page-break-after: always"></div>

# Experiment 6 — Mobile-robot mechatronics calculations

## 1. Aim
To size a mobile robot numerically — tractive effort, motor torque, speed and gearing, battery runtime — and to analyse a differential-drive robot's kinematics and dynamics, using a menu-driven Python program (`robot_calc/`) and checking it against hand calculations.

## 2. Learning outcomes
Compute the forces a drive system must overcome; convert wheel torque to motor torque through a gearbox; relate wheel and motor rpm to linear speed; estimate battery runtime and range; apply forward and inverse kinematics of a differential-drive robot; estimate torque for straight-line acceleration and for spinning in place.

## 3. Apparatus
- Any computer with Python 3.10+ (Windows, Linux or macOS) — no robot or ROS needed
- `robot_calc/` from this repo (`main.py`, `params.yaml`)
- `docs/Kinematics and Dynamics_AMR_Problems.pdf` (worked problems)
- Robot data sheet: mass, wheel radius, gear ratio, motor rpm and stall torque, battery voltage and capacity (BeetleBot figures: `docs/beetlebot/01-introduction.md`)
- Calculator for hand checks

## 4. Theory
Symbols: *m* mass, *g* = 9.81, *θ* slope, *r* wheel radius, *L* track width, *G* gear ratio, *η* efficiency.

**4.1 Tractive effort (set 1)**

| Quantity | Formula |
|---|---|
| Acceleration to top speed | a = v_top / t_acc |
| Normal force | N = m·g·cos θ |
| Acceleration force | F_a = m·a |
| Rolling resistance | F_rr = C_rr·N |
| Slope force | F_g = m·g·sin θ |
| **Total tractive force** | F_total = F_a + F_rr + F_g |
| Wheel torque | T_total = F_total·r ; per driven wheel T_wheel = T_total / n_driven |
| Motor torque | T_motor = T_wheel / (G·η) ; specified T_spec = T_motor·SF |
| Grip available | F_traction = μ_s·N·(driven/total wheels) |
| Traction margin | F_traction − F_total (negative ⇒ wheels slip); steepest slope tan θ_max = μ_s·(driven/total) − C_rr |

C_rr (wheel and bearing drag) and μ_s (the grip limit before slipping) are different coefficients.

**4.2 Speed and gearing (set 2)** — ω = rpm/60·2π ; v = ω·r ; ω_target = v_top/r ; rpm_motor = rpm_wheel·G.

**4.3 Battery (set 3)** — Q_usable = Q_pack·usable fraction ; runtime t = Q_usable/I_avg ; range d = t·3600·v_top ; climbing force F_climb = C_rr·m·g·cos θ + m·g·sin θ ; P_elec = F_climb·v_top/η ; I = P_elec/V_pack.

**4.4 Differential-drive kinematics (set 4)**
- Forward: v_r = r·ω_r, v_l = r·ω_l ; **v = r(ω_r + ω_l)/2**, **ω = r(ω_r − ω_l)/L** ; ẋ = v cos θ, ẏ = v sin θ.
- Inverse (circular path of radius R at speed v): ω = v/R ; v_r = v + ωL/2, v_l = v − ωL/2 ; wheel ω = v_wheel/r.

**4.5 Differential-drive dynamics (set 5)**
- Straight line: a = (v_f − v_i)/t ; F_total = m·a ; F_wheel = F_total/n_driven ; τ = F_wheel·r.
- Pure spin: T_chassis = I·α ; the wheel forces form a couple, F = T_chassis/L ; τ_r = F·r, τ_l = −F·r (the left motor brakes).

## 5. Pre-lab questions
1. Why must the slope term vanish when `climb_angle_deg = 0`?
2. If the wheel output speed is 200 rpm and G = 30, what is the motor-shaft speed?
3. Derive v and ω of a differential-drive robot from the two wheel speeds.
4. Why does a motor sized only for steady speed fail to accelerate the robot?

## 6. Procedure
1. Set up:
   ```bash
   cd robot_calc
   python3 -m venv .venv && source .venv/bin/activate     # Windows: py -m venv .venv ; .venv\Scripts\activate
   pip install -r requirements.txt
   pytest                                                  # expect all tests pass
   python main.py
   ```
2. **Hand calculation first.** For the BeetleBot values in `params.yaml`, compute set 1 by hand and write each step.
3. In the menu choose `c` (calculation sets) → set 1 `tractive_effort` → `s` (results with full working). Compare line by line with your hand work.
4. Repeat for sets 2 and 3. Use `e` inside a set to edit only the parameters it uses (e.g. change `climb_angle_deg` to 10° and record the change in motor torque).
5. **PDF problems.** Set the parameters to those of Problems 1–4 in the PDF (use `e`), run sets 4 and 5, and compare with the printed answers.
6. Replace the `confirm: true` estimates with the real values from the data sheet / measurement (wheel radius with a ruler, track width, mass on a scale), run all sets, and save with `v` (it asks first; saving rewrites `params.yaml` and drops its comments — keep a copy).
7. Regenerate the sample output if you changed a formula or default: `python make_sample_output.py`.
8. *(Optional, with a robot)* measure top speed over a known distance and runtime on a battery, and compare with the prediction.

## 7. Observations

**7.1 Parameters used**

| Parameter | Value | Unit | Source (data sheet / measured / estimate) |
|---|---|---|---|
| mass | | kg | |
| wheel radius | | m | |
| gear ratio | | – | |
| track width | | m | |
| top speed, accel time | | m/s, s | |
| battery voltage, capacity | | V, Ah | |

**7.2 Set 1 — hand vs program**

| Quantity | Hand | Program |
|---|---|---|
| Acceleration (m/s²) | | |
| F_a, F_rr, F_g (N) | | |
| F_total (N) | | |
| Wheel torque, per-wheel torque (N·m) | | |
| Torque per motor (N·m), % of stall | | |
| Traction margin (N), verdict | | |

**7.3 Sets 2–3**

| Quantity | Value |
|---|---|
| No-load speed (m/s, km/h) | |
| Wheel rpm / motor rpm at target speed | |
| Runtime (min) / range (km) | |
| Drive power (W) / pack current (A) | |

**7.4 PDF problems (sets 4–5)**

| Problem | Quantity | PDF | Program |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |

**7.5 Sensitivity** — change one parameter at a time:

| Parameter changed | From → to | Quantity affected | Change |
|---|---|---|---|
| climb angle | 0° → 10° | torque per motor | |
| mass | | runtime | |

## 8. Result
☐ State the sized motor torque and the margin against stall, the predicted runtime, and that the program matches the hand calculations and the PDF answers.

## 9. Viva questions
1. List the three components of tractive force and which dominates on the flat.
2. Why include the gearbox efficiency and a safety factor in motor torque?
3. Why can the traction margin be negative even when the motor has enough torque?
4. Why is one motor torque negative in the pure-spin case?
5. How does doubling the gear ratio change motor torque and motor rpm?
6. What assumptions does the model make (even weight distribution, rigid payload, no slip in the kinematics)?
7. Which parameters in your run were estimates, and how would you measure them?

<div style="page-break-after: always"></div>

# Experiment 7 — UNO Smart Robot Car: PID line following with obstacle avoidance

*(Arduino experiment — no ROS. It contrasts a small reactive controller with the ROS 2 stacks of Experiments 2–5.)*

## 1. Aim
To program the UNO Smart Robot Car to follow a black line using three IR sensors and a PID loop, detect obstacles with a servo-mounted ultrasonic sensor, steer around them, and re-acquire the line.

## 2. Learning outcomes
Read digital line sensors and form an error signal; tune P, I and D terms; drive two DC motors with PWM through an H-bridge; measure distance with an ultrasonic sensor; build a small state machine; calibrate hardware (motor polarity, left/right) before trusting control code.

## 3. Apparatus
| Item | Detail |
|---|---|
| Kit | UNO Smart Robot Car Kit V3.0: Arduino UNO, motor driver, 2 DC motors, 3 IR line sensors, HC-SR04, servo, battery |
| Track | Black tape (≈2 cm) on a light floor, with a curve; boxes as obstacles |
| PC | Arduino IDE 1.8.x or 2.x, USB cable, CH340 driver if required |
| Code | `uno_car/line_follow_obstacle_avoid/`: `Hardware_Test/Hardware_Test.ino`, `Line_Follow_Obstacle_Avoid_Car.ino` (originals `Line_tracking_car.ino`, `Obstacle_Avoidance_Car.ino`) |

Pin map: motor A = ENA 5 / IN1 9 / IN2 11, motor B = ENB 6 / IN3 7 / IN4 8; IR right = 10, middle = 4, left = 2; ultrasonic Echo = A4, Trig = A5; servo = 3 (10° right, 90° centre, 180° left).

## 4. Theory
**Line error.** Each IR sensor is digital (on the line = 1). The three bits give a position error, scaled ×2: L = −2, L+M = −1, M = 0, M+R = +1, R = +2. Positive error means the line is to the right. If the line is lost the error is held at ±3 toward the side where it was last seen, and the car stops after 2 s.

**PID.** correction = Kp·e + Ki·∫e + Kd·(e − e_prev)/Δt. The wheel speeds are `BASE_SPEED ± correction`. With only five discrete error values Ki contributes little (set to 0); Kd damps weaving. A slow sensor-to-motor loop causes overshoot — so the sketch avoids blocking calls.

**Differential drive.** Different PWM on the two sides turns the car; the sign of the PWM sets direction. The H-bridge direction pins (IN1–IN4) select forward or reverse; ENA/ENB take the PWM. Wiring polarity varies per car, hence the calibration flags `INVERT_MOTOR_DIRECTION` and `SWAP_SIDES`.

**Ultrasonic ranging.** The HC-SR04 emits a pulse and times the echo: distance = (echo time × 343 m/s) / 2. `0` means no echo. The sketch pings every 100 ms with a 6 ms timeout and needs two consecutive close readings (< 20 cm) to react.

**Avoidance state machine.** Obstacle ahead → stop → servo to the left, read distance → if clear, turn left, go forward, return; otherwise probe right; if both blocked, back off and re-scan → creep forward sweeping the IR sensors (3 s timeout) until the line is found → resume line following.

## 5. Pre-lab questions
1. Why does the car reverse if the motor leads are wired the other way?
2. Why do `pulseIn()` with a long timeout and frequent `Serial.print` hurt control quality?
3. With sensors L, M, R what is the error when L and M see the line?
4. Why is the integral term usually unhelpful with three binary sensors?

## 6. Procedure
**Safety:** wheels **off the ground** (car on a stand) for all motor tests.

**A. Upload and bring-up (`Hardware_Test`)**
1. Arduino IDE: Tools → Board = Arduino Uno, correct port. Copy `Hardware_Test.ino` into a folder named `Hardware_Test` if the IDE complains. Upload. If the port cannot be opened: check Device Manager / CH340 driver, close any open Serial Monitor.
2. Open the Serial Monitor at **9600 baud**. Type a menu letter + Enter; any key aborts a test.
3. **IR sensors** (menu `1`): put black tape under L, M, R in turn; `on-line` must be 1 on black and 0 on white, on the correct physical side. Adjust the module trim-pot if a sensor flickers.
4. **Ultrasonic** (menu `2`): ruler at 10, 20, 50 cm.
5. **Servo** (menu `3`): note which side faces forward at 10° and at 180°.
6. **Motors** (menus `4`, `5`): which wheel turns for motor A and B, and in which direction.
7. **Drive sequence** (menu `6`): forward, back, pivot left, pivot right. If forward/back are reversed press `i` (invert); if only the pivots are mirrored press `w` (swap sides); repeat until all four are right. Note the final `invert` and `swap`.
8. **Minimum PWM** (menu `7`): first PWM value at which each wheel turns; `BASE_SPEED` should be ~30 above the higher one.

**B. Line following**
9. In `Line_Follow_Obstacle_Avoid_Car.ino` copy your `INVERT_MOTOR_DIRECTION` and `SWAP_SIDES`, set `BASE_SPEED`. Upload.
10. **PID dry run, wheels up:** slide black under one sensor at a time and read `L M R E SL SR D` in the Serial Monitor. Expect L only → E = −2 with SL < SR; R only → E = +2 with SL > SR; M only → E = 0 with SL = SR; none → keeps turning to the last side, then stops after 2 s.
11. **On the track:** start with Kp = 40, Ki = 0, Kd = 20. Tune in this order: raise **Kp** until it follows curves, then raise **Kd** to stop weaving, **Ki** last (probably leave 0). Record each trial.

**C. Obstacle avoidance**
12. Place a box on the line ≈ 40 cm ahead. Observe detection distance, the direction chosen, and whether the line is re-found. Repeat with the left side blocked, then both sides blocked.

## 7. Observations

**7.1 Bring-up**

| Test | Observed |
|---|---|
| IR: L / M / R on black, on white | |
| Ultrasonic at 10 / 20 / 50 cm | |
| Servo: 10° faces ___ ; 180° faces ___ | |
| Motor A = ___ wheel ; motor B = ___ wheel | |
| Final `invert` = ___ ; `swap` = ___ | |
| Minimum PWM: A = ___ ; B = ___ | |

**7.2 PID dry run**

| Sensor state | E | SL | SR | As expected? |
|---|---|---|---|---|
| L only | | | | |
| M only | | | | |
| R only | | | | |
| none (after 2 s) | | | | |

**7.3 Tuning**

| Trial | Kp | Kd | Ki | BASE_SPEED | Behaviour | Lap time (s) |
|---|---|---|---|---|---|---|
| 1 | 40 | 20 | 0 | 110 | | |
| 2 | | | | | | |
| 3 | | | | | | |

**7.4 Obstacle avoidance**

| Trial | Obstacle | Detected at (cm) | Direction | Line re-found? |
|---|---|---|---|---|
| 1 | on line | | | |
| 2 | left blocked | | | |
| 3 | both blocked | | | |

## 8. Result
☐ State the final gains and speeds, whether the car completed the track and avoided the obstacle, and the main problems found.

## 9. Viva questions
1. Explain the error table and why a lost line keeps the last direction.
2. What does each of Kp, Ki, Kd do, and what symptom tells you each is wrong?
3. Why was the original sketch slow to react, and how does the new loop fix that?
4. How does the ultrasonic sensor compute distance? What does a reading of 0 mean?
5. Why calibrate motor polarity before tuning the PID?
6. Why must the two vendor sketches' pin mappings not be mixed?
7. Compare this controller with the obstacle-avoidance node of Experiment 3 and the Nav2 mission of Experiment 5: sensing, control, and failure modes.
