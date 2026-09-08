# Autonomous Navigation

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand Nav2 navigation stack architecture
* ✅ Launch full autonomous navigation system
* ✅ Send navigation goals to robot
* ✅ Monitor navigation status and progress
* ✅ Understand costmaps (global and local)
* ✅ Configure path planning and obstacle avoidance
* ✅ Tune navigation parameters for your environment
* ✅ Handle navigation failures gracefully
* ✅ Create autonomous navigation missions

#### ⏱️ Time Required

* **Reading & Architecture:** 30 minutes
* **First Navigation:** 35 minutes
* **Costmap Understanding:** 30 minutes
* **Parameter Tuning:** 40 minutes
* **Advanced Navigation:** 45 minutes
* **Mission Planning:** 30 minutes
* **Total:** \~210 minutes (3.5 hours)

#### 📚 Prerequisites

* ✅ Completed ALL previous tutorials (especially SLAM and Localization)
* ✅ Have saved maps
* ✅ Can localize robot on maps
* ✅ Understanding of coordinate frames
* ✅ Comfortable with RViz
* ✅ Can tune parameters

#### 🛠️ What You'll Need

* ✅ Beetlebot (fully charged, all sensors working)
* ✅ Laptop with ROS2 Jazzy
* ✅ Wireless controller (for emergency stop)
* ✅ Previously created map
* ✅ Mapped environment (unchanged)
* ✅ Large clear space (recommended 5m × 5m+)
* ✅ Patience and readiness to iterate!

***

### Part 1: Navigation Architecture

#### Nav2 Stack Overview

**Nav2 (Navigation2) = ROS2 navigation framework**

**Complete autonomous navigation system:**

```
Goal: "Go to (x, y, θ)"
    ↓
Nav2 BT Navigator (Behavior Tree)
    ↓
    ├─ Planner Server → Global path (A*, Theta*, etc.)
    ├─ Controller Server → Local trajectory (DWB, TEB, etc.)
    ├─ Smoother Server → Path smoothing (optional)
    ├─ Recovery Server → Behaviors (spin, backup, wait)
    └─ Lifecycle Manager → State management

All informed by:
    ├─ Localization (AMCL) → "Where am I?"
    ├─ Costmaps → "What obstacles exist?"
    │   ├─ Global costmap (static map + inflation)
    │   └─ Local costmap (recent scans, rolling window)
    └─ Sensor data (LiDAR, odometry, IMU)

Output: /cmd_vel → Motion!
```

***

#### Key Components Explained

**1. BT Navigator (Behavior Tree Navigator)**

* Mission control center
* Coordinates all other servers
* Handles retries, cancellations, timeouts
* Implements complex behaviors (navigate, follow path, etc.)

**2. Planner Server**

* **Global planner:** Long-term path from start → goal
* Algorithms: NavFn (Dijkstra), Smac (State Lattice), Theta\* (any-angle)
* Uses: Global costmap (entire map)
* Output: Sequence of waypoints (path)
* Runs: Infrequently (on new goal, or replanning needed)

**3. Controller Server**

* **Local controller:** Follow global path, avoid dynamic obstacles
* Algorithms: DWB (Dynamic Window), TEB (Timed Elastic Band), MPPI
* Uses: Local costmap (nearby area only)
* Output: Velocity commands (/cmd\_vel)
* Runs: High frequency (\~10-20 Hz)

**4. Smoother Server (Optional)**

* Smooths jagged paths from planner
* Makes motion more natural
* Reduces wear on motors

**5. Recovery Server**

* What to do when stuck?
* Behaviors: Spin in place, back up, wait, clear costmap
* Configurable sequence

**6. Costmap 2D**

* Represents obstacles and free space
* Two instances: Global (entire map) and Local (around robot)
* Multiple layers: Static map, obstacle, inflation, voxel, etc.

***

#### Coordinate Frames in Navigation

**Critical frames:**

```
map → odom → base_link → sensors

map:
  - Global reference
  - Provided by AMCL (localization)
  - Corrected when loop closures occur
  - Used by global planner

odom:
  - Local reference
  - Provided by odometry/EKF
  - Continuous, smooth
  - Drifts over time
  - Used by local controller

base_link:
  - Robot's center
  - All sensors positioned relative to this

sensor frames:
  - lidar_link, camera_link, imu_link
  - Transform to base_link for processing
```

**Why two (map and odom)?**

* Odom smooth but drifts
* Map accurate but can jump (localization corrections)
* Controllers use odom (need continuity)
* Planners use map (need global accuracy)

***

### Part 2: Launching Navigation

#### Prerequisites Check

**Before launching navigation:**

```bash
# 1. Verify map server running
ros2 node list | grep map_server

# If not:
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=/path/to/your_map.yaml

# 2. Verify AMCL running and localized
ros2 node list | grep amcl
ros2 topic echo /amcl_pose --once
# Check covariance is small (<0.05)

# 3. Verify robot base working
ros2 topic hz /scan        # ~10 Hz
ros2 topic hz /odom        # ~20 Hz
ros2 node list | grep lyra  # Motor control nodes

# 4. Verify localization quality
# Open RViz, check scans align with map
```

