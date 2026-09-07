# 02 — How ROS 2 works

ROS 2 = "Robot Operating System 2". It is **not an OS** — it's a middleware + toolset that
lets many small programs ("nodes") on one or more machines talk to each other over a
network, plus a build system and CLI tools. Version used here: **Jazzy Jalisco** on Ubuntu.

**Two tiers in this file.** §1–§6 are the lab-exam core — the computation graph, the CLI,
`colcon`, `rclpy` node anatomy, and a line-by-line read of the handout obstacle-avoidance
node. §7–§15 are the depth you need to *build* a stack rather than operate one: QoS,
parameters, lifecycle nodes, executors, actions, TF2, creating packages and custom
interfaces, launch files, and composition. Do §1–§6 first; come back for §7+ when
`build/03` sends you here.

Official reference for everything below: <https://docs.ros.org/en/jazzy/> (see
`03-official-docs-index.md` for the exact pages).

---

## 1. The computation graph

```
        ┌────────┐   /scan (LaserScan)    ┌─────────────────────┐
        │ lidar  │ ─────────────────────> │ obstacle_avoidance  │
        │ node   │                        │ node                │
        └────────┘                        └─────────┬───────────┘
                                                    │ /cmd_vel_nav (Twist)
                                                    v
                                          ┌─────────────────────┐
                                          │ lyra_bridge / motors│
                                          └─────────────────────┘
```

- **Node** — one process that does one job (read the LiDAR, fuse odometry, avoid obstacles).
  In `rclpy` a node is a Python object subclassing `rclpy.node.Node`.
- **Topic** — a named, typed, many-to-many message bus. Publishers `publish` messages;
  subscribers get a callback for each one. Asynchronous, fire-and-forget. Name starts with
  `/` (e.g. `/scan`, `/cmd_vel_nav`).
- **Message** — the data structure sent on a topic. Defined in a `.msg` file, lives in an
  interface package. E.g. `geometry_msgs/msg/Twist`, `sensor_msgs/msg/LaserScan`.
- **Service** — request/response, one-to-one, synchronous-ish. Used for "do a thing now":
  `/lyra/arm` and `/lyra/disarm` are services of type `std_srvs/srv/Trigger` (empty
  request, returns `success` + `message`).
- **Action** — long-running goal with feedback + result (e.g. "navigate to this pose").
  Nav2 uses these. You mostly consume them via RViz in this lab.
- **Parameter** — a named config value on a node, settable at launch or at runtime
  (`ros2 param get/set`). E.g. `lyra_bridge` has `control.cmd_vel_timeout_s`.
- **`/tf` (transforms)** — a special topic tree describing where each coordinate frame
  (`base_link`, `odom`, `map`, `laser`) is relative to the others, over time. SLAM/Nav
  depend on it. Inspect with `ros2 run tf2_tools view_frames`.

### DDS and `ROS_DOMAIN_ID`

ROS 2 has no central master (ROS 1 had `roscore`; ROS 2 does not). Nodes **discover each
other automatically** over the network using DDS. Two controls matter for the lab:

- **`ROS_DOMAIN_ID`** (0–101) — nodes only see other nodes with the *same* domain ID.
  The lab assigns you a number so students on one Wi-Fi don't stomp each other. Set it
  (`export ROS_DOMAIN_ID=<n>`) in **every terminal, PC and robot**.
- **`ROS_LOCALHOST_ONLY=1`** — restricts discovery to one machine. The robot needs this
  *off* so the PC can see it.

If `ros2 topic list` on the PC doesn't show the robot's topics: wrong domain ID, wrong
Wi-Fi, or `ROS_LOCALHOST_ONLY` set. That's the #1 connectivity bug.

---

## 2. CLI tools you must know (viva favourites)

All run after `source`-ing your environment.

### Discovery / inspection
```bash
ros2 node list                       # running nodes
ros2 node info /lyra_bridge          # its pubs, subs, services, params
ros2 topic list                      # active topics
ros2 topic list -t                   # ... with message types
ros2 topic info /scan                # type + publisher/subscriber count
ros2 topic echo /scan                # print messages live  (Ctrl+C to stop)
ros2 topic echo /scan --once         # just one message
ros2 topic hz /scan                  # publish rate (Hz)
ros2 topic bw /scan                  # bandwidth
ros2 interface show sensor_msgs/msg/LaserScan   # the message definition
ros2 service list
ros2 service type /lyra/arm          # -> std_srvs/srv/Trigger
ros2 param list /lyra_bridge
ros2 param get /lyra_bridge serial.port
```

