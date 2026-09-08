# ROS_LAB — BeetleBot (Lyra) academic lab preparation

Personal study repo for the **ROS 2 lab** built around the **VEEROBOT BeetleBot / Lyra**
robot (ROS 2 Jazzy, Raspberry Pi 5, RPLiDAR C1, STM32F405 motor controller).

Two goals:

- **Near term** — walk into the graded lab able to use a Linux terminal fluently,
  understand how ROS 2 works, and run the full BeetleBot workflow (connect → bring up →
  drive → record → SLAM → obstacle-avoidance node).
- **Long term** — be able to build a ROS 2 autonomy stack for *any* robot from scratch:
  description → simulation → control → localization → SLAM → path planning → navigation.

The guides are split into two tracks accordingly — see `learn/README.md`.

## Layout

| Path | What it is |
|------|-----------|
| `learn/` | Study guides — start at `learn/README.md`. Split into `foundations/` (shared), `lab/` (Track A — the graded lab), `build/` (Track B — building ROS 2 systems) |
| `docs/` | The raw instructor handouts (BeetleBot manual + obstacle-avoidance scripts). Plus `docs/beetlebot/` and `docs/wolf/` — MIT-licensed VEEROBOT tutorial docs mirrored from [SMARTS-LAB/Documention](https://github.com/SMARTS-LAB/Documention) (see each folder's `SOURCE.md`) |
| `bots/` | Robot upstream sources, each a **git submodule** (pinned pointer only): `BeetleBot/` (the lab robot, [VEEROBOT/BeetleBot](https://github.com/VEEROBOT/BeetleBot)), plus comparison platforms `jetbot/` ([NVIDIA-AI-IOT/jetbot](https://github.com/NVIDIA-AI-IOT/jetbot)), `acrux/`, `wolf/`, `rhino/` (all VEEROBOT). See [`learn/index.md`](learn/index.md) |
| `docs/ros-install/` | VEEROBOT's ROS 2 install scripts, vendored from [VEEROBOT/ros-scripts](https://github.com/VEEROBOT/ros-scripts) (see its `SOURCE.md`) |
| `.CLAUDE/` | Project brief + working rules for AI-assisted sessions |
| `TODO.md` | Task tracker |

## Study order

Full map with one-line descriptions of every file: **`learn/README.md`**. In short:

**Foundations (both tracks):**

1. `learn/foundations/01-linux-and-shell.md` — Linux/shell fluency for ROS work
2. `learn/foundations/02-ros2-concepts.md` — the ROS 2 model, `colcon`, `rclpy`, launch, QoS
3. `learn/foundations/03-official-docs-index.md` — curated links into the official docs
4. `learn/foundations/04-ros1-vs-ros2.md` — ROS 1 vs ROS 2 (the syllabus is ROS 1-era)

**Track A — the graded lab (`learn/lab/`):** `00-course-and-lab-map.md` →
`01-lab-day-runbook.md` → `02`/`03`/`04` lab-day checklists.

**Track B — building ROS 2 autonomy systems (`learn/build/`):**
`01-three-bots-architecture.md` and `02-ros2-across-robot-types.md` (worked examples), then
`03-build-a-ros2-autonomy-stack.md` (the spine) → `04` description/TF → `05` simulation →
`06` control / `ros2_control` → `07` localization & SLAM → `08` navigation & path planning.

## Get / refresh the robot sources (git submodules)

The five robots under `bots/` are **git submodules** — this repo tracks a pinned commit
pointer for each, not their file contents. Cloning this repo alone leaves those folders
empty; you need one extra step. Full list with pinned commits: [`learn/index.md`](learn/index.md).

| Path | URL | Role |
|------|-----|------|
| `bots/BeetleBot` | https://github.com/VEEROBOT/BeetleBot | The lab robot's upstream source (VEEROBOT / "Lyra") |
| `bots/jetbot` | https://github.com/NVIDIA-AI-IOT/jetbot | NVIDIA's Jetson robot — reference/comparison only |
| `bots/acrux` | https://github.com/VEEROBOT/acrux | VEEROBOT robot platform — reference/comparison only |
| `bots/wolf` | https://github.com/VEEROBOT/wolf | VEEROBOT 4-wheel AMR (the `docs/wolf/` tutorials' robot) — comparison only |
| `bots/rhino` | https://github.com/VEEROBOT/rhino | VEEROBOT 4-wheel AMR — comparison only |

```bash
# first checkout of this repo (or after a fresh clone)
git submodule update --init --recursive

# pull each submodule's latest upstream commit and re-pin it
git submodule update --remote
git add bots        # stage the new pins, then commit them
```