***

#### Launch Nav2 Stack

**Your robot likely has navigation pre-configured:**

```bash
# Check if already running
ros2 node list | grep nav

# Should show (if running):
# /behavior_server
# /bt_navigator
# /controller_server
# /planner_server
# /smoother_server
# /waypoint_follower

# If not running, launch:
ros2 launch lyra_bringup navigation.launch.py map:=/path/to/map.yaml
```

**What launches:**

* All Nav2 servers
* Configured with Beetlebot parameters
* Ready to receive navigation goals

***

#### Configure RViz for Navigation

**Full navigation visualization:**

```
1. Fixed Frame: "map"

2. Add Map:
   Topic: /map

3. Add LaserScan:
   Topic: /scan
   Color: Red

4. Add PoseArray:
   Topic: /particlecloud (AMCL particles)

5. Add Pose:
   Topic: /amcl_pose (current estimated pose)

6. Add Path (Global Plan):
   Topic: /plan
   Color: Yellow
   Line Width: 0.05

7. Add Path (Local Plan):
   Topic: /local_plan
   Color: Green
   Line Width: 0.03

8. Add Map (Global Costmap):
   Topic: /global_costmap/costmap
   Color Scheme: costmap
   Alpha: 0.5

9. Add Map (Local Costmap):
   Topic: /local_costmap/costmap
   Color Scheme: costmap
   Alpha: 0.7

10. Add Polygon (Footprint):
    Topic: /local_costmap/published_footprint
    Color: Blue

11. Add RobotModel:
    Description Topic: /robot_description

12. Enable "Nav2 Goal" tool (top toolbar)
```

\[PLACEHOLDER: Screenshot of fully configured RViz for navigation]

***

### Part 3: Your First Autonomous Navigation

#### Setting a Navigation Goal

**Method 1: Nav2 Goal (RViz) - Recommended**

```
1. In RViz, click "Nav2 Goal" button (top toolbar)
2. Click on map where you want robot to go
3. Drag to set desired final orientation
4. Release

Robot should:
- Plan path (yellow line appears)
- Start driving along path
- Avoid obstacles
- Arrive at goal
```

***

**Method 2: Action Client (Command Line)**

```bash
# Send goal via action
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "
pose:
  header:
    frame_id: 'map'
  pose:
    position: {x: 2.0, y: 1.0, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}"
```

***

**Method 3: Python Script**

> \[!WARNING] **TODO: Exercise Script Not Included in Core Repository** The `send_nav_goal.py` script below is an educational exercise. It is *not* pre-installed. You are encouraged to create it yourself!

```bash
nano ~/send_nav_goal.py
```

```python
#!/usr/bin/env python3

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
import sys

class NavGoalSender(Node):
    def __init__(self):
        super().__init__('nav_goal_sender')
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

    def send_goal(self, x, y, yaw=0.0):
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0

        # Convert yaw to quaternion
        from math import sin, cos
        goal_msg.pose.pose.orientation.z = sin(yaw / 2.0)
        goal_msg.pose.pose.orientation.w = cos(yaw / 2.0)

        self.get_logger().info(f'Sending goal: x={x}, y={y}, yaw={yaw}')

        self._action_client.wait_for_server()
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback)

        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected!')
            return

        self.get_logger().info('Goal accepted!')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        # Can print distance remaining, ETA, etc.
        pass

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info('Navigation complete!')
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)

    if len(sys.argv) < 3:
        print("Usage: send_nav_goal.py <x> <y> [yaw]")
        print("Example: send_nav_goal.py 2.0 1.5 0.0")
        sys.exit(1)

    x = float(sys.argv[1])
    y = float(sys.argv[2])
    yaw = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

    node = NavGoalSender()
    node.send_goal(x, y, yaw)

    rclpy.spin(node)

if __name__ == '__main__':
    main()
```

**Usage:**

```bash
chmod +x ~/send_nav_goal.py
python3 ~/send_nav_goal.py 2.0 1.5 0.0
```

***

#### Exercise 11.1: First Navigation

**Task:** Navigate to a simple goal

**Setup:**

```
1. Ensure robot localized (particles converged)
2. Clear path visible in RViz (no obstacles)
3. Choose goal 3-5 meters away
4. Goal should have clear path (no tight passages)
```

**Procedure:**

```
1. Set Nav2 Goal in RViz (click and drag)
2. Observe:
   - Yellow path appears (global plan)
   - Green path appears (local plan)
   - Robot starts moving
   - Follows path generally
   - Avoids unexpected obstacles
   - Slows as approaching goal
   - Stops at goal, rotates to final orientation

3. Check console for:
   - "Goal accepted"
   - "Navigation complete" (or "Goal reached")

Success criteria:
- Arrives within 20cm of goal position
- Final orientation within 15° of desired
- Smooth motion (no jerking or stopping)
- No collisions
```

**Typical time:** 30-60 seconds for 3-5m navigation

***

#### Monitoring Navigation Status