### Making things happen
```bash
ros2 run <pkg> <executable>                       # run one node
ros2 run turtlesim turtlesim_node
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=cmd_vel_nav

ros2 launch <pkg> <file.launch.py> [key:=value]   # run many nodes from a launch file
ros2 launch lyra_bringup robot.launch.py mode:=slam camera:=true imu:=true

ros2 topic pub <topic> <type> "<yaml msg>"        # publish from the CLI
ros2 topic pub --once /cmd_vel_nav geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
#   -r 10   = repeat at 10 Hz      -t 50 = send 50 messages then stop
#   --once  = send exactly one

ros2 service call /lyra/arm std_srvs/srv/Trigger  # call a service
```

### `--ros-args` and remapping
Anything after `--ros-args` configures the node: `-r from:=to` **remaps** a name,
`-p name:=value` sets a parameter. The teleop command remaps the node's default `cmd_vel`
output onto the robot's `cmd_vel_nav` topic without editing code.

### Recording data — `ros2 bag`
```bash
ros2 bag record /scan                       # record one topic
ros2 bag record -o scan_data_bag /scan      # -o = output folder name
ros2 bag record -a                          # record ALL topics
ros2 bag info scan_data_bag                 # inspect a recording
ros2 bag play scan_data_bag                 # replay it (nodes see it as live)
```
A "bag" is a folder (`rosbag2_*` / your `-o` name) holding an SQLite/mcap file + metadata.

### Visualisation
```bash
ros2 run rviz2 rviz2                 # 3D view: robot, laser scan, map, tf
rqt                                  # plugin GUI: image view, topic monitor, etc.
ros2 run rqt_graph rqt_graph         # draw the node/topic graph
```

### `ros2 doctor`
```bash
ros2 doctor            # or: ros2 doctor --report
```
Checks your ROS setup for common problems. Good first move when something's off.

---

## 3. Workspaces, packages, and `colcon`

### Layout
```
~/<reg>_ws/                  # a "workspace" = a folder you build
├── src/                     # you put package source here
│   └── my_pkg/
│       ├── package.xml      # package metadata + dependencies
│       ├── setup.py         # (Python pkg) build config + entry points
│       ├── setup.cfg
│       ├── resource/my_pkg
│       └── my_pkg/          # the Python module (same name as package)
│           ├── __init__.py
│           └── my_node.py
├── build/                   # colcon scratch (gitignored)
├── install/                 # built result — you 'source' install/setup.bash
└── log/                     # build/run logs
```

### Build
```bash
cd ~/<reg>_ws
colcon build                                  # build everything in src/
colcon build --packages-select lyra_control   # build just one package
colcon build --symlink-install                # Python: edits take effect without rebuild
source install/setup.bash                     # make the built packages visible THIS shell
```

- **`colcon`** is the meta-build tool. It builds Python packages with `setuptools` and C++
  with CMake/ament.
- You must `source install/setup.bash` **after every build** (in each terminal) or `ros2
  run` won't find your new executable.

### Underlay vs overlay
- **Underlay** = `/opt/ros/jazzy` — the base install. `source /opt/ros/jazzy/setup.bash`.
- **Overlay** = your workspace's `install/`. Source it *after* the underlay. Packages in
  the overlay shadow same-named packages in the underlay.
- The robot's own overlay is `~/lyra_ws/install/`. Your practice code is a *separate*
  overlay in `~/<reg>_ws/install/`.

### `package.xml` and `setup.py` (Python package)
- `package.xml` — name, version, maintainer, `<depend>` tags (e.g. `rclpy`, `sensor_msgs`,
  `geometry_msgs`). `rosdep` reads these to install system deps.
- `setup.py` → `entry_points={'console_scripts': [...]}` maps a **command name** to a
  **`module:function`**. This is what makes `ros2 run <pkg> <name>` work. The handout adds:
  ```python
  entry_points={
      'console_scripts': [
          'cmd_vel_mux = lyra_control.cmd_vel_mux:main',
          'joy_teleop_wrapper = lyra_control.joy_teleop_wrapper:main',
          'obstacle_avoid = lyra_control.obstacle_avoidance:main',   # <-- added
      ],
  }
  ```
  After editing this you **must** `colcon build --packages-select lyra_control` again.

---

## 4. Anatomy of an `rclpy` node

Minimal publisher + subscriber + timer:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan


class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')                       # node name in the graph

        # subscribe: (msg_type, topic, callback, queue_depth)
        self.sub = self.create_subscription(
            LaserScan, '/scan', self.on_scan, 10)

        # publish: (msg_type, topic, queue_depth)
        self.pub = self.create_publisher(Twist, '/cmd_vel_nav', 10)

        # timer: call self.tick() every 0.1 s
        self.timer = self.create_timer(0.1, self.tick)

        self.get_logger().info('my_node started')          # logging

    def on_scan(self, msg: LaserScan):
        # msg.ranges is a list of distances (metres); msg.range_min / msg.range_max are limits
        self.latest = msg

    def tick(self):
        cmd = Twist()
        cmd.linear.x = 0.2          # forward m/s
        cmd.angular.z = 0.0         # yaw rad/s  (+ = left)
        self.pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)           # start the ROS client library
    node = MyNode()
    try:
        rclpy.spin(node)            # process callbacks forever until Ctrl+C
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
```

Key ideas for the viva:
- `rclpy.init()` / `rclpy.shutdown()` bracket all ROS activity.
- `rclpy.spin(node)` is the event loop — nothing happens without it; it dispatches
  subscription callbacks and timer callbacks.
- `create_subscription` / `create_publisher` / `create_timer` / `create_service` are the
  building blocks, all called in `__init__`.
- The last argument `10` is the **QoS queue depth** — how many messages to buffer.
- `self.get_logger().info/warn/error(...)` for output (shows up with node name + timestamp).

---

## 5. Reading the handout obstacle-avoidance node

File: `docs/BEETLEBOT Updated _Obstacle_avoid.txt` (the fuller version — study this one).
It subscribes `/scan`, publishes `/cmd_vel_nav`, and runs a small state machine.

### What a `LaserScan` gives you
- `msg.ranges` — a list of ~N distances (metres), one per angular step, going around the
  robot. Index 0 = angle `angle_min`, each next index adds `angle_increment`.
- `msg.range_min`, `msg.range_max` — sensor limits. Values outside this, or `inf`/`nan`,
  are **invalid** and must be filtered.
- Convention the script assumes: index 0 = straight ahead, increasing index = turning left,
  wrap-around at the end = right side.

### The windowing (how it splits front/left/right)
```python
num_readings = len(msg.ranges)
front_window = num_readings // 12     # ~15° each side of dead ahead
side_window  = num_readings // 6      # ~30° band for each side

front_ranges = msg.ranges[-front_window:] + msg.ranges[:front_window]   # wraps around 0
left_ranges  = msg.ranges[front_window : side_window]
right_ranges = msg.ranges[num_readings - side_window : num_readings - front_window]
```
`msg.ranges[-front_window:] + msg.ranges[:front_window]` stitches the last few and first
few readings together because "straight ahead" straddles the start/end of the array.

`get_valid_ranges()` then drops `inf`, `nan` (`r == r` is False only for `nan`), zeros, and
anything outside `range_min/range_max`. `min(valid_front)` is the nearest obstacle ahead.

### The state machine
```
             front_distance < 0.45 m ?
             ┌── yes ──> set self.reversing = True, record start time, drive backward
             │            (next callbacks: keep reversing until 0.8 s elapsed,
             │             then turn toward whichever side has MORE free space)
             │
   scan ─────┤   0.45 m <= front_distance < 0.5 m ?
             ├── yes ──> stop forward, turn toward clearer side (left if left>right)
             │
             └── else ──> drive forward at 0.2 m/s
```
`self.reversing` + `self.reverse_start_time` make the reverse last a fixed wall-clock time
(`time.time()` deltas) across multiple scan callbacks — a common way to do a timed action
without blocking `spin()`.

### The safety handler
```python
signal.signal(signal.SIGINT, self.signal_handler)
```
Overrides `Ctrl+C` so that before exiting it publishes a zero `Twist` 20 times
(`for _ in range(20): self.cmd_pub.publish(stop_msg); time.sleep(0.02)`), guaranteeing the
last thing the motors hear is "stop". Then `destroy_node()` + `rclpy.try_shutdown()` +
`sys.exit(0)`.

### To run it (on the robot)
```bash
cd ~/lyra_ws/src/lyra_control/lyra_control/
nano obstacle_avoidance.py           # paste the script, Ctrl+O, Ctrl+X
chmod +x obstacle_avoidance.py
cd ~/lyra_ws/src/lyra_control/
nano setup.py                        # add the 'obstacle_avoid = ...:main' entry_point
cd ~/lyra_ws
colcon build --packages-select lyra_control
source install/setup.bash
ros2 run lyra_control obstacle_avoid
# (Terminal 1 must already be running: ros2 launch lyra_bringup robot.launch.py)
```

---

## 6. Practice without the robot — turtlesim

On any Linux box (or `docker run -it --rm ros:jazzy`):
```bash
sudo apt update && sudo apt install ros-jazzy-turtlesim ros-jazzy-teleop-twist-keyboard
source /opt/ros/jazzy/setup.bash

