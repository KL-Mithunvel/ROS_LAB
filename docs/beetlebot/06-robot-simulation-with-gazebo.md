# Robot Simulation with Gazebo

> \[!WARNING] **TODO: Feature Not Yet Implemented** The Gazebo simulation environment (`beetlebot_description` with gazebo integration, URDF physics, simulated worlds, etc.) is planned for a future release and is **not yet available in the current codebase**. The instructions on this page represent intended future functionality. Please use the real physical robot for your current learning and development!

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand URDF (robot description format)
* ✅ Visualize robot in RViz without hardware
* ✅ Launch Gazebo simulation environment
* ✅ Control virtual robot with keyboard/joystick
* ✅ Modify robot parameters and see effects
* ✅ Compare simulation vs. real robot behavior
* ✅ Use simulation for algorithm development
* ✅ Create custom worlds and obstacles

#### ⏱️ Time Required

* **Reading & Concepts:** 20 minutes
* **RViz Visualization:** 15 minutes
* **Gazebo Simulation:** 30 minutes
* **Experimentation:** 20 minutes
* **Total:** \~85 minutes

#### 📚 Prerequisites

* ✅ Completed ROS2 Communication & Tools
* ✅ Laptop with ROS2 Jazzy installed
* ✅ Can communicate with robot (for comparing)
* ⚠️ **Robot NOT required** - all simulation on laptop!
* ✅ 2GB+ free RAM for Gazebo

#### 🛠️ What You'll Need

* ✅ Laptop with ROS2 Jazzy
* ✅ Gazebo Harmonic installed
* ✅ Keyboard or joystick (for control)
* ⏸️ Physical robot (optional - for comparison)

***

### Part 1: Understanding URDF

#### What is URDF?

**URDF = Unified Robot Description Format**

**Analogy:** Like a blueprint for your robot

* Describes physical structure (links and joints)
* Defines dimensions, masses, inertias
* Specifies sensor locations
* Includes visual meshes (3D models)
* Contains collision geometries

**XML-based format** readable by both humans and robots

***

#### URDF Structure

**Key concepts:**

**Links (Rigid Bodies)**

* Base chassis
* Wheels
* Sensor mounts
* Camera
* LiDAR

**Joints (Connections Between Links)**

* **Fixed:** No motion (camera → chassis)
* **Continuous:** Unlimited rotation (wheels)
* **Revolute:** Limited rotation (steering, arms)
* **Prismatic:** Sliding motion (telescoping)

**Transforms (Spatial Relationships)**

* Where is camera relative to chassis?
* How high is LiDAR from ground?
* What's the wheelbase?

***

#### Beetlebot URDF Overview

Your robot's description includes:

**Links:**

* `base_footprint` - Ground projection point
* `base_link` - Main chassis (reference point)
* `fl_link`, `fr_link`, `bl_link`, `br_link` - Four wheels
* `lidar_link` - RPLidar C1 position
* `camera_link` - Pi Camera position
* `imu_link` - IMU sensor location

**Joints:**

* `base_footprint_joint` - Fixed (ground → chassis)
* `fl_joint`, `fr_joint`, `bl_joint`, `br_joint` - Continuous (rotating wheels)
* `lidar_joint` - Fixed (chassis → LiDAR)
* `camera_joint` - Fixed (chassis → camera)
* `imu_joint` - Fixed (chassis → IMU)

**Key measurements:**

* Ground clearance: 16.3cm (base\_footprint → base\_link)
* Wheelbase: 18.1cm (front-back distance)
* Track width: 29cm (left-right distance)
* Wheel diameter: 13cm
* LiDAR height: 20.6cm from ground
* Camera height: 8.8cm from ground

***

### Part 2: Visualization in RViz

#### Launch Robot State Publisher

**On your laptop:**

```bash
# Source ROS2
source /opt/ros/jazzy/setup.bash

# Navigate to workspace (or download Beetlebot packages first)
cd ~/beetlebot_ws

# Launch robot description
ros2 launch beetlebot_description display.launch.py
```

**What launches:**

* `robot_state_publisher` - Publishes TF tree from URDF
* `joint_state_publisher_gui` - Interactive joint control
* `rviz2` - 3D visualization

