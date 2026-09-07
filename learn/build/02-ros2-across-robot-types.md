# 02 — How ROS 2 is used across different robot types

`../foundations/02-ros2-concepts.md` teaches the ROS 2 mechanics (nodes/topics/services, `colcon`,
`rclpy`) and `01-three-bots-architecture.md` shows the *full* autonomy stack in detail — but
only for one robot class: wheeled mobile bases (AMRs). This file is the "zoom out" — the
same nodes/topics/services machinery gets reused for completely different kinds of robots
(a fixed-base robotic arm, a legged robot, a drone), by swapping out which packages,
messages, and control patterns you plug into it. Nothing here is specific to BeetleBot,
Acrux or JetBot — it's the general map you'll need the moment a lab, project, or job asks
you to work on something that isn't a wheeled AMR.

---

## 1. The one thing that doesn't change: the ROS 2 core

No matter what the robot's body looks like, every ROS 2 robot uses the same primitives from
`../foundations/02-ros2-concepts.md` §1: nodes, topics, services, actions, parameters, TF, `colcon`
workspaces. What changes between robot types is:

1. **What message types flow on the topics** (a `Twist` for a wheeled base means
   nothing to a 6-DOF arm — it needs `JointState`/`JointTrajectory` instead).
2. **What the control-loop abstraction is** (a custom bridge node like `lyra_bridge` for a
   mobile base vs the standardized `ros2_control` framework for almost everything else).
3. **What the "high-level brain" package is** (Nav2 for driving to a place; MoveIt 2 for
   moving an end-effector to a pose; nothing standardized yet for legs/multirotors — those
   use robot-specific or research packages).
4. **What "SLAM"/"localization"/"obstacle avoidance" even mean** — those words assume a
   robot moving through open space; an arm bolted to a table has no localization problem at
   all, and "obstacle avoidance" means something geometrically different (avoid the arm
   hitting *itself* or the table, not "avoid the wall while driving").

Keep that framing in mind through the rest of this file: same tools, different job.

---

## 2. Mobile base / AMR (what you already know)

This is BeetleBot/Acrux, and it's the pattern most ROS 2 tutorials assume by default.

| Layer | Package/concept | Purpose |
|---|---|---|
| Command input | `geometry_msgs/Twist` on `/cmd_vel` | "move at this linear + angular velocity" — one message covers the whole body since a wheeled base has one pose (x, y, yaw) to control |
| Low-level control | a custom bridge (`lyra_bridge`) or `ros2_control` `diff_drive_controller` | converts `Twist` → per-wheel velocities → motor driver |
| State estimate | `robot_localization` EKF + AMCL | fuses odometry/IMU, localizes on a map (`01` §5.1) |
| Environment model | SLAM Toolbox/Cartographer building `nav_msgs/OccupancyGrid`, then Nav2 costmaps | 2D grid of the room, inflated around obstacles (`01` §5.2/5.3) |
| High-level goal | Nav2 (`bt_navigator` + planner + controller) | "go to this (x, y, yaw) pose without hitting anything" (`01` §5.4) |
| Typical sensors | 2D LiDAR, wheel encoders, IMU, sometimes a depth camera | cheap, sufficient for 2D navigation in a mostly-flat environment |

The defining trait: the robot's **whole body moves as one rigid thing** through a
**2D (or occasionally 3D, e.g. drones) environment**, so the problem is fundamentally
"where am I, where do I want to be, what's in the way" — localization + mapping +
path planning. This is exactly what `01` walks through in depth.

---

## 3. Robotic arm / manipulator

A completely different problem: the base doesn't move — a chain of rotating/sliding
**joints** does, and the goal is usually "put the end-effector (gripper/tool) at this pose,"
not "go to this place."

