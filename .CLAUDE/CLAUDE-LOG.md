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
- Committed by kl mithunvel as `bfd3ad0` "Track Wolf robot as a git submodule".

## 2026-09-08 — bots/ folder, Rhino submodule, ros-scripts vendoring, learn/index.md

Four things in one block, all confirmed with the user first (two via a question):

1. **Rhino** — `git submodule add https://github.com/VEEROBOT/rhino.git bots/rhino`
   (`--name rhino`). Pinned `68b33a7` (branch `main`, no tags). Verified it's a real robot
   repo (same layout as Wolf: `four_w_amr`, `four_w_amr_nav2`, `micro_ros`, …; ROS 2 Humble).
2. **bots/ restructure** — user said root was crowded (5 bot folders) and asked my opinion;
   agreed. `git mv BeetleBot|jetbot|acrux|wolf → bots/…`; rhino added straight into `bots/`.
   `git mv` updated `.gitmodules` paths, `.git/config`, and each worktree's `.git` gitdir
   file; `.git/modules/` dirs stay flat (BeetleBot/acrux/jetbot/rhino/wolf). `git submodule
   status` and `git -C bots/<x> status` both clean. First rhino add landed as name
   `bots/rhino`; re-added with `--name rhino` for a consistent `.gitmodules`.
3. **VEEROBOT/ros-scripts** (`9529dd9`) — copied `ROS2Install/` → `docs/ros-install/`
   (`install_ros2.sh`, `install_ros2_jazzy.sh`, `install_ros2_v2.sh`, `UPSTREAM_README.md`,
   + a `SOURCE.md` and `README.md`). Upstream has **no LICENSE** — noted; `install_ros2_jazzy.sh`
   carries an Apache-2.0 header (ex-`Tiryoh/ros2_setup_scripts_ubuntu`). Copied
   `ros2_network_yaml/` (netplan configs) into **`docs/beetlebot/net/`** and
   **`docs/wolf/net/`** with a README each, as the user asked ("under beetle bot and wolf").
   **Redactions vs upstream:** WiFi `password:` → `<your-wifi-password>` (repo Development
   Rule 6 — no credentials in tracked files); `nameservers` de-duplicated; a literal TAB on
   the `via:` line of `70-wolf-net.yaml` (invalid YAML upstream) replaced with spaces. All
   four YAMLs `yaml.safe_load`-clean; all three scripts `bash -n`-clean.
4. **`learn/index.md`** (new) — index of every upstream repo + document this repo pulls
   from: the 5 bot submodules (URL + pinned commit + role), `ros-scripts`, the SMARTS-LAB
   vendored docs, the instructor `docs/` handouts, and links-only for the official ROS/Nav2/
   Gazebo docs.
- **Path references updated** for the `bots/` move: `.gitignore`, `README.md`,
  `.CLAUDE/CLAUDE.md` (Architecture table, ROS-graph heading, Data Files, Project TODO),
  `learn/build/01-three-bots-architecture.md` (7 source paths), `learn/foundations/01`
  (submodule comment), `learn/foundations/03` (BeetleBot doc paths). Old CLAUDE-LOG entries
  left unchanged (audit trail — they describe the state at the time).
- Nothing committed — user stages/commits ("stage it up and let me know").

## 2026-09-23 — Merged line-following + obstacle-avoidance sketch for the UNO Smart Robot Car Kit

- User asked to combine `docs/UNO Smart Robot Car Kit/Line_tracking_car.ino` and
  `Obstacle_Avoidance_Car.ino` (both Elegoo example sketches for the same kit) so the
  car follows a line by default, steers around an obstacle when one appears ahead, and
  reacquires the line afterward — including reacting if the first turn direction has no
  clear path.
- **Bug found while comparing the two sketches:** their motor pin mappings are
  electrically opposite for the same named function — `Line_tracking_car.ino`'s
  `forward()`/`back()` drive the identical physical pin states as
  `Obstacle_Avoidance_Car.ino`'s `back()`/`forward()` (verified by comparing each
  function's raw HIGH/LOW pattern per pin). The obstacle-avoidance sketch's function
  names match its own `Serial.println` comments; the line-tracking sketch's don't
  (`forward(){ ... println("go back!"); }`) — its names are swapped from correct wiring.
  Standardized the merged sketch on the obstacle-avoidance sketch's pin mapping.
- User then asked to move both originals into a separate folder alongside the merge.
  Created `docs/UNO Smart Robot Car Kit/line_follow_obstacle_avoid/` and `git mv`'d both
  originals into it (history preserved), then added the merged sketch there too.
- **New file:** `docs/UNO Smart Robot Car Kit/line_follow_obstacle_avoid/Line_Follow_Obstacle_Avoid_Car.ino`
  — state-machine sketch: `loop()` pings the ultrasonic every pass; below
  `OBSTACLE_DISTANCE_CM` (20 cm) it stops and probes left with the servo, steers around
  left if clear, probes right and steers around there if left is blocked, backs off and
  lets the next `loop()` re-scan if both sides are blocked. After going around, creeps
  forward sweeping the IR sensors (with a timeout) until the line is found, then hands
  control back to normal line-following. Dropped the originals' blocking
  `while(LT_R);`/`while(LT_L);` spins in favor of a per-loop check, so obstacle checks
  stay responsive during a turn.
