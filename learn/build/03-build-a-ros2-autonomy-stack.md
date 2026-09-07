# 03 — Building a ROS 2 autonomy stack (the spine)

This is the map. `01-three-bots-architecture.md` showed three finished stacks;
`02-ros2-across-robot-types.md` showed the pattern on non-AMR robots. This file is **how you
build one yourself**, for a robot that doesn't exist yet — the order to do things in, the
package layout, and where each of `04`–`08` plugs in.

Assumes you've done **Foundations** (`../foundations/01`, `../foundations/02`,
`../foundations/04`). Target: a wheeled mobile robot that can localize, map, and navigate to
a goal. Arms/drones diverge at the control + planning layers — `02-ros2-across-robot-types.md`
§3–4 for those.

---

## 1. The stack, in layers

Every AMR autonomy stack is the same seven layers. Data flows **up** (sensors → decisions)
and commands flow **down**.

```
         ┌─────────────────────────────────────────────┐
   (7)   │  MISSION / GOAL     "go to the kitchen"      │   RViz goal, waypoint follower, BT
         ├─────────────────────────────────────────────┤
   (6)   │  NAVIGATION (Nav2)  global plan + local ctrl │   planner_server, controller_server → build/08
         ├─────────────────────────────────────────────┤
   (5)   │  WORLD MODEL        map + costmaps           │   SLAM (build/07) or a saved map + costmap layers
         ├─────────────────────────────────────────────┤
   (4)   │  LOCALIZATION       "where am I" (map→odom,  │   robot_localization EKF + AMCL → build/07
         │                     odom→base_link)         │
         ├─────────────────────────────────────────────┤
   (3)   │  CONTROL            Twist → wheel commands   │   ros2_control diff_drive, or a bridge → build/06
         ├─────────────────────────────────────────────┤
   (2)   │  DESCRIPTION        URDF: frames, geometry   │   robot_state_publisher → build/04
         ├─────────────────────────────────────────────┤
   (1)   │  HARDWARE / SIM     motors, encoders, LiDAR, │   real drivers + micro-ROS/MCU, or Gazebo → build/05
         │                     IMU  (or their sim twins)│
         └─────────────────────────────────────────────┘
```

You build **bottom-up**, and you build **in simulation first** (layer 1 = Gazebo), because
every layer above only needs the *interface* of the layer below — `/scan`, `/odom`, `/tf`,
`/cmd_vel` — and Gazebo provides those identically to real hardware. Swapping sim for real
is then a launch-argument change, not a rewrite. This is the repo's "dev machine first,
hardware last" rule (`CLAUDE-COMMON.md`) applied to robotics.

---

## 2. Step 0 — decisions that cascade

Pin these before writing code; each one determines packages and message types downstream:

| Decision | Options | Cascades into |
|---|---|---|
| **Drive kinematics** | differential / skid-steer / ackermann / mecanum / omni | which `ros2_control` controller; the odometry math; whether `angular.z` alone can turn it |
| **Compute** | Pi / Jetson / NUC / x86 | ROS 2 distro (= Ubuntu version, `../foundations/04` §1), whether you can run Nav2 + SLAM together |
| **Real-time controller** | MCU over serial / micro-ROS / `ros2_control` hardware interface direct | layer 3 design (`build/06`) |
| **Primary sensor** | 2D LiDAR / 3D LiDAR / depth camera / stereo | SLAM choice, costmap sources, whether you need `pointcloud_to_laserscan` |
| **Localization aids** | wheel encoders / IMU / GPS / wheel + IMU | EKF config (`build/07`); outdoor vs indoor |
| **Map** | build with SLAM / provided / none (reactive only) | layer 5; whether you run AMCL |

Write them into a `README` in your robot repo. BeetleBot's answers: skid-steer, Pi 5, STM32
over UART, RPLiDAR C1, wheel+IMU, SLAM Toolbox — see how each shows up in `01` §2.

---

## 3. Step 1 — workspace and package layout

One workspace, several small packages (one concern each — mirrors BeetleBot's `lyra_ws`,
`01` §2):

