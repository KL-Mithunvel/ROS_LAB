# Lab Record — Waypoint Navigation Mission on Acrux

| | |
|---|---|
| **Student** | kl mithunvel |
| **Course** | BMHA314E — Autonomous Mobile Robots (practical) |
| **Experiment** | Waypoint mission: autonomous navigation through pre-surveyed waypoints with operator confirmation (ROS 2 + Nav2) |
| **Robot** | VEEROBOT Acrux (≈0.76 × 0.80 m, differential drive, 2D LiDAR + Intel RealSense, micro-ROS base) |
| **Period covered** | 2026-10-12 (start) → 2026-10-18 (this record) |
| **Status** | Design, tooling and software written and unit-tested. **Hardware / simulation runs still pending** — sections marked ☐ are to be filled in from the lab. |

> **Honesty note.** Everything in §4–§6 states what was actually done or tested.
> `mission_node.py`, `launch/safety.launch.py` and `config/collision_monitor.yaml` have
> **never been run** on Gazebo or the robot. Tables marked ☐ are deliberately blank — do not
> fill them in from expectation, only from observation.

---

## 1. Aim

To make the Acrux robot drive to up to four pre-surveyed **waypoints** on a saved map, stop and
wait at each one until a human operator confirms, avoid unexpected obstacles on the way, and
return to a home pose after the last waypoint.

## 2. Requirements (agreed 2026-10-12)

| # | Requirement | Decision |
|---|---|---|
| R1 | Number of waypoints | Up to **4**; the real count (3 or 4) is known only just before the run. Run with `--count N` to use the first N. |
| R2 | Action at a waypoint | **Stop and wait.** No speech / lights in v1. |
| R3 | Moving on | **Live operator command** ("yes" = next). Not a timer. |
| R4 | After the last waypoint | **Return home** automatically. |
| R5 | Unexpected obstacle | Avoid; never collide with an object or a person. |
| R6 | Where code runs | Mission logic on a **laptop over Wi-Fi**; safety layer **on the robot**. |
| R7 | Map | None exists — must be built (SLAM) before navigation. |
| R8 | Sensors | LiDAR is primary; **test the Intel RealSense** for obstacles above/below the scan plane. |

## 3. Apparatus and software

| Item | Detail |
|---|---|
| Robot | Acrux, Ubuntu 22.04, ROS 2 **Humble** (to be confirmed with `printenv ROS_DISTRO`) |
| Robot IP / login | see `tools/README.md` (kept out of this record) |
| Laptop | Ubuntu with ROS 2 + `nav2_simple_commander`, same Wi-Fi subnet and `ROS_DOMAIN_ID` as the robot |
| Navigation | Nav2 (costmaps, planner, DWB controller) shipped in `bots/acrux` |
| Mapping | Cartographer (as shipped) or SLAM Toolbox |
| This project | `waypoint_mission/` — `mission.py`, `mission_node.py`, `waypoint_config.py`, `waypoints.yaml`, `config/collision_monitor.yaml`, `launch/safety.launch.py`, `tools/` |

## 4. Chronological log of work

### 2026-10-12 — Remote-access tooling (commit `6b47a04`)

**Goal:** be able to operate the Acrux from a PC without sitting at the robot.

Built in `tools/` (now `waypoint_mission/tools/`):

| Script | Purpose |
|---|---|
| `acrux` | SSH helper: `run`, `ros`, `push`, `pull`, `sync`, `build`, `drive`, `teleop`, `nodes`, `stop` — key-based login, no password stored |
| `setup-key.sh` | One-time SSH key install |
| `vnc.sh` | TigerVNC + XFCE on the robot, bound to localhost and reached through an SSH tunnel |
| `dev-mode.sh` | Switch the robot's autostart `robot_bringup.service` between **demo** and **development** mode (acts on the correct user's systemd) |
| `wasd_teleop.py` | Hold-to-move keyboard teleop with 0.6 s deadman timeout and zero-velocity on exit; speed capped at 0.20 m/s, 0.60 rad/s |
| `sensor-test.sh`, `sensor_probe.sh` | Sensor bring-up probes |

**Design points:** the `drive` command is clamped (≤0.2 m/s, ≤0.6 rad/s, ≤5 s) and always ends
with a zero command; the lab's own `development.sh`/`demo.sh` act on the calling user's
systemd so they do nothing when run as `bot` — hence `dev-mode.sh`.

**Verification:** scripts syntax-checked. `vnc.sh` end-to-end run on the robot: ☐ pending.

### 2026-10-12 — Requirements and plan (commit `5ade00d`)

