# CLAUDE.md — ROS_LAB (BeetleBot / Lyra lab preparation)

> **IMPORTANT:** Read `CLAUDE-COMMON.md` first — general must-follow instructions (companion files, deployment model, workflow, template structure). This file contains repo-specific instructions and overrides `CLAUDE-COMMON.md` where they conflict.
>
> **Also read `PROJ_STARTER.md`** — the owner's personal preferences (interaction rules, coding standards, commit style). Those rules apply to every session in this repo.

---

## Project Overview

This repo is **kl mithunvel's personal study workspace** for an academic **ROS 2 lab** built
around the **VEEROBOT BeetleBot** robot (internal platform name **"Lyra"**).

- **Purpose:** two horizons —
  1. **Near term:** learn Linux terminal usage, how ROS 2 works, and the full BeetleBot
     operating workflow, before and during the lab / viva / practical exam.
  2. **Long term:** be able to build a ROS 2 autonomy stack for *any* robot from scratch —
     description → simulation → control → localization → SLAM → path planning → navigation.
- **This is a learning repo, not a software product.** The deliverables are study guides in
  `learn/`, not application code. There is no build, no test suite, no runtime here.
- **`learn/` is split into two tracks** (see `learn/README.md`): `foundations/` (shared),
  `lab/` (Track A — the graded lab), `build/` (Track B — building ROS 2 systems).
- **The robot itself** runs ROS 2 Jazzy on a Raspberry Pi 5 (Ubuntu 24.04). We do not have
  the robot in this repo — we prepare against its documentation and its public source.
- **Author:** kl mithunvel (`klm@smtw.in`). **License:** see `LICENSE`.

### The robot in one paragraph

BeetleBot is a 4-wheel skid-steer mobile robot: aluminium chassis, ~2.2 kg, max 1.0 m/s.
A Raspberry Pi 5 runs the ROS 2 stack (Nav2, SLAM Toolbox, EKF localization). A custom
**STM32F405 controller ("Lyra")** runs FreeRTOS and does the real-time PID motor control,
talking to the Pi over UART via the `lyra_bridge` node. Sensors: RPLiDAR C1 (360°, 12 m),
LSM6DSR IMU, wheel encoders (3600 ticks/rev), Pi Camera V1.3.

---

## Running the System

**There is nothing to run in this repo.** "Running the system" means operating the robot
from a Linux PC over SSH during the lab. The authoritative, reconciled procedure is
**`learn/lab/01-lab-day-runbook.md`** — follow that, not the individual handouts.

Skeleton of a lab session (full detail + caveats in the runbook):

```bash
# 0. On your Linux PC — same Wi-Fi as the robot (SSID: BEETLEBOT_5G)
ping 192.168.0.<robot-number>            # confirm reachable

# 1. Terminal 1 — SSH in, bring up hardware + LiDAR, leave running
ssh veerobot@192.168.0.<robot-number>
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<robot-number>
ros2 launch lyra_bringup robot.launch.py           # add mode:=slam camera:=true imu:=true for SLAM

# 2. Terminal 2 — SSH in again, same 3 source/export lines, then drive
ros2 service call /lyra/arm std_srvs/srv/Trigger   # ARM before any motion
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=cmd_vel_nav
# ... when done:
ros2 service call /lyra/disarm std_srvs/srv/Trigger

# 3. On the PC — same source + export, then observe
export ROS_DOMAIN_ID=<robot-number>
ros2 topic list
ros2 topic echo /scan
```

For local ROS 2 practice without the robot, use turtlesim on any Linux machine (or the
`ros:jazzy` Docker image) — see `learn/foundations/02-ros2-concepts.md`.

---

## Architecture

### This repo