```
~/ros2_ws/src/myrobot/
├── myrobot_interfaces/     # custom .msg/.srv/.action ONLY (ament_cmake) — foundations/02 §13
├── myrobot_description/    # URDF/xacro, meshes, RViz configs — no nodes            build/04
├── myrobot_bringup/        # launch files + top-level params — the entry points     §8
├── myrobot_control/        # ros2_control config, or the hardware bridge node       build/06
├── myrobot_localization/   # EKF config, wheel-odometry node if you write one       build/07
├── myrobot_slam/           # slam_toolbox launch + params                           build/07
├── myrobot_navigation/     # Nav2 params + launch, saved maps                       build/08
└── myrobot_gazebo/         # world files, sim launch, sim-specific params           build/05
```

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
ros2 pkg create --build-type ament_cmake  myrobot_interfaces
ros2 pkg create --build-type ament_python myrobot_bringup --dependencies rclpy
# ...one per package. description/slam/navigation are often launch+config only (ament_cmake, no code).
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install && source install/setup.bash
```

`--symlink-install` = edits to Python / config / launch take effect without rebuilding.

---

## 4. Step 2 — description (`build/04`)

Write `myrobot_description/urdf/myrobot.urdf.xacro`: one `<link>` per rigid body (base,
wheels, LiDAR, IMU), one `<joint>` connecting each (continuous for wheels, fixed for
sensors). This gives you:

- the **static TF** (`base_link → laser`, `base_link → imu_link`, …) via
  `robot_state_publisher`,
- collision/inertial data Gazebo and Nav2 need,
- a `<ros2_control>` block declaring the command/state interfaces (Step 4).

Verify: `ros2 launch myrobot_description display.launch.py` → RViz shows the robot;
`ros2 run tf2_tools view_frames` → the tree is connected with no gaps.

---

## 5. Step 3 — simulation (`build/05`)

Spawn the URDF into Gazebo with a world file. Add Gazebo sensor plugins so the sim
publishes the **same topics real hardware would**: `/scan`, `/imu/data`, `/camera/image_raw`,
and wheel `joint_states`. Add the `gz_ros2_control` plugin so `ros2_control` (Step 4) drives
the simulated wheels.

Everything from here up is developed against the sim. The contract every higher layer
depends on:

| Topic / TF | Provided by (sim) | Provided by (real) |
|---|---|---|
| `/scan` | Gazebo LiDAR plugin | `sllidar_ros2` / driver |
| `/imu/data` | Gazebo IMU plugin | IMU driver / MCU telemetry |
| `/joint_states`, wheel odom | `gz_ros2_control` | `ros2_control` + encoder hardware interface |
| `odom → base_link` TF | (from odometry, Step 5) | same |
| `/cmd_vel` in | your teleop / Nav2 | same |

Set `use_sim_time:=true` everywhere in sim so nodes use Gazebo's clock (`/clock`).

---

## 6. Step 4 — control (`build/06`)

Turn a `geometry_msgs/Twist` on `/cmd_vel` into actual wheel motion.

- **Standard path:** `ros2_control` with `diff_drive_controller` (or `ackermann_*`,
  `mecanum_*`). It reads your URDF's `<ros2_control>` interfaces, does the inverse
  kinematics, publishes `/odom` + the `odom → base_link` TF from wheel encoders, and
  subscribes `/cmd_vel`. Config is one YAML; you write **no code** for a standard drive.
- **Custom hardware:** write a `hardware_interface` plugin (C++) that talks to your motor
  driver — or, like BeetleBot, run a **bridge node** that sends desired wheel velocities to
  an MCU over serial and the MCU does the real-time PID (`01` §2). micro-ROS is the middle
  ground — the MCU becomes a ROS 2 node.

Verify: `ros2 run teleop_twist_keyboard teleop_twist_keyboard` drives the robot (in sim),
`/odom` updates, `ros2 run tf2_ros tf2_echo odom base_link` moves.

---

## 7. Step 5 — localization (`build/07`)

Wheel odometry alone drifts. Fuse it:

- **`robot_localization` `ekf_node`** — fuses wheel `/odom` + `/imu/data` into
  `/odometry/filtered` and broadcasts a smooth **`odom → base_link`** TF. One YAML
  (`ekf.yaml`) selects which fields of each source to trust (wheels for x/y, IMU for yaw).
- Once you have a map (Step 6), **AMCL** (`nav2_amcl`) adds the **`map → odom`** correction
  so you don't drift unboundedly.

Together: `map → odom → base_link`. Every layer above reasons in TF frames, so this chain
must be unbroken and have exactly one publisher per edge (`foundations/02` §12).

---

## 8. Step 6 — mapping (`build/07`)

Run **`slam_toolbox`** in mapping mode: it consumes `/scan` + `/odometry/filtered`,
publishes `/map` and the `map → odom` TF (replacing AMCL while mapping). Drive the robot
around slowly; watch `/map` fill in RViz. Save:
```bash
ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/src/myrobot_navigation/maps/my_map
```
→ `.pgm` + `.yaml`. In navigation mode you load this map and switch to AMCL.

---

## 9. Step 7 — navigation (`build/08`)

Bring up **Nav2** (`nav2_bringup` + your `nav2_params.yaml`): `map_server` + `amcl` +
`planner_server` + `controller_server` + `bt_navigator` + `behavior_server` + the two
costmaps. Set a "2D Pose Estimate" then a "Nav2 Goal" in RViz; the robot plans a path and
drives it, avoiding obstacles the LiDAR sees. Tuning `nav2_params.yaml` (costmap layers,
planner, controller, tolerances) is most of the work — `build/08`.

---

## 10. Step 8 — bringup composition

`myrobot_bringup/launch/robot.launch.py` is the one command an operator runs. It:

- `IncludeLaunchDescription`s the smaller launch files (description, control, localization,
  and — by argument — slam **or** navigation),
- passes a consistent `use_sim_time` and namespace through all of them,
- loads each node's params YAML from `myrobot_bringup/config/`.

```bash
ros2 launch myrobot_bringup robot.launch.py use_sim_time:=true mode:=slam
ros2 launch myrobot_bringup robot.launch.py use_sim_time:=true mode:=nav map:=.../my_map.yaml
```
Pattern and mechanics: `foundations/02` §14, worked example `01` §2 (`lyra_bringup`).

---

## 11. Step 9 — sim → real

What actually changes when you move onto hardware:

| Concern | Sim | Real |
|---|---|---|
| Clock | `use_sim_time:=true`, Gazebo `/clock` | `use_sim_time:=false` (system clock) |
| Layer 1 | Gazebo plugins | real sensor drivers + `ros2_control` hardware interface / MCU bridge |
| Device names | n/a | `udev` rules → `/dev/rplidar`, `/dev/imu` (`../foundations/01` §12) |
| Autostart | you launch by hand | `systemd` service (`../foundations/01` §11) |
| Networking | one machine | PC ↔ robot, same `ROS_DOMAIN_ID`, DDS discovery (`../foundations/01` §9) |
| Tuning | approximate | re-tune EKF noise, costmap inflation, controller gains against real dynamics |

Layers 2–7 (description, localization, SLAM, Nav2) are **identical** — that's the payoff of
building against interfaces.

---

## 12. Dependency order — what blocks what

```
description ──> everything (frames + geometry)
   │
   ├──> simulation ──> control ──> localization ──> SLAM ──> navigation ──> mission
   │                       │            │
   └────── control needs description's <ros2_control> block
                           │
             localization needs control's wheel /odom + the description's odom frame
                                        │
                          SLAM needs localization's /odometry/filtered + /scan
                                                     │
                                    navigation needs a map (from SLAM) + AMCL + costmaps