# terminal 1
ros2 run turtlesim turtlesim_node
# terminal 2
ros2 run turtlesim turtle_teleop_key            # arrow keys drive the turtle
# terminal 3 — inspect
ros2 topic list
ros2 topic echo /turtle1/cmd_vel
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 2.0}, angular: {z: 1.8}}"
ros2 bag record /turtle1/cmd_vel
```
Everything you learn here (topics, echo, pub, remap, bag) transfers directly to BeetleBot —
only the topic names and message shapes change.

---

# Builder depth (§7–§15)

Everything below is what separates "I can run a launch file" from "I can write the launch
file." `../build/03-build-a-ros2-autonomy-stack.md` is the map that ties these together.

## 7. QoS — Quality of Service

Every topic has a **QoS profile** on each end. If the publisher's and subscriber's profiles
are **incompatible**, they silently don't connect — `ros2 topic echo` shows nothing and
there's no error. This is one of the most common "why is my subscriber dead" bugs.

The settings that matter:

| Policy | Values | Meaning |
|---|---|---|
| **Reliability** | `RELIABLE` / `BEST_EFFORT` | RELIABLE re-sends dropped messages (TCP-like); BEST_EFFORT doesn't (UDP-like) |
| **Durability** | `VOLATILE` / `TRANSIENT_LOCAL` | TRANSIENT_LOCAL keeps the last N messages for subscribers that join *later* (latching) |
| **History / depth** | `KEEP_LAST` (depth N) / `KEEP_ALL` | how many messages to buffer — the `10` in `create_publisher(..., 10)` |
| **Liveliness / Deadline** | — | rarely tuned by hand; used for failure detection |

**Compatibility rule:** a subscriber can be *more* lenient than the publisher, never
stricter. `BEST_EFFORT` sub + `RELIABLE` pub → OK. `RELIABLE` sub + `BEST_EFFORT` pub →
**no connection.**

**The standard profiles** (`from rclpy.qos import ...`):

```python
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, DurabilityPolicy

# Sensor data (LiDAR, camera, IMU): BEST_EFFORT, depth 5 — drop a scan rather than lag
self.create_subscription(LaserScan, '/scan', self.cb, qos_profile_sensor_data)

# A map or a static transform: latched so late joiners get it
latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                     reliability=ReliabilityPolicy.RELIABLE)
self.create_publisher(OccupancyGrid, '/map', latched)
```

`/scan`, `/map`, `/tf_static` all use non-default QoS — if you subscribe with a bare `10`
you may get nothing. Check the publisher's profile with `ros2 topic info /scan --verbose`.

## 8. Parameters and YAML config

Parameters are a node's runtime-tunable settings. Declare them in the node, override them
from a YAML file at launch, inspect/change them live.

```python
class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        self.declare_parameter('max_speed', 0.5)                 # name, default
        self.declare_parameter('frame_id', 'base_link')
        self.max_speed = self.get_parameter('max_speed').value

        self.add_on_set_parameters_callback(self._on_param_change)   # react to live changes

    def _on_param_change(self, params):
        from rcl_interfaces.msg import SetParametersResult
        for p in params:
            if p.name == 'max_speed':
                self.max_speed = p.value
        return SetParametersResult(successful=True)
```

```bash
ros2 param list /my_node
ros2 param get /my_node max_speed
ros2 param set /my_node max_speed 0.8
ros2 param dump /my_node > my_node.yaml       # snapshot current values
```

A params YAML uses the node name and a `ros__parameters` key:
```yaml
my_node:
  ros__parameters:
    max_speed: 0.8
    frame_id: base_link
```
```bash
ros2 run my_pkg my_node --ros-args --params-file my_node.yaml
```
Nav2, `robot_localization`, `slam_toolbox` are all configured this way — a big YAML file
per node, loaded by the launch file (see `build/07`, `build/08`).

## 9. Lifecycle (managed) nodes

A **lifecycle node** has an explicit state machine —
`unconfigured → inactive → active → (finalized)` — so an orchestrator can bring a whole
system up in a controlled order: configure everyone (load params, allocate), *then*
activate (start publishing) once all are ready.

```
   ┌─────────────┐  configure   ┌──────────┐  activate   ┌────────┐
   │ unconfigured │ ───────────> │ inactive │ ──────────> │ active │
   └─────────────┘  <─────────── └──────────┘  <───────── └────────┘
                     cleanup                   deactivate
