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

## 2026-09-08 — Vendored VEEROBOT BeetleBot + Wolf tutorial docs into `docs/`

- **User's ask:** take the beetlebot and wolf bot documents from
  <https://github.com/SMARTS-LAB/Documention> and duplicate them into `docs/`.
- Checked the repo: MIT-licensed, it mirrors VEEROBOT's official tutorial docs
  (<https://docs.veerobot.com/ros-robots/>). Cloned at commit `c9eb011`.
- **Decisions (user via AskUserQuestion):** folder names without spaces
  (`docs/beetlebot/`, `docs/wolf/`); just copy the docs now — don't wire Wolf into the
  `learn/` robot comparisons yet.
- **Done:**
  - `docs/beetlebot/` ← `beetle bot/` (15 numbered `.md` + `README.md` + `images/beetlebot.jpeg`), verbatim.
  - `docs/wolf/` ← `wolf robot/` (16 numbered `.md` + `README.md` + `images/*` ×4), verbatim.
  - `docs/beetlebot/SOURCE.md`, `docs/wolf/SOURCE.md` — origin URL, commit SHA, retrieval
    date, full MIT license text (MIT requires the notice travels with the copy).
  - `.CLAUDE/CLAUDE.md` — Architecture table row, Data Files entry, Development Rule 2 now
    scope "read-only" to the instructor handouts (`*.txt`/`*.docx`/`*.pdf`) and say the
    vendored sets are kept verbatim / refreshed by re-copying.
  - `README.md` layout table, `TODO.md` updated.
- **Note:** Wolf's docs target **ROS 2 Foxy / Ubuntu 20.04** (EOL 2023) — older than
  BeetleBot's Jazzy; flagged in `docs/wolf/SOURCE.md`.
- Nothing committed — user commits when ready.

## 2026-09-07 — `learn/` restructure into two tracks + Track B build-out (all 11 phases)

- **User's ask:** (1) add a ROS 1 vs ROS 2 guide; (2) rework the Linux guide to cover ROS
  generally, not just BeetleBot; (3) new overarching goal — be able to build a ROS 2
  autonomy stack for *any* robot (localization, navigation, path planning, control), so
  rework whatever modules that needs; (4) move all lab content into its own folder so future
  lab experiments can be added while keeping document flow.
- **Decision (agreed with user via AskUserQuestion):** full Track-B build-out (not the lean
  single-file option), and extend `foundations/02` with builder depth rather than freezing it.
  Plan recorded as 11 phases in `TODO.md`.
- **Structure chosen:** `learn/foundations/` (shared: linux, ros2-concepts, docs-index,
  ros1-vs-ros2), `learn/lab/` (Track A — the graded lab, per-folder numbered 00–04),
  `learn/build/` (Track B — 01–08). Per-folder numbering from 01 so new files append cleanly.
- **Phase 1 done this session:**
  - `git mv` all 10 existing guides into the new folders with history preserved, renumbered
    per folder (`03-beetlebot-runbook`→`lab/01-lab-day-runbook`, `05/06/07`→`lab/02/03/04`,
    `04-ros2-official-docs`→`foundations/03-official-docs-index`, `01`→`foundations/01-linux-and-shell`,
    `08/09`→`build/01/02`). Script: `scratchpad/reorg.py`.
  - Rewrote every inter-guide cross-link to the new relative paths; fixed the `Next:` chain
    and every `# NN —` H1; reworked `lab/00-course-and-lab-map.md` §3 to a lab-only study
    path pointing at `learn/README.md` for the big picture; added a note to its §1 that the
    syllabus vocabulary (`move_base`, `actionlib`) is ROS 1-era.
  - **New:** `learn/README.md` — the two-track map + reading route.
  - **Changed:** root `README.md` (goal now two horizons; study order rewritten around the
    tracks), `.CLAUDE/CLAUDE.md` (Project Overview two horizons; Architecture table replaced
    with the tracked structure; new Development Rule 2a "keep the two tracks separate";
    path refs updated; Project TODO List updated), `TODO.md` (11-phase plan).
  - Saved the user's own early Linux notes to `scratchpad/user-old-linux-notes.md` to fold
    into `foundations/01` in Phase 2.
- **Phases 2–11 done this session too:**
  - **`foundations/01-linux-and-shell.md`** reworked (Phase 2) — now general ROS Linux:
    added SSH keys/`~/.ssh/config`, `rsync`, `tmux`, `systemd`/`journalctl`, `udev` rules,
    `rosdep`/`vcs`, `git` for workspaces, DDS discovery/multicast/firewall, users/groups,
    system inspection, shell ergonomics; folded in the user's early Linux notes; kept the
    BeetleBot examples and a "lab quick reference" box (§17).
  - **`foundations/02-ros2-concepts.md`** extended (Phase 3, additive only) — new §7–§15:
    QoS, parameters/YAML, lifecycle nodes, executors/callback groups, actions, TF2,
    creating packages + custom interfaces, launch files in depth, composition. §1–§6 (the
    lab-exam core, and the section numbers other files cite) untouched.
  - **New Track-B files:** `foundations/04-ros1-vs-ros2.md`,
    `build/03-build-a-ros2-autonomy-stack.md` (the spine — the 7-layer model + build order +
    package layout), `build/04-robot-description-and-tf.md`, `build/05-simulation-gazebo.md`,
    `build/06-control-and-ros2-control.md`, `build/07-localization-and-slam.md`,
    `build/08-navigation-and-path-planning.md`.
  - **Phase 11:** `build/01`/`02` footers now carry a §-mechanism → deep-dive-file map;
    reconciled the number-shorthand after the renumber (`08`→`01` for three-bots, bare `02`
    → `foundations/02` vs `02-ros2-across-robot-types.md` by meaning); a link-checker script
    confirms every inter-guide `.md` reference resolves.
- **Content basis:** the new `build/` files are written against the official ROS 2 Jazzy /
  Nav2 / `ros2_control` / Gazebo Harmonic docs and the vendored submodule source, but have
  **not been run end to end** — flagged in `TODO.md` under In Progress for live verification.
- **Not touched:** `docs/` (read-only), the lab checklist *content* (only moved + renumbered
  + Next-links), the submodules, `CLAUDE-COMMON.md`.
- Nothing committed — user commits when ready.

## 2026-09-08 — `practice/robot_calc/` mechatronics calculator

- kl mithunvel asked for a menu-driven program (in the style of his `menu` and
  `Furnace_simulation` repos) that does mobile-robot mechatronics calculations: a list of
  all calcs, then per-calc "view answer / view answer with steps / edit parameters / run".
  Mid-task he added `docs/Kinematics and Dynamics_AMR_Problems.pdf` and asked for those
  worked problems too.
- **Decisions (agreed with user):** location `practice/robot_calc/`; parameters in
  `params.yaml` (per PROJ_STARTER's YAML rule); 4 seed force/torque calcs + the rest built
  out from his list. This is the first real code in the repo — `practice/` subprojects now
  carry the full `CLAUDE-COMMON.md` venv / requirements / pytest discipline (recorded in
  `CLAUDE.md` Key Modules + Project-Specific Overrides).
- **Files created (all new, `practice/robot_calc/`):**
  - `klm_menu.py` — menu engine, copied verbatim from github.com/KL-Mithunvel/menu.
  - `calculations.py` — `Step`/`CalcResult`/`Calc` dataclasses, numeric helpers, 20 calc
    functions, the `CALCS` registry (menu is generated from it), and the answer / full-steps
    renderers.
  - `parameters.py` — YAML load/save, edit-all and edit-only-what-this-calc-uses helpers.
  - `params.yaml` — 28 parameters as `{value, unit, desc, confirm}`; BeetleBot seed values,
    estimates flagged `confirm: true` (incl. `design_safety_factor` and
    `motor_stall_torque_nm` for the motor-sizing calc).
  - `main.py` — menu definitions built from `CALCS` + dispatch loop (entry point).
  - `requirements.txt` (PyYAML, pytest), `README.md`, `tests/test_calculations.py`.
- **Calculations:** acceleration, accel force, friction/traction force, rolling resistance,
  gravity-on-slope, force to move (flat), force to climb, total tractive force, total wheel
  torque, torque per driven wheel, torque per motor (through gearbox), max no-load speed,
  wheel rpm at top speed, battery runtime + range, drive power, traction check; plus the PDF
  cases — diff-drive forward kinematics (v, ω, ẋ, ẏ), inverse kinematics (circular path →
  wheel ω), straight-line acceleration torque, pure-spin wheel torque. The last four
  reproduce the PDF's numeric answers when set to its parameter values (asserted in tests).
- **Verified:** `.venv` created, `pip install -r requirements.txt`, `py_compile` clean,
  `pytest` = 32 passed; drove the menu end to end with piped input.
- **Left for kl mithunvel:** replace the `confirm: true` params with real BeetleBot figures;
  hand over the rest of the calculation list to add.
- Nothing committed — user commits when ready.

## 2026-09-08 — `practice/robot_calc/` regrouped into 5 sets

- Staged the first version (20 one-output calcs), then kl mithunvel said 20 was too many
  and asked to combine the small calcs into "a set of calculations in one place then the
  other". Confirmed the split via a question; he picked the 5-set plan.
- **`calculations.py` rewritten:** `CalcResult` now holds `title` + a list of `Quantity`
  (name/value/unit/note) + `steps` + `notes` instead of one value + extras. The 20 functions
  became 5 set functions — `calc_tractive_effort`, `calc_speed_gearing`, `calc_battery_power`,
  `calc_dd_kinematics`, `calc_dd_dynamics` — each returning the whole group. Shared numeric
  helpers (`_acceleration`, `_normal_force`, `_rolling_resistance`, `_grade_force`, …) kept.
  Renderers: `render_answer` = results table (blank-line-grouped by the `group:` name
  prefix); `render_steps` = full working then the table then notes. `_n()` now uses
  thousands separators instead of scientific notation for ordinary sizes.
- **`main.py`:** menu wording only ("Calculation sets", "View results only / with full
  working", "Edit parameters used by this set"); dispatch unchanged (`<action>_<set id>`).
- **`params.yaml`:** unchanged — all 28 params are still each used by ≥1 set (a test now
  enforces this).
- **`tests/test_calculations.py` rewritten:** 12 cases — per-set output checks by name,
  PDF Problems 1–4 fidelity, slip verdict, zero-accel-time / zero-current errors,
  every-param-used, renderer text.
- **Docs updated:** `README.md` (5-set walkthrough + updated "add a set"), `CLAUDE.md`
  Key Modules + Project TODO, `TODO.md`.
- **Verified:** `py_compile` clean, `pytest` 12 passed, drove all 5 sets through the menu
  (results + working views).
- Earlier `git add` of the 20-calc version is now superseded — re-stage before committing.
- Committed by kl mithunvel as `cb8c855` "Regroup robot_calc into 5 calculation sets".

## 2026-09-08 — `practice/robot_calc/` sample output + error-handling hardening

- kl mithunvel asked to (a) put a full run of every set (working + output) into a
  markdown file in the folder, and (b) re-check the code for error-handling / hotkey /
  other bugs.
- **New:** `make_sample_output.py` (runs every set on `params.yaml`, writes the results
  table + full working for each) and its output `SAMPLE_OUTPUT.md`. README links it.
- **Bug review + fixes:**
  - `main.main()` now catches `EOFError` / `KeyboardInterrupt` for a clean exit (was a
    traceback on Ctrl-C / Ctrl-D / end-of-piped-input), and catches a missing / malformed
    `params.yaml` on startup with a message instead of a traceback.
  - `main.show_result()` moved `parameters.resolve()` inside the try (a non-numeric value
    in the YAML was an uncaught `ValueError`); also catches `ArithmeticError`.
  - `dispatch()` "reload params" wrapped in try/except.
  - `parameters.load()` wraps `yaml.YAMLError` as `ValueError` and checks each entry is a
    mapping with a `value` key.
  - `parameters.save()` now asks before overwriting (it rewrites via the YAML dumper, which
    drops the file's comments) and handles `OSError`.
  - `parameters._edit_keys()` skips a key that isn't in `params.yaml` instead of `KeyError`.
  - Menu / hotkey handling in `klm_menu.py` reviewed — bad number, bad char, empty and
    non-alnum input all re-prompt cleanly; no hotkey collisions in any menu (list uses
    a/c/d/e/f, sub-menus a/s/e/r, 'b' reserved for Back). No changes needed there.
  - `calc_tractive_effort` note that had wrapped onto two bullets folded into one.
- **Tests:** +2 (`load` rejects empty / bad-shape / missing file; `_edit_keys` skips an
  unknown key). 14 pass; `py_compile` clean; drove all 5 sets + save(declined) + reload
  through the menu; `params.yaml` untouched by the run.
- Nothing else committed — user stages/commits.

## 2026-09-08 — Wolf tracked as a git submodule

- kl mithunvel asked to hook up git for Wolf the same way as the other bots.
- `git submodule add https://github.com/VEEROBOT/wolf.git wolf` — pinned at `35bb3b5`
  (its only branch, `main`; no tags). Verified the repo is the right one first: it holds
  `four_w_amr`, `four_w_amr_nav2`, `micro_ros`, `teleop_twist_joy` and motor `.cpp`s — the
  4-wheel AMR the `docs/wolf/` tutorials cover.
- **Discrepancy noted:** `VEEROBOT/wolf` README targets **ROS 2 Humble**; `docs/wolf/`
  (SMARTS-LAB mirror of the VEEROBOT docs) says **Foxy**. Recorded in `.CLAUDE/CLAUDE.md`
  Data Files and `TODO.md`.
- **Files changed:** `.gitmodules` (+`wolf` entry), `.gitignore` (comment), `README.md`
  (Layout table + submodule table + clone command), `.CLAUDE/CLAUDE.md` (Architecture
  table + Data Files + Project TODO), `TODO.md`. New gitlink `wolf`.
- Nothing committed — user stages/commits.
