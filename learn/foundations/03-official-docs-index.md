# 03 — Official ROS 2 documentation index (Jazzy)

The authoritative source is **<https://docs.ros.org/en/jazzy/>**. Everything else (blogs,
YouTube, this repo) is secondary. Deep-link slugs occasionally change between doc builds —
if a link 404s, go to the section index page and find the tutorial by its title.

> Tip: the docs have a version switcher (top-left). Make sure it says **Jazzy**, not
> Rolling / Humble.

---

## Start here — the official beginner path

The docs themselves prescribe this order. Do it on a real Linux ROS 2 Jazzy install (or
`docker run -it --rm ros:jazzy`).

### 0. Install
- **Installation (landing)** — <https://docs.ros.org/en/jazzy/Installation.html>
- **Ubuntu (deb packages)** — <https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html>
  The robot and lab PC already have this; you need it only for your own practice machine.
- **Docker alternative** — `docker run -it --rm ros:jazzy` (no page needed; image is on Docker Hub).

### 1. Beginner: CLI tools
Section index — <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html>

| Tutorial | Why it matters for BeetleBot |
|---|---|
| Configuring your ROS 2 environment | `source`, `ROS_DOMAIN_ID`, `ROS_LOCALHOST_ONLY` — the exact things that make the PC see the robot |
| Using `turtlesim`, `ros2`, and `rqt` | your no-robot practice sandbox |
| Understanding nodes (`ros2 node ...`) | inspecting `lyra_*` nodes |
| Understanding topics (`ros2 topic ...`) | `/scan`, `/cmd_vel_nav`, `echo`, `pub`, `hz` |
| Understanding services (`ros2 service ...`) | `/lyra/arm`, `/lyra/disarm` |
| Understanding parameters (`ros2 param ...`) | `lyra_bridge` params in the troubleshooting matrix |
| Understanding actions | Nav2 goals (background knowledge) |
| Using `rqt_console` to view logs | reading node warnings/errors |
| Launching nodes (`ros2 launch`) | `ros2 launch lyra_bringup robot.launch.py` |
| Recording and playing back data (`ros2 bag`) | the "record `/scan`" lab task |

### 2. Beginner: Client libraries
Section index — <https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries.html>

| Tutorial | Why it matters |
|---|---|
| Using `colcon` to build packages | building `lyra_control` and your own workspace |
| Creating a workspace | `~/<reg>_ws/src`, underlay/overlay |
| Creating a package (Python) | structure of `package.xml` / `setup.py` |
| **Writing a simple publisher and subscriber (Python)** | this *is* the obstacle-avoidance node pattern — learn it cold |
| Writing a simple service and client (Python) — <https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html> | how `/lyra/arm` works under the hood |
| Creating custom msg and srv files | viva topic; not needed for the lab tasks |
| Using parameters in a class (Python) | tuning node behaviour without editing code |
| Using `ros2doctor` to identify issues | first move when something's broken |

### 3. Concepts (read after you've done the tutorials)
- **Concepts (landing)** — <https://docs.ros.org/en/jazzy/Concepts.html>
- **Basic Concepts** — <https://docs.ros.org/en/jazzy/Concepts/Basic.html>
  (nodes, discovery, interfaces, parameters, introspection, launch)
- Nodes / Topics / Services / Actions / Parameters — one page each under Concepts/Basic
- **Client libraries** (what `rclpy` / `rclcpp` are) — under Concepts/Basic

---

## Reference pages worth bookmarking

| Topic | Link |
|---|---|
| ROS 2 Jazzy docs home | <https://docs.ros.org/en/jazzy/> |
| Tutorials (all levels) | <https://docs.ros.org/en/jazzy/Tutorials.html> |
| How-to guides | <https://docs.ros.org/en/jazzy/How-To-Guides.html> |
| tf2 (transforms) tutorials | <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html> |
| Launch system | <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html> |
| `geometry_msgs/Twist` | <https://docs.ros.org/en/jazzy/p/geometry_msgs/msg/Twist.html> (or `ros2 interface show geometry_msgs/msg/Twist`) |
| `sensor_msgs/LaserScan` | <https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/LaserScan.html> (or `ros2 interface show sensor_msgs/msg/LaserScan`) |
| `rclpy` API reference | <https://docs.ros.org/en/jazzy/p/rclpy/> |

> The `ros2 interface show <type>` command is faster than the website and always matches
> the version installed. Use it in the lab.

---

## The other stacks BeetleBot uses (separate docs)