| Path | Role |
|------|------|
| `learn/README.md` | Index of both tracks + reading route |
| **`learn/foundations/`** | **Shared prerequisites for both tracks** |
| `foundations/01-linux-and-shell.md` | Linux/shell fluency for ROS work — files, perms, SSH/keys, `rsync`, `tmux`, `systemd`/`journalctl`, `udev`, networking & DDS discovery, `apt`/`rosdep`, `git` for workspaces |
| `foundations/02-ros2-concepts.md` | ROS 2 model (nodes/topics/services/actions/params), QoS, lifecycle, executors, TF2, `colcon`/workspaces/overlays, `rclpy` node anatomy, creating packages + custom interfaces, launch files |
| `foundations/03-official-docs-index.md` | Curated index into `docs.ros.org/en/jazzy` + Nav2/SLAM/`ros2_control` docs |
| `foundations/04-ros1-vs-ros2.md` | ROS 1 vs ROS 2 — `roscore` vs DDS, command/concept table, build systems, `ros1_bridge`, viva Q&A |
| **`learn/lab/`** | **Track A — the graded BeetleBot lab** |
| `lab/00-course-and-lab-map.md` | What the two syllabus PDFs require; maps every `docs/` file to its lab day |
| `lab/01-lab-day-runbook.md` | Single corrected lab-day procedure reconciling the four robot handouts |
| `lab/02-lab1-turtlesim-and-workspace.md` | Lab 1 checklist: workspace setup, turtlesim publish/subscribe |
| `lab/03-lab2-beetlebot-movement.md` | Lab 2 checklist: connect to the robot, arm, drive, teleop |
| `lab/04-lab3-obstacle-avoidance.md` | Lab 3 checklist: deploy/run the obstacle-avoidance node, v1-vs-v2 comparison |
| **`learn/build/`** | **Track B — building a ROS 2 autonomy stack for any robot** |
| `build/01-three-bots-architecture.md` | Full package walkthrough of BeetleBot/Acrux/JetBot; how localization, SLAM, obstacle avoidance and Nav2 plug together end to end |
| `build/02-ros2-across-robot-types.md` | ROS 2 on arms (MoveIt 2, `ros2_control`), legged robots, drones, multi-robot systems |
| `build/03-build-a-ros2-autonomy-stack.md` | The spine — scaffolding packages and assembling all the pieces into a new robot project |
| `build/04-robot-description-and-tf.md` | URDF/Xacro, links/joints, `robot_state_publisher`, the `map→odom→base_link→sensor` TF2 chain |
| `build/05-simulation-gazebo.md` | Gazebo + `ros_gz`, sim time, spawning, sensor plugins — develop here before hardware |
| `build/06-control-and-ros2-control.md` | `ros2_control` architecture, diff-drive/ackermann controllers, hardware interfaces, PID, MCU boundary / micro-ROS |
| `build/07-localization-and-slam.md` | Odometry, IMU, `robot_localization` EKF, AMCL, `slam_toolbox`/Cartographer — tuning, TF frames, failure modes |
| `build/08-navigation-and-path-planning.md` | Nav2 internals — costmap layers, global planners, controllers, behavior trees, recovery, tuning `nav2_params.yaml` |
| `docs/` (top level) | Original instructor handouts + course syllabus PDFs (read-only source material — do not edit) |
| `docs/beetlebot/`, `docs/wolf/` | Third-party MIT reference docs — verbatim copy of SMARTS-LAB's mirror of VEEROBOT's BeetleBot (Jazzy) and Wolf (Foxy) tutorials; see each folder's `SOURCE.md`. Not instructor handouts. Each also has a `net/` subfolder (netplan examples, added — not part of the upstream mirror). |
| `docs/ros-install/` | VEEROBOT's ROS 2 install scripts, vendored from `VEEROBOT/ros-scripts` `ROS2Install/` (see `SOURCE.md`; no upstream LICENSE). Not instructor handouts. |
| `bots/` | Robot upstream sources — five **git submodules** (pinned pointer only, see `.gitmodules`): `BeetleBot/` (the lab robot), `jetbot/` (NVIDIA, non-ROS), `acrux/`, `wolf/`, `rhino/` (VEEROBOT, comparison platforms). Full list + pinned commits in `learn/index.md`. |
| `learn/index.md` | Index of every upstream repo + document this repo pulls from, with original links and pinned commits |
| `TODO.md`, `.CLAUDE/CLAUDE-LOG.md` | Companion tracker + session log (see `CLAUDE-COMMON.md`) |

