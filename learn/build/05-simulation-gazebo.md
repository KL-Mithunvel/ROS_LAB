# 05 — Simulation with Gazebo

Layer 1's stand-in (`03` §5). You build and tune the entire stack against a simulated robot
that publishes the **same topics and TF** as the real one, then switch to hardware with a
launch argument. This is not optional polish — it's how you avoid chasing a real robot
around a room while debugging a TF typo.

---

## 1. The Gazebo naming mess (read once, then move on)

- **Gazebo Classic** (`gazebo`, versions 1–11) — the original. **Gazebo 11 is EOL as of
  Jan 2025.** Used by older ROS 1/2 robots (Acrux's `acrux_gazebo` is close to this era).
- **"Ignition Gazebo"** — a rewrite, later **renamed** back to just **"Gazebo"** with
  version names: **Fortress, Garden, Harmonic, Ionic**. Commands are `gz sim`, `gz topic`.
- New projects use **new Gazebo**. Pairings that "just work" via apt:

| ROS 2 | Recommended Gazebo | Integration package |
|---|---|---|
| Humble | Fortress (or Classic 11) | `ros_gz` / `gazebo_ros_pkgs` |
| **Jazzy** | **Harmonic** | `ros_gz` |
| Kilted / Rolling | Ionic | `ros_gz` |

BeetleBot (`01` §1) targets **Gazebo Harmonic**. The rest of this file is new-Gazebo.

```bash
sudo apt install ros-jazzy-ros-gz          # metapackage: bridge + sim + interfaces
```

---

## 2. The pieces

| Package / plugin | Role |
|---|---|
| `gz sim` (the simulator) | physics + rendering; loads a **world** (`.sdf`) |
| `ros_gz_sim` | launch helpers (`gz_sim.launch.py`), the `create` node to **spawn** a model |
| `ros_gz_bridge` (`parameter_bridge`) | forwards messages between Gazebo transport and ROS 2 topics |
| `gz_ros2_control` | a Gazebo system plugin that exposes the sim robot to `ros2_control` (`build/06`) |
| `<gazebo>` tags in the URDF | attach sensor plugins (LiDAR, IMU, camera) to links |

SDF (Simulation Description Format) is Gazebo's native format for **worlds**; your **robot**
stays in URDF/Xacro and Gazebo converts it on spawn.

---

## 3. A world

```xml
<!-- myrobot_gazebo/worlds/room.sdf -->
<sdf version="1.10">
  <world name="room">
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <light type="directional" name="sun"> ... </light>
    <include><uri>https://fuel.gazebosim.org/1.0/OpenRobotics/models/Ground Plane</uri></include>
    <!-- walls, furniture, obstacles ... -->
  </world>
</sdf>
```
Start with an empty/room world; add obstacles once navigation works. Fuel
(`fuel.gazebosim.org`) has ready-made models and warehouse worlds.

---

## 4. Sensor plugins in the URDF

Add a `<gazebo reference="...">` block per sensor link. Gazebo publishes on **its** transport;
the bridge (§6) maps it to ROS.

```xml
<gazebo reference="laser">
  <sensor name="lidar" type="gpu_lidar">
    <update_rate>10</update_rate>
    <topic>scan</topic>
    <lidar>
      <scan><horizontal><samples>360</samples><min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle></horizontal></scan>
      <range><min>0.15</min><max>12.0</max></range>
    </lidar>
    <gz_frame_id>laser</gz_frame_id>
  </sensor>
</gazebo>

<gazebo reference="imu_link">
  <sensor name="imu" type="imu">
    <update_rate>100</update_rate>
    <topic>imu/data</topic>
    <gz_frame_id>imu_link</gz_frame_id>
  </sensor>
</gazebo>
```
`<gz_frame_id>` must match the URDF link name, or the message's `frame_id` won't line up
with TF.

---

## 5. `gz_ros2_control`

So `ros2_control` drives the simulated wheels exactly like real ones:

```xml
<gazebo>
  <plugin filename="gz_ros2_control-system" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
    <parameters>$(find myrobot_control)/config/controllers.yaml</parameters>
  </plugin>
</gazebo>
```
Now `diff_drive_controller` + `joint_state_broadcaster` work in sim, publishing `/odom`,
`odom→base_link` TF, and `/joint_states`. Same YAML runs on the real robot (`build/06`).

---

## 6. The bridge

`ros_gz_bridge` maps Gazebo topics ↔ ROS 2 topics. Config file form:
```yaml
# myrobot_gazebo/config/bridge.yaml
- gz_topic_name: "scan"
  ros_topic_name: "scan"
  gz_type_name: "gz.msgs.LaserScan"
  ros_type_name: "sensor_msgs/msg/LaserScan"
  direction: GZ_TO_ROS
- gz_topic_name: "imu/data"
  ros_type_name: "sensor_msgs/msg/Imu"
  gz_type_name: "gz.msgs.IMU"
  direction: GZ_TO_ROS
- gz_topic_name: "clock"
  ros_type_name: "rosgraph_msgs/msg/Clock"
  gz_type_name: "gz.msgs.Clock"
  direction: GZ_TO_ROS
```
```python
Node(package='ros_gz_bridge', executable='parameter_bridge',
     arguments=['--ros-args', '-p', f'config_file:={bridge_yaml}'])
```
The `/clock` bridge is mandatory — it's what feeds `use_sim_time`.

---

## 7. Sim time

Gazebo runs its own clock (pausable, faster/slower than wall time). Every ROS node in a sim
session must use it:

```python
{'use_sim_time': True}     # pass to EVERY node's parameters
```
If one node misses it, its message timestamps disagree with the rest and TF lookups fail
with *"extrapolation into the past/future"*. Pass `use_sim_time` as a launch argument
threaded through every included launch file (`03` §10).

---

## 8. A sim bringup launch

```python
def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=<room.sdf path>),

        IncludeLaunchDescription(<ros_gz_sim gz_sim.launch.py>,
            launch_arguments={'gz_args': [LaunchConfiguration('world'), ' -r']}.items()),

        # robot_state_publisher with use_sim_time:=true   (build/04 §3)
        IncludeLaunchDescription(<myrobot_description display>, launch_arguments={'use_sim_time': 'true'}.items()),

        # spawn the robot from /robot_description
        Node(package='ros_gz_sim', executable='create',
             arguments=['-topic', 'robot_description', '-name', 'myrobot', '-z', '0.1']),

        Node(package='ros_gz_bridge', executable='parameter_bridge',
             arguments=['--ros-args', '-p', f'config_file:={bridge_yaml}']),

        # controllers (build/06), then localization/slam/nav as separate includes
    ])
```

```bash
ros2 launch myrobot_gazebo sim.launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

---

## 9. Verifying

- `gz sim` window shows the robot in the world, not falling through the floor.
- `ros2 topic list` shows `/scan`, `/imu/data`, `/clock`, `/joint_states`, `/odom`.
- `ros2 topic hz /scan` ≈ your configured rate; `ros2 topic echo /scan --once` has finite ranges.
- RViz (`Fixed Frame: odom`, `use_sim_time` on) shows the laser scan and the robot moving
  under teleop.
- `ros2 run tf2_tools view_frames` — full tree, `odom → base_link` updating.

---

## 10. The sim-to-real gap (know what sim won't tell you)

- **Sensor noise & artifacts** — real LiDAR has dropouts, reflective-surface ghosts, min-range
  blind zones; add noise models in the plugin, but expect to re-tune costmap/AMCL params on
  hardware.
- **Wheel slip & backlash** — skid-steer especially; sim odometry is often too good.
- **Timing & compute** — Nav2 + SLAM may run at 20 Hz in sim on your laptop and 5 Hz on the
  Pi. Profile on target.
- **Latency** — Wi-Fi/DDS latency between PC and robot doesn't exist in a one-machine sim.

Rule: sim proves the **logic and wiring**; hardware bring-up is a **tuning** pass, not a
rewrite.

---

## 11. Common mistakes

- Forgetting the `/clock` bridge or `use_sim_time` on one node → TF extrapolation errors.
- `<gz_frame_id>` ≠ URDF link name → scan renders in the wrong pose.
- No `<inertial>` / bad inertia in the URDF → model spasms (`build/04` §7).
- Bridging a topic in the wrong direction (`ROS_TO_GZ` vs `GZ_TO_ROS`).
- Running Gazebo Classic tutorials against new Gazebo (commands and plugin names differ).
- Spawning before `robot_state_publisher` is up → `create -topic robot_description` finds nothing.

---

Next: `06-control-and-ros2-control.md`.