**Check navigation state:**

```bash
# Action status
ros2 action list

# Send goal and monitor:
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 1.0}}}}" \
  --feedback

# Shows:
# - Distance remaining
# - Time elapsed
# - Current speed
# - Navigation state
```

***

**View current cmd\_vel:**

```bash
ros2 topic echo /cmd_vel

# Shows velocity commands being sent
# linear.x: forward speed
# angular.z: turn rate
```

***

### Part 4: Understanding Costmaps

#### What are Costmaps?

**Costmap = 2D grid representing traversability**

**Cell values (0-255):**

```
  0: FREE_SPACE (definitely safe)
  1-127: Low cost (prefer to avoid but okay)
  128-252: High cost (really avoid)
  253: INSCRIBED_INFLATED_OBSTACLE (robot footprint would touch)
  254: LETHAL_OBSTACLE (occupied by obstacle)
  255: NO_INFORMATION (unknown)
```

**Purpose:**

* Planners: Find paths through low-cost areas
* Controllers: Avoid high-cost areas
* Safety: Prevent collisions

***

#### Two Costmaps

**Global Costmap:**

* Covers entire map
* Static (from saved map) + dynamic (recent scans)
* Used by: Global planner
* Update rate: Slow (\~1 Hz)
* Purpose: Long-term planning

**Local Costmap:**

* Rolling window around robot (e.g., 5m × 5m)
* Dynamic obstacles only (from recent LiDAR)
* Used by: Local controller
* Update rate: Fast (\~5-10 Hz)
* Purpose: Short-term obstacle avoidance

***

#### Costmap Layers

**Typical layer stack:**

```
1. Static Layer (Global costmap only)
   - From saved map (.pgm file)
   - Walls, furniture
   - Doesn't change

2. Obstacle Layer
   - From LiDAR scans
   - Recent observations (last 1-2 seconds)
   - Dynamic obstacles
   - Raycasting to clear old obstacles

3. Inflation Layer
   - Inflates obstacles by robot radius + safety margin
   - Creates gradient (cost increases near obstacles)
   - Prevents robot from getting too close

4. Voxel Layer (optional, 3D)
   - 3D obstacle representation
   - Marks obstacles at different heights
   - Clears overhangs

5. Range Sensor Layer (optional)
   - For sonar, IR sensors
   - Beetlebot doesn't use this
```

\[PLACEHOLDER: Diagram showing costmap layers combining]

***

#### Visualizing Costmaps

**In RViz (already configured):**

```
Global Costmap:
- Topic: /global_costmap/costmap
- Black: Lethal obstacles
- Pink/Red: Inflated obstacles
- Blue: Free space
- Gray: Unknown

Local Costmap:
- Topic: /local_costmap/costmap
- Rolling window around robot
- Updates in real-time
- See dynamic obstacles appear/disappear
```

***

#### Exercise 11.2: Costmap Observation

**Task:** Understand how costmaps work

**Test 1: Static obstacles**

```
1. View global costmap in RViz
2. All walls should be black (lethal)
3. Pink/red inflation around walls
4. Blue free space in center of rooms
```

**Test 2: Dynamic obstacles**

```
1. View local costmap
2. Place object in front of robot (box, chair)
3. Watch black obstacle appear in costmap
4. Remove object
5. Watch obstacle fade after ~2 seconds (raycasting clears it)
```

**Test 3: Inflation**

```
1. Measure inflation radius in RViz
2. Should be robot_radius + inflation_radius
3. Typical: 0.5-1.0 meter total
4. Robot won't plan path closer than this to walls
```

***

### Part 5: Path Planning

#### Global Planner

**Finds path from current position → goal**

**Algorithm (NavFn / Dijkstra by default):**

```
1. Start at goal position
2. Propagate cost outward (like ripples in pond)
3. Cost increases with distance
4. Obstacles block propagation (infinite cost)
5. Gradient flows from start to goal
6. Follow gradient downhill → optimal path
```

**Alternative planners:**

* **Smac Planner:** State lattice, considers robot kinematics
* *Theta:*\* Any-angle paths (not grid-aligned)
* *Smac Hybrid-A:*\* Car-like kinematics

**Beetlebot default: NavFn (simple, fast, proven)**

***

#### Path Characteristics

**Good path properties:**

* ✅ Smooth curves (not zigzag)
* ✅ Wide clearance from obstacles
* ✅ Reasonable length (not excessively long)
* ✅ Feasible for differential drive

**Poor path properties:**

* ❌ Jagged, grid-aligned
* ❌ Cuts corners too tight
* ❌ Requires in-place rotations where not needed
* ❌ Unnecessarily long detours

***

#### Replanning

**When does global planner replan?**

```
Triggers:
1. New goal received
2. Current path blocked (obstacle appeared)
3. Robot significantly off path
4. Periodic replanning (configurable)

Replanning interval:
- Default: Only when needed
- Can set periodic: Every N seconds
- Trade-off: CPU vs. adaptability
```

***

#### Exercise 11.3: Path Planning Scenarios

**Scenario 1: Direct path**

