# 08 — Navigation and path planning (Nav2)

Layers 6–7 (`03` §9). `01-three-bots-architecture.md` §5.3–5.4 walks the Nav2 pipeline with
BeetleBot's real params. This file is the **builder's reference**: the architecture, every
plugin slot and the common choices, how to tune `nav2_params.yaml`, and how to send goals.

---

## 1. What Nav2 is

Not one node — a set of **lifecycle servers** (`../foundations/02-ros2-concepts.md` §9)
orchestrated by a **behavior tree**. You send a goal pose; the BT calls the planner for a
path, the controller to follow it, and recovery behaviors when stuck.

```
  goal (NavigateToPose action)
        │
        ▼
  ┌─────────────┐   path    ┌──────────────────┐   /cmd_vel   ┌───────────────┐
  │ bt_navigator │◄────────►│ planner_server    │             │ controller_    │──►
  │  runs the BT │           │ (global path on   │             │ server         │
  │              │◄────────► │  global costmap)  │             │ (follow path,  │
  │              │           └──────────────────┘             │  local costmap)│
  │              │◄────────► ┌──────────────────┐             └───────────────┘
  │              │           │ behavior_server   │  spin / backup / wait / drive_on_heading
  │              │           └──────────────────┘
  └─────────────┘◄────────► smoother_server, waypoint_follower, velocity_smoother
        ▲
        │ map→odom→base_link TF (build/07)   +   /scan   +   the saved map
```