| Stack | What it does on the robot | Docs |
|---|---|---|
| **Nav2** | autonomous navigation (planners, controllers, behaviour tree) | <https://docs.nav2.org/> |
| **SLAM Toolbox** | builds the map in `mode:=slam` | <https://github.com/SteveMacenski/slam_toolbox> |
| **robot_localization** | EKF fusing wheel odometry + IMU → `/odom`, `/tf` | <https://docs.ros.org/en/melodic/api/robot_localization/html/> (concepts still apply) |
| **teleop_twist_keyboard** | the keyboard driver you remap to `/cmd_vel_nav` | <https://github.com/ros-teleop/teleop_twist_keyboard> |
| **sllidar_ros2** | RPLiDAR C1 driver → `/scan` | <https://github.com/Slamtec/sllidar_ros2> |
| **RViz2** | 3D visualisation | <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-Main.html> |

---

## BeetleBot's own documentation

- Vendor docs: <https://docs.veerobot.com/ros-robots/beetle-bot> (the README says
  "40–60 hours beginner → autonomous navigation")
- Upstream source: <https://github.com/VEEROBOT/BeetleBot> (cloned locally at `BeetleBot/`)
  - `BeetleBot/docs_ros2/LYRA_QUICK_REFERENCE.md` — the `lyra-*` command reference + a good
    troubleshooting matrix
  - `BeetleBot/docs_ros2/README.md`, `LYRA_COMMAND_UTILITY_SETUP.md` — command-utility setup
  - `BeetleBot/lyra_ws/src/` — the actual packages (`lyra_bringup`, `lyra_control`, `lyra_bridge`, …)

> Note the mismatch flagged in `.CLAUDE/CLAUDE.md` → Known Technical Debt: the upstream repo
> drives `/cmd_vel`, the lab handouts drive `/cmd_vel_nav`. **Trust the handouts for the lab.**

---

## Track B docs (building a stack — pairs with `../build/`)

| Topic | `build/` file | Docs |
|---|---|---|
| URDF / Xacro | `04` | <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/URDF-Main.html> · <https://github.com/ros/xacro/wiki> |
| TF2 | `04` | <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html> · REP-105 <https://www.ros.org/reps/rep-0105.html> |
| Gazebo (Harmonic) + `ros_gz` | `05` | <https://gazebosim.org/docs/harmonic/> · <https://github.com/gazebosim/ros_gz> |
| `ros2_control` | `06` | <https://control.ros.org/jazzy/> · demos <https://github.com/ros-controls/ros2_control_demos> |
| `gz_ros2_control` | `05`/`06` | <https://github.com/ros-controls/gz_ros2_control> |
| micro-ROS | `06` | <https://micro.ros.org/> |
| `robot_localization` | `07` | <https://docs.ros.org/en/melodic/api/robot_localization/html/> (params unchanged) |
| SLAM Toolbox | `07` | <https://github.com/SteveMacenski/slam_toolbox> |
| Cartographer ROS | `07` | <https://google-cartographer-ros.readthedocs.io/> |
| Nav2 (concepts + config) | `08` | <https://docs.nav2.org/> · tuning <https://docs.nav2.org/tuning/index.html> |
| Nav2 plugins (planners/controllers) | `08` | <https://docs.nav2.org/plugins/index.html> |
| `nav2_simple_commander` (Python API) | `08` | <https://docs.nav2.org/commander_api/index.html> |
| MoveIt 2 (arms) | `../build/02` | <https://moveit.picknik.ai/main/index.html> |
| Behavior trees (BT.CPP / Groot2) | `08` | <https://www.behaviortree.dev/> |

---

## Suggested pre-lab reading budget (~4–6 hours)

1. `01-linux-and-shell.md` + practice each in a terminal — 45 min
2. Official "Configuring your ROS 2 environment" + "Understanding nodes/topics/services" — 90 min
3. Official "Writing a simple publisher and subscriber (Python)" — do it, don't just read — 60 min
4. `02-ros2-concepts.md` §4–5 (rclpy anatomy + the obstacle-avoidance walkthrough) — 45 min
5. `../lab/01-lab-day-runbook.md` — read twice, then recite the connect→arm→drive→disarm→stop chain from memory — 30 min

---

Next: `04-ros1-vs-ros2.md`. Then branch — **Track A** (the lab) starts at
`../lab/00-course-and-lab-map.md`; **Track B** (building a stack) starts at
`../build/01-three-bots-architecture.md`. Full map: `../README.md`.
