# 04 — Robot description (URDF/Xacro) and TF2

Layer 2 of the stack (`03` §4). The description is a machine-readable model of the robot's
**bodies, how they connect, and where they are relative to each other**. Get it right and
you get the static TF tree, collision geometry, and control interfaces for free. Get a joint
axis wrong and the robot drives in circles in sim and you spend a day on it.

TF2 background: `../foundations/02-ros2-concepts.md` §12.

---

## 1. URDF: links and joints

A **URDF** (Unified Robot Description Format) is XML describing a tree of **links** (rigid
bodies) connected by **joints**. Exactly one root link; every other link has exactly one
parent joint.

```xml
<robot name="myrobot">

  <link name="base_link">
    <visual>   <geometry><box size="0.3 0.3 0.1"/></geometry> </visual>
    <collision><geometry><box size="0.3 0.3 0.1"/></geometry> </collision>
    <inertial>
      <mass value="2.0"/>
      <inertia ixx="0.02" ixy="0" ixz="0" iyy="0.02" iyz="0" izz="0.03"/>
    </inertial>
  </link>

  <link name="left_wheel">
    <visual><geometry><cylinder radius="0.05" length="0.03"/></geometry></visual>
    <collision><geometry><cylinder radius="0.05" length="0.03"/></geometry></collision>
    <inertial><mass value="0.1"/><inertia ixx="1e-4" ixy="0" ixz="0" iyy="1e-4" iyz="0" izz="1e-4"/></inertial>
  </link>

  <joint name="left_wheel_joint" type="continuous">
    <parent link="base_link"/>
    <child  link="left_wheel"/>
    <origin xyz="0 0.17 0" rpy="-1.5708 0 0"/>   <!-- position + orientation of child in parent -->
    <axis   xyz="0 0 1"/>                          <!-- rotation axis, in the child frame -->
  </joint>

</robot>
```

