# Claude Log

## 2026-09-04 — Repo turned into BeetleBot lab-prep workspace

- Read `.CLAUDE/` (CLAUDE.md, CLAUDE-COMMON.md, PROJ_STARTER.md, CLAUDE-LOG.md, skills) and all four handouts in `docs/`.
- Fetched the BeetleBot repo overview and the ROS 2 Jazzy tutorial URLs from the web.
- **Decisions (agreed with user):**
  - BeetleBot source included as a plain `git clone` into `BeetleBot/`, added to a new root `.gitignore`. Not a submodule, not vendored. User updates it with `git pull`.
  - Learning guides written "lab-exam focused" — CLI tools, topics/services, `rclpy`, `colcon`, bags, SLAM basics; not the full DDS/QoS/URDF treatment.
- **Files created:**
  - `.gitignore` — ignores `BeetleBot/`, colcon `build/install/log`, Python/editor cruft, rosbags.
  - `README.md` — repo purpose, layout, study order.
  - `learn/01-linux-commands.md` — terminal commands used across the lab.
  - `learn/02-ros2-concepts.md` — ROS 2 model + `rclpy` node anatomy, walking through the handout obstacle-avoidance script.
  - `learn/03-beetlebot-runbook.md` — consolidated lab-day procedure, reconciling the four handouts.
  - `learn/04-ros2-official-docs.md` — curated index into docs.ros.org/en/jazzy.
- **Files rewritten:**
  - `.CLAUDE/CLAUDE.md` — from library-template to real project brief for this repo.
  - `TODO.md` / `.CLAUDE/CLAUDE-LOG.md` — filled from empty.
- **Left incomplete / open questions:**
  - The handouts disagree on robot identity (IP `192.168.0.128` vs `.129` vs `.bot_No`; hostname `beetlebot-124.local`; Wi-Fi password truncated `15619xxx`; drive topic `/cmd_vel_nav` in handouts vs `/cmd_vel` in the upstream repo). Recorded as technical debt in `CLAUDE.md`; user to confirm with instructor.
  - Nothing committed yet — waiting on user.

## 2026-09-04 — Added JetBot and Acrux reference clones

- User asked to clone `NVIDIA-AI-IOT/jetbot` and `VEEROBOT/acrux` the same way `BeetleBot/`
  was cloned (comparison reference only — not part of the lab robot), and to record all
  three repo links in `README.md`.
- Verified both remote URLs with `git ls-remote` before cloning.
- **Files created (gitignored, not tracked):** `jetbot/`, `acrux/` — plain `git clone`s at
  repo root.
- **Files changed:**
  - `.gitignore` — added `jetbot/` and `acrux/` ignore blocks, same style as `BeetleBot/`.
  - `README.md` — added both to the Layout table; replaced the single-repo "Get / refresh
    the BeetleBot source" section with a three-repo table + clone commands for all of
    BeetleBot, JetBot, Acrux.
  - `TODO.md` — logged the addition under Done.
- Did **not** touch `.CLAUDE/CLAUDE.md`'s architecture/robot narrative — jetbot/acrux are
  reference clones only, not part of the BeetleBot lab workflow.

## 2026-09-04 — Course syllabus + lab-day study guides

- User asked to read the two course syllabus PDFs in `docs/` plus every other handout, and
  produce study material organized around the three actual lab sessions (Lab 1: turtlesim
  publish/subscribe, Lab 2: movement commands, Lab 3: obstacle avoidance) with the "why"
  for every command, not just the "what".
- Extracted PDF/docx text with `pdftotext -layout` and a small inline Python
  zipfile/regex script (no `python-docx` available) since `pdftoppm`/image rendering
  wasn't installed.
- **Finding:** `learn/01-04` already covered most of the mechanics (CLI reference, ROS 2
  concepts + colcon + a full line-by-line read of the "Updated" obstacle-avoidance node,
  and a fully reconciled runbook). Decided against one new file per raw `docs/` document
  (would have mostly re-pasted `01-04`) and instead wrote thin, cross-linked, lab-day
  checklist files plus one genuinely new file for content nothing else covered.
- **Files created:**
  - `learn/00-course-and-lab-map.md` — what the two syllabus PDFs (`BMHA314E` practical
    variant with a "List of Experiments", `BMHA314L` theory-only variant) actually require,
    plus a table mapping every `docs/` file to its lab day and covering `learn/` file.
  - `learn/05-lab1-turtlesim-and-workspace.md` — Lab 1 checklist (workspace, turtlesim
    pub/sub), cross-linking `01`/`02` instead of re-explaining CLI/colcon mechanics.
  - `learn/06-lab2-beetlebot-movement.md` — Lab 2 checklist (connect/arm/drive/teleop),
    with the `Twist` field meanings and the `-r`/`-t`/`&&` movement-recipe pattern spelled
    out, cross-linking `03-beetlebot-runbook.md` for the full reconciled procedure.
  - `learn/07-lab3-obstacle-avoidance.md` — Lab 3 checklist (deploy/register/build/run the
    node), plus a side-by-side comparison of the plain vs "Updated" obstacle-avoidance
    scripts (zones, thresholds, fixed-vs-compared turn direction, timed reverse) — this
    comparison didn't exist anywhere else in the repo.
- **Files changed:**
  - `README.md` — study order now starts at `00`, splits into "reference guides" (`01-04`)
    and "lab-day checklists" (`05-07`).
  - `.CLAUDE/CLAUDE.md` — Architecture table lists the four new `learn/` files and the
    `jetbot/`/`acrux/` reference clones.
  - `TODO.md` — logged under Done.
