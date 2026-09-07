# 04 — ROS 1 vs ROS 2

You are learning **ROS 2 Jazzy**. But ROS 1 is everywhere you look:

- Your **syllabus** (`../lab/00-course-and-lab-map.md` §1) lists experiments using
  `move_base` and `actionlib` — both ROS 1 names. The paperwork predates the switch.
- **Acrux** (a vendored submodule) ships a ROS 1 `noetic` branch alongside its
  `ros2-humble` one — the same robot, both ecosystems.
- Most tutorials, Stack Overflow answers, and older robot repos you'll find are ROS 1.
- Viva examiners trained before ~2022 will ask you the difference.

This file is the map between the two. You never have to *write* ROS 1 here — you have to
**translate** it.

---

## 1. One-paragraph history

ROS 1 started at Willow Garage in 2007. Its releases are named alphabetically
(…Kinetic, Melodic, **Noetic**). **ROS Noetic (2020) is the last ROS 1 distro ever** — it
reached end-of-life in **May 2025**. ROS 2 was a ground-up rewrite (first usable release
~2017) to fix ROS 1's architectural limits: no real-time, no multi-robot story, a single
point of failure, Linux-only, no security. ROS 2 distros are also alphabetical
(Foxy, Galactic, **Humble** 2022, Iron, **Jazzy** 2024, Kilted, …). All new robots ship
ROS 2; ROS 1 is legacy maintenance only.

### Distros are tied to Ubuntu versions

Each distro targets **one** Ubuntu LTS and is supported for that LTS's life:

| ROS | Distro | Ubuntu | Support until | In this repo |
|---|---|---|---|---|
| ROS 1 | Noetic | 20.04 | **EOL May 2025** | Acrux `noetic` branch (legacy) |
| ROS 2 | Humble | 22.04 | May 2027 | **Acrux** (`ros2-humble`) |
| ROS 2 | Jazzy | 24.04 | May 2029 | **BeetleBot** (the lab robot) |

This is why the three robots run different versions — it's not arbitrary, it's whichever
Ubuntu the robot's image was built on. You cannot `apt install ros-jazzy-*` on Ubuntu
22.04; the distro *is* the Ubuntu pairing. (JetBot uses no ROS at all — `build/01` §4.)

---

## 2. The core architectural difference: master vs DDS

**ROS 1** has a central **`roscore`** (the "master") — a name-service every node registers
with to find other nodes. Kill `roscore` and the whole graph is blind. Every machine points
at it via `ROS_MASTER_URI=http://<master-ip>:11311`.

**ROS 2 has no master.** Nodes find each other **peer-to-peer** using **DDS** (Data
Distribution Service), an industrial pub/sub standard. Discovery is automatic over UDP
multicast on the subnet. There is no single process to crash, and startup order doesn't
matter.

| | ROS 1 | ROS 2 |
|---|---|---|
| Discovery | central `roscore` master | distributed, DDS (no master) |
| "Which network?" | `ROS_MASTER_URI` (one IP) | `ROS_DOMAIN_ID` (a number 0–101) |
| Transport | custom TCPROS / UDPROS | DDS (RTPS) over UDP, pluggable vendor |
| Startup order | master must be up first | any order |
| Single point of failure | yes (`roscore`) | no |
| QoS control | none (TCP or bust) | per-topic (reliability, durability, depth — `02` §7) |
| Real-time | no | yes (executors, deterministic allocators) |
| Multi-robot | awkward (namespaces + one master) | domain IDs / namespaces / discovery servers |
| Security | none | SROS2 (auth, encryption, access control) |
| Platforms | Linux only (practically) | Linux, Windows, macOS, RTOS, microcontrollers (micro-ROS) |

The practical lab consequence: in ROS 1 you'd `export ROS_MASTER_URI=http://192.168.0.124:11311`
on your PC to talk to the robot. In ROS 2 you `export ROS_DOMAIN_ID=<n>` (the same number)
on both — and discovery does the rest. (`01-linux-and-shell.md` §9, `02` §1.)

---

## 3. Command and concept translation table