```
1. Send goal with clear, straight line possible
2. Observe path hugs walls slightly (inflation)
3. Should be nearly straight

Expected: Smooth, direct path
```

**Scenario 2: Around obstacle**

```
1. Place large obstacle between robot and goal
2. Send goal
3. Observe path goes around obstacle

Expected: Clear detour around obstacle, returns to direct path after
```

**Scenario 3: Through doorway**

```
1. Send goal through doorway
2. Observe path centers in doorway

Expected: Path through middle of door, not clipping edges
```

**Scenario 4: Complex environment**

```
1. Send goal requiring multiple turns
2. Observe path navigates through rooms/hallways

Expected: Logical route, not getting stuck in corners
```

***

### Part 6: Local Control

#### Controller's Job

**Follow global plan while:**

* Avoiding dynamic obstacles
* Staying on path
* Respecting velocity limits
* Smooth motion

**Algorithm (DWB - Dynamic Window Approach):**

```
1. Sample possible velocities (v, ω) within robot's capability
2. Simulate forward for ~1-2 seconds
3. Score each trajectory:
   - How well does it follow global path? (path alignment)
   - How far from obstacles? (obstacle avoidance)
   - How fast? (goal approach)
   - How smooth? (prefer less rotation)
4. Choose best scoring trajectory
5. Execute for 0.1-0.2 seconds
6. Repeat (10-20 Hz)
```

***

#### DWB Scoring Components

**Typical scoring:**

```yaml
critics: ["RotateToGoal", "Oscillation", "BaseObstacle",
          "GoalAlign", "PathAlign", "PathDist", "GoalDist"]

Each critic adds cost:
- RotateToGoal: Rotate toward goal when close
- Oscillation: Penalize back-and-forth motion
- BaseObstacle: Avoid obstacles (high cost near collision)
- GoalAlign: Face toward goal
- PathAlign: Stay parallel to global path
- PathDist: Stay close to global path
- GoalDist: Get closer to goal

Total cost = weighted sum of all critics
```

***

#### Velocity Limits

**Controller respects these limits:**

```yaml
# Maximum velocities
max_vel_x: 0.8          # m/s forward
min_vel_x: -0.4         # m/s backward (if allowed)
max_vel_theta: 1.5      # rad/s turn rate

# Acceleration limits
acc_lim_x: 0.5          # m/s² forward
acc_lim_theta: 1.0      # rad/s² rotational

# Simulation
sim_time: 1.5           # Seconds to simulate ahead
sim_granularity: 0.05   # Time steps (50ms)
```

**Note:** These are controller limits. Robot's Lyra controller also has hardware ramping (8 RPM/cycle)!

***

#### Exercise 11.4: Controller Behavior

**Task:** Observe controller adapting to situations

**Test 1: Following straight path**

```
1. Send goal 5m straight ahead
2. Observe cmd_vel:
   ros2 topic echo /cmd_vel

3. Should show:
   - Constant linear.x (~0.5-0.8 m/s)
   - angular.z near zero (going straight)
```

**Test 2: Avoiding obstacle**

```
1. Navigate toward goal
2. Place obstacle in path
3. Observe:
   - Controller detects obstacle in local costmap
   - Trajectory curves around obstacle
   - May slow down near obstacle
   - Returns to path after clearing
```

**Test 3: Tight passage**

```
1. Navigate through doorway or narrow gap
2. Observe:
   - Slows down approaching passage
   - Centers in gap
   - Accelerates after clearing
```

**Test 4: Final approach**

```
1. Navigate to goal
2. As robot approaches (< 0.5m):
   - Linear velocity decreases
   - More precise steering
   - Final rotation to goal orientation
```

***

### Part 7: Parameter Tuning

#### When to Tune

**Default parameters work reasonably for most cases!**

**Tune when:**