```

Nav2's servers (`planner_server`, `controller_server`, `bt_navigator`, `map_server`, …)
and many sensor drivers are lifecycle nodes; Nav2's `lifecycle_manager` walks them through
the transitions together.

```bash
ros2 lifecycle nodes                       # which nodes are managed
ros2 lifecycle get  /planner_server
ros2 lifecycle set  /planner_server configure
ros2 lifecycle set  /planner_server activate
```
In `rclpy`: subclass `rclpy.lifecycle.LifecycleNode` and implement `on_configure`,
`on_activate`, `on_deactivate`, `on_cleanup`.

## 10. Executors and callback groups

`rclpy.spin(node)` runs a **single-threaded executor**: it dispatches subscription, timer,
and service callbacks **one at a time**. A callback that blocks for 2 s freezes *every*
other callback for 2 s — including your safety timer. This is the cause of most "my node
randomly stops responding" reports.

```python
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup, MutuallyExclusiveCallbackGroup

exec_ = MultiThreadedExecutor(num_threads=4)
exec_.add_node(node)
exec_.spin()
```

- **MutuallyExclusiveCallbackGroup** (default) — callbacks in the same group never run
  concurrently. Put things that share state here.
- **ReentrantCallbackGroup** — callbacks may run in parallel / re-enter. Needed when one
  callback calls a service and waits for the response (otherwise deadlock on a
  single-threaded executor).
- Rule of thumb: keep callbacks short and non-blocking; if a callback must do slow work or
  call another service synchronously, give it a reentrant group and a multi-threaded
  executor.

## 11. Actions in depth

An **action** is for a long-running goal that needs progress feedback and can be cancelled —
"navigate to this pose", "follow this trajectory", "dock". It's three interfaces bundled:
a **goal** request, periodic **feedback**, and a final **result**. Built on topics +
services under the hood; in ROS 2 it's first-class in `rclpy` (no `actionlib`).

```python
from rclpy.action import ActionServer, ActionClient
from nav2_msgs.action import NavigateToPose

# server
self._srv = ActionServer(self, NavigateToPose, 'navigate_to_pose', self.execute_cb)

def execute_cb(self, goal_handle):
    fb = NavigateToPose.Feedback()
    while not done:
        goal_handle.publish_feedback(fb)
        if goal_handle.is_cancel_requested:
            goal_handle.canceled(); return NavigateToPose.Result()
    goal_handle.succeed()
    return NavigateToPose.Result()

# client
client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
client.wait_for_server()
future = client.send_goal_async(goal_msg, feedback_callback=self.on_feedback)
```

```bash
ros2 action list
ros2 action info /navigate_to_pose
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {...}}" --feedback
```

**Choosing:** topic = continuous stream, fire-and-forget. Service = quick request/response
(< ~1 s, no feedback). Action = slow, needs feedback and/or cancellation.

## 12. TF2 in depth

TF2 tracks where every **coordinate frame** is relative to every other, over time. The
frames form a **tree** (each frame has exactly one parent). For a mobile robot:

```
map ──> odom ──> base_link ──> laser
                          └──> imu_link
                          └──> camera_link
```

- `map → odom` — published by SLAM or AMCL; corrects long-term drift (jumps).
- `odom → base_link` — published by the localization EKF / wheel odometry; smooth, drifts.
- `base_link → laser` etc. — **static**, from the URDF via `robot_state_publisher`.

```python
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster, Buffer, TransformListener

# broadcast a dynamic transform
self.br = TransformBroadcaster(self)
t = TransformStamped()
t.header.stamp = self.get_clock().now().to_msg()
t.header.frame_id = 'odom'; t.child_frame_id = 'base_link'
t.transform.translation.x = x; t.transform.rotation.z = ...   # quaternion!
self.br.sendTransform(t)