```

Skipping ahead fails loudly: Nav2 with no `map → odom` TF just says "waiting for
transform"; SLAM with bad odometry produces a smeared map; control with a wrong URDF joint
axis drives in circles.

---

## 13. First-project checklist

- [ ] Step 0 decisions written down
- [ ] Workspace builds clean, `rosdep` satisfied
- [ ] `view_frames` shows a connected TF tree, no duplicate edges
- [ ] Robot spawns in Gazebo; `/scan`, `/imu/data`, `/joint_states` publish
- [ ] Teleop drives it; `/odom` and `odom→base_link` track motion
- [ ] EKF publishes `/odometry/filtered`; TF still single-publisher per edge
- [ ] SLAM builds a usable map; saved to disk
- [ ] Nav2 comes up all-active (`ros2 lifecycle` / RViz); goal → plan → drive works
- [ ] One `bringup` launch does all of it with `use_sim_time` + `mode` args
- [ ] Same launch runs on real hardware with `use_sim_time:=false` and real drivers

---

## 14. Common first-project mistakes

- **Building on hardware from day one.** Sim first — you'll iterate 10× faster and not chase
  a wheel while debugging a TF typo.
- **One giant package.** Split by concern (Step 1); it's much easier to reason about and reuse.
- **Custom messages when a standard one exists.** Use `geometry_msgs`, `sensor_msgs`,
  `nav_msgs` — only make a `_interfaces` package for genuinely robot-specific data.
- **Two nodes publishing the same TF edge** — the tree flickers, everything downstream jitters.
- **Forgetting `use_sim_time`** on one node — its timestamps disagree with the rest, TF
  lookups fail with extrapolation errors.
- **QoS mismatch on `/scan` or `/map`** — subscriber gets nothing, no error (`foundations/02` §7).
- **Tuning Nav2 before localization is solid.** If AMCL/EKF is wrong, no controller gain
  will save you. Fix layers bottom-up.

---

Next: `04-robot-description-and-tf.md`, then `05` (sim), `06` (control), `07` (localization
& SLAM), `08` (navigation).