\[PLACEHOLDER: Screenshot of RViz showing Beetlebot model]

***

#### Explore the Model in RViz

**What you see:**

1. **3D robot model** - Gray chassis, blue wheels
2. **Coordinate frames** - Red/Green/Blue axes (TF)
3. **Joint slider panel** - Control wheel rotations

**Interactive exploration:**

```
Move wheels:
- Drag sliders in Joint State Publisher GUI
- Watch wheels rotate in RViz
- See how chassis stays fixed

Change view:
- Left-click + drag: Rotate view
- Middle-click + drag: Pan
- Scroll wheel: Zoom

Toggle displays:
- Uncheck RobotModel → see TF frames only
- Uncheck TF → see model only
- Check/uncheck to understand layering
```

***

#### Understanding the TF Tree

**View frame relationships:**

```bash
# In new terminal
ros2 run tf2_tools view_frames

# Wait 5 seconds, then Ctrl+C
# Opens frames.pdf showing tree
```

**Expected tree:**

```
base_footprint
    └─ base_link
        ├─ fl_link (front-left wheel)
        ├─ fr_link (front-right wheel)
        ├─ bl_link (back-left wheel)
        ├─ br_link (back-right wheel)
        ├─ lidar_link
        ├─ camera_link
        │   └─ camera_optical_link
        └─ imu_link
```

**Key insight:** All sensor positions defined relative to `base_link`!

***

#### Exercise 3.1: Measure Robot Dimensions

**Task:** Use RViz to verify robot dimensions

```bash
# While RViz running, check measurements
# In RViz: Panels → Add New Panel → TF

# Check key transforms:
ros2 run tf2_ros tf2_echo base_link fl_link

# Output shows:
# Translation: [x, y, z]
# x: 0.094m (forward from center)
# y: 0.145m (left from center)
# z: -0.098m (down from center)

# Calculate wheelbase:
ros2 run tf2_ros tf2_echo bl_link fl_link
# x difference = front-back distance

# Calculate track width:
ros2 run tf2_ros tf2_echo fl_link fr_link
# y difference × 2 = left-right distance
```

**Verify matches specifications:**

* Wheelbase: \~18cm ✅
* Track width: \~29cm ✅
* Wheel height: \~9.8cm below chassis ✅

***

### Part 3: Gazebo Simulation Basics

#### Installing Gazebo Harmonic

**Check if installed:**

```bash
gz sim --version
```

**If not installed:**

```bash
# Install Gazebo Harmonic
sudo apt install gz-harmonic -y

# Install ROS2-Gazebo bridge
sudo apt install ros-jazzy-ros-gz -y
```

***

#### Launch Beetlebot in Gazebo

```bash
# Launch Gazebo simulation
cd ~/lyra_ws/src/beetlebot_description/gazebo/
./run_beetlebot_worlds.sh
# Or with custom world:
./run_beetlebot.sh shapes
```

**What launches:**

* Gazebo simulator with physics engine
* ROS2-Gazebo bridge (connects ROS topics ↔ Gazebo)
* Robot model spawned in world
* `/cmd_vel` topic available for control

\[PLACEHOLDER: Screenshot of Gazebo with Beetlebot in empty world]

***

#### Gazebo Interface Tour

**Main window sections:**

**Scene (center):**

* 3D world view
* Robot model with physics
* Ground plane, lighting

**World Tree (left):**

* Scene hierarchy
* Robot parts listed
* Plugins shown

**Entity Tree (right):**

* Select objects to inspect
* View properties
* Modify parameters

**Toolbar (top):**

* Translate, rotate, scale tools
* Play/pause simulation
* Reset world

***

#### Camera Controls

```
Rotate view:
- Right-click + drag

Pan view:
- Middle-click + drag
- Or Shift + Right-click + drag

Zoom:
- Scroll wheel

Follow robot:
- Right-click robot → "Follow"
```

***

#### Exercise 3.2: Physics Exploration

**Task:** Understand Gazebo physics

**Test 1: Gravity**

```
1. Play simulation (▶️ button)
2. Robot should sit on ground stably
3. Try to lift robot with translate tool
4. Release → robot falls (gravity works!)
```