| Task | ROS 1 | ROS 2 |
|---|---|---|
| Start the graph | `roscore` | *(nothing — no master)* |
| Run a node | `rosrun pkg node` | `ros2 run pkg node` |
| Launch many | `roslaunch pkg file.launch` (XML) | `ros2 launch pkg file.launch.py` (Python/XML/YAML) |
| List/echo topics | `rostopic list` / `rostopic echo /t` | `ros2 topic list` / `ros2 topic echo /t` |
| Publish from CLI | `rostopic pub /t type "..."` | `ros2 topic pub /t type "..."` |
| Services | `rosservice call /s "..."` | `ros2 service call /s type "..."` |
| Parameters | central **Parameter Server** (global) | **per-node** parameters (`ros2 param ...`) |
| Params at launch | `<param>` / `<rosparam>` in XML | YAML file with `ros__parameters:` (`02` §8) |
| Dynamic params | `dynamic_reconfigure` (separate cfg) | native — `ros2 param set` + a set-param callback |
| Actions | `actionlib` (separate library) | built into `rclpy`/`rclcpp` (`02` §11) |
| Build tool | `catkin_make` / `catkin build` | `colcon build` |
| Build system | `catkin` (CMake) | `ament` (CMake or Python) |
| Workspace output | `devel/` + `install/` | `install/` only |
| Package manifest | `package.xml` format 2 | `package.xml` format 3 |
| Client libs | `rospy`, `roscpp` | `rclpy`, `rclcpp` (thin wrappers over `rcl`) |
| Node init | `rospy.init_node('n')` | `rclpy.init()` + `Node('n')` (a class) |
| Spin | `rospy.spin()` | `rclpy.spin(node)` (+ executors) |
| Transforms | `tf` → `tf2` | `tf2` (same lib, ported) |
| Nav stack | `move_base` | **Nav2** (`nav2_bringup`, behavior trees) |
| SLAM (2D) | `gmapping`, `hector_slam`, `cartographer` | `slam_toolbox`, `cartographer` |
| Localization | `amcl`, `robot_pose_ekf` / `robot_localization` | `nav2_amcl`, `robot_localization` (ported) |
| Sim | Gazebo Classic | Gazebo (Harmonic/Ionic) + `ros_gz`, or Gazebo Classic 11 (EOL) |
| Control | custom, or `ros_control` | `ros2_control` |
| Bags | `.bag` file, `rosbag record` | directory (`.mcap`/`.db3`), `ros2 bag record` |
| Introspection GUI | `rqt`, `rviz` | `rqt`, `rviz2` |
| Message compat | `.msg` syntax **identical** | `.msg` syntax **identical** (mostly) |

**Names that trip people up:** `catkin`→`colcon`, `roscore`→(gone), `rosrun`→`ros2 run`,
`move_base`→Nav2, `actionlib`→native actions, `dynamic_reconfigure`→native params,
`nodelet`→**components/composition** (`02` §15).

---

## 4. Code: a minimal publisher, side by side

**ROS 1 (`rospy`)** — module-style, global init:
```python
#!/usr/bin/env python
import rospy
from geometry_msgs.msg import Twist

rospy.init_node('driver')
pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
rate = rospy.Rate(10)
while not rospy.is_shutdown():
    msg = Twist(); msg.linear.x = 0.2
    pub.publish(msg)
    rate.sleep()
```

**ROS 2 (`rclpy`)** — class-style, explicit lifecycle:
```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class Driver(Node):
    def __init__(self):
        super().__init__('driver')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_timer(0.1, self.tick)          # 10 Hz — no manual rate.sleep loop
    def tick(self):
        msg = Twist(); msg.linear.x = 0.2
        self.pub.publish(msg)

def main():
    rclpy.init()
    rclpy.spin(Driver())
    rclpy.shutdown()
```

Differences that matter: ROS 2 nodes are **objects** (you can have several per process);
work happens in **timer/subscription callbacks** driven by `spin`, not a hand-rolled
`while` loop; `queue_size` became the QoS depth argument; the build wiring
(`setup.py` entry points) replaces `rosrun`'s script discovery. Full ROS 2 node anatomy:
`02` §4.

---

## 5. What is *the same*

Don't over-learn the differences — a lot carries straight over:

- **The mental model** — nodes, topics, services, messages, the pub/sub graph.
- **`.msg` / `.srv` / `.action` file syntax** — nearly identical; most `common_interfaces`
  (`std_msgs`, `geometry_msgs`, `sensor_msgs`, `nav_msgs`) have the **same fields**.
