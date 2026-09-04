# ROS_LAB — BeetleBot (Lyra) academic lab preparation

Personal study repo for the **ROS 2 lab** built around the **VEEROBOT BeetleBot / Lyra**
robot (ROS 2 Jazzy, Raspberry Pi 5, RPLiDAR C1, STM32F405 motor controller).

Goal: walk into the lab able to (1) use a Linux terminal fluently, (2) understand how
ROS 2 works, and (3) run the full BeetleBot workflow — connect → bring up → drive →
record data → SLAM → obstacle-avoidance node.

## Layout

| Path | What it is |
|------|-----------|
| `learn/` | Study guides written for this lab — start here |
| `docs/` | The raw handouts I was given (BeetleBot manual + obstacle-avoidance scripts) |
| `BeetleBot/` | **Git submodule** pinned to [github.com/VEEROBOT/BeetleBot](https://github.com/VEEROBOT/BeetleBot) — the lab robot's upstream source |
| `jetbot/` | **Git submodule** pinned to [NVIDIA-AI-IOT/jetbot](https://github.com/NVIDIA-AI-IOT/jetbot) — comparison platform only, not used in this lab |
| `acrux/` | **Git submodule** pinned to [VEEROBOT/acrux](https://github.com/VEEROBOT/acrux) — another VEEROBOT robot platform, comparison only |
| `.CLAUDE/` | Project brief + working rules for AI-assisted sessions |
| `TODO.md` | Task tracker |

## Study order

Start with `learn/00-course-and-lab-map.md` — it maps every file below to the lab day it
belongs to. Reference guides (deep "how it works"):

1. `learn/01-linux-commands.md` — every terminal command the lab uses, explained
2. `learn/02-ros2-concepts.md` — nodes, topics, services, `colcon`, workspaces, `rclpy`
3. `learn/03-beetlebot-runbook.md` — the corrected, consolidated lab-day procedure
4. `learn/04-ros2-official-docs.md` — curated links into the official ROS 2 Jazzy docs

Lab-day checklists (practical, step-by-step, "why" for each command, cross-linking 1–4):

5. `learn/05-lab1-turtlesim-and-workspace.md` — workspace setup, turtlesim publish/subscribe
6. `learn/06-lab2-beetlebot-movement.md` — connect, arm, drive, teleop the real robot
7. `learn/07-lab3-obstacle-avoidance.md` — deploy and run the obstacle-avoidance node

## Get / refresh the reference source (git submodules)

`BeetleBot/`, `jetbot/`, and `acrux/` are **git submodules** — this repo tracks a pinned
commit pointer for each, not their file contents. Cloning this repo alone leaves those
three folders empty; you need one extra step.

| Repo | URL | Role |
|------|-----|------|
| BeetleBot | https://github.com/VEEROBOT/BeetleBot | The lab robot's upstream source (VEEROBOT / "Lyra") |
| JetBot | https://github.com/NVIDIA-AI-IOT/jetbot | NVIDIA's Jetson-based robot — reference/comparison only |
| Acrux | https://github.com/VEEROBOT/acrux | Another VEEROBOT robot platform — reference/comparison only |

```bash
# first checkout of this repo (or after a fresh clone)
git submodule update --init --recursive

# pull each submodule's latest upstream commit and re-pin it
git submodule update --remote
git add BeetleBot jetbot acrux    # stage the new pin, then commit it
```
