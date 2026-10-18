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