- **URDF / Xacro** — unchanged (`build/04`).
- **TF tree concept and `tf2` API shape** — same frames, same `lookup_transform` idea.
- **RViz**, **rqt**, **Gazebo** — same tools, `2`-suffixed binaries.
- **Nav concepts** — costmaps, global/local planners, AMCL particle filter, EKF fusion —
  Nav2 is a re-architecture of the same algorithms, not new theory (`build/07`, `build/08`).
- **`rosdep`**, **`package.xml` dependency tags**, the workspace/overlay idea.

So ROS 1 tutorials are still useful for *concepts* — you just retype the commands.

---

## 6. Why ROS 2 (what the rewrite bought)

1. **No single point of failure** — no `roscore`.
2. **QoS** — choose reliability/latency per topic; sensor streams can drop, commands can't.
3. **Real-time capable** — bounded executors, lock-free options; the control loop can meet
   deadlines.
4. **Multi-robot** — domain IDs, namespaces, discovery servers instead of one shared master.
5. **Security** — SROS2: authentication, encryption, and access control on the DDS layer.
6. **Cross-platform + embedded** — Windows/macOS, and **micro-ROS** puts a real ROS 2 node
   on a microcontroller (an STM32/ESP32 can be a first-class node, not just a serial slave —
   contrast BeetleBot's `lyra_bridge` + dumb-serial STM32, `build/01` §2 / `build/06`).
7. **Standard middleware** — DDS is an existing OMG industrial standard with multiple vendors
   (Fast DDS, Cyclone DDS), not a bespoke ROS transport.

---

## 7. Talking to ROS 1 from ROS 2 — `ros1_bridge`

During migration you often have one ROS 1 sensor driver and an otherwise ROS 2 system.
`ros1_bridge` is a process that runs in both worlds and forwards topics/services between
them:
```bash
# with both a ROS 1 setup.bash and a ROS 2 setup.bash sourced
ros2 run ros1_bridge dynamic_bridge --bridge-all-topics
```
It matches messages by name+fields. Custom messages need to be built for both sides. It's a
transition tool, not a permanent architecture — the goal is always to finish porting.

---

## 8. How this maps back to this repo

| Where you meet ROS 1 | What to do |
|---|---|
| Syllabus says `move_base` / `actionlib` (`../lab/00` §1) | Answer in Nav2 / native-actions terms; note the syllabus is ROS 1-era |
| Acrux `noetic` branch / `gmapping.yaml` (`build/01` §3, §5.2) | It's the legacy option; the `ros2-humble` branch + `slam_toolbox` is what you'd run |
| A tutorial or repo uses `catkin`, `rosrun`, `roscore` | Translate with §3's table; the concepts transfer, the commands don't |
| Old `robot_localization` docs (they're on the Melodic site) | The EKF math and params are unchanged — `build/07` |
| Exam: "difference between ROS 1 and ROS 2?" | §2 (master vs DDS) is the headline; then QoS, real-time, multi-robot, security, embedded |

---

## 9. Viva rapid-fire

- **Biggest architectural change?** No master — ROS 2 uses distributed DDS discovery.
- **`ROS_MASTER_URI` equivalent in ROS 2?** `ROS_DOMAIN_ID` (a number, not a URL).
- **Last ROS 1 distro?** Noetic (Ubuntu 20.04), EOL May 2025.
- **`catkin_make` equivalent?** `colcon build`.
- **`rospy` equivalent?** `rclpy`.
- **What is QoS and why does ROS 1 not have it?** Per-topic delivery guarantees
  (reliability/durability/depth); ROS 1's transport was fixed TCP/UDP with no knobs.
- **Why can ROS 2 do real-time and ROS 1 can't?** Bounded/configurable executors,
  lock-free middleware paths, no Python-GIL-bound master loop in the critical path.
- **What's micro-ROS?** ROS 2 client library for microcontrollers over a serial/UDP
  transport — an MCU becomes a real node.
- **Did message definitions change?** Syntax essentially the same; `common_interfaces`
  fields mostly identical, so `.msg` knowledge transfers.
- **How do a ROS 1 and a ROS 2 node talk?** `ros1_bridge`.
- **Is `move_base` in ROS 2?** No — replaced by **Nav2** (behavior-tree architected).

---

Next: pick a track — **Track A** (the lab): `../lab/00-course-and-lab-map.md`.
**Track B** (build a stack): `../build/01-three-bots-architecture.md`. Full map: `../README.md`.