Requirements R1–R8 above were agreed. Source files of `bots/acrux` were read
(`nav2_params.yaml`, `autobringup.launch.py`, `navigation.launch.py`, `cartographer.launch.py`,
`lidar.lua`). Findings that shape the design:

| Finding | Consequence |
|---|---|
| Footprint ≈0.76 × 0.80 m, inflation radius 0.55 m, DWB `max_vel_x` 0.3 m/s | Waypoints need ≥0.8 m standoff and ≥1.5 m lanes between them |
| Costmaps use `/scan` and `/camera/points` | RealSense matters; must be tested (R8) |
| With `exploration:=False` nothing launches AMCL, and Cartographer still runs in mapping mode | "Navigate on a saved map" may not localise against the saved map — open item |
| No collision-monitor layer exists | Added one (see below) |
| The `cmd_vel` chain (`cmd_vel_nav` → smoother → `/cmd_vel`?) could not be confirmed from source | Must be checked on the robot before wiring the monitor |

### 2026-10-12 — Design and implementation

**Architecture.** The mission "brain" is a pure-Python state machine, separate from ROS, so
every path can be unit-tested on a normal PC:

```
IDLE ─y─► NAVIGATING ─arrived─► AT_WAYPOINT ─y─► NAVIGATING … ─► RETURNING_HOME ─► DONE
            │ fail → auto-retry → BLOCKED (operator: r retry / s skip / h home)
            │ p → PAUSED        q → ABORTED        h → RETURNING_HOME
```

| File | Role |
|---|---|
| `mission.py` | State machine: operator commands + Nav2 results in → actions out. No ROS import. |
| `waypoint_config.py` | Loads/validates `waypoints.yaml` (max 4, finite numbers, frame, yaw range, `surveyed` flag). |
| `mission_node.py` | ROS 2 adapter: `nav2_simple_commander` goals, stdin + `/waypoint/command` topic input, goal timeout, Ctrl+C cancels the goal. |
| `waypoints.yaml` | Home + 4 waypoint poses in the `map` frame. **Placeholders**, `surveyed: false`. |
| `config/collision_monitor.yaml`, `launch/safety.launch.py` | Nav2 Collision Monitor: front stop box + larger slow-down box, runs on the robot. |

**Safety design (five layers).**

| # | Layer | Where |
|---|---|---|
| 1 | Nav2 costmaps re-plan around obstacles (LiDAR + RealSense) | robot |
| 2 | Speed cap (0.3 m/s) | robot |
| 3 | Collision monitor — stop/slow boxes in front | robot |
| 4 | Operator commands: pause, home, quit, Ctrl+C | laptop |
| 5 | Physical e-stop / hand on power | human |

**Deliberate choices.**
- `--count` has **no default**, so the operator must state the number of waypoints.
- `mission_node.py` **refuses** to drive while `surveyed: false` (override `--allow-unsurveyed`, sim only).
- "n"/"no" are *not* aliases for "yes".
- The stop polygon is front-only: a stop zone blocks *all* motion including reversing, so a full ring could trap the robot.

### 2026-10-12 — Unit testing

`pytest` in `waypoint_mission/`: **60 tests, all passing** (state machine paths: full runs for
1–4 waypoints, wait-until-told, retry, blocked/skip, pause/resume, home from any state, abort,
invalid counts; config validation: shipped file valid but unsurveyed, bad/missing fields, limits).

### 2026-10-13 — Merge of both branches

PR #1 (remote tooling) and PR #2 (waypoint mission) merged to `main` (`3683a95`, `5fa336d`).

### 2026-10-18 — Reorganisation and renaming

The experiment was moved from `practice/acrux_greeter/`, `tools/acrux/` and
`learn/build/09-…` into one self-contained root folder **`waypoint_mission/`**, and the
"guest/greeter/gift" vocabulary was replaced by neutral **waypoint** terms:

| Old | New |
|---|---|
| `acrux_greeter/`, `guests.yaml`, `greeter_config.py` | `waypoint_mission/`, `waypoints.yaml`, `waypoint_config.py` |
| `slots`, `guest_count`, `MAX_GUESTS`, `AT_GUEST` | `waypoints`, `waypoint_count`, `MAX_WAYPOINTS`, `AT_WAYPOINT` |
| `/greeter/command` | `/waypoint/command` |

`pytest` re-run after the rename: **60 passed**.

## 5. Procedure (to be followed in the lab)

Full detail is in [`GUIDE.md`](GUIDE.md) §10–§12. Summary:

1. **Connect** — `./tools/acrux status`; confirm ROS distro (`printenv ROS_DISTRO`).
2. **Stop the autostart stack** — `./tools/dev-mode.sh on`; verify `ros2 node list` is empty.
3. **Base bring-up** — start the micro-ROS agent, `./tools/acrux drive 0.1 0 1.5` as a first movement test.
4. **Sensor tests** — LiDAR `/scan`; RealSense `/camera/points` (rate, stability, what it sees that LiDAR misses).
5. **Map** — SLAM mode, drive slowly, close loops, save map.
6. **Survey** — read 5 poses (home + 4 waypoints) in the map frame; enter in `waypoints.yaml`; set `surveyed: true`.
7. **Wire the safety layer** — confirm the `cmd_vel` chain (`ros2 topic info /cmd_vel -v`), launch `safety.launch.py` with the real topic names, cardboard-box stop test.
8. **Test ladder** — Gazebo → wheels lifted → cardboard obstacles → rehearsal with 3 and 4 waypoints.
9. **Run** — `python3 mission_node.py --count N`; press `y` to start, `y` at each waypoint.

## 6. Observations and results

### 6.1 Open-item checks (GUIDE §14)

| # | Check | Command / method | Observed | Pass? |
|---|---|---|---|---|
| 1 | Robot ROS distro | `printenv ROS_DISTRO` | ☐ | ☐ |
| 2 | What provides `map → odom` with `exploration:=False`? | `ros2 node list`, `ros2 run tf2_tools view_frames` | ☐ | ☐ |
| 3 | `cmd_vel` chain | `ros2 topic info /cmd_vel -v` | ☐ | ☐ |
| 4 | Collision-monitor parameter names accepted by the installed Nav2 | launch and read errors | ☐ | ☐ |
| 5 | Scan topic is `/scan` (not `/lidar/scan`) | `ros2 topic hz /scan` | ☐ | ☐ |
| 6 | Polygon frame is `base_link` | `view_frames` | ☐ | ☐ |
| 7 | RealSense `/camera/points` stable, rate, CPU cost | `ros2 topic hz`, `top` | ☐ | ☐ |
| 8 | Payload not in LiDAR plane / camera view | RViz scan with payload loaded | ☐ | ☐ |

### 6.2 Surveyed poses (map frame)

| Point | x (m) | y (m) | yaw (rad) |
|---|---|---|---|
| Home | ☐ | ☐ | ☐ |
| Waypoint 1 | ☐ | ☐ | ☐ |
| Waypoint 2 | ☐ | ☐ | ☐ |
| Waypoint 3 | ☐ | ☐ | ☐ |
| Waypoint 4 | ☐ | ☐ | ☐ |

### 6.3 Mission runs

| Run | Environment | Waypoints (N) | Reached all? | Time to complete (s) | Obstacle test | Remarks |
|---|---|---|---|---|---|---|
| 1 | Gazebo | ☐ | ☐ | ☐ | ☐ | ☐ |
| 2 | Robot, wheels lifted | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3 | Robot, cardboard obstacle | ☐ | ☐ | ☐ | ☐ | ☐ |
| 4 | Full rehearsal, 3 waypoints | ☐ | ☐ | ☐ | ☐ | ☐ |
| 5 | Full rehearsal, 4 waypoints | ☐ | ☐ | ☐ | ☐ | ☐ |

### 6.4 Position accuracy at each waypoint

| Waypoint | Commanded (x, y) | Measured (x, y) | Error (m) |
|---|---|---|---|
| 1–4 | ☐ | ☐ | ☐ |

## 7. Result (to be completed)

☐ State whether all waypoints were reached, whether the safety stop worked, and the main
failure modes seen.

## 8. Viva questions this experiment prepares for

1. Why is the mission logic separated from ROS? *(testability; deterministic state machine.)*
2. Why stop and wait for a command instead of a timer? *(a human confirms the task; timers fail silently.)*
3. What stops the robot hitting a person? *(five layers: costmap re-plan, speed cap, collision monitor, operator, e-stop.)*
4. Why must the safety layer run on the robot, not the laptop? *(Wi-Fi loss must not disable it.)*
5. Why must the waypoint standoff be ≥0.8 m? *(otherwise the target sits inside the stop box and the robot freezes.)*
6. What is the difference between a global and a local costmap, and what is inflation? *(see `learn/build/08`.)*
7. What goes wrong if AMCL is not running while navigating on a saved map? *(no `map → odom`; pose drifts, goals are wrong.)*
8. Why is a 2D LiDAR not enough on its own? *(sees one slice; the RealSense covers heights it misses.)*

## 9. Conclusion (to be completed)

☐ Write after the runs.

## 10. Files in this experiment

See [`README.md`](README.md) for the file table and [`GUIDE.md`](GUIDE.md) for the full
design, safety reasoning and event-day runbook.
