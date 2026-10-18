# TODO

## In Progress

- [ ] Work through `learn/foundations/01-linux-and-shell.md` and practice each command in a real terminal
- [ ] Verify the Track B guides against a live ROS 2 Jazzy + Gazebo Harmonic environment
      (written against docs/source, not yet run end to end — no Linux box in this session)

### Waypoint mission (Acrux) — verify in the lab (planned 2026-10-12)

Plan: `waypoint_mission/GUIDE.md`; code: `waypoint_mission/`; record: `waypoint_mission/LAB-RECORD.md`. The state
machine is pytest-tested; **everything ROS-side is written but never run.** Open items are
tracked with a result column in guide §14 — fill them in there as you go.

- [ ] **Check the robot's ROS distro** (`printenv ROS_DISTRO`) — not known yet; repo says Humble
- [ ] Confirm what provides `map → odom` with `exploration:=False` (is AMCL launched at all?)
- [ ] Confirm the real `cmd_vel` chain (`ros2 topic info /cmd_vel -v`) and wire the collision monitor
- [ ] Test the Intel RealSense (`/camera/points`): stable? sees what LiDAR misses? CPU cost? (guide §9)
- [ ] Make the lab map; survey home + 4 waypoints; set `surveyed: true` in `waypoints.yaml`
- [ ] Gazebo run (`--sim`), then robot with wheels lifted, then cardboard obstacles, then rehearsal
- [ ] Decide laptop setup (native Ubuntu vs WSL2 mirrored networking) and install `nav2_simple_commander`
- [ ] Later: status lights; optional camera-based target detection (guide §15)

### UNO Smart Robot Car Kit — hardware bring-up tests (kit not in hand yet, 2026-09-24)

The PID line-follower + obstacle-avoid sketch is **compiled but never run on hardware**. Do
these in order; sketches are in `docs/UNO Smart Robot Car Kit/line_follow_obstacle_avoid/`.
Tests 1-7 use `Hardware_Test/Hardware_Test.ino` (Serial Monitor 9600 baud, type the menu
letter + Enter, any key aborts). Put the bot on a stand, **wheels off the ground**, for motor tests.

- [ ] **0. Upload works.** Earlier upload failed (`unable to open port COM6`, `not in sync`) —
      that was the port/driver/cable, not the code (compile was fine). Check Device Manager
      for the port + CH340 driver, close any Serial Monitor, Tools → Board = Arduino Uno.
      Note: the Arduino IDE wants each sketch in a folder of the same name — copy each
      `.ino` into its own folder (e.g. `Line_Follow_Obstacle_Avoid_Car/`) if the IDE complains.
- [ ] **1. IR sensors (menu `1`).** For each of L/M/R: black tape under it → `on-line=1`,
      white floor → `on-line=0` (`raw` is the inverse). Confirm the *physically left* sensor
      is the one labelled L (pin 2) and the right is R (pin 10). If a sensor flickers or never
      triggers, turn the trim-pot on that module and re-test. Record: ________
- [ ] **2. Ultrasonic (menu `2`).** Ruler at 10 / 20 / 50 cm — readings within about ±2 cm;
      `0` means no echo. Record: ________
- [ ] **3. Servo (menu `3`).** Which physical side does the sensor face at angle 10 and at 180?
      The sketch assumes **10 = right, 180 = left** (if reversed, swap the two `myservo.write`
      probe angles in `avoidObstacle()`). Record: ________
- [ ] **4/5. Single motors (menu `4` then `5`).** Which wheel spins for Motor A, which for B,
      and does "forward" turn it forward? Sketch assumes **Motor A = right wheel, Motor B =
      left wheel**. Record: A = ________  B = ________
- [ ] **6. Drive sequence (menu `6`).** Forward must go forward, back backward, "pivot left"
      counter-clockwise, "pivot right" clockwise. Forward/back reversed → press `i`
      (invert). Pivots mirrored but forward/back right → press `w` (swap sides). Repeat `6`
      until all four are right, then copy the final values into `INVERT_MOTOR_DIRECTION` and
      `SWAP_SIDES` in `Line_Follow_Obstacle_Avoid_Car.ino`. Record: invert=___ swap=___
