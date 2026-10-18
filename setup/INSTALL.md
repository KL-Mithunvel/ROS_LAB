# Setting up this repo on a bare machine

For someone with **no ROS and no libraries installed**. After this you can read the guides,
run the projects' tests, practise with turtlesim, and (with a robot on the network) run the
labs and the waypoint mission.

> **Status:** `install.sh` is written and syntax/dry-run checked, but **not yet run on a clean
> Ubuntu**. If a step fails, the manual steps in §4 are the fallback — and tell the repo
> owner what broke.

---

## 1. What you need

| Need | Detail |
|---|---|
| OS | **Ubuntu 22.04** (installs ROS 2 **Humble**) or **Ubuntu 24.04** (installs ROS 2 **Jazzy**), 64-bit |
| Disk / time | ~8 GB free; 20–40 min on a good connection |
| Rights | A user with `sudo` |
| Network | Internet during install. To reach a robot later: the same Wi-Fi subnet as the robot |

**Which distro?** Use the one the robot runs. BeetleBot runs **Jazzy** (Ubuntu 24.04); Acrux
runs **Humble** (Ubuntu 22.04) — confirm with `printenv ROS_DISTRO` on the robot.

**Windows:** ROS 2 does not run natively in any convenient way. Use one of
- **WSL2** with Ubuntu 22.04/24.04 (fine for building, tests, RViz; for talking to a robot enable mirrored networking in `%UserProfile%\.wslconfig`: `[wsl2]` / `networkingMode=mirrored`),
- a Linux VM with a **bridged** network adapter, or
- Docker: `docker run -it ros:jazzy` (no GUI by default).

**macOS:** use a Linux VM.

Only want to read the guides or run the pure-Python tests? Skip ROS: see §6.

---

## 2. One-command install

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/KL-Mithunvel/ROS_LAB.git ~/ROS_LAB
cd ~/ROS_LAB/setup
./install.sh --dry-run        # read what it would do (changes nothing)
./install.sh                  # do it (asks for confirmation; -y to skip)
```

If the script is not executable: `bash install.sh`.

When it finishes, **open a new terminal** (so `~/.bashrc` loads ROS) and run the checks in §5.

### What it installs

| Component | Flag | Default | Contents |
|---|---|---|---|
| Base | — | always | `git curl build-essential python3-venv python3-pip openssh-client rsync`, UTF-8 locale |
| ROS 2 | `--no-ros` to skip | on | official apt repo, `ros-<distro>-desktop` (RViz, rqt, demos), `colcon`, `rosdep`, `vcstool`; `source` line in `~/.bashrc` |
| Nav2 (waypoint mission) | `--without-nav2` | on | `nav2-bringup`, `nav2-simple-commander`, `nav2-msgs`, `nav2-collision-monitor`, `nav2-map-server`, `slam-toolbox` |
| Lab tools | `--without-lab` | on | `turtlesim`, `teleop-twist-keyboard`, `rqt`, `rqt-graph`, `cv-bridge`, `python3-opencv`, `numpy` |
| Python projects | `--without-practice` | on | `.venv` + `pip install -r requirements.txt` + `pytest` for `waypoint_mission/` and `robot_calc/` |
| Gazebo | `--with-gazebo` | off | `ros-<distro>-ros-gz` (needed for the mission's `--sim`) |
| Robot sources | `--with-bots` | off | git submodules in `bots/` (BeetleBot, Acrux, …; large). Needed only for `./acrux sync` and reading the vendored source |

Other flags: `--all`, `--distro humble|jazzy`, `--dir PATH` (clone location when run outside a
checkout), `-y`, `--dry-run`, `--help`.

The script is **re-runnable**: it skips an existing apt key/source, an existing `rosdep` init,
an existing `.venv`, and does `git pull --ff-only` on an existing clone.

---

## 3. Recreating a specific project

| Goal | Command |
|---|---|
| Practise ROS without a robot | `ros2 run turtlesim turtlesim_node` and `ros2 run turtlesim turtle_teleop_key` (lab-manual experiment 1) |
| Run the calculator | `cd robot_calc && .venv/bin/python main.py` |
| Test the waypoint mission logic | `cd waypoint_mission && .venv/bin/python -m pytest` → 60 passed |
| Run the mission against a robot | follow `waypoint_mission/README.md` and `GUIDE.md` (survey `waypoints.yaml` first) |
| Operate the BeetleBot labs | `lab-manual/` and `learn/lab/01-lab-day-runbook.md` |
| Reach Acrux over SSH/VNC | `waypoint_mission/tools/README.md` (`./acrux status`) |

---

## 4. Manual steps (what the script does)

Use these if you prefer, or if the script fails. Replace `<distro>` with `humble` or `jazzy`.

```bash
# base
sudo apt-get update
sudo apt-get install -y git curl gnupg lsb-release ca-certificates software-properties-common \
     locales build-essential python3-venv python3-pip openssh-client rsync