**Test 2: Collisions**

```
1. Insert obstacle:
   - Insert → box
   - Resize: 1m × 1m × 0.5m high
2. Position in front of robot
3. Drive robot toward box
4. Robot should collide and stop
```

**Test 3: Wheel Physics**

```
1. Observe wheels when driving
2. Should rotate smoothly
3. Check for slip on turns
4. Compare to real robot behavior
```

***

### Part 4: Controlling Simulated Robot

#### Keyboard Teleop

**Launch teleop:**

```bash
# New terminal
source /opt/ros/jazzy/setup.bash

ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args --remap /cmd_vel:=/cmd_vel
```

**Drive with keyboard:**

```
u i o    ← Forward + turn
j k l    ← Turn in place
m , .    ← Backward + turn

q/z: increase/decrease max speeds by 10%
w/x: increase/decrease only linear speed by 10%
e/c: increase/decrease only angular speed by 10%

Space: force stop
CTRL-C: quit
```

**Try driving patterns:**

* Straight line (press 'i', wait, press 'k')
* Square (i, j, i, j, i, j, i, j)
* Circle (i + j held together)

***

#### Joystick Control

**If you have the Cosmic Byte controller:**

```bash
# Plug RF dongle into laptop USB

# Launch joy node
ros2 run joy joy_node

# In another terminal, verify joy messages:
ros2 topic echo /joy

# Launch Beetlebot teleop
ros2 run lyra_control lyra_teleop_node

# Drive with joystick:
# - Hold LB (Left Bumper)
# - Left stick = forward/back
# - Right stick = turn left/right
```

**Note:** Same controls as real robot!

***

#### Exercise 3.3: Compare Sim vs Real

**Task:** Drive same path in simulation and real robot

**Path:** 1 meter forward, turn 90° left, repeat 4× (square)

**In Simulation:**

```bash
# Record odometry
ros2 bag record -o sim_square /odom /cmd_vel

# Drive square with keyboard
# Record final position
```

**On Real Robot:**

```bash
# Power on robot
# Record odometry
ros2 bag record -o real_square /odom /cmd_vel

# Drive square with joystick
# Record final position
```

**Compare:**

* Did both end near starting position?
* Which had more drift?
* Why differences?

<details>

<summary>Expected results</summary>

**Simulation:** Near-perfect square (minimal drift)

* Ideal physics, no slip
* Perfect wheel diameters
* No encoder noise

**Real robot:** Some drift (\~10-20cm)

* Wheel slip on turns
* Floor friction variations
* Encoder quantization

**Key lesson:** Simulation is optimistic! Real world has imperfections.

</details>

***

### Part 5: Modifying Robot Parameters

#### Change Wheel Size Experiment

**Goal:** See how wheel diameter affects motion

**Edit URDF temporarily:**

```bash
# Copy URDF to workspace
cp ~/beetlebot_ws/src/beetlebot_description/urdf/beetlebot.urdf ~/test_robot.urdf

# Edit file
nano ~/test_robot.urdf

# Find wheel radius (search for "0.065")
# Change from 0.065 to 0.08 (larger wheels)

# Launch with modified URDF
ros2 launch beetlebot_description display.launch.py urdf_file:=$HOME/test_robot.urdf
```

**Observe in RViz:**

* Wheels look bigger
* Ground clearance increased
* Check with tf2\_echo

**Predict:** If wheels are bigger, robot will go \_\_\_ (faster/slower) for same motor RPM?

<details>

<summary>Answer</summary>

\*\*Faster!\*\* Bigger wheels = more distance per revolution Formula: distance = 2 × π × radius 0.065m radius → 0.408m per revolution 0.080m radius → 0.503m per revolution (+23% faster)

</details>

***

#### Exercise 3.4: Wheelbase Experiment

**Task:** Change wheelbase (front-back distance), observe turning

**Modify URDF:**

```bash
nano ~/test_robot.urdf

# Find front wheel joint (fl_joint):
# <origin xyz="0.094 0.145 -0.098" ...>

# Change first number (x position):
# From: 0.094 → 0.150 (wider wheelbase)

# Also change back wheel (bl_joint):
# <origin xyz="-0.087 0.145 -0.098" ...>
# Change to: -0.150

# Now wheelbase = 0.150 - (-0.150) = 0.30m (was 0.18m)
```

