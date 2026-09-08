# TODO

## In Progress

- [ ] Work through `learn/foundations/01-linux-and-shell.md` and practice each command in a real terminal
- [ ] Verify the Track B guides against a live ROS 2 Jazzy + Gazebo Harmonic environment
      (written against docs/source, not yet run end to end — no Linux box in this session)

## Done

### `practice/robot_calc/` — mechatronics calculator (2026-09-08, commit: _pending_)

- [x] Built a menu-driven CLI mechatronics calculator under `practice/robot_calc/`
  (own `.venv`, `requirements.txt` = PyYAML + pytest), on the `klm_menu` engine
  (copied verbatim from github.com/KL-Mithunvel/menu), same shape as `Furnace_simulation`.
- [x] **5 grouped calculation sets**, each runs its whole group and shows a results table
  or the full working: (1) tractive effort — acceleration, all forces, wheel + motor
  torque, traction margin/verdict/max-climb-angle; (2) speed, wheel rpm & gearing;
  (3) battery runtime, range & drive power; (4) diff-drive kinematics (forward + inverse);
  (5) diff-drive dynamics (straight-line accel + pure spin). Sets 4–5 reproduce the
  `docs/Kinematics and Dynamics_AMR_Problems.pdf` worked answers.
  *(Started as 20 tiny one-output calcs; kl mithunvel asked to combine them into sets.)*
- [x] `params.yaml` holds all parameters as `{value, unit, desc, confirm}`; BeetleBot
  seed values from `docs/beetlebot/01-introduction.md`, estimates flagged `confirm: true`.
  Edit in-app (all params, or just the ones a calc uses) and save back to YAML.
- [x] `tests/test_calculations.py` — 14 pytest cases: per-set numeric checks,
  PDF-handout fidelity (Problems 1-4), slip verdict, error paths, bad-YAML handling,
  renderer output, "every parameter used by some set". All green; `py_compile` clean.
- [x] Error-handling pass: clean exit on EOF / Ctrl-C, missing/malformed `params.yaml`
  caught with a message, resolve() errors caught, Save asks before overwriting, menu
  hotkeys reviewed (no collisions). `make_sample_output.py` + `SAMPLE_OUTPUT.md` added.
- [x] Updated `.CLAUDE/CLAUDE.md` (Key Modules, Project-Specific Overrides, Project TODO).
- [ ] *(kl mithunvel)* replace `confirm: true` params with real BeetleBot figures;
  list + add the remaining calculations wanted.

### Vendored VEEROBOT tutorial docs into `docs/` (2026-09-08, commit: _pending_)

- [x] Copied `beetle bot/` → `docs/beetlebot/` and `wolf robot/` → `docs/wolf/` verbatim from
  <https://github.com/SMARTS-LAB/Documention> (MIT, commit `c9eb011`). 16 `.md` chapters +
  README + images each. Added `SOURCE.md` (provenance + MIT text) to each folder.
- [x] Updated `.CLAUDE/CLAUDE.md` (Architecture table, Data Files, Development Rule 2) and
  `README.md` to record these as third-party reference docs, distinct from the read-only
  instructor handouts. Wolf docs target ROS 2 **Foxy / Ubuntu 20.04** (noted).
- [ ] *(future, not now)* consider tracking Wolf as a submodule + adding it to the
  `learn/build/` robot comparisons and the ROS-distro/version tables

### `learn/` restructure + Track B build-out (2026-09-07, commit: _pending_)

Reorganised `learn/` into `foundations/` + `lab/` (Track A) + `build/` (Track B) and built
Track B out so it covers building a ROS 2 autonomy stack for any robot — description, sim,
control, localization, SLAM, path planning, navigation. All 11 phases complete:

- [x] **Phase 1 — reorg** — `learn/{foundations,lab,build}/` created, 10 guides `git mv`'d in
      with per-folder numbering, all cross-links fixed, `learn/README.md` written, root
      `README.md` + `.CLAUDE/CLAUDE.md` + `TODO.md` + `CLAUDE-LOG.md` updated
- [x] **Phase 2 — reworked `foundations/01-linux-and-shell.md`** — retitled; added SSH keys/
      `~/.ssh/config`, `rsync`, `tmux`, `systemd`/`journalctl`, `udev` rules, `rosdep`/`vcs`,
      `git` for workspaces, DDS discovery/multicast/firewall, users/groups; folded in the
      user's own early Linux notes (`rmdir`/`cp`/`mv`/`rm`/`less`/`find`/`man`/`which`/`chown`
      + tab-completion/history); kept BeetleBot examples + a "lab quick reference" box (§17)
- [x] **Phase 3 — extended `foundations/02-ros2-concepts.md`** — added §7–§15: QoS,
      parameters/YAML, lifecycle nodes, executors/callback groups, actions, TF2, creating
      packages + custom interfaces, launch files in depth, composition (§1–§6 untouched)
- [x] **Phase 4 — `foundations/04-ros1-vs-ros2.md`** (new)
- [x] **Phase 5 — `build/03-build-a-ros2-autonomy-stack.md`** (new — the spine)
- [x] **Phase 6 — `build/04-robot-description-and-tf.md`** (new)
- [x] **Phase 7 — `build/05-simulation-gazebo.md`** (new)
- [x] **Phase 8 — `build/06-control-and-ros2-control.md`** (new)
- [x] **Phase 9 — `build/07-localization-and-slam.md`** (new)
- [x] **Phase 10 — `build/08-navigation-and-path-planning.md`** (new)
- [x] **Phase 11 — final pass** — `build/01`/`02` footers point at the deep dives with a
      §-to-file map; renumber shorthand (`08`→`01` etc.) reconciled; all inter-guide `.md`
      references verified to resolve; indexes cross-checked

### Earlier

- [x] Read both course syllabus PDFs and all `docs/` handouts; wrote the course-and-lab map and three lab-day checklists (commit: _pending_) — *files now `learn/lab/00`–`04`, renumbered in the restructure*
- [x] Read the actual checked-out source of all three submodules and wrote the three-bots architecture walkthrough with the end-to-end localization/SLAM/obstacle-avoidance/Nav2 pipeline (commit: _pending_) — *now `learn/build/01-three-bots-architecture.md`*
- [x] Wrote the "ROS 2 across robot types" guide (arms/MoveIt 2, legged, drones, multi-robot) (commit: _pending_) — *now `learn/build/02-ros2-across-robot-types.md`*

## Not Started

- [ ] `practice/robot_calc/`: confirm the `confirm: true` params with the instructor /
      BeetleBot datasheet; add the remaining wanted calculations to `calculations.py` + `CALCS`
- [ ] Read `learn/foundations/02-ros2-concepts.md`; run the turtlesim publisher/subscriber tutorial on a Linux machine
- [ ] Read `learn/lab/01-lab-day-runbook.md`; memorise the connect → bringup → arm → drive → disarm sequence
- [ ] Practice writing a minimal `rclpy` node from memory (publisher + subscriber + timer)
- [ ] Trace `docs/BEETLEBOT Updated _Obstacle_avoid.txt` line by line; be able to explain the LaserScan windowing and the reverse/turn state machine
- [ ] Skim the official ROS 2 Jazzy tutorials linked in `learn/foundations/03-official-docs-index.md` (Beginner CLI + Beginner Client Libraries)
- [ ] Confirm my own robot number / `ROS_DOMAIN_ID` / IP / Wi-Fi password with the lab instructor (handouts disagree)
- [ ] Install ROS 2 Jazzy (or use Docker `ros:jazzy`) on a personal Linux machine for offline practice
