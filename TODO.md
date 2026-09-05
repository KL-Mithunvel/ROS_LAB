# TODO

## In Progress

- [ ] Work through `learn/01-linux-commands.md` and practice each command in a real terminal

## Done

- [x] Set up repo as BeetleBot lab-prep workspace — cloned upstream `BeetleBot/` (gitignored), rewrote `.CLAUDE/CLAUDE.md` from template to real project brief, filled `README.md` / `TODO.md` / `.CLAUDE/CLAUDE-LOG.md` (commit: _pending_)
- [x] Wrote study guides in `learn/` (linux commands, ROS 2 concepts, BeetleBot runbook, official-doc index) (commit: _pending_)
- [x] Cloned `jetbot` (NVIDIA-AI-IOT) and `acrux` (VEEROBOT) as gitignored reference-only source, alongside `BeetleBot/`; linked all three in `README.md` (commit: _pending_)
- [x] Converted `BeetleBot/`, `jetbot/`, `acrux/` from gitignored plain clones to **git submodules** (`.gitmodules`) — pinned pointers tracked in the repo, contents still live upstream (commit: _pending_)
- [x] Read both course syllabus PDFs and all `docs/` handouts; wrote `learn/00-course-and-lab-map.md` (syllabus summary + doc-to-lab map) and three lab-day checklists — `05-lab1-turtlesim-and-workspace.md`, `06-lab2-beetlebot-movement.md`, `07-lab3-obstacle-avoidance.md` (the last includes a v1-vs-v2 obstacle-avoidance script comparison not covered elsewhere) (commit: _pending_)
- [x] Read the actual checked-out source of all three submodules (`BeetleBot/lyra_ws/src/*`, `acrux/acrux_*`, `jetbot/jetbot/*`) and wrote `learn/08-three-bots-architecture.md` — package/file-by-file walkthrough of all three robots plus a detailed localization/SLAM/obstacle-avoidance/Nav2 pipeline explanation with an end-to-end diagram (commit: _pending_)
- [x] Wrote `learn/09-ros2-across-robot-types.md` — how ROS 2 concepts extend to robotic arms (MoveIt 2, `ros2_control`, joint trajectories), legged robots, drones, and multi-robot systems, contrasted against the AMR pattern used by this lab's robots (commit: _pending_)

## Not Started

- [ ] Read `learn/02-ros2-concepts.md`; run the turtlesim publisher/subscriber tutorial on a Linux machine
- [ ] Read `learn/03-beetlebot-runbook.md`; memorise the connect → bringup → arm → drive → disarm sequence
- [ ] Practice writing a minimal `rclpy` node from memory (publisher + subscriber + timer)
- [ ] Trace `docs/BEETLEBOT Updated _Obstacle_avoid.txt` line by line; be able to explain the LaserScan windowing and the reverse/turn state machine
- [ ] Skim the official ROS 2 Jazzy tutorials linked in `learn/04-ros2-official-docs.md` (Beginner CLI + Beginner Client Libraries)
- [ ] Confirm my own robot number / `ROS_DOMAIN_ID` / IP / Wi-Fi password with the lab instructor (handouts disagree)
- [ ] Install ROS 2 Jazzy (or use Docker `ros:jazzy`) on a personal Linux machine for offline practice