`lifecycle_manager` brings all servers `configure`→`activate` together (and is why "Nav2 is
up but does nothing" usually means a server didn't activate — check `ros2 lifecycle get`).

---

## 2. Costmaps

A costmap is an occupancy grid where each cell has a cost `0–254` (254 = lethal). Nav2 runs
**two**:

| | Global costmap | Local costmap |
|---|---|---|
| Size | whole map | small window (e.g. 5×5 m), `rolling_window: true` |
| Frame | `map` | `odom` |
| Update rate | ~1 Hz | ~5–10 Hz |
| Used by | planner_server | controller_server |
| Purpose | plan a full route around known obstacles | react to obstacles *now*, incl. ones not on the map |

### Layers (plugins, composited bottom-up)

| Layer | Does | Key params |
|---|---|---|
| `static_layer` | loads the saved map's occupied/free cells | `map_topic` |
| `obstacle_layer` | marks cells hit by `/scan` as lethal; **clears** cells the beam passed through | `observation_sources`, `max_obstacle_height`, `raytrace_max_range`, `obstacle_max_range` |
| `voxel_layer` | 3D version of obstacle_layer for depth cameras / 3D LiDAR | `z_resolution`, `mark_threshold` |
| `inflation_layer` | spreads cost outward from lethal cells so paths keep clearance | `inflation_radius`, `cost_scaling_factor` |

```yaml
local_costmap:
  local_costmap:
    ros__parameters:
      update_frequency: 10.0
      publish_frequency: 5.0
      global_frame: odom
      robot_base_frame: base_link
      rolling_window: true
      width: 5
      height: 5
      resolution: 0.05
      robot_radius: 0.18                    # or a footprint polygon
      plugins: ["obstacle_layer", "inflation_layer"]
      obstacle_layer:
        plugin: nav2_costmap_2d::ObstacleLayer
        observation_sources: scan
        scan:
          topic: /scan
          max_obstacle_height: 2.0
          clearing: true
          marking: true
          data_type: "LaserScan"
          raytrace_max_range: 12.0
          obstacle_max_range: 8.0
      inflation_layer:
        plugin: nav2_costmap_2d::InflationLayer
        inflation_radius: 0.55
        cost_scaling_factor: 3.0
```

**Tuning intuition:** `inflation_radius` ≈ how far from walls you want the robot to stay
(too big → can't fit through doors; too small → clips corners). `cost_scaling_factor` shapes
how sharply cost decays (higher = hugs the inflation edge less). `robot_radius`/footprint
must be honest or the planner routes through gaps the robot can't take.

---

## 3. Global planners (`planner_server`)

| Plugin | Algorithm | Use for |
|---|---|---|
| `NavfnPlanner` | Dijkstra (or A* with `use_astar: true`) on a grid | differential/omni robots; fast, simple, the default |
| `SmacPlanner2D` | A* on a grid, smoothed | like Navfn, better paths |
| `SmacPlannerHybrid` | Hybrid-A* with motion primitives, respects a turning radius | **ackermann / car-like**, tight spaces |
| `SmacPlannerLattice` | State-lattice with precomputed feasible motions | non-circular robots, kinematically-constrained |
| `ThetaStarPlanner` | any-angle A* | shorter, less zig-zag paths on open maps |

```yaml
planner_server:
  ros__parameters:
    planner_plugins: ["GridBased"]
    GridBased:
      plugin: nav2_navfn_planner/NavfnPlanner
      tolerance: 0.5
      use_astar: false
      allow_unknown: true          # plan through not-yet-mapped cells (useful mid-SLAM)
```

---

## 4. Controllers / local planners (`controller_server`)

Turns "follow this path" into `/cmd_vel`, checking the local costmap every cycle.

| Plugin | Idea | Good for | Notes |
|---|---|---|---|
| `DWBLocalPlanner` (DWA) | sample velocities, score trajectories by weighted critics | differential/omni, dynamic obstacles | many critics to tune; flexible |
| `RegulatedPurePursuit` (RPP) | chase a lookahead "carrot" on the path, slow down for curves/obstacles | differential, predictable following | few params, robust — BeetleBot's choice |
| `MPPI` | sampling-based model-predictive control | smooth, high-quality, dynamic | heavier CPU; the modern default where compute allows |
| `RotationShimController` | rotate to face the path, then hand off | wrap around another controller to fix "drives off sideways at start" |
| `GracefulController` | smooth pose-following control law | differential, docking-style precision | |

```yaml
controller_server:
  ros__parameters:
    controller_frequency: 20.0
    controller_plugins: ["FollowPath"]
    FollowPath:
      plugin: nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController
      desired_linear_vel: 0.5
      lookahead_dist: 0.6
      min_lookahead_dist: 0.3
      max_lookahead_dist: 0.9
      use_regulated_linear_velocity_scaling: true
      regulated_linear_scaling_min_radius: 0.9
      max_allowed_time_to_collision_up_to_carrot: 1.0
    # progress + goal checkers:
    progress_checker:
      plugin: nav2_controller::SimpleProgressChecker
      required_movement_radius: 0.5
      movement_time_allowance: 10.0
    goal_checker:
      plugin: nav2_controller::SimpleGoalChecker
      xy_goal_tolerance: 0.15
      yaw_goal_tolerance: 0.2
```

Match the controller to the drivetrain: RPP/DWB/MPPI for differential; for ackermann use a
controller that respects the turning radius (and `SmacPlannerHybrid` above).

---

## 5. The behavior tree (`bt_navigator`)

The BT is an XML file wiring together "compute path", "follow path", and recovery actions
with fallback/retry logic. The **default BT** (`navigate_to_pose_w_replanning_and_recovery.xml`)
does: plan → follow, replan every 1 s, and on failure run recoveries (clear costmaps →
spin → wait → backup) before retrying or aborting.

- Customize by pointing `default_nav_to_pose_bt_xml` at your own file.
- **Groot2** visualizes/edits BTs live.
- `NavigateThroughPoses` is the multi-waypoint variant.

### Recovery behaviors (`behavior_server`)

`spin` (rotate in place to clear the costmap / escape), `backup` (reverse a set distance),
`drive_on_heading`, `wait`, `assisted_teleop`. Tune distances/speeds conservatively — a
recovery that reverses 1 m into an unseen obstacle is worse than the stuck condition.

---

## 6. Bringing Nav2 up

```python
IncludeLaunchDescription(<nav2_bringup bringup_launch.py>, launch_arguments={
    'use_sim_time': use_sim,
    'params_file': <myrobot_navigation/config/nav2_params.yaml>,
    'map': <maps/my_map.yaml>,            # omit + 'slam': 'True' to map instead
    'autostart': 'True',
}.items())
```

`nav2_params.yaml` is one big file with a top-level key per server
(`amcl:`, `planner_server:`, `controller_server:`, `bt_navigator:`, `local_costmap:`,
`global_costmap:`, `behavior_server:`, `waypoint_follower:`, `velocity_smoother:`). Start
from `nav2_bringup`'s template and change only what you need.

```bash
ros2 lifecycle get /bt_navigator            # all servers should be 'active'
ros2 topic echo /plan --once                 # a path appears after a goal
```

---

## 7. Sending goals

- **RViz:** "2D Pose Estimate" (tell AMCL where you are), then "Nav2 Goal".
- **CLI:**
  ```bash
  ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
    "{pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: 1.0}, orientation: {w: 1.0}}}}"
  ```
- **Python** (`nav2_simple_commander` — the clean API):
  ```python
  from nav2_simple_commander.robot_navigator import BasicNavigator
  nav = BasicNavigator()
  nav.waitUntilNav2Active()
  nav.goToPose(make_pose(2.0, 1.0, 0.0))
  while not nav.isTaskComplete():
      fb = nav.getFeedback()          # distance remaining, ETA
  print(nav.getResult())
  ```
- **Waypoints:** `nav.followWaypoints([p1, p2, p3])`, or the `waypoint_follower` server with
  task executors at each stop.

---

## 8. Tuning workflow and failure modes

Localization must be solid first (`build/07` §7). Then:

1. **Costmaps look right in RViz** — static layer matches the map; obstacle layer lights up
   on real obstacles and clears when they move; inflation isn't swallowing doorways.
2. **Global path is sane** — not hugging walls, not cutting corners, exists at all
   (`/plan`). Bad → `robot_radius`/inflation, or `allow_unknown`.
3. **Controller follows without weaving/stalling** — tune `lookahead_dist` (RPP) or critic
   weights (DWB) or `desired_linear_vel`. Oscillation near goal → goal checker tolerances /
   `RotationShim`.
4. **Recoveries don't make things worse** — cap backup distance and spin speed.

| Symptom | Likely cause |
|---|---|
| "Nav2 up, goal does nothing" | a server not `active` (`ros2 lifecycle get`), or no `map→base_link` TF |
| Robot spins forever at start | needs `RotationShimController`, or goal-checker yaw tolerance too tight |
| Plans through walls | `static_layer` not loaded / wrong `map_topic`; costmap `global_frame` mismatch |
| Refuses to enter a room | `inflation_radius` too big for the doorway; footprint too large |
| Weaves down straight corridors | DWB critic weights, or RPP `lookahead_dist` too short |
| Stops far from obstacles | `inflation_radius` / `cost_scaling_factor`, or controller collision-time param |
| "Costmap doesn't update" | `use_sim_time` mismatch, `/scan` QoS mismatch (`foundations/02` §7), or observation source topic wrong |

---

## 9. Path planning beyond Nav2

Nav2's planner and controller slots are **`pluginlib` interfaces** — you can drop in your
own:

- **Global planner plugin:** implement `nav2_core::GlobalPlanner` (`configure`, `activate`,
  `createPlan(start, goal) -> nav_msgs/Path`). This is where a custom search (RRT*, D* Lite,
  a lattice for your kinematics, a learned planner) goes.
- **Controller plugin:** implement `nav2_core::Controller`
  (`computeVelocityCommands(pose, velocity) -> TwistStamped`).

For arms/drones the planning problem is different (`02-ros2-across-robot-types.md` §3–4): MoveIt 2 (OMPL sampling
planners) for manipulators; 3D planners over `octomap` for aerial. Same idea — a planner
produces a path, a controller executes it — different state space.

---

## 10. Verifying (end-to-end)

```bash
# with sim (build/05) or robot up, localization active:
ros2 launch myrobot_navigation navigation.launch.py use_sim_time:=true map:=maps/my_map.yaml
ros2 lifecycle get /bt_navigator                 # active
# RViz: set 2D Pose Estimate, then Nav2 Goal across the room
#   -> /plan shows a path, robot drives it, avoids a box you place in its way
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{...}" --feedback
```

---

That's the stack, layer 1 to layer 7. Back to the map: `03-build-a-ros2-autonomy-stack.md`
§13 (checklist). For non-AMR robots: `02-ros2-across-robot-types.md`. Full index:
`../README.md`.