sudo locale-gen en_US en_US.UTF-8 && sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# ROS 2 apt repository
sudo add-apt-repository -y universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
     -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
     | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
sudo apt-get update

# ROS 2 + tooling
sudo apt-get install -y ros-<distro>-desktop python3-colcon-common-extensions \
     python3-rosdep python3-vcstool python3-argcomplete
sudo rosdep init && rosdep update
echo "source /opt/ros/<distro>/setup.bash" >> ~/.bashrc

# Nav2 + lab tools
sudo apt-get install -y ros-<distro>-nav2-bringup ros-<distro>-nav2-simple-commander \
     ros-<distro>-nav2-msgs ros-<distro>-nav2-collision-monitor ros-<distro>-nav2-map-server \
     ros-<distro>-slam-toolbox ros-<distro>-turtlesim ros-<distro>-teleop-twist-keyboard \
     ros-<distro>-rqt ros-<distro>-rqt-graph ros-<distro>-cv-bridge python3-opencv python3-numpy

# project environments
git clone https://github.com/KL-Mithunvel/ROS_LAB.git ~/ROS_LAB
cd ~/ROS_LAB/waypoint_mission && python3 -m venv --system-site-packages .venv \
     && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m pytest
cd ~/ROS_LAB/robot_calc && python3 -m venv .venv \
     && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m pytest
```

The official reference is <https://docs.ros.org/en/jazzy/Installation.html> (swap `jazzy` for
`humble`). This repo also vendors VEEROBOT's installers in `docs/ros-install/`
(see its `SOURCE.md`); `install.sh` is separate and does not use them.

---

## 5. Verify

```bash
printenv ROS_DISTRO                       # humble or jazzy
ros2 doctor --report | head               # no red errors
ros2 run demo_nodes_cpp talker &          # then:
ros2 run demo_nodes_cpp listener          # hears the talker; Ctrl+C both
python3 -c "from nav2_simple_commander.robot_navigator import BasicNavigator; print('nav2 ok')"
cd ~/ROS_LAB/waypoint_mission && .venv/bin/python -m pytest -q    # 60 passed
```

To talk to a robot: same Wi-Fi subnet, and the **same `ROS_DOMAIN_ID`** in every terminal on
both machines (`export ROS_DOMAIN_ID=<n>`), then `ros2 topic list` should show its topics.

---

## 6. Without ROS (reading and Python tests only)

```bash
./install.sh --no-ros        # on Ubuntu; installs git, python, creates the venvs, runs pytest
```

On Windows, with only Python installed:

```powershell
cd waypoint_mission
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ROS 2 install supports Ubuntu 22.04 … 24.04` | Wrong OS. Use WSL2/VM/Docker (§1) |
| `E: Unable to locate package ros-<distro>-…` | apt source not added or `apt-get update` failed; check `/etc/apt/sources.list.d/ros2.list`, network/proxy; the distro must match the Ubuntu release |
| `curl` to `raw.githubusercontent.com` fails | DNS/proxy issue; see `docs/ros-install/UPSTREAM_README.md` for the hosts workaround |
| `rosdep init` says already initialised | harmless; run `rosdep update` |
| `import rclpy` fails in the venv | the venv was created without `--system-site-packages`; recreate: `rm -rf .venv && python3 -m venv --system-site-packages .venv && .venv/bin/pip install -r requirements.txt`, and `source /opt/ros/<distro>/setup.bash` |
| `ros2: command not found` | new terminal needed, or `source /opt/ros/<distro>/setup.bash` |
| Robot topics not visible | `ROS_DOMAIN_ID` mismatch, different subnet, WSL without mirrored networking (§1) |
| `nav2_…` package not found for `humble`/`jazzy` | rerun with `--with-nav2`; if apt still cannot find it, `apt-cache search nav2` and report the name |

## 8. Uninstall

```bash
sudo apt-get remove --purge 'ros-<distro>-*' && sudo apt-get autoremove
sudo rm /etc/apt/sources.list.d/ros2.list /usr/share/keyrings/ros-archive-keyring.gpg
sed -i '/opt\/ros\/<distro>\/setup.bash/d' ~/.bashrc
rm -rf ~/ROS_LAB          # only if you no longer need the repo
```