- **Files moved (`git mv`, history preserved):**
  `docs/UNO Smart Robot Car Kit/Line_tracking_car.ino` →
  `docs/UNO Smart Robot Car Kit/line_follow_obstacle_avoid/Line_tracking_car.ino`;
  `Obstacle_Avoidance_Car.ino` → same folder.
- Not yet run on real hardware — untested firmware, written from the two source sketches.
  Tuning constants (`OBSTACLE_DISTANCE_CM`, `AVOID_TURN_MS`, `AVOID_FORWARD_MS`,
  `LINE_SEARCH_TIMEOUT_MS`, `carSpeed`) are estimates; user should tune on the actual kit.

## 2026-09-23 — documented Lab 4 (colour detection node)

User added `docs/color_detection_beetlebot` (commit `2db5c3f`, prior to this session) — their
own `rclpy` node from last week's lab work, not an instructor handout: subscribes
`/pi_camera/image_raw`, HSV-thresholds a centre ROI (green/red/blue), publishes `Twist` on
`/cmd_vel_nav` (green→forward, red→stop, blue→backward, with hysteresis — holds last command
if nothing clears the 20% coverage threshold). Asked to "update the document accordingly".

- Read the node in full first. Noted it maps to syllabus Experiment 5 ("Object detection
  using OpenCV" — `learn/lab/00-course-and-lab-map.md` §1) and that its shutdown safety
  differs from the obstacle-avoidance node's: `try/except KeyboardInterrupt` + `finally:`
  publishing a zero `Twist` 10×, not a `signal.signal(SIGINT, ...)` handler.
- Flagged before writing anything: `docs/color_detection_beetlebot` sits in `docs/`, which
  this repo defines as read-only instructor handouts — it doesn't belong there structurally.
  Asked the user via `AskUserQuestion` (leave as-is + document vs. move into `practice/` with
  its own `.venv`/`requirements.txt`/`tests/` now). User: leave as-is for now — "there is
  some issue with over all document format with some other work also we will check and
  reformat later". Documented only; did not move the file.
- Wrote **`learn/lab/05-lab4-color-detection.md`** (new) — same checklist shape as
  `04-lab3-obstacle-avoidance.md`: what the node does, the shutdown-safety difference called
  out explicitly, full deploy sequence (bringup with `camera:=true`, cv_bridge/OpenCV dep
  check, copy node into `lyra_control` as `color_control.py`, register entry point,
  `colcon build`, arm, run, disarm), HSV tuning notes, viva checklist, and a closing note on
  the file's current location + the planned future move.
- **Files changed:** `learn/lab/00-course-and-lab-map.md` (table row + study-path entry),
  `learn/README.md` (Track A table row 05, bumped "future labs" to `06-…`),
  `.CLAUDE/CLAUDE.md` (Architecture table row, Known Technical Debt #8 — flags the `docs/`
  placement, Project TODO ✅ line), `TODO.md` (dated Done entry), `TODO.md`/this file kept in
  sync per the companion-file rule. New file: `learn/lab/05-lab4-color-detection.md`.
- Noted in passing: while working, another session merged the UNO Smart Robot Car Kit
  sketches and committed (`4204e40`) — unrelated to this task, left untouched.
- Not yet committed — awaiting the user's go-ahead to commit.

## 2026-09-24 — UNO car: PID line following + hardware bring-up test sketch

Follow-up to the 2026-09-23 merged sketch. User flashed it (after fixing a COM6 upload
failure — port/driver/cable, the compile was fine) and reported on hardware: the bot drove
in reverse on the line, then after an invert fix drove forward and turned right correctly
but "didn't turn left" although the Serial log showed `L:1`, then concluded direction was
fine but the bot "easily moves out of the line" given the small 3-sensor array. User
suggested a PID loop + lower motor speed, and said the kit isn't in hand now — so code
everything, and document tests in the TODO to run later. Then: "commit is now".

- **Diagnosis (reasoned, not measured):** `left()`/`right()` are exact mirrors under the
  invert flag, so a pin bug can't explain right-works/left-doesn't; the L sensor was firing.
  Real cause of the overshoot: `loop()` pinged the ultrasonic every iteration and
  `pulseIn(..., 30000)` blocks up to 30 ms on every no-echo ping (i.e. almost always), plus
  an every-loop Serial print (~20 ms at 9600 baud) — a very slow sensor→motor loop, and
  `left()/right()` were full-strength pivots. The earlier "reversed motors" fix
  (`INVERT_MOTOR_DIRECTION`) stays, but is now a calibration constant to confirm on hardware.
- **`Line_Follow_Obstacle_Avoid_Car.ino` rewritten:** PID over the 3 binary sensors
  (error x2 scale: L=-2, L+M=-1, M=0, M+R=+1, R=+2; lost line → keep turning toward the
  last-seen side, stop after 2 s, resume automatically when found), per-wheel PWM via
  `setMotorA/B/setWheels`, `forward/back/left/right` reimplemented on top of it. New
  constants `SWAP_SIDES` (assumes Motor A = right wheel, B = left — derived from the old
  `left()`), `BASE_SPEED` 110, `carSpeed` 170→130, `KP` 40 / `KI` 0 / `KD` 20. Ultrasonic
  every 100 ms with 6 ms timeout, 2 consecutive close pings to react, PID state reset after
  each avoidance manoeuvre, diagnostics throttled to 200 ms (`L M R E SL SR D`). The
  IDE had re-indented the whole file by 4 spaces since the last commit; the rewrite
  normalises that.
- **`Hardware_Test/Hardware_Test.ino` (new):** Serial-menu sketch — IR sensors raw/on-line,
  ultrasonic, servo sweep (checks the 10=right/180=left assumption), Motor A/B alone, drive
  sequence, PWM ramp (minimum moving PWM), runtime toggles `i` (invert) / `w` (swap) / `+ -`
  (test speed) so the two calibration constants can be settled without reflashing.
- **`TODO.md`:** new In Progress checklist "hardware bring-up tests" (steps 0-10: upload,
  each sensor, ultrasonic, servo, each motor, drive sequence, min PWM, PID dry run, track
  tuning order KP→KD→KI, obstacle avoidance) with a record-the-result blank per step, plus a
  Done entry.
- **Verification:** both sketches compile with zero warnings via the Arduino IDE's own
  `avr-g++ -fsyntax-only` (ATmega328P, real 1.8.7 core, Servo lib). **No hardware run** —
  every constant (`KP`, `KD`, speeds, avoid timings, A=right/B=left) is an untested estimate.
- Left out of the commit: a pre-existing uncommitted `.gitignore` change (not from this task).
- Known wrinkle left for later: `line_follow_obstacle_avoid/` holds several `.ino` files in
  one folder, but the Arduino IDE wants one sketch per same-named folder (noted in TODO step 0).

## 2026-10-12 — Acrux gift-greeter mission: plan + code

- **Task (from user):** Acrux must carry gifts to 3 or 4 special guests standing at pre-decided
  spots, wait at each for a live operator "yes", avoid unexpected obstacles/people, return home.
  Count only known just before the event. Mission code runs on a laptop over Wi-Fi.
- **Decisions agreed with user:** max 4 guests (run with N uses the first N spots); present
  action = stop and wait only; live input = operator command; return home after the last
  guest; no map exists yet (must be made); test the Intel RealSense; lights later; robot's
  ROS distro unknown — check in the lab.
- **Read in `bots/acrux`:** `nav2_params.yaml` (footprint ~0.76x0.80 m, inflation 0.55, DWB
  0.3 m/s, `/scan` + `/camera/points`), `autobringup.launch.py`, `navigation.launch.py`,
  `cartographer.launch.py`, `lidar.lua`. **Findings recorded in guide §8/§14:** with
  `exploration:=False` nothing launches AMCL and Cartographer still runs in mapping mode, so
  "navigate on a saved map" may not localize against the saved map; no collision-monitor layer
  exists; the `cmd_vel` chain could not be confirmed from source.
- **Files created:**
  - `learn/build/09-acrux-greeter-mission.md` — full plan, safety layers, runbook, open items.
  - `practice/acrux_greeter/` — `mission.py` (ROS-free state machine), `greeter_config.py`,
    `mission_node.py` (Nav2 adapter, laptop side), `guests.yaml` (placeholders,
    `surveyed: false`), `config/collision_monitor.yaml`, `launch/safety.launch.py`,
    `requirements.txt`, `README.md`, `tests/` (60 pytest tests).
- **Files changed:** `learn/README.md`, `.CLAUDE/CLAUDE.md` (file table, Key Modules, TODO
  list), `TODO.md`.
- **Design choices:** mission logic separated from ROS so it is testable on Windows; safety
  (collision monitor) runs on the robot, not the laptop; `--count` has no default;
  `mission_node.py` refuses placeholder coordinates unless `--allow-unsurveyed`; "n"/"no" are
  deliberately not aliases for yes; stop polygon is front-only because a stop zone blocks all
  motion including reversing.
- **Verification:** `pytest` 60 passed; `mission_node.py` and `safety.launch.py` only
  byte-compile checked. **Never run on Gazebo or the robot.** Nav2 collision-monitor
  parameter names (`max_points`, polygon `points` format) are from memory of the Humble docs
  and unverified.
- **Left out of the commit:** pre-existing uncommitted `.gitignore` change and `AGENTS.md`.

## 2026-10-18 — Acrux experiment moved to root, renamed to "waypoint", lab record + lab manual

- **Task (from user):** the Acrux guest work is a lab experiment: move it to the repo root, write a
  lab record from the start to now, rename the project to waypoint terms (no "guest"), and write a
  full lab manual for the class. Scope/format agreed: whole course, Markdown, folder `waypoint_mission/`.
- **Moves (`git mv`, history kept):** `practice/acrux_greeter/*` → `waypoint_mission/`;
  `tools/acrux/*` → `waypoint_mission/tools/` (the `acrux` script's `../..` still resolves to the repo
  root); `learn/build/09-acrux-greeter-mission.md` → `waypoint_mission/GUIDE.md`.
- **Rename:** `guests.yaml`→`waypoints.yaml`, `greeter_config.py`→`waypoint_config.py`, `slots`→`waypoints`,
  `guest_count`→`waypoint_count`, `MAX_GUESTS`→`MAX_WAYPOINTS`, `AT_GUEST`→`AT_WAYPOINT`,
  `/greeter/command`→`/waypoint/command`, `--guests`→`--waypoints`; "gift" wording became "payload / task
  done". Cross-links fixed. `pytest` 60 passed after the rename.
- **New files:** `waypoint_mission/LAB-RECORD.md`, `lab-manual/00-front-matter.md`, `lab-manual/01`–`05`.
- **Updated:** `learn/README.md`, `README.md`, `.CLAUDE/CLAUDE.md`, `TODO.md`.
- **Not done / caveats:** result and observation tables are deliberately blank — nothing ran on hardware.
  Old `practice/acrux_greeter/.venv` (untracked) was deleted with the folder; new `.venv` in
  `waypoint_mission/`. `AGENTS.md` (untracked mirror of CLAUDE.md) not synced. Past log entries keep the old names.
  Nothing committed.

## 2026-10-18 — Standalone install script and setup docs

- **Task (from user):** an install script so someone with no ROS/libraries can install ROS, clone the repo and recreate the work; user clarified it is repo-wide documentation, not lab-specific.
- **Files created:** `setup/install.sh` (Ubuntu 22.04→Humble, 24.04→Jazzy; flags `--with/--without-nav2|lab|practice`, `--with-gazebo`, `--with-bots`, `--no-ros`, `--all`, `--distro`, `--dir`, `-y`, `--dry-run`), `setup/INSTALL.md` (needs, one-command + manual steps, verify, troubleshooting, uninstall).
- **Files changed:** `README.md`, `.CLAUDE/CLAUDE.md`, `TODO.md`. Deliberately not touched: `waypoint_mission/README.md`, `lab-manual/`, `docs/ros-install/`.
- **Verification:** `bash -n` and `--dry-run --all` on Windows Git Bash only. **Never run on a real Ubuntu**; apt package names (e.g. `nav2-collision-monitor`, `slam-toolbox`, `ros-gz`) not checked against the live repos.
- Added `slam-toolbox` to the Nav2 set (needed for mapping) beyond the agreed list.

## 2026-10-18 — robot_calc and uno_car moved to root as lab experiments 6 and 7

- **Task (from user):** the numerical-calculation program and the UNO Smart Robot Car Kit are lab experiments too. Defaults agreed: move the whole UNO folder (vendor files included, unedited); do not restructure the sketches for the Arduino IDE.
- **Moves (`git mv`):** `practice/robot_calc/` -> `robot_calc/`; `docs/UNO Smart Robot Car Kit/` -> `uno_car/`; `practice/` removed. `robot_calc/.venv` recreated (a moved venv has stale paths); `pytest` 14 passed.
- **References fixed:** `setup/install.sh`, `setup/INSTALL.md`, `README.md`, `learn/index.md`, `learn/README.md`, `learn/lab/05-...`, `lab-manual/02-...`, `robot_calc/README.md`, test docstring, `.CLAUDE/CLAUDE.md`, `TODO.md`. Old paths remain only in historical log/Done entries.
- **New files:** `robot_calc/LAB-RECORD.md`, `uno_car/LAB-RECORD.md`, `lab-manual/06-robot-calculations.md`, `lab-manual/07-uno-car-line-follow-obstacle.md`; `lab-manual/00-front-matter.md` extended to experiments 1-7.
- **Accuracy note:** the UNO merged sketch WAS flashed once (2026-09-24 user report: reversed, right turn OK, left not turning, drifted off line); the later PID rewrite and `Hardware_Test` were compile-checked only. The record says so. All result tables are blank by design.
- **Caveats:** the `docs/` read-only rule was bent for the UNO move (vendor files moved, not edited). `AGENTS.md` not synced. Nothing committed.


## 2026-10-20 — Coin-D6 lidar live plotter (`coin_d6/`)

- User has a MENGJIE Coin-D6 TOF lidar on a USB2LDS adapter and asked for a Python live plot; no baud/protocol info.
- **Probing (read-only):** adapter is a CP210x on COM3. Listened at 230400/115200/460800/921600/128000/153600 baud and all four DTR/RTS combos: 0 bytes. User confirmed the motor is not rotating, so likely power/wiring/motor-control pin, not code. Scratch scripts stayed in the session scratchpad.
- **Web search:** only a reseller page (230400 baud UART, ~10 Hz, 4000 samples/s, 4-pin with motor control). No public packet format found.
- **Files created:** `coin_d6/coin_d6.py` (profile-driven parser, reader thread, sniffer with header guess), `coin_d6/plot_live.py` (polar live plot, `--sniff`), `coin_d6/profile_example.yaml`, `coin_d6/requirements.txt`, `coin_d6/tests/test_parser.py`.
- **Decision:** default `ld06` profile (LDROBOT LD06 layout) is an **unverified guess**; the real Coin-D6 layout goes in a `--profile-file` YAML once the vendor protocol is obtained.
- **Open:** lidar must spin first; then sniff, then confirm/replace the profile. Tracked in `TODO.md`.


## 2026-10-27 — Add figures to AMR lab record

- Source: `Downloads/AMR_Lab_Record_23BMH1029.zip` (original HTML + 106 images). Matched each image to the md paragraph preceding it in the HTML.
- **Changed:** `docs/AMR_Lab_Record_23BMH1029.md` — 117 `![Figure](...)` lines inserted (106 distinct images, nothing skipped, incl. cover/logo pages); no existing text altered.
- **Added:** `docs/AMR_Lab_Record_23BMH1029_images/` (106 files, ~20 MB), a new folder so it does not clash with `docs/wolf/images`.
- **Caveat:** placement is automatic (text alignment) - eyeball the cover pages and the multi-image steps. Nothing committed.

## 2026-11-09 - Portfolio artifact source saved to the repo

- User asked to run "the showcase gui"; the repo's only GUI is `beetle_patrol/beetle_gui.py` (needs ROS 2 Humble + `/usr/bin/python3`, not runnable on this Windows box, WSL has no distro). User meant the published artifact instead: "Mithunvel ROS 2 Portfolio" (https://claude.ai/artifact/95mdeAT51U9ifLwxFLowbr), opened it.
- No source for it in `ROS_LAB` or the sibling `SHOW-CASE` repo, so read the published artifact and saved its HTML to `showcase/portfolio.html` (4,599,855 bytes, byte-identical to the live version `1794225074-4273`).
- Committed with only these two doc entries; the unrelated uncommitted tunnel-rig notes in `TODO.md` / `CLAUDE-LOG.md` were left out of the commit.

## 2026-11-07 — Tunnel inspection rig (ESP32 + MG996R) added

- User asked for an ESP32 web GUI to pan/tilt a camera in a small tunnel: zero on boot, a HOME button that returns to zero. Defaults agreed: zero = 0 deg, 2 servos (Pan GPIO13, Tilt GPIO14), no light output, AP mode (`TunnelRig`).
- **Files created:** `tunnel_rig/tunnel_rig.ino`, `tunnel_rig/README.md` (wiring, flash, use).
- Adapted the user's pasted sketch: zero replaces the 90 deg home, ZERO and Home merged into one HOME button, saved-home/Preferences removed, Tilt min widened to 0.
- Build fix: the web page raw string failed to compile (everything after the first ~120 lines was parsed as C++); fixed by splitting it with `)rawliteral" R"rawliteral(` at the `<script>` tag.
- Compiled (arduino-cli, esp32 core 3.3.3, ESP32Servo 3.2.1) and flashed to COM3; serial shows `[ZERO] driving to zero` -> AP up -> `READY`. Servos/GUI not yet tested on hardware.
- Camera is the Ethernet one and goes to the laptop, not the ESP; GUI only embeds an MJPEG/snapshot URL.
- Nothing committed.

## 2026-11-11 — Tunnel rig rewritten: servos/Wi-Fi out, MDD3A motors + Bluetooth in

- User dropped the servo pan/tilt and wants motor movement via a Cytron MDD3A over Android Classic Bluetooth. Agreed: 4 motors as tank drive (left pair on channel 1, right pair on channel 2), Android only, Wi-Fi GUI removed (Wi-Fi + Classic BT together is unreliable on the ESP32).
- **Files rewritten:** `tunnel_rig/tunnel_rig.ino`, `tunnel_rig/README.md`; updated `TODO.md` and the `tunnel_rig/` entry in `.CLAUDE/CLAUDE.md`.
- **Design:** MDD3A PWM-PWM mode (A = forward PWM, B = reverse PWM, both 0 = brake), 20 kHz 8-bit LEDC. Pins: left GPIO25/26, right GPIO32/33 (not GPIO14/12 — boot-time glitches). Commands F/B/L/R/G/I/H/J/S + 0–9 speed; acceleration ramped, S/failsafe stop instantly; 500 ms failsafe (`CMD_TIMEOUT_MS`, 0 disables); `INVERT_LEFT/RIGHT` flags; USB serial accepts the same characters for bench tests.
- Compiled (arduino-cli 1.5.1, esp32 core 3.3.3, no extra libs; 81 % flash) and uploaded to COM3; boot log shows `[BT] ready ... 'TunnelRig'`. **Not tested with the MDD3A or motors wired**, nor paired from an Android phone.
- Nothing committed.

## 2026-11-11 — Tunnel rig: Windows PC control panel

- User asked for a PC control panel (option 1 of: PC panel / ESP web page / Android app). `TunnelRig` was already paired with this PC; Windows exposes it as outgoing **COM6** (MAC 8C94DF4CB662; COM4/COM7 are incoming ports, COM5 is another device).
- **Files created in `tunnel_rig/`:** `control_panel.py` (Tkinter GUI + pyserial, connect in a background thread, hold-to-drive with 150 ms keepalive, key auto-repeat debounce, stop on release/focus loss/disconnect/close), `panel_logic.py` (held directions → F/B/L/R/G/I/H/J/S; opposites cancel), `panel_config.yaml`, `requirements.txt`, `tests/test_panel_logic.py`, local `.venv`.
- **Verified:** 33 pytest tests pass; headless open of COM6 took 1.8 s and the ESP32 answered `speed 5` to `S` + `5`; the panel window starts without errors. **No drive command has been sent to the rig**, so motor behaviour is untested.
- `repeat_ms` is clamped to 50–400 ms so it can never exceed the firmware's 500 ms failsafe. The panel rewrites `panel_config.yaml` (port) on each successful connect.
- Nothing committed.


## 2026-11-11 — Tunnel rig: Bluetooth -> Wi-Fi/UDP with comm-health bar

- Bluetooth dropped as soon as the rig entered the tunnel. New plan (user): router inside the tunnel, ESP32 joins it over Wi-Fi, router -> Ethernet -> laptop; PoE camera (192.168.1.250) on a PoE switch uplinked to the router. Router model/settings taken from the old `Tile_Sorting` project (`documents/electrical/network_plan.md`): D-Link DIR-825 AC1200, LAN 192.168.1.1/24, DHCP .100-.199, planned SSID `TileLine` (Wi-Fi never verified there). User clarified none of the tile project's other nodes are used.
- Earlier same day: both `INVERT_*` flags set `true` (motors ran backwards) and reflashed over USB; forward/turns then OK. Remaining hardware fault: **left side does not move on reverse** -> suspect GPIO25 -> M1A jumper (A inputs = physical reverse after inversion).
- **Firmware rewritten (`tunnel_rig.ino`):** Bluetooth removed; Wi-Fi STA with fixed IP 192.168.1.60, UDP 4210, `"<seq>:<cmd>"` in / `"<seq>,<rssi>,<speed>,<last>"` out, `?` = ping, auto-reconnect every 5 s, `stopNow()` on Wi-Fi loss, 500 ms failsafe kept. Credentials in gitignored `secrets.h` (`secrets.h.example` committed; `.gitignore` updated). Compiles (69 % flash). **Not flashed** - `secrets.h` holds placeholders.
- **Panel rewritten:** pyserial/COM port replaced by a UDP socket; packet every 150 ms (held command or STOP, doubles as ping); `HealthTracker` + `health_score` in `panel_logic.py` (50 % loss / 25 % RTT / 25 % RSSI -> GOOD/FAIR/POOR/LOST); coloured health bar + RSSI/RTT/loss text; drive disabled on LINK LOST; speed re-sync from replies; Windows UDP connreset handled; Open camera button. `requirements.txt` now pyyaml + pytest.
- **Verified:** 56 pytest tests pass (one test of mine was wrong and fixed); the panel run against a fake UDP rig on localhost showed healthy -> hold W sends F -> release sends S -> silence gives LOST with drive disabled -> recovery. Not tested against the real ESP32/router/motors.
- **Docs:** new `tunnel_rig/WIFI-PLAN.md` (topology, addressing, protocol, safety, health scoring, test procedure, results table, open items); `README.md` rewritten; `TODO.md` and `CLAUDE.md` updated.
- Nothing committed.

## 2026-10-28 — Beetle patrol: robot setup + pure-logic modules

- **Robot (192.168.0.154, ROS 2 Jazzy):** installed a new SSH key; fixed OpenCV by moving the user-site NumPy 2.5.3 to `~/.local/numpy2_backup` (system NumPy 1.26.4 + cv2 4.6.0 now import); built `explore_lite` from robo-friends/m-explore-ros2 `main` in a separate `~/patrol_ws` (not run yet); `apt update` + installed `ros-jazzy-compressed-image-transport`. `lyra_ws` untouched.
- **Laptop:** new `beetle_patrol/` — `patrol/{heatmap,priority,motion,fusion,config,schema}.py`, `patrol.yaml`, `zones.yaml`, 35 tests (all pass). Credentials in gitignored `beetle_patrol/secrets.env` (+ `.example`); `.gitignore` updated.
- **Decisions:** camera weight < warn threshold so the camera alone cannot raise a warning; EKF (wheel+IMU) is reused for ego-motion, not rebuilt; ORB-SLAM deferred.
- **Note:** pytest must run with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` when ROS Humble is sourced (its plugins need `lark`).
- **Open:** node, bag recording, sim, GUI, robot launch file. Nothing committed.

## 2026-10-28 (later) — Beetle patrol: engine, node, bag recorder, robot comms test

- **Added:** `patrol/engine.py` (mode + goal + decision logic), `patrol/bag.py` (`ros2 bag record`, sqlite3+zstd because Humble has no mcap plugin), `patrol_node.py` (Nav2 goals, tf, E-STOP via disarm + zero-vel stream), `topics`/`recording` sections in `patrol.yaml`. 46 tests pass.
- **Design fix found by a test:** a just-visited high-risk zone was re-picked immediately -> added `priority.min_revisit_s` (30 s).
- **Correction to earlier plan:** a laptop-only node cannot stop the robot over a dead link; Nav2 runs on the robot and just finishes/aborts its goal. Documented in `patrol_node.py`.
- **Robot:** started base stack (`~/patrol_logs/start_base.sh`: `robot.launch.py mode:=teleop imu:=true camera:=true`, log `~/patrol_logs/base.log`). Camera topic is `/pi_camera/image_raw/compressed` (config corrected).
- **Comms test (10 s rclpy probe):** scan, imu, camera, odom, armed all received; `map->base_link` tf OK; arm/disarm services return success.
- **Not verified:** `/lyra/armed` flaps between True/False after arming, so real arming is unproven; no motion command was sent. Node never run against Nav2.
- Nothing committed.

## 2026-10-28 (evening) — Arming investigation: shared ROS domain

- **Root cause (very likely):** `/lyra/armed` flapped and every node appeared twice because another BeetleBot shares ROS_DOMAIN_ID 155 on the lab Wi-Fi (my robot runs one copy; `ps` agrees). On domain 154 each node appears once. My earlier `/lyra/arm` + `/lyra/disarm` calls on 155 may have been answered by the other robot; no motion command was ever sent.
- **Also found:** broken `lyra_base.service` (mangled ExecStart, restart counter ~596) — untouched.
- **Blocked:** a name-pattern `pkill` of the robot stack was denied by the permission system (could hit other processes); stale pids 6568/6580 remain. Chose a reboot instead.
- **Docs:** added `beetle_patrol/README.md`; TODO updated. Nothing committed.

## 2026-10-28 (night) — Arming fixed (private domain), robot rebooted

- Rebooted the robot at the user's request (`sudo systemctl reboot`, stale pids gone). Started one stack on **ROS_DOMAIN_ID=154**: 13 nodes, none duplicated; scan 8 Hz, odom 17 Hz (the earlier doubled rates were two robots).
- The `map` frame seen earlier came from the other robot's SLAM; in teleop mode there is no `map` frame, so `map->base_link` fails until SLAM/AMCL runs on our robot.
- **Arm test (laptop rclpy, no motion):** arm -> `/lyra/armed` True 40/43, one flip, steady; disarm -> all False. Arming confirmed working.
- Open: motion test, then SLAM + explore_lite, then patrol. Nothing committed.

## 2026-10-28 (night, cont.) — Motion test

- First attempt aborted safely before arming (no odom within 2 s; disarm service not discovered). The robot had meanwhile rebooted again at 07:15 (clean `systemd-reboot`, power OK, throttled=0x0; trigger unknown - no sudo/cron entry). Test script hardened: waits up to 20 s for odom, requires arm AND disarm services before arming, always zero+disarm in `finally`.
- **Result:** arm OK; 0.1 m/s x 1 s on `/cmd_vel_nav` reached `/cmd_vel` through the gate (26 msgs); odom shows 0.027 m, peak 0.049 m/s; disarm -> stopped (final odom vx ~0), armed False.
- **Open:** odometry vs commanded distance gap (ramp-up vs wheel-odom spike filtering vs real slip) - needs a physical measurement. Nothing committed.

## 2026-10-28 (night, cont.) — Retune for 3 m x 3 m test area

- `zones.yaml`: 3x3 grid of 1.0 m, origin (-1.5,-1.5) (assumes robot starts mid-room). `patrol.yaml`: visit radius 0.5, max_age 120, alert memory 60, min_revisit 15, failed cooldown 30, cluster gap 0.25, max cluster 0.8.
- `heatmap.build_zones` now rejects risk/blocked cells outside the grid (the old "2,3" override would have been silently ignored). Engine tests now use their own fixed 3x4 grid so they do not depend on the shipped yaml. 48 tests pass.
- Nav2 params read, not changed (vendor config): robot_radius 0.15 < real ~0.26, inflation 0.25-0.30, cruise 0.4 m/s.
- Nothing committed.

## 2026-10-28 (night, cont.) — Robot ladder, Part A (disarmed bring-up)

- Subagents (Sonnet, planned by Opus): protocol.py (37 tests), robot/ stack files + watchdog (14 tests), tools (overlay, bag_check; 23 tests) done; sim, GUI, node fixes still running. Suite 122 passing at last count.
- Fixed `robot/deploy.sh` key-path expansion (secrets.env holds a literal `$HOME`). Dry run, then `--go`: files now in `~/patrol_ws/beetle_patrol_robot/` (compile OK under Jazzy python).
- Started `~/patrol_logs/start_patrol.sh` (patrol_robot.launch.py explore:=false, domain 154, pid in ~/patrol_logs/patrol.pid, log ~/patrol_logs/patrol.log). Nav2 lifecycle: "Managed nodes are active"; only a benign bt_navigator error-code warning.
- Verified from the laptop (rclpy, Humble): /navigate_to_pose server present, explore + watchdog + image_throttle nodes up, our Nav2 params loaded (footprint 0.375x0.36, 0.15 m/s), explore min_frontier_size 0.3, map 247x246 @0.05, tf map->odom, map->base_link, base_link->lidar_link all OK, camera throttled to 4.5 Hz x 32 KB (was ~56 Hz), /lyra/armed False. NOTHING ARMED OR MOVED.
- Part B (arm + goal with wheels lifted, E-STOP, watchdog) waits for the node fixes + explicit user confirmation that wheels are off the ground.

## 2026-10-28 (late) — Wheels-lifted movement test + first hardware run of node and GUI

- Sonnet agents finished: simulator (18 tests, isolated domain 77), GUI (20 tests), node fixes (25 new tests; 182/183 pass, one stale test being fixed), tools. A further Sonnet agent is fixing Nav2 result delivery (below).
- **Wheels-lifted test (scratchpad lifted_test.py, my own rclpy script, domain 154):** arm OK after the heartbeat is primed (an earlier run aborted before motion because the robot never confirmed armed; cause not fully proven); forward/reverse/rotate: all four wheels turn in the right direction, ticks ~1350-1370 per wheel and mirrored on reverse; odom distance 0.155 m vs 0.30 m commanded (3 s at 0.1 m/s); yaw odom unreliable when lifted (IMU does not rotate). Watchdog disarmed the robot 2.03 s after the heartbeat stopped. 
- **Found:** (1) Nav2 goals are accepted but the RESULT never reaches the Humble client (Jazzy result msg differs) - the robot log shows 'Goal failed'/'Goal canceled' while the laptop waited -> patrol would stall; fix delegated (use /navigate_to_pose/_action/status + goal timeout). (2) Nav2 planner aborted both goals ('Failed to create plan' from (0.08,0.01)) - lifted robot, nearly unknown map; retest on the floor in the 3x3 room. (3) cmd_vel_gate forwards /cmd_vel_nav to /cmd_vel even when disarmed (auto_arm_for_nav=True); stopping relies on the bridge/STM32 refusing commands while disarmed - NOT yet proven at wheel level (no wheel-tick check after disarm).
- Node (pid in scratchpad) + GUI started on domain 154 from detached scripts; node status valid against protocol.validate_status at ~2 Hz with live robot pose; nothing armed, no Start sent. Lesson: background `&` jobs die when the tool call ends - use `setsid nohup`.

## 2026-10-28 (late night) — Reduced scope + boxes turn green on entry

- User reduced scope: fixed 3x3 m box, virtual boundary, only revisit those zones. Stopped the dynamic-zone agent mid-run; its code (patrol/discovery.py, set_start, zones[].n, engine/heatmap changes) stays in the tree but `zones.yaml` `dynamic.enabled: false`; one test updated; 244 tests pass in both interpreters.
- E-STOP stuck: node was in `estop` and the GUI window had its own latch streaming zero Twist (~18 Hz) on /cmd_vel_nav; node released via `release` command; the GUI latch must be released from the GUI (not closed by me - could not confirm that window was mine).
- Heatmap rule changed: entering a box (point inside its rectangle, or within visit radius) turns it green in EVERY mode (before: patrol mode only, centre radius only). Verified live on the robot: box R2C2 at pose (0.79, 0.51) age 0.0 s while the other 8 aged 19.6 s. Node restarted by PID (domain 154).
- Open: virtual boundary (geofence) not built yet; need the robot's start position inside the box to place the grid origin; zone numbers n are row-major (R0C0 = 1), not 'start = 1'. Motion warnings still skipped on hardware (map<-lidar_link tf lookup fails at the scan stamp).

## 2026-11-12 — Tunnel rig: ESP32 flash, router debugging, Pi alternative

- Flashed `tunnel_rig.ino` to the ESP32 on COM3 (first tries failed "No serial data received"; worked with `--upload-property upload.speed=115200`). Serial shows it loops `joining 'TileLine'` / `retrying...` forever: the D-Link DIR-825 (`dc:ea:e7:b0:b4:4f`) 2.4 GHz radio (`...:51`) still broadcasts a blank SSID on channel 7 and 5 GHz is the factory `DIR-825-5G-B44E`, so the router's wireless config was not applied. Camera `192.168.1.250` also did not answer.
- Found: laptop Wi-Fi `LRL-Home` and the D-Link LAN are both 192.168.1.0/24, so plugging Ethernet in kills Wi-Fi/internet. Workaround: join the iPhone hotspot. Not changed on the PC.
- Wrote the Pi 5 alternative in `tunnel_rig/pi/` (`rig_logic.py`, `rig_server.py`, `rig_config.yaml`, `tunnel-rig.service`, README with the header-pin wiring GPIO12/13/19/16 -> MDD3A). Same UDP protocol as the ESP32, so the PC panel is unchanged. `tests/test_rig_logic.py` added (8 tests; 69 total pass). **Not run on the Pi**: `klmpi` did not answer at `192.168.1.11` or `172.20.10.4`. Nothing committed.
- Later 2026-11-12: Pi came up at `192.168.1.11` (hostname `tile-pi`, key SSH as `klm`, deps already installed). Deployed `tunnel_rig/pi/*` to `~/tunnel_rig_pi`; smoke test sent only `?`/`S`/`4` and got correct replies in ~1 ms (no drive commands, motors/GPIO untested). `panel_config.yaml` host changed `192.168.1.60` -> `192.168.1.11`. systemd service not installed yet.
- 2026-11-12 (evening): Smoke during first Pi test run - a thin Pi<->MDD3A GND jumper burned (likely motor return current through the signal ground; battery - must go to MDD3A POWER - first). Pi diagnostics after: all PMIC rails fine, temp 46 C, no SD errors; under-voltage warnings earlier (5 V rail 4.96 V, 900 mA limit) cleared with a different supply (`throttled=0x0`, 5.08 V). Rig test showed the channels swapped: `pi/rig_config.yaml` now maps left = GPIO19/16, right = GPIO12/13, `invert_right: false` (software only, wiring unchanged; **not yet re-tested on the wheels**). Panel got Start/Stop Pi server buttons (SSH via `ssh_server_command` in `panel_logic.py`; 74 tests pass). Pitfall: `pkill -f rig_server.py` over ssh kills its own shell - use `'[r]ig_server'`.

## 2026-11-14 — Tunnel rig: Pi on router, direction flip, panel reverse checkboxes

- Direct-Ethernet attempt failed (no reply; PC adapter change needs admin). Pi then reachable via the router at `192.168.1.11`.
- Front/back were reversed on the rig: flipped `invert_left` -> false, `invert_right` -> true in `tunnel_rig/pi/rig_config.yaml`, copied to the Pi and restarted `rig_server.py` (**not yet re-tested on the wheels**).
- Panel (laptop only): added `flip_command()` in `panel_logic.py`, two checkboxes "Reverse fwd/back" / "Reverse left/right" in `control_panel.py` (applied in `send()`), startup defaults `reverse_fwd_back` / `reverse_left_right` (both false) in `panel_config.yaml`, new test. Key map checked: W/S/A/D + arrows -> F/B/L/R, diagonals G/I/H/J. 75 tests pass. Not committed.