**Test in Gazebo:**

* Launch modified robot
* Drive in circle
* Compare turning radius

**Wider wheelbase = \_\_\_ turning radius** (larger/smaller)?

<details>

<summary>Answer</summary>

\*\*Larger turning radius!\*\* Wider wheelbase = harder to turn (need more space) Like the difference between a sports car (tight turns) and a truck (wide turns)

</details>

***

### Part 6: Creating Custom Worlds

#### Empty World (Default)

```bash
ros2 launch beetlebot_description gazebo.launch.py world:=empty
```

**Features:**

* Flat ground plane
* Sun lighting
* No obstacles
* Good for basic testing

***

#### Adding Obstacles

**Manually in Gazebo:**

```
1. Click "Insert" tab (left side)
2. Scroll to shapes:
   - Box
   - Sphere
   - Cylinder
3. Click shape
4. Click in world to place
5. Use transform tools to position
```

**Build a simple maze:**

* 8× boxes arranged in maze pattern
* Each box: 2m × 0.2m × 0.5m
* Space between: 1m (robot width + clearance)

\[PLACEHOLDER: Diagram of simple maze layout]

***

#### Saving Custom World

```bash
# In Gazebo
# File → Save World As
# Save to: ~/my_beetlebot_world.sdf

# Launch your world:
ros2 launch beetlebot_description gazebo.launch.py \
  world:=$HOME/my_beetlebot_world.sdf
```

***

#### Exercise 3.5: Obstacle Course Challenge

**Task:** Create and navigate obstacle course

**Setup:**

1. Create world with 5 obstacles
2. Place target zone (use colored box as goal)
3. Start position: 3 meters from goal

**Challenge:**

* Navigate from start to goal
* Avoid all obstacles
* Fastest time wins!

**Practice first in simulation, then try on real robot!**

***

### Part 7: Sensor Simulation

#### LiDAR in Gazebo

**Check if LiDAR active:**

```bash
# While Gazebo running
ros2 topic list | grep scan

# Should see:
# /scan

# View scan data
ros2 topic echo /scan
```

**Visualize in RViz:**

```bash
# Launch RViz
rviz2

# Add LaserScan display:
# - Add → By Topic → /scan → LaserScan
# - Fixed Frame: "odom"
# - Color: Rainbow by "intensity"
```

\[PLACEHOLDER: Screenshot of RViz showing simulated LiDAR]

**Drive toward obstacle in Gazebo, watch RViz:**

* Red/orange = close obstacles
* Green/blue = far obstacles
* Black = no return (infinite distance)

***

#### Camera in Gazebo

**Check camera topic:**

```bash
ros2 topic list | grep camera

# Should see:
# /pi_camera/image_raw
# /pi_camera/camera_info
```

**View image:**

```bash
ros2 run rqt_image_view rqt_image_view
```

**Select topic:** `/pi_camera/image_raw`

\[PLACEHOLDER: Screenshot of simulated camera view]

***

#### IMU Simulation

```bash
# Check IMU data
ros2 topic echo /imu/data

# Should show:
# orientation, angular_velocity, linear_acceleration
```

**Test IMU:**

* Drive robot in simulation
* Watch angular\_velocity change during turns
* Watch linear\_acceleration during acceleration

***

### Part 8: Simulation Limitations

#### What Simulation Does Well

✅ **Physics basics:**

* Gravity, collisions, friction (approximately)
* Mass and inertia effects
* Wheel dynamics

✅ **Sensor geometry:**

* LiDAR beam positions
* Camera field of view
* Coordinate transforms

✅ **Algorithm development:**

* Test navigation logic
* Develop mapping algorithms
* Prototype behaviors

✅ **Safety:**

* No battery drain
* No mechanical wear
* No crashes damage hardware

***

#### What Simulation Doesn't Capture

❌ **Real-world imperfections:**

* Wheel slip varies by surface
* Encoder noise and quantization
* Motor response delays
* Voltage drop under load

❌ **Sensor noise:**

* LiDAR reflectivity variations
* Camera exposure, motion blur
* IMU drift over time
* Temperature effects

