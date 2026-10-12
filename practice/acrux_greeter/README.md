# `practice/acrux_greeter/` — Acrux gift-greeter mission

Drives Acrux to up to 4 guests one after another, **stops and waits at each until you say
"yes"**, then goes home. The full plan, safety reasoning and event-day runbook are in
[`learn/build/09-acrux-greeter-mission.md`](../../learn/build/09-acrux-greeter-mission.md) —
read that first.

> **Status:** `mission.py` and `greeter_config.py` are unit-tested (`pytest`, runs anywhere).
> `mission_node.py`, `launch/safety.launch.py` and `config/collision_monitor.yaml` are
> **written but have never been run** on Gazebo or on the robot. The coordinates in
> `guests.yaml` are **placeholders**.

## Files

| File | Role |
|------|------|
| `mission.py` | Pure-Python state machine: commands + Nav2 results in, actions out. No ROS |
| `greeter_config.py` | Loads and validates `guests.yaml` |
| `mission_node.py` | ROS 2 adapter (laptop): Nav2 goals via `nav2_simple_commander`, live commands |
| `guests.yaml` | Home + 4 guest spots (placeholders until surveyed) and mission settings |
| `config/collision_monitor.yaml` | Stop/slow boxes for Nav2's collision monitor (robot side) |
| `launch/safety.launch.py` | Starts the collision monitor + its lifecycle manager on the robot |
| `tests/` | pytest: state machine (`test_mission.py`), config (`test_config.py`) |

## Run the tests (any OS, no ROS)

```powershell
cd practice\acrux_greeter
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Run the mission (laptop with ROS 2 — same distro as the robot)

```bash
sudo apt install ros-<distro>-nav2-simple-commander      # once
pip install pyyaml                                        # or: sudo apt install python3-yaml
source /opt/ros/<distro>/setup.bash
export ROS_DOMAIN_ID=<n>                                  # same as the robot

python3 mission_node.py --count 3                         # today's guest count (1-4)
```

| Flag | Meaning |
|------|---------|
| `--count N` | **Required.** Number of guests. No default on purpose |
| `--guests PATH` | Alternative `guests.yaml` |
| `--sim` | Gazebo run (`use_sim_time`) |
| `--set-initial-pose` | Publish `home` as the AMCL initial pose (robot must really be at home) |
| `--no-wait` | Don't wait for Nav2/AMCL lifecycle nodes (use if Acrux has no `amcl`) |
| `--allow-unsurveyed` | Drive even though `surveyed: false` (simulation only) |

Live commands (type in the terminal, or publish `std_msgs/String` to `/greeter/command`):
`y`/Enter next · `s` skip · `r` retry · `p` pause/resume · `h` home · `q` quit · `?` status.

Do **not** start it with `ros2 launch` — launch does not forward the keyboard.

## Run the safety layer (on the robot)

```bash
ros2 launch ~/acrux_greeter/launch/safety.launch.py cmd_vel_in:=<nav2 output> cmd_vel_out:=cmd_vel
```

Find the real topic names first (`ros2 topic info /cmd_vel -v`) — see §7 of the guide.
Copy this folder to the robot with `scp -r` (it is not a colcon package).

## Before you trust it

Work through §14 of the guide ("Open items") — especially: which ROS distro Acrux runs,
whether AMCL is actually launched, and the real `cmd_vel` chain.