# look one up
self.buf = Buffer(); self.listener = TransformListener(self.buf, self)
tf = self.buf.lookup_transform('map', 'base_link', rclpy.time.Time())   # Time() = "latest"
```

```bash
ros2 run tf2_tools view_frames                     # writes frames.pdf of the whole tree
ros2 run tf2_ros tf2_echo map base_link            # live transform between two frames
```

**Common TF errors:**
- *"frame X does not exist"* — nobody is publishing that edge; check `view_frames`.
- *"lookup would require extrapolation into the future"* — you asked for a stamp newer than
  the latest transform; use `Time()` for latest, or wait with a timeout.
- *"extrapolation into the past"* — the buffer's default 10 s window expired; increase
  `Buffer(cache_time=...)` or look up sooner.
- Two nodes publishing the *same* edge → the tree flickers. Exactly one publisher per edge.

## 13. Creating a package and custom interfaces

```bash
cd ~/ros2_ws/src
ros2 pkg create --build-type ament_python  my_pkg --dependencies rclpy std_msgs
ros2 pkg create --build-type ament_cmake   my_cpp_pkg --dependencies rclcpp
```
- `ament_python` — pure Python, `setup.py` + `setup.cfg`, entry points in `setup.py`.
- `ament_cmake` — C++ (or anything with a `CMakeLists.txt`), also required for packages that
  **define messages**.

**Custom messages/services/actions** live in their own `ament_cmake` **interface package**
(convention: `<robot>_interfaces` or `<robot>_msgs`):

```
my_robot_interfaces/
├── CMakeLists.txt        # rosidl_generate_interfaces(${PROJECT_NAME} "msg/..." "srv/...")
├── package.xml           # <buildtool_depend>rosidl_default_generators</buildtool_depend>
├── msg/WheelState.msg    #   float64[4] velocities
│                         #   int32[4]   ticks
├── srv/SetMode.srv       #   string mode
│                         #   ---
│                         #   bool success
└── action/DockTo.action  #   goal / --- / result / --- / feedback
```

After `colcon build`, use them like any built-in:
```python
from my_robot_interfaces.msg import WheelState
from my_robot_interfaces.srv import SetMode
```
```bash
ros2 interface show my_robot_interfaces/msg/WheelState
```
Keep interface packages **separate** from code packages — everyone depends on the
interfaces, and mixing them creates circular build deps.

## 14. Launch files in depth

A launch file starts many nodes with one command, with shared parameters and arguments.
Python is the most common form:

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    use_sim = LaunchConfiguration('use_sim_time')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),

        Node(
            package='my_pkg', executable='my_node', name='my_node',
            parameters=[PathJoinSubstitution([FindPackageShare('my_pkg'), 'config', 'my_node.yaml']),
                        {'use_sim_time': use_sim}],
            remappings=[('cmd_vel', 'cmd_vel_nav')],
            output='screen',
        ),

        IncludeLaunchDescription(                       # compose another launch file
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('sllidar_ros2'), 'launch', 'sllidar.launch.py'])),
            launch_arguments={'serial_port': '/dev/rplidar'}.items(),
        ),

        GroupAction([PushRosNamespace('robot1'),        # namespace a whole subtree
                     Node(package='...', executable='...')]),
    ])
```

Key pieces:
- **`DeclareLaunchArgument` + `LaunchConfiguration`** — CLI args: `ros2 launch pkg
  file.launch.py use_sim_time:=true`.
- **Substitutions** — values resolved at launch time (`FindPackageShare`,
  `PathJoinSubstitution`, `EnvironmentVariable`, `Command` for `xacro`).
- **`IncludeLaunchDescription`** — build big launches from small ones (this is how
  `lyra_bringup/robot.launch.py` works — `../build/01-three-bots-architecture.md` §2).
- **`RegisterEventHandler`** — do X when node Y exits / starts (e.g. spawn a controller
  only after the robot model is loaded).
- ROS 2 also accepts **XML** and **YAML** launch files for simple cases — less power, less
  boilerplate. XML looked like ROS 1's `.launch`; ROS 2's default is Python because launch
  logic (conditionals, loops, event handlers) is real code.

## 15. Composition and intra-process communication

Normally each node is its own process (`ros2 run`). **Composition** loads multiple nodes as
"components" into one process, so messages between them are passed by pointer — no
serialization, no loopback network — which matters for camera/point-cloud pipelines.

```bash
ros2 run rclcpp_components component_container                       # a container process
ros2 component load /ComponentManager pkg pkg::MyNode                # load a node into it
```
Or from a launch file with `ComposableNodeContainer` + `ComposableNode`, adding
`extra_arguments=[{'use_intra_process_comms': True}]`.

Python components exist but the big win (zero-copy) is a C++ feature. For most robot logic,
separate processes are fine and easier to debug — reach for composition when profiling says
a high-rate topic is costing you.

---

Next: `03-official-docs-index.md`.