### The robot's ROS 2 graph (for understanding, from `bots/BeetleBot/` source + handouts)

```
   PC (Linux)                         Raspberry Pi 5 (Ubuntu 24.04 + ROS 2 Jazzy)
 ┌───────────────┐   Wi-Fi / DDS    ┌──────────────────────────────────────────────┐
 │ rviz2, rqt    │ <══════════════> │ lyra_bringup  (launch: base / lidar / ekf)    │
 │ teleop_*_key  │  same            │ lyra_bridge   <──UART──> STM32F405 "Lyra"      │
 │ ros2 topic/…  │  ROS_DOMAIN_ID   │ lyra_control  (cmd_vel_mux, joy teleop wrap)   │
 └───────────────┘                  │ sllidar_ros2  ──> /scan                        │
                                    │ robot_localization EKF ──> /odom, /tf          │
                                    │ slam_toolbox / nav2  (when launched)           │
                                    └──────────────────────────────────────────────┘

 Key topics:  /cmd_vel_nav (Twist, drive)   /scan (LaserScan)   /odom   /imu/data_raw
              /battery_voltage              /joy                /map (SLAM/nav only)
 Key services: /lyra/arm  /lyra/disarm   (both std_srvs/srv/Trigger)
```

---

## Key Modules

The study guides in `learn/` are the main content — no code modules there. When adding
to them, keep one concern per file (per `CLAUDE-COMMON.md` Documentation Discipline) and
cross-link rather than duplicate.

Practice code lives under `practice/`, one self-contained project per subfolder, each
with its own `.venv` / `requirements.txt` / `tests/` and a note in this section.

### `practice/robot_calc/` — mobile-robot mechatronics calculator

A standalone menu-driven CLI study tool (lab exercise), built on the `klm_menu` engine
(github.com/KL-Mithunvel/menu). Given ~28 robot parameters it runs any of **5 calculation
sets**, each computing a whole group of related quantities at once, viewable as a results
table alone or with the full working:

1. `tractive_effort` — acceleration, all resistive/driving forces, total tractive force,
   wheel torque, torque per driven wheel, torque per motor (gearbox + efficiency + safety
   factor, vs stall), traction margin + slip verdict + max climb angle
2. `speed_gearing` — max no-load speed (m/s, km/h), wheel rpm and motor-shaft rpm at target speed
3. `battery_power` — usable capacity, runtime (h/min), range (m/km), drive power + pack current on the slope
4. `dd_kinematics` — differential-drive forward + inverse kinematics
5. `dd_dynamics` — differential-drive straight-line acceleration + pure-spin wheel torque

Parameters are edited in-app (all, or just the ones a set uses) and saved back to `params.yaml`.

| File | Role |
|------|------|
| `main.py` | Entry point; builds the menu from the `CALCS` registry + dispatch loop |
| `calculations.py` | `Step` / `Quantity` / `CalcResult` / `Calc` dataclasses, numeric helpers, the 5 set functions, the `CALCS` registry, the results / working renderers |
| `parameters.py` | Load / save `params.yaml`; edit-all and edit-subset helpers |
| `params.yaml` | Robot parameters (`value` / `unit` / `desc` / `confirm`); BeetleBot seed values |
| `klm_menu.py` | Menu engine, copied verbatim from github.com/KL-Mithunvel/menu |
| `make_sample_output.py` | Regenerates `SAMPLE_OUTPUT.md` (run after changing a formula/default) |
| `SAMPLE_OUTPUT.md` | Every set run on the default params — full working + results table |
| `tests/test_calculations.py` | pytest — per-set numeric checks, PDF-handout fidelity, error paths |

Run: `cd practice/robot_calc && py -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && python main.py`
Test: `pytest` from that folder.

