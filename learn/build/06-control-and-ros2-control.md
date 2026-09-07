# 06 — Control and `ros2_control`

Layer 3 (`03` §6). Two jobs:

1. **Command:** turn a `geometry_msgs/Twist` on `/cmd_vel` into per-actuator commands
   (wheel velocities, steering angle) and get them to the hardware.
2. **Feedback:** read encoders, compute wheel odometry, publish `/odom` +
   `odom → base_link` TF and `/joint_states`.

Everything above (localization, SLAM, Nav2) depends on those outputs and never touches the
motors directly.

---

## 1. Two approaches

| | `ros2_control` (standard) | Custom bridge node |
|---|---|---|
| When | you have a normal drivetrain and a supported motor interface | unusual hardware, an MCU that already does closed-loop control, fastest path to "it moves" |
| Code you write | usually **none** for a standard drive (config only); a C++ hardware plugin if the interface is custom | one node (Python is fine) |
| Odometry | `diff_drive_controller` computes and publishes it | you compute it (or the MCU sends it) |
| Real-time | `controller_manager` update loop, C++, can be RT-tuned | Python node = not RT; push RT to firmware |
| Examples | most modern robots, MoveIt arms, `gz_ros2_control` | **BeetleBot** `lyra_bridge` → STM32 (`01` §2), Acrux `acrux_firmware` → ESP32 |

Learn `ros2_control` — it's the transferable skill and it's what sim (`gz_ros2_control`)
and arms (`02-ros2-across-robot-types.md` §3) use. The bridge pattern is a pragmatic fallback.

---

## 2. `ros2_control` architecture

```
        /cmd_vel ──►┌────────────────────┐        ┌──────────────────────────┐
                    │ diff_drive_controller│      │ joint_state_broadcaster   │──► /joint_states
                    │  (a "controller")    │      └───────────┬──────────────┘
                    └─────────┬──────────┘  reads state       │ reads state
         /odom  ◄──────────── │           writes commands     │
   odom→base_link TF ◄──────  │                  ▼            ▼
                    ┌──────────────────────────────────────────────────┐
                    │            controller_manager                     │
                    │   loads controllers, runs the update() loop at    │
                    │   `update_rate` Hz, owns the hardware resources    │
                    └───────────────────────┬──────────────────────────┘
                                            │ claims command/state interfaces
                    ┌───────────────────────▼──────────────────────────┐
                    │   hardware_interface plugin  (a "SystemInterface")│
                    │   read()  : encoders  → state interfaces          │
                    │   write() : command interfaces → motor driver     │
                    └───────────────────────┬──────────────────────────┘
                                            ▼
                               real motor driver  /  gz_ros2_control  /  mock
```

Four concepts:

- **Command interface** — something you can write, e.g. `left_wheel_joint/velocity`.
- **State interface** — something you can read, e.g. `left_wheel_joint/position`,
  `left_wheel_joint/velocity`.
- **Hardware component** (`SystemInterface`) — a plugin that maps those interfaces to real
  I/O in `read()` / `write()`.
- **Controller** — consumes/produces interfaces on the `controller_manager` loop
  (`diff_drive_controller`, `joint_trajectory_controller`, `joint_state_broadcaster`, …).

### The `<ros2_control>` block in the URDF (`build/04` §5)

```xml
<ros2_control name="myrobot" type="system">
  <hardware>
    <!-- pick ONE -->
    <plugin>mock_components/GenericSystem</plugin>                 <!-- no hardware, echo commands to state -->
    <!-- <plugin>gz_ros2_control/GazeboSimSystem</plugin> -->      <!-- simulation -->
    <!-- <plugin>myrobot_hardware/MyRobotSystem</plugin> -->       <!-- your real plugin -->
  </hardware>
  <joint name="left_wheel_joint">
    <command_interface name="velocity"/>
    <state_interface   name="position"/>
    <state_interface   name="velocity"/>
  </joint>
  <joint name="right_wheel_joint"> ...same... </joint>
</ros2_control>
```

### `controllers.yaml`

```yaml
controller_manager:
  ros__parameters:
    update_rate: 50            # Hz — the hard real-time loop
    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster
    diff_drive_controller:
      type: diff_drive_controller/DiffDriveController

diff_drive_controller:
  ros__parameters:
    left_wheel_names:  ["left_wheel_joint"]
    right_wheel_names: ["right_wheel_joint"]
    wheel_separation: 0.34
    wheel_radius: 0.05
    publish_rate: 50.0
    odom_frame_id: odom
    base_frame_id: base_link
    enable_odom_tf: true          # <-- see §6: turn OFF if the EKF publishes odom→base_link
    use_stamped_vel: false        # subscribe /cmd_vel as Twist (true = TwistStamped)
```

---

## 3. Bringing controllers up

`controller_manager` starts with the robot; then each controller is loaded + activated by a
**spawner**:

```python
Node(package='controller_manager', executable='ros2_control_node',
     parameters=[robot_description, controllers_yaml]),

Node(package='controller_manager', executable='spawner',
     arguments=['joint_state_broadcaster']),
Node(package='controller_manager', executable='spawner',
     arguments=['diff_drive_controller']),
```
```bash
ros2 control list_hardware_interfaces      # what's available / claimed
ros2 control list_controllers             # active / inactive
ros2 control load_controller --set-state active diff_drive_controller
```

