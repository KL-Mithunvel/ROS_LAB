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
| `BeetleBot/` | **Git submodule** pinned to [github.com/VEEROBOT/BeetleBot](https://github.com/VEEROBOT/BeetleBot) — the lab robot's upstream source |
| `jetbot/` | **Git submodule** pinned to [NVIDIA-AI-IOT/jetbot](https://github.com/NVIDIA-AI-IOT/jetbot) — comparison platform only, not used in this lab |
| `acrux/` | **Git submodule** pinned to [VEEROBOT/acrux](https://github.com/VEEROBOT/acrux) — another VEEROBOT robot platform, comparison only |
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
