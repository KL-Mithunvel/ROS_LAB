# 00 — Course context and lab-day map

Two things this file does: (1) says what the **official course paperwork** actually
requires, from the two syllabus PDFs in `docs/`; (2) maps every `docs/` handout to the lab
day it belongs to and the `learn/` file that covers it, so you can walk in study order.

---

## 1. The official syllabus (from the two PDFs)

`docs/` has **two different VIT course-code documents** for "Autonomous Mobile Robots" —
confusingly, their suffixes don't mean what you'd guess:

| File | Course code | Format (LTPC) | Has a "List of Experiments"? |
|---|---|---|---|
| `BMHA314E_..._BMHA314E.pdf` | BMHA314**E** | 3-0-2-4 (lecture + embedded hands-on) | **Yes** — this is the practical variant |
| `BMHA314L_..._BMHA314L.pdf` | BMHA314**L** | 3-0-0-3 (lecture only) | No — pure theory modules |

Both share the same 8-module structure (Introduction → Locomotion/Kinematics → Perception
→ Localization & Mapping → Path Planning → Control → Multi-robot systems → Contemporary
Issues) and the same core textbook (Siegwart, Nourbakhsh & Scaramuzza, *Introduction to
Autonomous Mobile Robots*, MIT Press). The **E** variant is the one whose "List of
Experiments (Indicative)" actually names what the hands-on component is:

1. Set up the ROS environment and understand the fundamentals.
2. Simulate a mobile robot model (e.g. TurtleBot) in Gazebo.
3. Implement SLAM using the ROS Navigation Stack.
4. Design a path-planning algorithm using ROS navigation packages (e.g. `move_base`).
5. Object detection/recognition using ROS perception libraries (OpenCV, PCL).
6. Multi-robot communication over ROS topics/services/actionlib.

> **The syllabus is written in ROS 1 vocabulary.** `move_base` (superseded by Nav2) and
> `actionlib` (folded into `rclcpp`/`rclpy` in ROS 2) are ROS 1 names — the paperwork
> predates the lab's move to ROS 2 Jazzy. Whenever a handout or exam question uses one, map
> it to its ROS 2 equivalent (`move_base` → Nav2, `actionlib` → ROS 2 actions,
> `catkin` → `colcon`, `roscore` → DDS discovery). The full table is in
> `../foundations/04-ros1-vs-ros2.md`, and examiners trained on ROS 1 do ask about the split.

**What this means for you:** the BeetleBot lab (this repo's actual focus) is VEEROBOT's
concrete implementation of experiments 1 and (partially) 3–4 — "set up ROS and understand
the fundamentals" became Lab 1 (turtlesim pub/sub), and the movement/obstacle-avoidance labs
build the perception→control loop the syllabus describes in Modules 3, 5 and 6. Evaluation
per the PDFs is CAT + Assignment + Quiz + FAT (+ Projects for the E variant) — expect viva
questions to map back to these module names (kinematics, localization, path planning,
control architectures), not just "which command did what".

---

## 2. `docs/` → lab day → `learn/` file

| `docs/` file | What it actually is | Lab day | Read |
|---|---|---|---|
| `BMHA314E_AUTONOMOUS-MOBILE-ROBOTS_ETH_..._BMHA314E.pdf` | Official syllabus, practical variant | course context, not a lab | this file, §1 |
| `BMHA314L_AUTONOMOUS-MOBILE-ROBOTS_TH_..._BMHA314L.pdf` | Official syllabus, theory-only variant | course context, not a lab | this file, §1 |
| `Beetlebot Manual.docx` | Phase 1–2: workspace setup + turtlesim; Phase 3–5: hardware connect, bringup, visualisation, `scp` | **Lab 1** (+ overlaps into Lab 2's connect step) | `02-lab1-turtlesim-and-workspace.md` |
| `VEEROBOT BEETLE BOT LYRA.txt` | Arm/disarm, the movement-command cookbook, keyboard teleop guide | **Lab 2** | `03-lab2-beetlebot-movement.md` |
| `BEETLEBOT  Obstacle_avoid.txt` | Obstacle-avoidance node, **v1** (simple, single front window) | **Lab 3** | `04-lab3-obstacle-avoidance.md` |
| `BEETLEBOT Updated _Obstacle_avoid.txt` | Obstacle-avoidance node, **v2 / "Updated"** (front+left+right windows, timed reverse state machine) | **Lab 3** | `04-lab3-obstacle-avoidance.md`, and the full line-by-line code read in `../foundations/02-ros2-concepts.md` §5 |

## 3. Study path (Track A — the lab)

Do these in order; each is a **checklist you can run start-to-finish**:

1. **`02-lab1-turtlesim-and-workspace.md`** — your own workspace, turtlesim publish/subscribe.
2. **`03-lab2-beetlebot-movement.md`** — connect to the real robot, arm, drive, teleop.
3. **`04-lab3-obstacle-avoidance.md`** — deploy and run the autonomous obstacle-avoidance node.

Supporting references — read for the "why" behind any command:

- `../foundations/01-linux-and-shell.md` — the terminal commands the lab uses, explained.
- `../foundations/02-ros2-concepts.md` — the ROS 2 computation model, `colcon`/workspaces,
  `rclpy` node anatomy, and the full line-by-line obstacle-avoidance code read.
- `01-lab-day-runbook.md` — the single reconciled lab-day procedure (exam-day quick-reference).
- `../foundations/03-official-docs-index.md` — curated links into the official ROS 2 Jazzy docs.
- `../foundations/04-ros1-vs-ros2.md` — ROS 1 vs ROS 2 (the syllabus vocabulary in §1 is
  ROS 1-era; expect viva questions on the difference).

Once the lab makes sense and you want to build a ROS 2 autonomy stack for *any* robot —
localization, SLAM, path planning, navigation, control logic — switch to **Track B** in
`../build/` (start at `../build/01-three-bots-architecture.md`). The full two-track map is
`../README.md`.

Next: `02-lab1-turtlesim-and-workspace.md`.