| Layer | Package/concept | Purpose |
|---|---|---|
| Body model | URDF/xacro with a **kinematic chain** of `<joint>` elements (revolute/prismatic), each with limits (`<limit lower=".." upper=".." effort=".." velocity="..">`) | describes the arm's links and how each joint moves relative to the next — this *is* the arm's kinematics, machine-readable |
| Control framework | **`ros2_control`** — a hardware-abstraction layer (`ControllerManager` + a `hardware_interface` plugin per real/simulated arm) | standardizes "read joint positions in, write joint effort/velocity/position commands out" regardless of which actual servo/driver board is underneath — this replaces the bespoke `lyra_bridge`-style approach an AMR uses |
| Low-level controller | `joint_trajectory_controller` (a `ros2_control` controller) subscribing `trajectory_msgs/JointTrajectory` | takes a **time-stamped sequence of joint-angle waypoints** and interpolates/executes it smoothly across all joints in sync — the arm's equivalent of `/cmd_vel`, except it's a whole trajectory, not one instantaneous velocity |
| State feedback | `sensor_msgs/JointState` on `/joint_states` (position, velocity, effort per joint) | published by `ros2_control` from encoders — the arm's equivalent of odometry, but per-joint instead of one body pose |
| Kinematics | forward kinematics (joint angles → end-effector pose) computed from the URDF chain; inverse kinematics (desired end-effector pose → joint angles) solved by a plugin (e.g. **KDL**, **TRAC-IK**, or a robot-specific analytic solver) | this is the arm's real equivalent of an AMR's "localization" — instead of asking "where is my whole body," you ask "what joint angles put my hand exactly here" |
| High-level goal & planning | **MoveIt 2** — the arm-world's Nav2 equivalent | given a target end-effector pose (or joint goal), builds a **planning scene** (the arm's URDF + any known obstacles, e.g. a table or a box from a depth camera), runs a motion planner (commonly **OMPL** sampling-based planners) to find a joint-space path that reaches the goal **without the arm colliding with itself or the environment**, then hands the resulting trajectory to `joint_trajectory_controller` to execute |
| "Obstacle avoidance" here means | keeping the *entire arm body* — not just the end-effector — collision-free against a **planning scene** (self-collision + known obstacles), computed once per motion plan, not a continuous reactive loop like a LiDAR-based AMR | this is the single biggest conceptual difference from §2: an AMR reacts moment-to-moment to a LiDAR scan; an arm plans an entire collision-free path *before* it moves at all, in joint space |
| Typical sensors | joint encoders (mandatory), sometimes a wrist-mounted or fixed depth camera / RGB-D for visual servoing or picking | no LiDAR, no 2D occupancy grid — the "environment" is usually a static or slowly-changing 3D scene near the arm, not a whole room to navigate |
| Gripper/end-effector | `control_msgs/GripperCommand` action, or a dedicated gripper driver package | closing/opening the tool at the end of a planned motion |

**Direct comparison to what you already studied:**

| Question | AMR answer (BeetleBot) | Arm answer |
|---|---|---|
| "Where am I / what's my state?" | EKF + AMCL → one (x, y, yaw) pose | `/joint_states` → N joint angles; forward kinematics derives end-effector pose from those |
| "How do I command motion?" | `Twist` velocity on `/cmd_vel` | `JointTrajectory` (a planned sequence of joint waypoints) via `joint_trajectory_controller` |
| "How do I reach a goal without hitting anything?" | Nav2: costmap + global planner + local controller, **continuously reactive** | MoveIt 2: planning scene + sampling-based planner, **plans once, then executes** (re-plans only if the scene changes or execution fails) |
| "What does the map look like?" | 2D occupancy grid of a room | a 3D "planning scene" — the arm's own geometry plus a handful of known/sensed obstacle shapes, not a whole explored environment |
| Real-time control | a bridge node/firmware doing PID at a fixed rate (BeetleBot: 20 Hz on the STM32) | `ros2_control`'s hardware interface + the arm's own joint-level servo firmware/drivers doing position/velocity/effort control |

A minimal ROS 2 arm stack, in the same "what talks to what" shape as `01` §5.5's diagram:

```
   MoveIt 2 (planning scene + OMPL planner)
        │  computes a collision-free JointTrajectory
        v
   joint_trajectory_controller (ros2_control)
        │  interpolates + sends per-joint commands
        v
   hardware_interface (ros2_control plugin: real servo driver, or a simulator)
        │
        v
   physical joints  ──> /joint_states (feedback, closes the loop back to MoveIt/RViz)
```

---

## 4. A quick tour of other robot classes

You won't need these in depth for this lab, but knowing the shape of each helps you
recognize what kind of problem you're looking at when you meet one later.

| Robot class | What's different from an AMR | Typical ROS 2 packages |
|---|---|---|
| **Legged robot** (quadruped/biped) | The body's pose depends on a **gait** (a coordinated joint-angle pattern per leg over time) just to stand/walk at all, before any navigation happens; balance is a real-time control problem, not just "spin the wheels" | `ros2_control` per-joint (like an arm, but many chains at once), a gait/whole-body controller (often robot-specific, e.g. Unitree/ANYbotics stacks, or research frameworks like `champ`), then Nav2 can sit *on top* once a velocity-command interface exists, same as an AMR |
| **Aerial (drone/MAV)** | Moves in full 3D (x, y, z, roll, pitch, yaw) with no wheels touching the ground — "localization" needs 3D pose estimation (often GPS + IMU + visual-inertial odometry), and "navigation" has to reason about a 3D volume, not a 2D grid | `mavros`/`mavlink` bridges to a flight controller (PX4/ArduPilot) which does the actual real-time attitude/rate control — analogous to BeetleBot's STM32 doing PID that ROS never touches directly; higher-level planning uses 3D costmaps (e.g. `octomap`) instead of Nav2's 2D grid |
| **Multi-robot systems** | Not a different body — the same node/topic/service model, but multiplied: each robot runs its own graph, usually under its own **namespace** (`/robot1/cmd_vel`, `/robot2/cmd_vel`) and/or its own `ROS_DOMAIN_ID`, with a shared layer (fleet manager, shared map, or `actionlib`-style task allocation) coordinating them | namespacing + remapping (the same `-r`/`-p` args from `../foundations/02-ros2-concepts.md` §2, just applied per-robot at scale), domain bridges when robots must cross domain IDs |

---

## 5. So which of this repo's tools carry over, and to what?

- **`rclpy`/node anatomy, `colcon`, topics/services/actions, TF, launch files** (`foundations/02`) —
  100% the same regardless of robot type. This is the actual transferable skill.
- **`robot_localization`'s EKF pattern** (fuse multiple noisy sensors into one state
  estimate, publish TF) — reused conceptually for a drone's visual-inertial odometry, not
  just wheeled odometry; the *math* (Kalman filtering) is the same, only the sensor topics
  fed in change.
- **Nav2** — specific to bodies that move through a traversable 2D-ish space: AMRs,
  and (with 3D costmap extensions) some legged/aerial robots. **Not** used for arms.
- **MoveIt 2** — specific to fixed-base or mobile manipulators (an arm, possibly mounted on
  an AMR — "mobile manipulation" combines both stacks: Nav2 drives the base, MoveIt 2 moves
  the arm, and they're two separate node graphs cooperating over shared TF).
- **`ros2_control`** — the one framework that generalizes best: it's used for AMR wheel
  controllers, arm joint controllers, and legged-robot joint controllers alike. If you only
  learn one "how do I control actual hardware from ROS 2" abstraction beyond what
  `lyra_bridge` shows you, make it this one.

Cross-links: `../foundations/02-ros2-concepts.md` (the ROS 2 mechanics all of the above
assumes), `01-three-bots-architecture.md` (the full worked example of the AMR pattern from
§2 above, in three real robots), `03-build-a-ros2-autonomy-stack.md` onward (how to build
the AMR stack layer by layer — `06` control also covers the `ros2_control` +
`joint_trajectory_controller` path used by arms and legged robots).

Next: `03-build-a-ros2-autonomy-stack.md`.
