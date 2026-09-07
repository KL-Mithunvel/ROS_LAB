# `learn/` — study guides

Two goals, two tracks. Everyone does **Foundations** first.

```
learn/
├── foundations/   things both tracks need — Linux, the ROS 2 model, the docs, ROS 1 vs 2
├── lab/           Track A — pass the graded BeetleBot lab + viva
└── build/         Track B — be able to build a ROS 2 autonomy stack for ANY robot
                   (localization · SLAM · path planning · navigation · control logic)
```

Guides follow the house style: the exact command (not a generic example), *why* it exists,
whether it runs **on the PC** or **on the robot**, cross-links instead of repetition, and a
citation when a value comes from the official docs or the vendored submodule source.

---

## Foundations — do these first (`foundations/`)

| # | File | What it gives you |
|---|------|-------------------|
| 01 | `foundations/01-linux-and-shell.md` | The Linux/shell fluency ROS work needs — files, permissions, SSH & keys, `rsync`, `tmux`, `systemd`/`journalctl`, `udev`, networking & DDS discovery, `apt`/`rosdep`, `git` for workspaces |
| 02 | `foundations/02-ros2-concepts.md` | The ROS 2 computation model — nodes/topics/services/actions/params, QoS, lifecycle, executors, TF2, `colcon`/workspaces/overlays, `rclpy` node anatomy, creating packages + custom interfaces, launch files |
| 03 | `foundations/03-official-docs-index.md` | Curated index into `docs.ros.org/en/jazzy` + Nav2/SLAM/`ros2_control` docs, with why each page matters |
| 04 | `foundations/04-ros1-vs-ros2.md` | ROS 1 vs ROS 2 — architecture (`roscore` vs DDS), command/concept table, build systems, why ROS 2, `ros1_bridge`, viva Q&A |

---

## Track A — the lab (`lab/`)

The graded BeetleBot (Lyra) lab: connect → bring up → drive → record → SLAM →
obstacle-avoidance node. Each numbered file is a checklist you can run start to finish.

| # | File | Lab |
|---|------|-----|
| 00 | `lab/00-course-and-lab-map.md` | What the syllabus PDFs require; which handout maps to which lab day |
| 01 | `lab/01-lab-day-runbook.md` | The single reconciled lab-day procedure (all four handouts merged) |
| 02 | `lab/02-lab1-turtlesim-and-workspace.md` | Lab 1 — your workspace, turtlesim publish/subscribe |
| 03 | `lab/03-lab2-beetlebot-movement.md` | Lab 2 — connect, arm, drive, teleop the real robot |
| 04 | `lab/04-lab3-obstacle-avoidance.md` | Lab 3 — deploy/register/build/run the obstacle-avoidance node |

Future lab experiments slot in as `lab/05-…`, `lab/06-…`.

---

## Track B — building ROS 2 autonomy systems (`build/`)

The goal: given any robot, be able to stand up its ROS 2 stack —
**description → simulation → control → localization → SLAM → path planning → navigation**.
Start with the two worked-example files, then the deep dives.

| # | File | Concern |
|---|------|---------|
| 01 | `build/01-three-bots-architecture.md` | Full package-by-package walkthrough of BeetleBot / Acrux / JetBot from the vendored source, and how localization/SLAM/obstacle-avoidance/Nav2 plug together end to end |
| 02 | `build/02-ros2-across-robot-types.md` | The same ROS 2 machinery on arms (MoveIt 2, `ros2_control`), legged robots, drones, multi-robot systems |
| 03 | `build/03-build-a-ros2-autonomy-stack.md` | **The spine** — scaffolding packages and assembling all the pieces below into a *new* robot project |
| 04 | `build/04-robot-description-and-tf.md` | URDF/Xacro, links/joints, `robot_state_publisher`, the `map → odom → base_link → sensor` TF2 chain |
| 05 | `build/05-simulation-gazebo.md` | Gazebo + `ros_gz`, sim time, spawning, sensor plugins — develop here before touching hardware |
| 06 | `build/06-control-and-ros2-control.md` | `ros2_control` architecture, diff-drive/ackermann controllers, writing a hardware interface, PID, the MCU boundary / micro-ROS |
| 07 | `build/07-localization-and-slam.md` | Odometry, IMU, the `robot_localization` EKF, AMCL, `slam_toolbox`/Cartographer — tuning, TF frames, common failure modes |
| 08 | `build/08-navigation-and-path-planning.md` | Nav2 internals — costmap layers, global planners (NavFn / Smac), controllers (DWB / RPP / MPPI), behavior trees, recovery, tuning `nav2_params.yaml` |

---

## Suggested route

1. **Foundations 01 → 02 → 04** (03 is a reference you dip into).
2. Doing the graded lab soon? **Track A**, `lab/00` onward.
3. Building toward the "any robot" goal? **Track B**, `build/01` onward — `build/03` is the
   map, then `04`–`08` in order (`04` description and `05` sim before `06`–`08`, because
   control, localization and navigation are all easier to learn and test in simulation).