Sets 4–5 reproduce the worked problems in `docs/Kinematics and Dynamics_AMR_Problems.pdf`.
Many `params.yaml` values (`wheel_radius_m`, `gear_ratio`, `motor_no_load_rpm`,
`track_width_m`, `accel_time_s`, `climb_angle_deg`, the coefficients,
`moment_of_inertia_kgm2`) are estimates flagged `confirm: true` — replace them with real
BeetleBot / your-robot figures.

---

## Data Files

- `docs/*.txt`, `docs/*.docx`, `docs/*.pdf` — instructor handouts + syllabus. **Committed, read-only source. Never edit.**
- `docs/beetlebot/`, `docs/wolf/` — third-party **MIT-licensed** reference docs: a verbatim
  copy of the `beetle bot/` and `wolf robot/` folders from
  <https://github.com/SMARTS-LAB/Documention> (commit `c9eb011`, retrieved 2026-09-08), which
  itself mirrors <https://docs.veerobot.com/ros-robots/>. Provenance + license in each
  folder's `SOURCE.md`. Keep the `.md`/image files as copied (don't edit upstream content);
  refresh by re-copying from a newer upstream commit and updating `SOURCE.md`. BeetleBot docs
  target ROS 2 Jazzy; **Wolf docs target ROS 2 Foxy / Ubuntu 20.04** (older). The added
  `docs/{beetlebot,wolf}/net/` subfolders (netplan examples from `VEEROBOT/ros-scripts`) are
  **not** part of the verbatim mirror — refresh them from `ros-scripts`, not SMARTS-LAB.
- `docs/ros-install/` — vendored from `VEEROBOT/ros-scripts` `ROS2Install/` (commit
  `9529dd9`). No upstream LICENSE; `install_ros2_jazzy.sh` is Apache-2.0. Refresh by
  re-copying + updating `docs/ros-install/SOURCE.md`.
- `maps/`, rosbags — if produced during the lab, save on the **robot**, then `scp` to the PC.
  Do not commit `.pgm`/`.yaml` maps or `rosbag2_*` dirs here (they are gitignored).
- `bots/BeetleBot/`, `bots/jetbot/`, `bots/acrux/`, `bots/wolf/`, `bots/rhino/` — **git
  submodules** (`.gitmodules`). This repo tracks only a pinned commit pointer for each, never
  their file contents — `git submodule update --remote` + `git add bots` + commit is how you
  refresh them, not editing files inside. `learn/index.md` has the full list + pinned
  commits. Note `bots/wolf` and `bots/rhino` (the code repos) target ROS 2 **Humble**,
  whereas `docs/wolf/` (the tutorial text) targets **Foxy** — the two upstreams disagree.
- No credentials belong in this repo. Wi-Fi / SSH passwords live only in the handouts as
  given; do not copy them into new tracked files — the `docs/**/net/*.yaml` netplan examples
  have their WiFi password redacted to `<your-wifi-password>` for this reason.

---

## Platform Constraints

| | This machine (dev) | Lab PC | Robot |
|--|--|--|--|
| OS | Windows 11 | Ubuntu 22.04 / 24.04 | Ubuntu 24.04 Server (ARM64) |
| ROS 2 | none needed | Jazzy (for rviz/rqt/teleop) | Jazzy (full stack) |
| Shell | PowerShell / Git Bash | bash | bash |
| Role | write study guides, read source | visualise + send commands | run everything |

- **ROS 2 does not run natively on Windows 11 in any convenient way for this lab.** All
  hands-on ROS practice happens on a Linux machine, the lab PC, or `docker run -it ros:jazzy`.
- Robot and PC must share the same Wi-Fi subnet **and** the same `ROS_DOMAIN_ID`
  (set it in *every* terminal, on *both* machines) or they will not see each other.
- The robot's real-time motor control is on the STM32, not Linux — never expect
  deterministic motor timing from ROS-side code.

---

## Deployment Notes

No deployment from this repo. "Deployment" = operating the physical robot, which is
covered by `learn/lab/01-lab-day-runbook.md`. Pre-lab checklist:

- [ ] Can SSH to the robot and get a prompt
- [ ] `ros2 topic list` on the PC shows the robot's topics (proves DDS + `ROS_DOMAIN_ID` OK)
- [ ] Know the arm → drive → disarm sequence and every emergency stop from memory
- [ ] Know how to `Ctrl+C` a launch cleanly and how the obstacle-avoidance node halts wheels on `SIGINT`

---

## Known Technical Debt

The four handouts in `docs/` **contradict each other and the upstream repo.** Confirm the
real values with the lab instructor on the day. Do not assume; the safe move is to ask.

| # | Conflict | Handout(s) | Upstream repo | Action |
|---|----------|-----------|---------------|--------|
| 1 | Robot IP | `192.168.0.128` (Lyra manual) vs `192.168.0.129` example vs `192.168.0.<bot_No>` (docx) | n/a | Use *your* assigned robot number for the last octet; confirm on the day |
| 2 | Robot hostname | `beetlebot-124.local` (obstacle-avoid docs) | n/a | Either `ssh veerobot@<ip>` or `ssh veerobot@<hostname>`; try both |
| 3 | Drive topic | `/cmd_vel_nav` (all handouts, teleop remap `-r cmd_vel:=cmd_vel_nav`) | `/cmd_vel` (upstream README + `lyra-` aliases) | The **handouts win** for the lab — use `/cmd_vel_nav`. The upstream repo is a slightly different config. |
| 4 | Arm mechanism | `ros2 service call /lyra/arm std_srvs/srv/Trigger` (Lyra manual) | `lyra-arm` alias (wraps the same service) | Same thing; the raw `ros2 service call` form is portable |
| 5 | Wi-Fi password | `15619xxx` (docx, truncated) | n/a | Get the full password from the instructor |
| 6 | Workspace name | `~/lyra_ws` (robot's own) vs `~/ros2_ws` / `~/<registerno>_ws` (your workspace, docx) | `~/lyra_ws` | The robot's stack is `~/lyra_ws`; you build *your* code in your own `~/<registerno>_ws` |
| 7 | Serial port | `/dev/ttyAMA0` (quick ref) vs `/dev/ttyACM0` (common example text) | `/dev/ttyAMA0` | Robot-side detail; only matters for bridge debugging |

Also: the two `docs/*Obstacle_avoid*.txt` files are two versions of the same task — the
**"Updated"** one is the fuller implementation (left/front/right windowing + reverse state
machine). Study that one; the plain one is the simpler first version.

---

## Development Rules

1. **This is a study repo — accuracy of the guides is the whole point.** Every command in
   `learn/` must be one that actually works on ROS 2 Jazzy / Ubuntu. When unsure, check the
   official docs (`learn/foundations/03-official-docs-index.md`) or the vendored submodule
   source, and cite where it came from.
2. **The `docs/` handouts (`*.txt`/`*.docx`/`*.pdf`) are read-only.** They are the
   instructor's source material. Corrections and reconciliations go in
   `learn/lab/01-lab-day-runbook.md`, never by editing a handout. The vendored reference
   sets `docs/beetlebot/` and `docs/wolf/` are also kept verbatim (refresh by re-copying
   from upstream, don't hand-edit their `.md` files).
2a. **Keep the two tracks separate.** `learn/foundations/` = shared prerequisites;
   `learn/lab/` = the graded BeetleBot lab (stays exam-focused, BeetleBot-specific);
   `learn/build/` = general "build a ROS 2 stack for any robot" material. Lab-specific
   quirks (the `docs/` technical debt, `/cmd_vel_nav`, `lyra_*`) do not leak into `build/`;
   general theory does not bloat the `lab/` checklists — cross-link instead. One concern per
   file (per `CLAUDE-COMMON.md`). New lab experiments slot in as `lab/05-…` onward.
3. **`CLAUDE-COMMON.md` is a shared file — never edit it.** (Per the `update-docs` skill.)
   If it needs changes, tell the user.
4. **Prefer the raw `ros2 ...` command form over the `lyra-*` aliases** in the guides, with
   the alias shown alongside. The aliases only exist once `lyra_commands.sh` is sourced on
   the robot; the raw commands are transferable knowledge and work in the viva.
5. **Distinguish "on the PC" from "on the robot (SSH)" for every command** in the runbook.
   Mixing them up is the most common lab mistake.
6. **No secrets in tracked files.** Passwords stay in the handouts as given.
7. Keep `TODO.md` and `.CLAUDE/CLAUDE-LOG.md` in sync with every change, in the same commit
   (per `CLAUDE-COMMON.md`).

---

## Project TODO List

Legend: 🔴 Bug / rule violation  |  🟡 Incomplete feature  |  🟢 Not started  |  ✅ Done

- ✅ Track BeetleBot, JetBot, Acrux, Wolf, Rhino upstream sources as git submodules under `bots/`
- ✅ Vendor `VEEROBOT/ros-scripts` install scripts (`docs/ros-install/`) + netplan examples (`docs/{beetlebot,wolf}/net/`); add `learn/index.md` source index
- ✅ Rewrite this file from library-template to real project brief
- ✅ Create `learn/` study guides (linux, ROS 2 concepts, runbook, doc index)
- ✅ Fill `README.md`, `TODO.md`, `.CLAUDE/CLAUDE-LOG.md`
- ✅ Restructure `learn/` into `foundations/` + `lab/` (Track A) + `build/` (Track B); add `learn/README.md`
- ✅ Track B build-out — reworked `foundations/01`, extended `foundations/02` (§7–§15),
  wrote `foundations/04-ros1-vs-ros2` and `build/03`–`build/08`
- 🟡 Verify the guides (esp. the new `build/` files) against a live ROS 2 Jazzy + Gazebo
  Harmonic environment — written against docs/source, not yet run end to end
- ✅ Add `practice/robot_calc/` — menu-driven mobile-robot mechatronics calculator
  (5 grouped calculation sets, incl. the `Kinematics and Dynamics_AMR_Problems.pdf`
  cases; ~28 params in `params.yaml`; pytest suite)
- 🟢 Add a hand-written minimal `rclpy` publisher/subscriber node under `practice/`
- 🟡 Fill in real BeetleBot values for the `confirm: true` params in
  `practice/robot_calc/params.yaml`; add the rest of kl mithunvel's wanted calculations
- 🟢 Confirm the technical-debt table values with the instructor and update it

See `TODO.md` for the live tracker.

---

## User Rules

The binding rules for this repo are:

1. **`CLAUDE-COMMON.md` → Standard User Rules** — companion files (`TODO.md`,
   `CLAUDE-LOG.md`), deployment model (dev first, hardware last), documentation discipline
   (write decisions down immediately, in the same commit), venv + `requirements.txt`
   discipline if any Python is added, lint + test before commit.

2. **`PROJ_STARTER.md`** — in full. Most load-bearing for day-to-day interaction:
   - **Open every response with "ok KLM"** + a one-line statement of what you're doing.
   - **Explain before acting.** Before any file write/edit, list every file and what
     changes, and wait for explicit confirmation.
   - **Every commit** ends with a blank line then `Co-authored-by: kl mithunvel <klm@smtw.in>`.
   - Commit messages: imperative, ≤72-char subject, no trailing period, no vague messages.
   - DRY, explicit-over-clever, real error handling, no deprecated APIs, `pytest` in
     `tests/`, YAML for config, pip+venv (flag `uv` when relevant).

### Project-Specific Overrides

- **The `learn/` guides carry no code.** "Lint and test before commit" for guide changes
  means: proof-read the guide and sanity-check every command.
- **`practice/` holds real Python** (as of 2026-09-08, `practice/robot_calc/`). Each
  `practice/` subproject has its own `.venv` + `requirements.txt` + `tests/`; the
  `CLAUDE-COMMON.md` venv / `pip freeze` / `pytest` / lint-before-commit rules apply to it
  in full. Activate that subproject's `.venv` before running its `python` / `pip` /
  `pytest`.
- **`docs/` handouts are read-only** (Development Rule 2 above).
- When explaining a ROS 2 or Linux concept, prefer showing the exact command the lab uses
  over a generic example, and always say whether it runs on the PC or on the robot.