❌ **Unexpected behaviors:**

* Cable snag
* Wheel stuck on obstacle edge
* Battery suddenly low
* WiFi dropout

❌ **Timing issues:**

* Real hardware latencies
* USB device delays
* Network jitter

***

#### The Reality Gap

**Simulation-to-Reality Transfer:**

**Algorithms developed in simulation may need tuning on real hardware:**

**Example: Navigation**

* Sim: Robot stops exactly at goal (perfect)
* Real: Oscillates around goal (needs larger tolerance)

**Example: Turning**

* Sim: 90° turn = exactly 90°
* Real: 90° turn = 88-92° (needs calibration)

**Best practice:**

1. Develop algorithm in simulation (safe, fast iteration)
2. Test on real robot (find real-world issues)
3. Adjust parameters based on real performance
4. Validate in multiple real environments

***

### Part 9: Practical Simulation Workflows

#### Workflow 1: Algorithm Development

```
1. Write code on laptop
2. Test in Gazebo simulation
3. Debug until it works in sim
4. Deploy to real robot
5. Tune parameters on hardware
6. Validate in real environment
```

**Example:** Path following algorithm

* Simulate 100 iterations in 10 minutes
* Would take hours on real robot (battery, space)

***

#### Workflow 2: Teaching and Demos

**Safe demonstrations:**

* Show navigation concepts
* Demonstrate SLAM
* Explain control algorithms
* No risk of damaging robot

**Parallel operation:**

* Students use simulation
* Instructor uses real robot
* Compare results

***

#### Workflow 3: Testing Edge Cases

**Scenarios hard to test on real robot:**

* Very tight spaces
* Steep ramps (beyond hardware capability)
* High-speed maneuvers
* Extreme lighting conditions
* Multiple robots (need multiple units)

**Test in simulation first:**

* Validate algorithm handles edge case
* Then carefully test on hardware

***

### Part 10: Advanced Simulation Topics

#### Multi-Robot Simulation

**Launch multiple robots:**

```bash
# Robot 1
ros2 launch beetlebot_description gazebo.launch.py \
  robot_name:=robot1 robot_namespace:=robot1 x:=0 y:=0

# Robot 2 (new terminal)
ros2 launch beetlebot_description gazebo.launch.py \
  robot_name:=robot2 robot_namespace:=robot2 x:=2 y:=0

# Now control independently!
```

**Use cases:**

* Multi-robot coordination
* Leader-follower algorithms
* Swarm behaviors

***

#### Recording Simulation Data

**Save simulation for replay:**

```bash
# Record all topics
ros2 bag record -a

# Run simulation scenario
# Stop recording

# Replay later for analysis
ros2 bag play my_simulation.db3
```

**Benefits:**

* Analyze behavior offline
* Share scenarios with team
* Debug without re-running sim

***

#### Procedural World Generation

**Python script to generate random obstacles:**

```python
# generate_world.py
import random

def generate_obstacle_world(num_obstacles, world_size):
    xml = '<?xml version="1.0"?><sdf version="1.6"><world name="default">'

    for i in range(num_obstacles):
        x = random.uniform(-world_size, world_size)
        y = random.uniform(-world_size, world_size)
        xml += f'<model name="obstacle_{i}">...'  # Box model XML

    xml += '</world></sdf>'
    with open('random_world.sdf', 'w') as f:
        f.write(xml)

# Generate 20 random obstacles in 10m × 10m area
generate_obstacle_world(20, 5.0)
```

***

### Part 11: Troubleshooting Simulation

#### Gazebo Won't Launch

**Check installation:**

```bash
gz sim --version
# Should show Gazebo Harmonic

# If not:
sudo apt install gz-harmonic
```

***

#### Robot Falls Through Ground

**Cause:** Collision meshes missing

**Fix:**

```bash
# Check URDF has <collision> tags for all links
nano ~/beetlebot_ws/src/beetlebot_description/urdf/beetlebot.urdf

# Each link needs both <visual> and <collision>
```

***

#### Robot Doesn't Move

**Checklist:**