* Robot too cautious (won't go through doorways)
* Robot too aggressive (cuts corners)
* Motion not smooth (jerky, oscillating)
* Specific environment needs (narrow hallways, open warehouse)

***

#### Key Parameters to Tune

**Global Costmap:**

```yaml
# In global_costmap_params.yaml

global_costmap:
  global_frame: map
  robot_base_frame: base_link
  update_frequency: 1.0    # Hz (slow for global)
  publish_frequency: 1.0

  resolution: 0.05         # 5cm cells (match map)

  # Plugins (layers)
  plugins: ["static_layer", "obstacle_layer", "inflation_layer"]

  # Obstacle layer
  obstacle_layer:
    observation_sources: scan
    scan:
      topic: /scan
      max_obstacle_height: 2.0
      clearing: true        # Raycasting to clear
      marking: true         # Mark new obstacles

  # Inflation layer
  inflation_layer:
    cost_scaling_factor: 3.0   # How fast cost increases (higher = steeper)
    inflation_radius: 0.55     # How far to inflate (meters)
```

***

**Local Costmap:**

```yaml
# In local_costmap_params.yaml

local_costmap:
  global_frame: odom
  robot_base_frame: base_link
  update_frequency: 5.0    # Hz (faster for local)
  publish_frequency: 2.0

  resolution: 0.05

  rolling_window: true     # Follows robot
  width: 5                 # 5 meters
  height: 5                # 5 meters

  plugins: ["obstacle_layer", "inflation_layer"]

  # No static layer (rolling window, no saved map)
```

***

**Controller (DWB):**

```yaml
# In controller_params.yaml

controller_server:
  ros__parameters:
    controller_frequency: 20.0   # Control loop Hz

    FollowPath:
      plugin: "dwb_core::DWBLocalPlanner"

      # Velocity limits (must be within robot capability)
      max_vel_x: 0.8
      min_vel_x: -0.2         # Allow backing up
      max_vel_theta: 1.5
      min_speed_xy: 0.0
      max_speed_xy: 0.8

      # Acceleration limits
      acc_lim_x: 0.5
      acc_lim_theta: 1.0
      decel_lim_x: -0.5
      decel_lim_theta: -1.0

      # Simulation
      sim_time: 1.5            # Look-ahead time

      # Trajectory generation
      vx_samples: 20           # Velocity samples
      vy_samples: 0            # Diff drive can't strafe
      vtheta_samples: 40       # Angular velocity samples

      # Scoring
      critics: ["RotateToGoal", "Oscillation", "BaseObstacle",
                "GoalAlign", "PathAlign", "PathDist", "GoalDist"]

      BaseObstacle.scale: 0.02
      PathAlign.scale: 32.0
      PathAlign.forward_point_distance: 0.1
      GoalAlign.scale: 24.0
      PathDist.scale: 32.0
      GoalDist.scale: 24.0
```

***

#### Common Tuning Scenarios

**Scenario 1: Robot won't go through doorway**

**Problem:** Too cautious, inflation too large

**Solution:**

```yaml
inflation_layer:
  inflation_radius: 0.4     # Was 0.55 (reduce)
  cost_scaling_factor: 2.0  # Was 3.0 (gentler gradient)
```

***

**Scenario 2: Robot cuts corners too close**

**Problem:** Not enough safety margin

**Solution:**

```yaml
inflation_layer:
  inflation_radius: 0.7     # Was 0.55 (increase)
  cost_scaling_factor: 5.0  # Was 3.0 (steeper gradient)
```

***

**Scenario 3: Motion too jerky**

**Problem:** Controller changing commands too rapidly

**Solution:**

```yaml
# Reduce sample resolution
vx_samples: 10              # Was 20
vtheta_samples: 20          # Was 40

# Prefer smoother paths
PathAlign.scale: 48.0       # Was 32.0 (stronger path following)

# Increase simulation time
sim_time: 2.0               # Was 1.5 (smoother long-term planning)
```

***

**Scenario 4: Robot too slow**

**Problem:** Conservative velocity limits

**Solution:**

```yaml
max_vel_x: 1.0              # Was 0.8 (if robot capable)

# Prefer speed
GoalDist.scale: 30.0        # Was 24.0 (prioritize getting closer)
```

***

#### Exercise 11.5: Parameter Tuning

**Task:** Optimize for your environment

**Baseline test:**

```
1. Create standard course:
   - Start position
   - Goal through doorway
   - Goal in narrow hallway
   - Goal in open area

2. With default parameters:
   - Time each segment
   - Note any failures
   - Record smoothness (subjective 1-10)

3. Baseline metrics recorded
```

**Tuning iteration:**

```
1. Identify issue (too slow, won't fit through door, etc.)
2. Change ONE parameter
3. Retest entire course
4. Compare to baseline
5. Keep if better, revert if worse
6. Repeat
```

**Document your findings!**

***

### Part 8: Recovery Behaviors

#### What Happens When Stuck?

**Robot gets stuck when:**

* Path blocked by obstacle
* Can't find feasible trajectory
* Oscillating in place
* Taking too long

**Nav2 Recovery Behaviors:**

```
1. Clear costmap (maybe obstacle is stale)
2. Spin in place (look for alternative path)
3. Back up (get away from obstacle)
4. Wait (let dynamic obstacle pass)
5. Cancel goal (give up)
```

***

#### Recovery Sequence

**Configurable behavior tree:**

```xml
<RecoveryNode number_of_retries="6">
  <Sequence>
    <ClearEntireCostmap service_name="global_costmap/clear_entirely_global_costmap"/>
    <ClearEntireCostmap service_name="local_costmap/clear_entirely_local_costmap"/>
    <Spin spin_dist="1.57"/>  <!-- 90 degrees -->
    <Wait wait_duration="5"/>
  </Sequence>
</RecoveryNode>
```

**After 6 retries: Goal aborted**

***

#### Manual Recovery

**If robot stuck, you can trigger manually:**

```bash
# Clear costmaps
ros2 service call /local_costmap/clear_entirely_local_costmap std_srvs/srv/Empty
ros2 service call /global_costmap/clear_entirely_global_costmap std_srvs/srv/Empty

# Spin recovery
ros2 action send_goal /spin nav2_msgs/action/Spin "{target_yaw: 1.57}"

# Backup recovery
ros2 action send_goal /backup nav2_msgs/action/BackUp "{target: {x: -0.5}}"

# Cancel current navigation
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose --cancel
```

***

#### Exercise 11.6: Recovery Testing

**Task:** Observe recovery behaviors

**Test 1: Blocked path**

```
1. Send navigation goal
2. While robot moving, place obstacle blocking path
3. Observe:
   - Robot detects blocked path
   - Attempts to find alternative route
   - If no route, triggers recovery (spin)
   - After recovery, tries again
   - Eventually aborts if truly stuck
```

**Test 2: Trap robot**

```
1. Navigate into corner
2. Place obstacles blocking exit (U-shape trap)
3. Send goal outside trap
4. Observe recovery attempts:
   - Spin to look for opening
   - Back up
   - Clear costmap
   - Multiple retries
   - Eventually aborts
```

**Expected:** Robot should try \~6 recovery attempts over 1-2 minutes before aborting

***

### Part 9: Advanced Navigation

#### Waypoint Following

**Navigate through sequence of waypoints:**

```bash
nano ~/waypoint_follower.py
```

```python
#!/usr/bin/env python3

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from nav2_msgs.action import FollowWaypoints
from geometry_msgs.msg import PoseStamped

class WaypointFollower(Node):
    def __init__(self):
        super().__init__('waypoint_follower')
        self._action_client = ActionClient(self, FollowWaypoints, 'follow_waypoints')

    def send_waypoints(self, waypoints):
        """waypoints = [(x1, y1), (x2, y2), ...]"""

        goal_msg = FollowWaypoints.Goal()

        for x, y in waypoints:
            pose = PoseStamped()
            pose.header.frame_id = 'map'
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.orientation.w = 1.0
            goal_msg.poses.append(pose)

        self.get_logger().info(f'Sending {len(waypoints)} waypoints')

        self._action_client.wait_for_server()
        send_goal_future = self._action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Waypoints rejected!')
            return

        self.get_logger().info('Waypoints accepted, following...')
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        self.get_logger().info('All waypoints reached!')
        rclpy.shutdown()

def main():
    rclpy.init()

    # Define patrol route
    waypoints = [
        (2.0, 1.0),
        (2.0, -1.0),
        (-2.0, -1.0),
        (-2.0, 1.0),
        (0.0, 0.0)  # Return to start
    ]

    node = WaypointFollower()
    node.send_waypoints(waypoints)

    rclpy.spin(node)

if __name__ == '__main__':
    main()
```

**Usage:**

```bash
chmod +x ~/waypoint_follower.py
python3 ~/waypoint_follower.py
```

**Robot will visit each waypoint in sequence!**

***

#### Dynamic Goal Updates

**Change goal mid-navigation:**

```python
# Send initial goal
action_client.send_goal_async(goal1)

# If situation changes, cancel and send new goal
action_client.cancel_goal_async()
action_client.send_goal_async(goal2)
```

**Use case:**

* Operator changes mind
* New information received
* Higher priority task

***

#### Pause and Resume

**Pause navigation:**

```bash
ros2 lifecycle set /controller_server pause
```

**Resume:**

```bash
ros2 lifecycle set /controller_server resume
```

**Robot stops but remembers goal, can continue later**

***

### Part 10: Creating Autonomous Missions

#### Mission Planning

**Complex autonomous behavior:**

```python
#!/usr/bin/env python3
# autonomous_mission.py

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
import time

class AutonomousMission(Node):
    def __init__(self):
        super().__init__('autonomous_mission')
        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

    def navigate_to(self, x, y, yaw=0.0):
        """Navigate to position, wait for completion"""
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y

        from math import sin, cos
        goal.pose.pose.orientation.z = sin(yaw / 2.0)
        goal.pose.pose.orientation.w = cos(yaw / 2.0)

        self.get_logger().info(f'Navigating to ({x}, {y})')

        self._nav_client.wait_for_server()
        send_goal_future = self._nav_client.send_goal_async(goal)

        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected')
            return False

        # Wait for result
        get_result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, get_result_future)

        result = get_result_future.result().result
        self.get_logger().info('Goal reached!')
        return True

    def patrol_mission(self):
        """Example mission: Patrol 4 corners"""

        waypoints = [
            (3.0, 3.0, 0.0),
            (3.0, -3.0, -1.57),  # Face left
            (-3.0, -3.0, 3.14),  # Face back
            (-3.0, 3.0, 1.57),   # Face right
            (0.0, 0.0, 0.0)      # Return home
        ]

        for i, (x, y, yaw) in enumerate(waypoints):
            self.get_logger().info(f'Waypoint {i+1}/{len(waypoints)}')

            success = self.navigate_to(x, y, yaw)

            if not success:
                self.get_logger().error('Mission failed!')
                return

            # Pause at waypoint
            self.get_logger().info('Waiting 5 seconds...')
            time.sleep(5)

        self.get_logger().info('Mission complete!')

def main():
    rclpy.init()
    mission = AutonomousMission()

    try:
        mission.patrol_mission()
    except KeyboardInterrupt:
        pass

    mission.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Run mission:**

```bash
python3 autonomous_mission.py
```

***

#### Exercise 11.7: Create Custom Mission

**Task:** Design and execute multi-step mission

**Requirements:**

1. At least 5 waypoints
2. Include different goal orientations
3. Pause at each waypoint (simulate task)
4. Handle navigation failures gracefully
5. Log progress

**Example missions:**

* **Security patrol:** Visit 4 corners, check each area
* **Delivery:** Pick up at point A, deliver to point B, return
* **Inspection:** Navigate to specific equipment locations
* **Cleaning:** Cover entire floor systematically

***

### Part 11: Troubleshooting Navigation

#### Problem: Robot Won't Start Navigation

**Checklist:**

```bash
# 1. Check localization
ros2 topic echo /amcl_pose --once
# Covariance should be small (<0.05)

# 2. Check map loaded
ros2 topic hz /map
# Should publish (even just once)

# 3. Check nav servers running
ros2 node list | grep -E "planner|controller|behavior|bt_navigator"

# 4. Check goal is valid
# Goal should be:
# - In free space (not inside wall)
# - On map (not outside boundaries)
# - Reachable (path exists)

# 5. Check TF tree
ros2 run tf2_tools view_frames
# map → odom → base_link should exist
```

***

#### Problem: Robot Stuck Oscillating

**Symptoms:** Robot wiggles back and forth, makes no progress

**Causes:**

1. **Conflicting critics**

```yaml
   # PathAlign wants robot on path
   # GoalAlign wants robot facing goal
   # If goal sideways to path → conflict!

   Solution: Reduce GoalAlign.scale (prioritize path following)
```

2. **Narrow passage**

```yaml
   # Robot sees passage as barely passable
   # Oscillates trying to center

   Solution: Reduce inflation_radius
```

3. **Local minimum**

```yaml
   # Controller can't see global path clearly

   Solution: Increase sim_time (look further ahead)
```

***

#### Problem: Path Goes Through Walls

**Cause:** Costmap not reflecting actual obstacles

**Debug:**

```bash
# View costmaps in RViz
# Check if walls marked as obstacles (black)

# If not:
# 1. Check map loaded correctly
ros2 topic echo /map_metadata --once

# 2. Check static layer enabled
ros2 param get /global_costmap/global_costmap plugins

# 3. Reload map
ros2 service call /global_costmap/clear_entirely_global_costmap std_srvs/srv/Empty
```

***

#### Problem: Navigation Very Slow

**Causes:**

1. **Too conservative parameters**

```yaml
   max_vel_x: 0.8 → 1.0  # Increase if robot capable
```

2. **High inflation**

```yaml
   inflation_radius: 0.55 → 0.4  # Robot stays far from walls
```

3. **Too many trajectory samples**

```yaml
   vx_samples: 20 → 10
   vtheta_samples: 40 → 20
   # Faster computation, slightly less optimal
```

***

#### General Debugging

**Most navigation issues fixed by:**

1. **⚡ Power cycle robot** (clears stuck states)
2. **Clear costmaps** (remove stale obstacles)
3. **Re-localize** (set 2D Pose Estimate again)
4. **Check RViz alignment** (scans should match map)
5. **Verify goal validity** (in free space, reachable)

***

### Part 12: Knowledge Check

#### Concept Quiz

1. **What's the difference between global and local costmaps?**
2. **Why does robot need both a planner and controller?**
3. **What triggers recovery behaviors?**
4. **Why inflate obstacles in costmap?**
5. **Can navigation work without localization?**

***

#### Final Challenge

**Task:** Complete autonomous navigation system

**Mission: Autonomous Office Patrol**

**Requirements:**

1. Create map of test environment (or use existing)
2. Configure navigation stack
3. Create patrol route with 6+ waypoints
4. Robot must:
   * Localize automatically (global localization)
   * Execute patrol route autonomously
   * Handle dynamic obstacles (person walks through)
   * Complete 3 full patrol loops
   * Return to start position
   * Log all waypoint arrivals with timestamps
5. Tune parameters for optimal performance
6. Handle failures gracefully (retry, skip unreachable waypoints)

**Deliverable:**

* Complete launch file for autonomous operation
* Tuned parameter files
* Mission script with error handling
* Performance report:
  * Total mission time
  * Success rate per waypoint
  * Number of recovery behaviors triggered
  * Final localization error
* Video recording of full mission
* Lessons learned document

**Estimated time:** 3-4 hours for complete implementation and testing

***

### Part 13: What You've Learned

#### ✅ CONGRATULATIONS! YOU'VE COMPLETED THE ENTIRE COURSE!

**You now have mastered:**

**Foundation (Tutorials 1-3):**

* ✅ Robot hardware and architecture
* ✅ ROS2 communication fundamentals
* ✅ Simulation for safe testing

**Perception (Tutorials 4-5):**

* ✅ Sensor data visualization and interpretation
* ✅ IMU signal processing and filtering

**Control (Tutorials 6-7):**

* ✅ Teleoperation techniques
* ✅ Multi-sensor fusion with EKF

**Mapping & Localization (Tutorials 8-10):**

* ✅ SLAM mapping of environments
* ✅ Camera-based perception
* ✅ Localization on known maps

**Autonomous Navigation (Tutorial 11):**

* ✅ Nav2 stack architecture
* ✅ Path planning algorithms
* ✅ Local trajectory control
* ✅ Costmap configuration
* ✅ Recovery behaviors
* ✅ Parameter tuning
* ✅ Complex mission planning

***

### Beyond This Course

#### 🎯 You're Now Ready For:

**Advanced Topics:**

* Multi-robot coordination
* Outdoor navigation (GPS fusion)
* 3D navigation (stairs, ramps)
* Semantic mapping (recognize object types)
* Machine learning perception (object detection, recognition)
* Visual SLAM (camera-based)
* Advanced planners (RRT, RRT\*, etc.)

**Real Applications:**

* Warehouse automation
* Security patrol robots
* Cleaning robots
* Delivery robots
* Agricultural robots
* Inspection robots

**Competitions:**

* RoboCup
* DARPA challenges
* AutoNav competitions

**Research:**

* Human-robot interaction
* Swarm robotics
* Learning-based navigation
* Robust navigation in dynamic environments

***

### Quick Reference

#### Complete Navigation Launch

```bash
# Full navigation stack (map, localization, navigation)
ros2 launch lyra_bringup full_navigation.launch.py \
  map:=/path/to/map.yaml \
  use_sim_time:=false
```

***

#### Essential Navigation Commands

```bash
# --- Check Status ---
ros2 node list | grep -E "map|amcl|planner|controller|bt"
ros2 topic hz /scan /odom /map

# --- Send Goal (CLI) ---
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 1.0}}}}"