- **`<visual>`** — what RViz/Gazebo draw (mesh or primitive).
- **`<collision>`** — geometry for collision checking (keep it simple — a box, not a 50k-tri
  mesh — it's evaluated constantly).
- **`<inertial>`** — mass + inertia tensor. Gazebo needs realistic values or the robot
  behaves oddly (flips, sinks, jitters). Approximate with primitive formulas.
- **`<origin>`** on a joint — the transform from parent to child (`xyz` metres, `rpy`
  radians roll-pitch-yaw). This is what becomes a static TF.
- **`<axis>`** — for moving joints, the axis of motion in the child's frame.

### Joint types

| Type | Motion | Use |
|---|---|---|
| `fixed` | none | sensor mounts, structural links (→ static TF) |
| `continuous` | rotation, no limit | wheels |
| `revolute` | rotation, with `<limit lower= upper= effort= velocity=>` | arm joints, steering |
| `prismatic` | linear slide, with limits | linear actuators, grippers |
| `floating` / `planar` | rare | free-floating bases |

---

## 2. Xacro — URDF without the copy-paste

Real URDFs use **Xacro** (XML macros): properties, math, macros, file includes. A 4-wheel
robot's wheels differ only in sign — write the wheel once.

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="myrobot">

  <xacro:property name="wheel_radius" value="0.05"/>
  <xacro:property name="track"        value="0.34"/>

  <xacro:macro name="wheel" params="prefix y_reflect">
    <link name="${prefix}_wheel"> ... </link>
    <joint name="${prefix}_wheel_joint" type="continuous">
      <parent link="base_link"/>
      <child  link="${prefix}_wheel"/>
      <origin xyz="0 ${y_reflect * track/2} 0" rpy="${-pi/2} 0 0"/>
      <axis xyz="0 0 1"/>
    </joint>
  </xacro:macro>

  <xacro:wheel prefix="left"  y_reflect="1"/>
  <xacro:wheel prefix="right" y_reflect="-1"/>

  <xacro:include filename="$(find myrobot_description)/urdf/sensors.xacro"/>
  <xacro:include filename="$(find myrobot_description)/urdf/ros2_control.xacro"/>

</robot>
```

Expand it to plain URDF:
```bash
xacro myrobot.urdf.xacro > myrobot.urdf          # to inspect / debug
check_urdf myrobot.urdf                          # validates the tree, prints the hierarchy
urdf_to_graphiz myrobot.urdf                     # writes a PDF of the link/joint graph
```
In a launch file you don't pre-expand — you run xacro at launch time:
```python
robot_description = {'robot_description':
    Command(['xacro ', PathJoinSubstitution([FindPackageShare('myrobot_description'),
                                             'urdf', 'myrobot.urdf.xacro'])])}
```

---

## 3. Publishing the model: `robot_state_publisher`

`robot_state_publisher` reads `robot_description` + the live `/joint_states` and publishes
the **whole TF tree of the robot body**:

- **fixed** joints → `/tf_static` (published once, latched)
- **moving** joints → `/tf`, updated from `/joint_states` (wheel angles, arm angles)

```python
Node(package='robot_state_publisher', executable='robot_state_publisher',
     parameters=[robot_description, {'use_sim_time': use_sim}])
```

Where `/joint_states` comes from:
- **real robot / sim with control:** `ros2_control`'s `joint_state_broadcaster` (`build/06`)
  publishes real encoder positions.
- **no hardware, just visualising:** run `joint_state_publisher_gui` — sliders for each
  joint, handy for checking the URDF.

---

## 4. The mobile-robot TF tree (REP-105)

ROS standardises the frame names and who owns each edge:

```
  map ───────────────►  odom ──────────────►  base_link ──►  laser
  (SLAM or AMCL)        (localization EKF)    (URDF static)   imu_link
  corrects drift,       smooth, high-rate,                    camera_link
  can jump              drifts slowly
                             │
                             └──►  base_footprint  (optional: base_link projected to the ground plane)
```

| Edge | Publisher | Character |
|---|---|---|
| `map → odom` | `slam_toolbox` (mapping) **or** `nav2_amcl` (navigation) — never both | discrete corrections, may jump |
| `odom → base_link` | `robot_localization` EKF, or `diff_drive_controller` | continuous, smooth, drifts over time |
| `base_link → <sensor>` | `robot_state_publisher` from the URDF | fixed |
| `base_link → wheels` | `robot_state_publisher` from `/joint_states` | rotates, cosmetic |

Rules:
- **Exactly one publisher per edge.** Two nodes publishing `odom → base_link` (e.g. the
  controller *and* the EKF) makes the tree flicker — pick one, disable the other's TF output.
- The tree is a **tree** — `base_link` has one parent (`odom`), not two.
- `map` and `odom` are both "world-fixed"; the difference is `odom` is continuous (good for
  control) and `map` is accurate but jumpy (good for goals). Nav2 needs both.

Sensor frames must match what the driver stamps its messages with: if the LiDAR publishes
`/scan` with `frame_id: laser`, your URDF needs a `laser` link.

---

## 5. What else lives in the URDF

- **`<ros2_control>` block** — declares the command interfaces (e.g. `velocity` on each
  wheel joint) and state interfaces (`position`, `velocity`) that `ros2_control` binds to.
  Details in `build/06`.
- **`<gazebo>` tags** — sim-only: material colours, friction, and **sensor plugins** (LiDAR,
  IMU, camera) that make Gazebo publish `/scan`, `/imu/data`, etc. Details in `build/05`.

Keep these in separate xacro includes (`ros2_control.xacro`, `gazebo.xacro`) so the core
description stays readable and you can see exactly what's real vs sim.

---

## 6. Verifying the description

```bash
# 1. it parses and the tree is sane
xacro myrobot.urdf.xacro > /tmp/r.urdf && check_urdf /tmp/r.urdf

# 2. it looks right
ros2 launch myrobot_description display.launch.py        # RViz + robot_state_publisher + joint_state_publisher_gui

# 3. the TF tree is connected, no gaps, no duplicates
ros2 run tf2_tools view_frames                           # -> frames.pdf
ros2 run tf2_ros tf2_echo base_link laser                # a specific transform

# 4. frames match your sensor drivers
ros2 topic echo /scan --field header.frame_id --once
```

A `display.launch.py` is boilerplate worth keeping:
```python
def generate_launch_description():
    rd = {'robot_description': Command(['xacro ', <path to xacro>])}
    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher', parameters=[rd]),
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui'),
        Node(package='rviz2', executable='rviz2', arguments=['-d', <path to .rviz>]),
    ])
```

---

## 7. Common mistakes

- **Wrong `<axis>` or `rpy` on a wheel joint** → wheels spin the wrong way, robot arcs or
  spins in place. Check with `joint_state_publisher_gui` sliders before blaming the controller.
- **Missing/zero `<inertial>`** → Gazebo model explodes, sinks through the floor, or won't
  move. Every link needs mass + a non-degenerate inertia tensor.
- **Collision mesh = visual mesh (high-poly)** → simulation crawls. Use primitives or a
  decimated hull for `<collision>`.
- **Sensor `frame_id` in the driver ≠ link name in URDF** → TF lookups fail, LiDAR points
  render in the wrong place.
- **`base_footprint` vs `base_link` confusion** — pick one as the controller/EKF child
  frame and be consistent across every YAML (`ekf.yaml`, `nav2_params.yaml`, AMCL).
- **Pre-expanding xacro and committing the `.urdf`** — then editing the `.xacro` and
  forgetting to regenerate. Run xacro at launch time instead.

---

Next: `05-simulation-gazebo.md`.
