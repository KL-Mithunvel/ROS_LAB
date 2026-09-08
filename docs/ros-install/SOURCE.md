# Source

The `install_ros2*.sh` scripts and `UPSTREAM_README.md` in this folder are copied
**verbatim** from the `ROS2Install/` directory of:

- **Repo:** <https://github.com/VEEROBOT/ros-scripts>
- **Commit:** `9529dd93ea9ad6052e69cf445bdf103ac9529f14` (2025-06-10)
- **Retrieved:** 2026-09-08
- **Path in upstream:** `ROS2Install/`

Kept here only for convenience while preparing for the lab — VEEROBOT's own
install scripts for putting ROS 2 on an Ubuntu machine (host PC or the robot's
Pi). Refresh by re-copying from a newer upstream commit and updating this file.

## What each script does

| File | Notes |
|------|-------|
| `install_ros2.sh` | Detects the Ubuntu release and installs the matching ROS 2 distro (Humble on 22.04, Jazzy on 24.04). Takes ~15 min. |
| `install_ros2_jazzy.sh` | Jazzy-only (`TARGET_OS=noble`). Carries an **Apache-2.0** header — it is derived from [Tiryoh/ros2_setup_scripts_ubuntu](https://github.com/Tiryoh/ros2_setup_scripts_ubuntu), itself based on the official ROS 2 docs (CC-BY-4.0, Open Robotics). |
| `install_ros2_v2.sh` | Newer single-file installer; `UPSTREAM_README.md` says "latest version of ROS on Ubuntu 24". |

`UPSTREAM_README.md` is `ROS2Install/README.md` from upstream — it also lists the
extra `pip3` dev-tools step and a `wget` / `/etc/hosts` workaround for when
`raw.githubusercontent.com` will not resolve.

## Licence

The upstream repo <https://github.com/VEEROBOT/ros-scripts> has **no LICENSE
file**. `install_ros2_jazzy.sh` is explicitly Apache-2.0 (see its header). The
other two scripts carry no licence notice; they are retained here for personal
study reference only. If in doubt, run the official instructions instead:
<https://docs.ros.org/en/jazzy/Installation.html>.

These are **not** this course's instructor handouts and **not** MIT-licensed
like `docs/beetlebot/` and `docs/wolf/`.