Drive it:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/diff_drive_controller/cmd_vel_unstamped
```
(or remap `/cmd_vel` → the controller's input in your launch).

### Other drive types

| Kinematics | Controller |
|---|---|
| differential / skid-steer | `diff_drive_controller` |
| car-like (front steer) | `ackermann_steering_controller` / `tricycle_controller` |
| mecanum (holonomic) | `mecanum_drive_controller` |
| arm | `joint_trajectory_controller` (`02-ros2-across-robot-types.md` §3) |
| any, raw | `forward_command_controller`, `velocity_controllers/*` |

---

## 4. Writing a hardware interface (custom motor driver)

A C++ class implementing `hardware_interface::SystemInterface`. The skeleton:

```cpp
class MyRobotSystem : public hardware_interface::SystemInterface {
  CallbackReturn on_init(const HardwareInfo & info) override;      // parse URDF params, size buffers
  std::vector<StateInterface>   export_state_interfaces() override;   // advertise position/velocity
  std::vector<CommandInterface> export_command_interfaces() override; // advertise velocity command
  CallbackReturn on_activate(...) override;    // open the serial port / enable drivers
  CallbackReturn on_deactivate(...) override;  // stop motors, close port
  return_type read(const Time&, const Duration&) override;   // encoders -> hw_positions_/hw_velocities_
  return_type write(const Time&, const Duration&) override;  // hw_commands_ -> motor driver
};
PLUGINLIB_EXPORT_CLASS(myrobot_hardware::MyRobotSystem, hardware_interface::SystemInterface)
```

`read()` and `write()` run **every `controller_manager` tick** and must not block — do
serial I/O on a buffer, not a synchronous round-trip. Params (port, baud) come from the
URDF `<hardware><param name="...">` tags, never hard-coded (`CLAUDE-COMMON.md`
deployment rule). Package it `ament_cmake` with a `pluginlib` export XML.

---

## 5. The MCU boundary — bridge node and micro-ROS

When a microcontroller already runs the real-time loop (PID at a fixed rate in
firmware/RTOS), ROS's job is just to ship setpoints and read telemetry:

- **Serial bridge node** (BeetleBot `lyra_bridge`, `01` §2): a ROS node subscribes
  `/cmd_vel`, runs inverse kinematics, sends wheel setpoints as binary frames over UART at
  ~20 Hz, reads telemetry frames back, publishes `/odom`, `/imu/data_raw`, `/joint_states`,
  battery, and the arm/disarm services. A software deadman zeros the command if `/cmd_vel`
  goes stale. The MCU's watchdog independently fails safe if the heartbeat stops.
- **micro-ROS** — the MCU runs an actual ROS 2 node (over serial or UDP via a micro-ROS
  agent on the host). No custom protocol; the MCU publishes/subscribes real topics. Better
  for new designs; needs an RTOS (FreeRTOS/Zephyr) and the micro-ROS client lib.

Either way: **the real-time PID stays off Linux.** ROS gives desired velocities; firmware
closes the loop deterministically.

---

## 6. Odometry and the TF ownership question

`diff_drive_controller` (or your bridge) integrates wheel encoders into `/odom` and, if
`enable_odom_tf: true`, publishes the `odom → base_link` transform.

**But** `robot_localization`'s EKF (`build/07`) also wants to publish `odom → base_link`
(the fused wheel+IMU estimate, which is better). **Exactly one may publish that edge**
(`foundations/02` §12, `build/04` §4). Standard resolution:

- EKF in use → set `enable_odom_tf: false` on the controller; the controller still publishes
  the `/odom` *topic* (an EKF input), just not the TF.
- No EKF (wheel-only) → leave `enable_odom_tf: true`, skip `robot_localization`.

---

## 7. Verifying

```bash
ros2 control list_controllers            # joint_state_broadcaster + diff_drive_controller = active
ros2 topic echo /joint_states            # wheel positions change when you push the robot
# teleop forward:
ros2 topic echo /odom                    # pose.x increases
ros2 run tf2_ros tf2_echo odom base_link # translation tracks motion
# spin in place: odom yaw changes, x/y roughly constant
```
Sanity check the scale: drive a measured 1.0 m, check `/odom` says ~1.0 m. If it's off by a
constant factor, `wheel_radius` or `wheel_separation` is wrong.

---

## 8. Common mistakes

- **Both the controller and the EKF publishing `odom → base_link`** → TF flicker, Nav2
  jitter. Pick one (§6).
- **`wheel_separation` / `wheel_radius` wrong** → odometry scale/rotation error; navigation
  drifts predictably.
- **Blocking I/O in `read()`/`write()`** → `controller_manager` loop overruns, jerky motion.
- **Hard-coded serial port** instead of a URDF param + `udev` name (`../foundations/01` §12).
- **Expecting deterministic motor timing from a Python node** — it won't happen; that's what
  the MCU/`ros2_control` C++ loop is for.
- **Forgetting the spawner** — `controller_manager` is up but no controller is active, so
  `/cmd_vel` does nothing and there's no obvious error.

---

Next: `07-localization-and-slam.md`.
