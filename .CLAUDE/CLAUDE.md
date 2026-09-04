# CLAUDE.md — ROS_LAB (BeetleBot / Lyra lab preparation)

> **IMPORTANT:** Read `CLAUDE-COMMON.md` first — general must-follow instructions (companion files, deployment model, workflow, template structure). This file contains repo-specific instructions and overrides `CLAUDE-COMMON.md` where they conflict.
>
> **Also read `PROJ_STARTER.md`** — the owner's personal preferences (interaction rules, coding standards, commit style). Those rules apply to every session in this repo.

---

## Project Overview

This repo is **kl mithunvel's personal study workspace** for an academic **ROS 2 lab** built
around the **VEEROBOT BeetleBot** robot (internal platform name **"Lyra"**).

- **Purpose:** learn (1) Linux terminal usage, (2) how ROS 2 works, (3) the full BeetleBot
  operating workflow, before and during the lab / viva / practical exam.
- **This is a learning repo, not a software product.** The deliverables are study guides in
  `learn/`, not application code. There is no build, no test suite, no runtime here.
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
**`learn/03-beetlebot-runbook.md`** — follow that, not the individual handouts.

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
`ros:jazzy` Docker image) — see `learn/02-ros2-concepts.md`.

---

## Architecture

### This repo

| Path | Role |
|------|------|
| `learn/00-course-and-lab-map.md` | What the two syllabus PDFs actually require; maps every `docs/` file to its lab day and `learn/` file |
| `learn/01-linux-commands.md` | Terminal commands used across the lab, each explained with the exact form the lab uses |
| `learn/02-ros2-concepts.md` | ROS 2 computation model (nodes/topics/services/params), `colcon` + workspace/overlay model, `rclpy` node anatomy, line-by-line read of the handout obstacle-avoidance node |
| `learn/03-beetlebot-runbook.md` | Single corrected lab-day procedure reconciling the four robot handouts |
| `learn/04-ros2-official-docs.md` | Curated index into `docs.ros.org/en/jazzy` with why each page matters here |
| `learn/05-lab1-turtlesim-and-workspace.md` | Lab 1 checklist: workspace setup, turtlesim publish/subscribe |
| `learn/06-lab2-beetlebot-movement.md` | Lab 2 checklist: connect to the robot, arm, drive, teleop |
| `learn/07-lab3-obstacle-avoidance.md` | Lab 3 checklist: deploy/run the obstacle-avoidance node, v1-vs-v2 script comparison |
| `docs/` | Original instructor handouts + course syllabus PDFs (read-only source material — do not edit) |
| `BeetleBot/` | Upstream BeetleBot source clone — gitignored, reference only |
| `jetbot/` | NVIDIA-AI-IOT JetBot clone — gitignored, comparison platform only |
| `acrux/` | VEEROBOT Acrux clone — gitignored, comparison platform only |
| `TODO.md`, `.CLAUDE/CLAUDE-LOG.md` | Companion tracker + session log (see `CLAUDE-COMMON.md`) |

### The robot's ROS 2 graph (for understanding, from `BeetleBot/` source + handouts)

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

Not applicable — this repo has no code modules. The study guides in `learn/` are the
content. When adding to them, keep one concern per file (per `CLAUDE-COMMON.md`
Documentation Discipline) and cross-link rather than duplicate.

If practice code is added later (e.g. a personal `rclpy` node), it goes in a new
`practice/` folder with its own note in this section.

---

## Data Files

- `docs/` — instructor handouts (`.txt` + `.docx`). **Committed, read-only source. Never edit.**
- `maps/`, rosbags — if produced during the lab, save on the **robot**, then `scp` to the PC.
  Do not commit `.pgm`/`.yaml` maps or `rosbag2_*` dirs here (they are gitignored).
- `BeetleBot/` — gitignored clone. Never commit its contents into this repo.
- No credentials belong in this repo. Wi-Fi / SSH passwords live only in the handouts as
  given; do not copy them into new tracked files.

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
covered by `learn/03-beetlebot-runbook.md`. Pre-lab checklist:

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
   official docs (`learn/04-...`) or the `BeetleBot/` source, and cite where it came from.
2. **`docs/` is read-only.** It is the instructor's source material. Corrections and
   reconciliations go in `learn/03-beetlebot-runbook.md`, never by editing a handout.
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

- ✅ Clone BeetleBot upstream into `BeetleBot/` (gitignored)
- ✅ Rewrite this file from library-template to real project brief
- ✅ Create `learn/` study guides (linux, ROS 2 concepts, runbook, doc index)
- ✅ Fill `README.md`, `TODO.md`, `.CLAUDE/CLAUDE-LOG.md`
- 🟡 Verify every guide against a live ROS 2 Jazzy environment (not yet done — no Linux box in this session)
- 🟢 Add a `practice/` folder with a hand-written minimal `rclpy` publisher/subscriber node
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

- **No Python application code is expected here.** The venv / `requirements.txt` /
  `pytest` rules from `CLAUDE-COMMON.md` only activate if a `practice/` folder with real
  code is added. Until then, "lint and test before commit" means: proof-read the guides
  and sanity-check every command.
- **`docs/` handouts are read-only** (Development Rule 2 above).
- When explaining a ROS 2 or Linux concept, prefer showing the exact command the lab uses
  over a generic example, and always say whether it runs on the PC or on the robot.
