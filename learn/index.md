# Index — every source this repo pulls from

Original links for all the upstream repos and documents vendored or submoduled
into `ROS_LAB`. For the **study route** (what to read in what order) see
[`learn/README.md`](README.md).

Pinned commits are what this repo currently tracks — refresh with
`git submodule update --remote` (submodules) or by re-copying (vendored docs),
then update the relevant `SOURCE.md`.

---

## Robot source — git submodules (`bots/`)

Cloning this repo does **not** fetch these. Run once:

```bash
git submodule update --init --recursive
```

| Path | Upstream | Pinned | Role |
|------|----------|--------|------|
| `bots/BeetleBot/` | <https://github.com/VEEROBOT/BeetleBot> | `9427abf` | **The lab robot** (VEEROBOT BeetleBot / "Lyra"). ROS 2 Jazzy on a Pi 5. |
| `bots/acrux/` | <https://github.com/VEEROBOT/acrux> | `c8092f4` (branch `ros2-humble`) | VEEROBOT Acrux — comparison platform. |
| `bots/wolf/` | <https://github.com/VEEROBOT/wolf> | `35bb3b5` (`main`) | VEEROBOT Wolf, a 4-wheel AMR — comparison. Code targets ROS 2 **Humble** (its `docs/wolf/` tutorials say Foxy). |
| `bots/rhino/` | <https://github.com/VEEROBOT/rhino> | `68b33a7` (`main`) | VEEROBOT Rhino, another 4-wheel AMR — comparison. Same layout as Wolf, ROS 2 Humble. |
| `bots/jetbot/` | <https://github.com/NVIDIA-AI-IOT/jetbot> | `3ebfff2` | NVIDIA JetBot — plain-Python (non-ROS) comparison platform. |

Walkthrough of BeetleBot / Acrux / JetBot internals:
[`build/01-three-bots-architecture.md`](build/01-three-bots-architecture.md).

---

## Scripts — vendored copy (`docs/ros-install/`)

| Path | Upstream | Pinned | What |
|------|----------|--------|------|
| `docs/ros-install/` | <https://github.com/VEEROBOT/ros-scripts> (`ROS2Install/`) | `9529dd9` | VEEROBOT's ROS 2 install scripts for Ubuntu. Provenance + licence in its `SOURCE.md`. |
| `docs/beetlebot/net/`, `docs/wolf/net/` | same repo, `ros2_network_yaml/` | `9529dd9` | Netplan static-WiFi-IP examples. WiFi passwords **redacted**. |

---

## Tutorial docs — vendored copy (`docs/beetlebot/`, `docs/wolf/`)

| Path | Upstream | Pinned | Notes |
|------|----------|--------|-------|
| `docs/beetlebot/` | <https://github.com/SMARTS-LAB/Documention> (`beetle bot/`) | `c9eb011` | MIT. Targets ROS 2 **Jazzy**. |
| `docs/wolf/` | <https://github.com/SMARTS-LAB/Documention> (`wolf robot/`) | `c9eb011` | MIT. Targets ROS 2 **Foxy / Ubuntu 20.04** (older). |

SMARTS-LAB's repo itself mirrors VEEROBOT's docs site:
<https://docs.veerobot.com/ros-robots/>. Full provenance + MIT text in each
folder's `SOURCE.md`.

---

## Instructor material (`docs/`, committed, read-only)

Not from a public repo — the course handouts. **Never edit these;** corrections
go in [`lab/01-lab-day-runbook.md`](lab/01-lab-day-runbook.md).

| File | What |
|------|------|
| `docs/Beetlebot Manual.docx` | The BeetleBot / Lyra operating manual. |
| `docs/BEETLEBOT  Obstacle_avoid.txt` | Lab 3 obstacle-avoidance node (first version). |
| `docs/BEETLEBOT Updated _Obstacle_avoid.txt` | Lab 3 obstacle-avoidance node (fuller version — study this one). |
| `docs/BMHA314L_AUTONOMOUS-MOBILE-ROBOTS_TH_1.0_0_BMHA314L.pdf` | Theory syllabus. |
| `docs/BMHA314E_AUTONOMOUS-MOBILE-ROBOTS_ETH_1.1_0_BMHA314E.pdf` | Lab / practical syllabus. |
| `docs/Kinematics and Dynamics_AMR_Problems.pdf` | Worked diff-drive kinematics + dynamics problems (basis for `practice/robot_calc/` sets 4–5). |

---

## Official upstream documentation (not vendored — links only)

Curated, with *why each page matters*, in
[`foundations/03-official-docs-index.md`](foundations/03-official-docs-index.md).

| Topic | Link |
|-------|------|
| ROS 2 Jazzy | <https://docs.ros.org/en/jazzy/> |
| ROS 2 Jazzy install | <https://docs.ros.org/en/jazzy/Installation.html> |
| Nav2 | <https://docs.nav2.org/> |
| SLAM Toolbox | <https://github.com/SteveMacenski/slam_toolbox> |
| `ros2_control` | <https://control.ros.org/> |
| `robot_localization` (EKF) | <https://docs.ros.org/en/melodic/api/robot_localization/html/> |
| Gazebo + `ros_gz` | <https://gazebosim.org/docs> · <https://github.com/gazebosim/ros_gz> |

---

## This repo's own study material

| Path | What |
|------|------|
| [`learn/README.md`](README.md) | The two-track study route (Foundations → Track A lab / Track B build). |
| `learn/foundations/` · `learn/lab/` · `learn/build/` | The guides. |
| `practice/robot_calc/` | Menu-driven mobile-robot mechatronics calculator (5 calculation sets). |