- [ ] **7. Minimum PWM (menu `7`).** First PWM value at which each wheel actually turns (repeat
      once on the floor with the bot's weight). Set `BASE_SPEED` at least ~30 above the higher
      of the two. Record: A=___ B=___
- [ ] **8. PID dry run (main sketch, wheels off ground).** Slide black under one sensor at a
      time and read `E:`/`SL:`/`SR:` in the Serial Monitor. Expect: L only → `E:-2`, `SL` < `SR`;
      R only → `E:2`, `SL` > `SR`; M only → `E:0`, `SL` = `SR`; none → keeps last direction, then
      stops after 2 s. If the signs are wrong, fix wiring/`SWAP_SIDES`, not the PID.
- [ ] **9. Track test.** Gentle curve, then a tight left curve (the case that failed before).
      Tune in this order: `BASE_SPEED` down until it holds the line → raise `KP` until it just
      starts to weave → raise `KD` to damp it → only then touch `KI`. Record final KP/KD/BASE_SPEED.
- [ ] **10. Obstacle avoidance.** Box ~15 cm ahead on the line: does it detect (`D:` in the
      log), pick a side, get round, and re-find the line? Tune `AVOID_TURN_MS`,
      `AVOID_FORWARD_MS` (these were written for speed 170, now 130), `LINE_SEARCH_TIMEOUT_MS`.
      Also check the both-sides-blocked case (walls both sides → it should back off, not hit).

## Done

### Acrux experiment reorganised, lab record and lab manual (2026-10-18, commit: _pending_)

- [x] Moved `practice/acrux_greeter/`, `tools/acrux/`, `learn/build/09-…` into root `waypoint_mission/`
- [x] Renamed guest/greeter/gift vocabulary to waypoint terms (files, identifiers, topic `/waypoint/command`); 60 tests pass
- [x] Wrote `waypoint_mission/LAB-RECORD.md` (timeline 2026-10-12 → now; result tables blank until run)
- [x] Wrote `lab-manual/` — front matter + experiments 1–5

### Waypoint mission (Acrux) — plan + code (2026-10-12, commit: _pending_)

- [x] Wrote `waypoint_mission/GUIDE.md` (was `learn/build/09-acrux-greeter-mission.md`) — requirements, architecture (laptop brain,
      robot-side safety), state machine, live commands, 5 safety layers, localization pitfalls
      found in `bots/acrux`, RealSense test plan, mapping/survey steps, runbook, risks, open items
- [x] Added `waypoint_mission/` (was `practice/acrux_greeter/`) — `mission.py` + `waypoint_config.py` (60 pytest tests pass),
      `mission_node.py`, `waypoints.yaml` (placeholders), collision-monitor config + safety launch
- [x] Linked into `learn/README.md` and `.CLAUDE/CLAUDE.md`

### UNO Smart Robot Car Kit — PID line following + bring-up test sketch (2026-09-24, commit: _pending_)

- [x] Rewrote line following as a PID loop over the 3 binary IR sensors (error -2..+2, x2
  scale, lost-line = keep turning to last-seen side, stop after 2 s), with per-wheel PWM so
  it curves instead of hard-pivoting. Motion helpers (`setWheels`, `forward/back/left/right`)
  now share one implementation, with `INVERT_MOTOR_DIRECTION` and `SWAP_SIDES` constants.
- [x] Lowered speeds (`BASE_SPEED` 110, `carSpeed` 170 → 130) for controllability.
- [x] Fixed loop latency that made it overshoot: ultrasonic now pings every 100 ms (not every
  loop) with a 6 ms `pulseIn` timeout (was 30 ms, blocking on every no-echo ping), needs 2
  consecutive close pings to react, and the Serial diagnostics are rate-limited to 200 ms.
- [x] Added `Hardware_Test/Hardware_Test.ino` — interactive Serial menu for sensors,
  ultrasonic, servo, single motors, drive sequence, PWM ramp, and runtime toggles for the
  invert/swap constants. Both sketches compile clean for the Uno (avr-g++, real core).
- [ ] Run the bring-up checklist above once the kit is in hand.

### Documented Lab 4 — colour detection node (2026-09-23, commit: _pending_)

- [x] kl mithunvel added `docs/color_detection_beetlebot` (own `rclpy` node: camera → HSV
  threshold → `/cmd_vel_nav`, green/red/blue = forward/stop/backward) in commit `2db5c3f`.
- [x] Wrote `learn/lab/05-lab4-color-detection.md` — deployment checklist (same shape as
  Lab 3's), colour-decision logic explained, shutdown-safety difference vs. the
  obstacle-avoidance node's `SIGINT` handler called out, viva checklist.
- [x] Mapped it into `learn/lab/00-course-and-lab-map.md` (table + study path,
  linked to syllabus Experiment 5) and `learn/README.md` (Track A table).
- [x] Flagged in `.CLAUDE/CLAUDE.md` Known Technical Debt (#8): the source file sits in
  `docs/`, which is otherwise read-only handouts — parked as-is per kl mithunvel
  (a broader documentation-format reformat is planned that will likely move it into
  `practice/` later, matching `practice/robot_calc/`'s shape).
- [ ] *(future)* relocate `docs/color_detection_beetlebot` into `practice/` with its own
  `.venv`/`requirements.txt`/`tests/`, as part of the planned reformat pass.

### UNO Smart Robot Car Kit — merged line-follow + obstacle-avoidance sketch (2026-09-23, commit: _pending_)

- [x] Merged `Line_tracking_car.ino` + `Obstacle_Avoidance_Car.ino` into a new state-machine
  sketch: follows the line by default, stops and steers around an obstacle (<20 cm ahead)
  via the servo/ultrasonic — probes left first, falls back to right if left is blocked,
  backs off and re-scans if both are blocked — then reacquires the line and resumes.
- [x] Found + fixed a real bug: the two original sketches use opposite motor pin polarity
  for their `forward()`/`back()` (line-tracking sketch's names were swapped relative to
  its own comments). Standardized on the obstacle-avoidance sketch's (correct) mapping.
- [x] Moved both originals into a new subfolder (`git mv`, history preserved) and added the
  merge there: `docs/UNO Smart Robot Car Kit/line_follow_obstacle_avoid/` now holds
  `Line_tracking_car.ino`, `Obstacle_Avoidance_Car.ino`, and
  `Line_Follow_Obstacle_Avoid_Car.ino`.
- [ ] *(kl mithunvel)* flash + tune on the real kit — `OBSTACLE_DISTANCE_CM`, `AVOID_TURN_MS`,
  `AVOID_FORWARD_MS`, `LINE_SEARCH_TIMEOUT_MS`, `carSpeed` are untested estimates.

### bots/ restructure + Rhino + ros-scripts vendoring (2026-09-08, commit: _pending_)

- [x] Added `VEEROBOT/rhino` as a git submodule (another 4-wheel AMR, ROS 2 Humble).
- [x] Moved all five robot submodules into `bots/` (`git mv` for BeetleBot/jetbot/acrux/wolf,
  fresh add for rhino) — root was getting crowded. `.gitmodules` paths + `.git/config` +
  each submodule's `.git` gitdir all updated; `git submodule status` clean.
- [x] Vendored `VEEROBOT/ros-scripts` `ROS2Install/` → `docs/ros-install/` (3 install
  scripts + upstream README + `SOURCE.md`; no upstream LICENSE, `install_ros2_jazzy.sh`
  is Apache-2.0).
- [x] Copied the repo's netplan examples (`ros2_network_yaml/`) into `docs/beetlebot/net/`
  and `docs/wolf/net/` with a README each — **WiFi password redacted** to
  `<your-wifi-password>` (repo rule: no credentials in tracked files), nameservers
  de-duplicated, a stray TAB in `70-wolf-net.yaml` fixed.
- [x] Wrote `learn/index.md` — index of every upstream repo + document (original links,
  pinned commits).
- [x] Updated all path references: `.gitignore`, `README.md`, `.CLAUDE/CLAUDE.md`,
  `learn/build/01`, `learn/foundations/01` + `03`. (CLAUDE-LOG history left as-is.)

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
- [x] Track Wolf as a git submodule — committed `bfd3ad0`, then moved to `bots/wolf/` (below).
- [ ] *(future)* add Wolf + Rhino to the `learn/build/` robot comparisons and the ROS-distro
  tables (both code repos target ROS 2 Humble; `docs/wolf/` tutorial text targets Foxy)

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