# --- Cancel Goal ---
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose --cancel

# --- Clear Costmaps ---
ros2 service call /local_costmap/clear_entirely_local_costmap std_srvs/srv/Empty
ros2 service call /global_costmap/clear_entirely_global_costmap std_srvs/srv/Empty

# --- Manual Recovery ---
ros2 action send_goal /spin nav2_msgs/action/Spin "{target_yaw: 1.57}"
ros2 action send_goal /backup nav2_msgs/action/BackUp "{target: {x: -0.5}}"

# --- Check Parameters ---
ros2 param list /controller_server
ros2 param get /controller_server FollowPath.max_vel_x

# --- Lifecycle Control ---
ros2 lifecycle set /controller_server pause
ros2 lifecycle set /controller_server resume

# --- Monitor Progress ---
ros2 topic echo /cmd_vel          # Current velocity commands
ros2 topic echo /plan             # Global path
ros2 topic echo /local_plan       # Local trajectory
```

***

#### Configuration File Locations

```
~/lyra_ws/src/lyra_bringup/config/
  ├── nav2_params.yaml              # Main navigation config
  ├── global_costmap_params.yaml    # Global costmap
  ├── local_costmap_params.yaml     # Local costmap
  ├── planner_params.yaml           # Planner settings
  └── controller_params.yaml        # Controller settings