- Left `02-ros2-concepts.md` §5 as the canonical line-by-line code walkthrough (not
  duplicated into `07`) and `03-beetlebot-runbook.md` as the canonical single-session
  procedure (not duplicated into `05`/`06`) — the new files link to both instead.

## 2026-09-04 — BeetleBot/JetBot/Acrux converted to git submodules

- User asked about pushing the full BeetleBot/JetBot/Acrux source trees into this repo.
  Advised against vendoring (combined ~300 MB of other people's code for a repo whose
  actual deliverable is the `learn/` guides; license mixing; each is its own git repo so
  a plain copy would either lose their history or break as a dangling gitlink; staleness
  vs. the existing `git pull`-refreshed clones). Recommended keeping the current gitignored
  setup, offered git submodules as a middle ground. **User chose submodules.**
- Removed the three plain clones and re-added with `git submodule add` for each:
  `https://github.com/VEEROBOT/BeetleBot.git`, `https://github.com/NVIDIA-AI-IOT/jetbot.git`,
  `https://github.com/VEEROBOT/acrux.git` — all at their existing paths (`BeetleBot/`,
  `jetbot/`, `acrux/`). Created `.gitmodules`; each path is now a tracked gitlink (a pinned
  commit SHA), not gitignored, and their file contents are **not** duplicated into this
  repo's history.
- **Files changed:**
  - `.gitignore` — removed the three ignore blocks (a gitignored path can't cleanly become
    a submodule), replaced with a note pointing at `.gitmodules`.
  - `README.md` — "Get / refresh the reference source" section now documents
    `git submodule update --init --recursive` (first checkout) and
    `git submodule update --remote` + commit (to bump the pin), replacing the old plain
    `git clone` instructions.
  - `.CLAUDE/CLAUDE.md` — Architecture table and Data Files section updated from
    "gitignored clone, never commit" to "git submodule — pinned pointer tracked, contents
    stay upstream"; TODO List entry updated.
  - `TODO.md` — logged under Done.
- Staged everything (`.gitmodules`, the three gitlinks, `.gitignore`, `README.md`,
  `.CLAUDE/CLAUDE.md`, `TODO.md`) but did **not** commit — user commits themselves.

## 2026-09-05 — Deep architecture doc for all three bots + ROS-across-robot-types doc

- User asked for a full walkthrough of all three bots (BeetleBot/JetBot/Acrux) — architecture,
  every package/file and what it does, setup/run commands, and specifically how
  localization, SLAM, obstacle avoidance, and navigation work and plug together — plus,
  separately, a general doc on how ROS 2 is used across different robot types (arm, AMR,
  etc.) for learning beyond this lab's own robot.
- Read the actual checked-out submodule source (not just each README) to get this right:
  `BeetleBot/lyra_ws/src/*` (all packages — `lyra_bridge/node.py`, `lyra_control/cmd_vel_mux.py`,
  `lyra_localization`, `lyra_slam/config/slam_toolbox.yaml`, `lyra_nav2/config/{amcl,nav2_params}.yaml`),
  `acrux/acrux_*` (all packages, plus its three SLAM configs — SLAM Toolbox, Cartographer
  `lidar.lua`, gmapping), and `jetbot/jetbot/*` (confirmed JetBot is plain Python, not ROS —
  `robot.py`, `motor.py`, camera/AI modules, notebook-driven).
- **Finding worth flagging:** Acrux's shipped `acrux_slam/config/ekf.yaml` has `imu0_config`
  all `false` — IMU is wired up but not actually fused, only wheel odometry is. Documented
  as a live "spot the config bug" note in `08` rather than silently treating it as fused.
- **Files created:**
  - `learn/08-three-bots-architecture.md` — hardware/software comparison table; full
    package-by-package breakdown for each of the three robots with real file names, node
    names, topics, and services; setup/run commands per robot; then the core technical
    section: how the EKF (wheel+IMU fusion) and AMCL (map-based correction) together do
    localization, how SLAM Toolbox vs Cartographer vs gmapping build the map, how the two
    *different* obstacle-avoidance mechanisms in this repo (the reactive handout node vs
    Nav2's costmap layers) are not the same thing and don't run together, how Nav2's
    behavior-tree/planner/controller/behavior-server pipeline does goal-directed navigation,
    and one end-to-end ASCII diagram tying sensors → EKF → {SLAM or AMCL} → costmaps →
    planner/controller → cmd_vel_mux → lyra_bridge → STM32 → wheels together.
  - `learn/09-ros2-across-robot-types.md` — AMR pattern recap, then a full robotic-arm
    section (URDF kinematic chains, `ros2_control`, `joint_trajectory_controller`, MoveIt 2
    planning scenes, why "obstacle avoidance" means self/environment collision-checked
    planning for an arm rather than a continuous reactive loop), plus a shorter tour of
    legged robots, drones/MAVs, and multi-robot namespacing, closing with which of this
    repo's tools (rclpy/colcon/TF vs Nav2 vs `robot_localization` vs `ros2_control`) carry
    over to which robot class.
- **Files changed:**
  - `README.md` — added `08`/`09` to the study order as a new "deeper reference" tier.
  - `.CLAUDE/CLAUDE.md` — Architecture table gained rows for `08`/`09`.
  - `learn/00-course-and-lab-map.md` — study-path list extended with `08`/`09` as
    post-lab, viva-depth material.
  - `TODO.md` — logged both new files under Done.
- Did not touch `docs/` or any lab-day checklist (`05`–`07`) — this content is additive
  reference depth, not a replacement for the existing lab-focused guides.
- Nothing committed — user commits when ready.
