# Autonomous Mobile Robots — Lab Manual

**Course:** BMHA314E Autonomous Mobile Robots (practical component)
**Platforms:** VEEROBOT BeetleBot "Lyra" (Labs 2–4, ROS 2 Jazzy, Raspberry Pi 5) and VEEROBOT Acrux (Experiment 5, Nav2)
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
| 1 | [Workspace setup and turtlesim publish/subscribe](01-workspace-and-turtlesim.md) | PC only | 1 — Set up ROS, fundamentals | `learn/lab/02-…` |
| 2 | [Connecting to BeetleBot and movement commands](02-beetlebot-movement.md) | BeetleBot | 1 (fundamentals on real hardware) | `learn/lab/03-…` |
| 3 | [LiDAR obstacle avoidance](03-obstacle-avoidance.md) | BeetleBot | 3–4 (perception → control loop) | `learn/lab/04-…` |
| 4 | [Colour-based control with the camera](04-color-detection.md) | BeetleBot | 5 — Object detection (OpenCV) | `learn/lab/05-…` |
| 5 | [Waypoint navigation mission](05-waypoint-mission.md) | Acrux | 3–4 — SLAM and path planning (Nav2) | `waypoint_mission/` |

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
changed. A worked example of a record is [`waypoint_mission/LAB-RECORD.md`](../waypoint_mission/LAB-RECORD.md).

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
