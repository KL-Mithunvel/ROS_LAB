# Experiment 5 — Waypoint navigation mission (Acrux, Nav2)

## 1. Aim
To make the Acrux robot navigate autonomously through up to four pre-surveyed waypoints on a map, stop and wait at each until the operator confirms, avoid unexpected obstacles, and return home.

## 2. Learning outcomes
Build a map with SLAM; survey poses in the `map` frame; send goals to Nav2 through `nav2_simple_commander`; design a testable mission state machine; add a collision-monitor safety layer; test a depth camera as an obstacle sensor.

## 3. Apparatus
- VEEROBOT Acrux (≈0.76 × 0.80 m, LiDAR, Intel RealSense, micro-ROS base), ROS 2 Humble (confirm)
- Laptop with ROS 2 and `nav2_simple_commander` on the same Wi-Fi/`ROS_DOMAIN_ID`
- Project folder `waypoint_mission/` (mission code, config, tools, [GUIDE](../waypoint_mission/GUIDE.md), [LAB-RECORD](../waypoint_mission/LAB-RECORD.md))
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
Full detail: [`waypoint_mission/GUIDE.md`](../waypoint_mission/GUIDE.md) §9–§12.

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