```bash
# 1. Is simulation playing? (▶️ button pressed)

# 2. Are cmd_vel messages being sent?
ros2 topic hz /cmd_vel
# Should be >0 Hz

# 3. Is ROS-Gazebo bridge working?
ros2 topic list
# Should see both /cmd_vel and /odom

# 4. Check Gazebo console for errors
# Look in Gazebo terminal output
```

***

#### Performance Issues (Slow Simulation)

**Reduce complexity:**

```bash
# 1. Lower physics update rate (in world SDF)
# <physics><real_time_update_rate>100</real_time_update_rate>
# Change to 50 or 25

# 2. Simplify collision meshes
# Use boxes instead of complex meshes

# 3. Reduce sensor rates
# LiDAR: 5 Hz instead of 10 Hz
```

***

#### General Troubleshooting

**Most simulation issues fixed by:**

1. **Restart Gazebo**

```bash
   # Ctrl+C in Gazebo terminal
   # Re-launch
```

2. **Clear Gazebo cache**

```bash
   rm -rf ~/.gz/sim/*
```

3. **Check ROS2 daemon**

```bash
   ros2 daemon stop
   ros2 daemon start
```

***

### Part 12: Knowledge Check

#### Concept Quiz

1. **What does URDF stand for?**
2. **What's the difference between a 'link' and a 'joint'?**
3. **Why is simulation useful if it's not perfectly accurate?**
4. **Name 3 things simulation doesn't capture well:**
5. **How can you make wheels bigger in simulation?**

***

#### Hands-On Challenge

**Task:** Create a navigable environment and test it

**Requirements:**

1. Custom Gazebo world with 10+ obstacles
2. Clear path from start (0,0) to goal (5,5)
3. Record rosbag of successful navigation
4. Visualize in RViz during playback

**Deliverable:**

* Screenshot of Gazebo world
* Screenshot of RViz showing trajectory
* Rosbag file of run

***

### Part 13: What You've Learned

#### ✅ Congratulations!

You now understand:

**URDF & Robot Description:**

* ✅ What URDF files contain
* ✅ Links, joints, and transforms
* ✅ How robot structure is defined
* ✅ Modifying robot parameters

**Visualization:**

* ✅ Using RViz to view robot model
* ✅ Understanding TF trees
* ✅ Checking spatial relationships

**Simulation:**

* ✅ Launching Gazebo
* ✅ Controlling simulated robot
* ✅ Creating custom worlds
* ✅ Adding obstacles

**Practical Skills:**

* ✅ Comparing sim vs real behavior
* ✅ Testing algorithms safely
* ✅ Recording simulation data
* ✅ Troubleshooting simulation issues

**Limitations:**

* ✅ What simulation models well
* ✅ What it doesn't capture
* ✅ When to use sim vs hardware

***

### Next Steps

#### 🎯 You're Now Ready For:

**Development:**

* Write navigation algorithms in simulation
* Test in Gazebo before deploying to robot
* Iterate quickly without hardware wear

**Learning:** → Sensor Data Visualization - Work with real LiDAR and camera\
→ SLAM Mapping - Build maps (sim first, then real)\
→ Autonomous Navigation - Full path planning

**Advanced Topics:**

* Multi-robot coordination (simulation)
* Custom sensor plugins
* Procedural world generation

***

### Quick Reference

#### Common Gazebo Commands

```bash
# Launch empty world
ros2 launch beetlebot_description gazebo.launch.py

# Launch with custom world
ros2 launch beetlebot_description gazebo.launch.py \
  world:=/path/to/world.sdf

# Control with keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Visualize in RViz
rviz2

# View TF tree
ros2 run tf2_tools view_frames

# Check simulation topics
ros2 topic list
```

***

#### URDF Quick Edits

```bash
# Copy URDF for testing
cp beetlebot.urdf test.urdf

# Common modifications:
# - Wheel radius: Search for "0.065"
# - Wheelbase: Edit joint xyz positions
# - Sensor height: Edit sensor joint z-values

# Launch with modified URDF
ros2 launch beetlebot_description display.launch.py \
  urdf_file:=$HOME/test.urdf
```

***

**Completed Robot Simulation!** 🎉

→ Continue to Sensor Data Visualization\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 3 of 11 - Beginner Level*\
*Estimated completion time: 85 minutes*
