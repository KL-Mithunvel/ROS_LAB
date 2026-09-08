# ros-install — VEEROBOT ROS 2 install scripts

Copied from [`VEEROBOT/ros-scripts`](https://github.com/VEEROBOT/ros-scripts)
`ROS2Install/`. Provenance and licence: **`SOURCE.md`**. Upstream's own notes
(the `pip3` dev-tools step, the `raw.githubusercontent.com` / `/etc/hosts`
workaround): **`UPSTREAM_README.md`**.

| Script | Use it when |
|--------|-------------|
| `install_ros2.sh` | Any supported Ubuntu — detects the release, installs the matching ROS 2 (Humble on 22.04, Jazzy on 24.04). |
| `install_ros2_jazzy.sh` | You specifically want **Jazzy** on Ubuntu 24.04 (Noble). Apache-2.0, from `Tiryoh/ros2_setup_scripts_ubuntu`. |
| `install_ros2_v2.sh` | Newer single-file installer for Ubuntu 24. |

```bash
chmod +x install_ros2.sh
sudo bash ./install_ros2.sh          # ~15 minutes
```

**When in doubt, follow the official instructions instead:**
<https://docs.ros.org/en/jazzy/Installation.html> — see also
`../../learn/foundations/03-official-docs-index.md`. These scripts are a
convenience, not authoritative.

This machine (Windows) can't run ROS 2 — use these on the Lab PC, the robot's
Pi, or a Linux VM / `docker run -it ros:jazzy` (see
`../../learn/foundations/01-linux-and-shell.md`).