```

***

#### Typical Navigation Stack Flowchart

```
User sends goal → BT Navigator
                     ↓
                 Planner Server
                     ↓
                 Global Path
                     ↓
                 Controller Server
                     ↓
                 Local Trajectory
                     ↓
                 /cmd_vel
                     ↓
                 Robot moves!
                     ↓
                 Localization (AMCL)
                     ↓
                 Update position
                     ↓
                 Loop (until goal reached)
```

***

### Final Words

#### 🎉 YOU DID IT!

You've completed all 11 tutorials of the Beetlebot wiki!

**What you've accomplished:**

* Built maps of your environment
* Localized robot on those maps
* Commanded autonomous navigation
* Tuned parameters for optimal performance
* Created complex autonomous missions

**This is REAL robotics!** 🤖

The skills you've learned here are used in:

* Self-driving cars
* Warehouse robots
* Delivery drones
* Space exploration
* And countless other applications

***

#### Keep Learning!

**Resources:**

* ROS2 Documentation: <https://docs.ros.org>
* Nav2 Documentation: <https://navigation.ros.org>
* VEEROBOT Support: <support@veerobot.com>
* Community forums, GitHub, research papers

**Practice:**

* Create more complex environments
* Test in different conditions
* Experiment with parameters
* Build custom behaviors
* Contribute to open source

***

#### Share Your Work!

We'd love to see what you build:

* Post videos of your robot navigating
* Share parameter configurations
* Contribute improvements
* Help other users

**You're now part of the robotics community!** 🌟

***

**Tutorial Series Complete!** 🏆

→ Return to Tutorial Index\
→ Visit Support & Resources\
→ Start your own robotics project\
→ Goto next section for optimization!

***

*Last Updated: January 2026*\
*Tutorial 11 of 11 - Advanced Level*\
*Estimated completion time: 210 minutes (3.5 hours)*\
*�� COURSE COMPLETE! 🎓*
