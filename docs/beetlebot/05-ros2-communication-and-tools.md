# ROS2 Communication & Tools

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand ROS2 communication paradigms (topics, services, actions)
* ✅ List and inspect topics, services, and nodes
* ✅ Publish and subscribe to topics from command line
* ✅ Call services to control robot
* ✅ Use rqt tools for visualization and debugging
* ✅ Record and playback data with rosbags
* ✅ Debug communication issues
* ✅ Understand message types and interfaces

#### ⏱️ Time Required

* **Reading & Concepts:** 25 minutes
* **Command Line Tools:** 30 minutes
* **RQT Tools:** 25 minutes
* **Rosbag Practice:** 20 minutes
* **Debugging:** 15 minutes
* **Total:** \~115 minutes

#### 📚 Prerequisites

* ✅ Completed Getting Started
* ✅ Robot powered on and connected
* ✅ SSH access to robot
* ✅ Basic Linux command line knowledge
* ✅ Understanding of terminal navigation

#### 🛠️ What You'll Need

* ✅ Beetlebot (powered on, base system running)
* ✅ Laptop with ROS2 Jazzy installed
* ✅ Both robot and laptop on same WiFi network
* ✅ Terminal access (SSH to robot or direct)

***

### Part 1: ROS2 Communication Paradigms

#### Topics (Publish-Subscribe)

**What are topics?**

* Continuous data streams
* Many-to-many communication
* Publishers send data, subscribers receive
* Asynchronous (fire-and-forget)

**Example:**

```
LiDAR sensor → publishes → /scan topic → subscribers (SLAM, Nav2, visualization)
```

**When to use:**

* Sensor data (LiDAR, camera, IMU)
* Status updates (battery, position)
* Continuous streams (video, telemetry)

***

#### Services (Request-Response)

**What are services?**

* One-time request-response
* Synchronous (wait for response)
* Client sends request, server responds
* Like function calls

**Example:**

```
Client: "ARM the robot"
Robot service: "OK, motors armed"
```

**When to use:**

* Commands (ARM, DISARM, emergency stop)
* Queries (get parameter, check status)
* One-time actions

***

#### Actions (Goal-Based)

**What are actions?**

* Long-running tasks with feedback
* Can be cancelled
* Provides progress updates
* Goal → Feedback → Result

**Example:**

```
Goal: "Navigate to (x, y)"
Feedback: "50% complete, 10m remaining"
Result: "Goal reached"
```

**When to use:**

* Navigation goals
* Long tasks (mapping, complex motions)
* Need progress updates or cancellation

***

### Part 2: Exploring Your Robot's Topics

#### List All Topics

```bash
ros2 topic list
```

**Your robot has these key topics:**

```
/scan               # LiDAR data
/imu/data           # IMU (filtered)
/imu/data_raw       # IMU (raw)
/wheel/odom         # Wheel-only odometry
/odometry/filtered  # Fused odometry (wheel + IMU via EKF)
/odom               # Same as /odometry/filtered (alias)
/cmd_vel            # Velocity commands (main control)
/cmd_vel_joy        # Velocity from joystick
/cmd_vel_nav        # Velocity from autonomous navigation
/joy                # Raw joystick input
/battery_voltage    # Battery status
/wheel_rpm          # Wheel speeds (RPM)
/wheel_ticks        # Encoder ticks
/pi_camera/image_raw           # Camera images
/pi_camera/image_raw/compressed # Compressed camera
/pi_camera/camera_info         # Camera calibration
/map                # Map from SLAM/map_server
/amcl_pose          # Localization estimate
/particle_cloud     # AMCL particles
/plan               # Global navigation path
/tf                 # Transform tree
/tf_static          # Static transforms
/lyra/armed         # ARM status (bool)
```

***

#### Get Topic Information

```bash
# Check topic type
ros2 topic type /scan
# Output: sensor_msgs/msg/LaserScan

ros2 topic type /cmd_vel
# Output: geometry_msgs/msg/Twist

ros2 topic type /battery_voltage
# Output: std_msgs/msg/Float32

# Check publish rate
ros2 topic hz /scan
# Output: average rate: 10.xxx Hz

ros2 topic hz /odometry/filtered
# Output: average rate: 30.xxx Hz

# Check bandwidth
ros2 topic bw /scan
# Output: average: X.XX MB/s

# Get detailed info
ros2 topic info /cmd_vel
# Output:
# Type: geometry_msgs/msg/Twist
# Publisher count: 3
# Subscription count: 2
```

***

#### Exercise 2.1: Topic Discovery

**Task:** Identify all sensor topics and their rates

```bash
# List all topics, save to file
ros2 topic list > topics.txt

# Check each sensor topic rate:
ros2 topic hz /scan              # LiDAR (should be ~10 Hz)
ros2 topic hz /imu/data          # IMU (should be ~100 Hz)
ros2 topic hz /odometry/filtered # Fused odom (should be ~30 Hz)
ros2 topic hz /wheel/odom        # Wheel odom (should be ~20 Hz)
ros2 topic hz /battery_voltage   # Battery (should be ~1-10 Hz)

# Questions to answer:
# 1. Which sensor has highest rate?
# 2. Which has lowest?
# 3. Why might rates differ?
```

<details>

<summary>Expected Answers</summary>

1. **Highest rate:** IMU (\~100 Hz) - fast dynamics, needs high sampling
2. **Lowest rate:** Battery (\~1-10 Hz) - slow changing, doesn't need frequent updates
3. **Rate differences:** Based on sensor physics and application needs
   * LiDAR: 10 Hz (motor rotation speed)
   * IMU: 100 Hz (capture fast dynamics)
   * Odometry: 20-30 Hz (control loop rate)
   * Battery: 1-10 Hz (slow changing)

</details>

***

### Part 3: Reading Topic Data

#### Echo Topics (View Live Data)

```bash
# View LiDAR data (LOTS of output!)
ros2 topic echo /scan

# Press Ctrl+C to stop

# View single message
ros2 topic echo /scan --once

# View specific field
ros2 topic echo /scan --field ranges --once

# View with limited samples
ros2 topic echo /scan --no-arr  # Don't print arrays (cleaner)
```

***

#### Exercise 2.2: Understanding Sensor Data

**Task:** Examine different sensor message formats

**LiDAR data:**

```bash
ros2 topic echo /scan --once

# Look for:
# - angle_min, angle_max: Scan range (radians)
# - angle_increment: Angular resolution
# - range_min, range_max: Distance limits
# - ranges[]: Array of distance measurements

# Questions:
# 1. How many range measurements per scan?
# 2. What's the angular resolution?
# 3. What's max range?
```

**IMU data:**

```bash
ros2 topic echo /imu/data --once

# Look for:
# - orientation: Quaternion (x, y, z, w)
# - angular_velocity: Rotation rates (rad/s)
# - linear_acceleration: Accelerations (m/s²)

# Questions:
# 1. What's current orientation?
# 2. Is robot moving? (check angular_velocity)
# 3. What's gravity reading? (linear_acceleration.z)
```

**Odometry data:**

```bash
ros2 topic echo /odometry/filtered --once

# Look for:
# - pose.pose.position: (x, y, z) in meters
# - pose.pose.orientation: Quaternion
# - twist.twist.linear: Linear velocity
# - twist.twist.angular: Angular velocity
# - covariance: Uncertainty estimates

# Questions:
# 1. Where is robot? (x, y position)
# 2. Which direction facing? (orientation)
# 3. How fast moving? (linear.x)
```

***

### Part 4: Publishing to Topics

#### Understanding Message Structure

**First, see what a message looks like:**

```bash
ros2 interface show geometry_msgs/msg/Twist

# Output:
# Vector3  linear
#   float64 x
#   float64 y
#   float64 z
# Vector3  angular
#   float64 x
#   float64 y
#   float64 z
```

**For differential drive (Beetlebot):**

* `linear.x`: Forward/backward speed (m/s)
* `angular.z`: Turn rate (rad/s)
* Other fields unused (can't strafe sideways or fly!)

***

#### Publishing Commands

**⚠️ CRITICAL: Command Timeout**

Your robot has a **500ms command timeout**. Commands must be published **continuously** (at least 2 Hz) or the robot will automatically DISARM and stop.

**❌ THIS WILL NOT WORK:**

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
# Robot ignores single command due to timeout!
```

**✅ THIS WORKS:**

```bash
# First, ARM the robot
ros2 service call /lyra/arm std_srvs/srv/Trigger

# Then publish continuously at 10 Hz
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Robot moves forward at 0.3 m/s
# Press Ctrl+C to stop
```

***

#### Exercise 2.3: Manual Robot Control

**Task:** Drive robot using command line

**Test 1: Forward motion**

```bash
# ARM robot
ros2 service call /lyra/arm std_srvs/srv/Trigger

# Drive forward 0.3 m/s
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Let it run for 3 seconds, then Ctrl+C
# Robot should travel ~0.9 meters
```

**Test 2: Rotation**

```bash
# ARM robot (if needed)
ros2 service call /lyra/arm std_srvs/srv/Trigger

# Rotate in place (1.0 rad/s ≈ 57°/s)
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.0}}"

# Let it run for 1.57 seconds for 90° turn
# Then Ctrl+C
```

**Test 3: Arc motion**

```bash
# ARM robot
ros2 service call /lyra/arm std_srvs/srv/Trigger

# Drive in arc (forward + turn)
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"

# Creates curved path
# Ctrl+C to stop
```

**Test 4: Using timeout command**

```bash
# ARM robot
ros2 service call /lyra/arm std_srvs/srv/Trigger

# Drive for exactly 2 seconds then auto-stop
timeout 2 ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# No need for Ctrl+C, stops automatically
```

***

### Part 5: Services

#### List Available Services

```bash
ros2 service list | grep lyra

# Output:
# /lyra/arm
# /lyra/disarm
# /lyra/emergency_stop
```

***

#### Calling Services

**ARM/DISARM robot:**

```bash
# ARM robot (enable motors)
ros2 service call /lyra/arm std_srvs/srv/Trigger

# Output:
# waiting for service to become available...
# requester: making request: std_srvs.srv.Trigger_Request()
#
# response:
# std_srvs.srv.Trigger_Response(success=True, message='Motors armed')

# DISARM robot (disable motors)
ros2 service call /lyra/disarm std_srvs/srv/Trigger

# Output:
# response:
# std_srvs.srv.Trigger_Response(success=True, message='Motors disarmed')

# Emergency stop
ros2 service call /lyra/emergency_stop std_srvs/srv/Trigger

# Output:
# response:
# std_srvs.srv.Trigger_Response(success=True, message='Emergency stop activated')
```

***

#### Check Service Type and Interface

```bash
# Get service type
ros2 service type /lyra/arm
# Output: std_srvs/srv/Trigger

# See interface definition
ros2 interface show std_srvs/srv/Trigger

# Output:
# ---
# bool success     # indicate successful run of triggered service
# string message   # informational, e.g. for error messages
```

***

#### Exercise 2.4: Service Control Flow

**Task:** Test ARM → Drive → DISARM sequence

```bash
# Step 1: Check ARM status
ros2 topic echo /lyra/armed --once
# Expected: data: false

# Step 2: ARM robot
ros2 service call /lyra/arm std_srvs/srv/Trigger
# Expected: success=True

# Step 3: Verify ARMED
ros2 topic echo /lyra/armed --once
# Expected: data: true

# Step 4: Send velocity command
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
# Robot should move

# Step 5: Stop command (Ctrl+C)

# Step 6: Wait 1 second (command timeout)
sleep 1

# Step 7: Check ARM status (should auto-DISARM)
ros2 topic echo /lyra/armed --once
# Expected: data: false (auto-disarmed due to timeout)

# Step 8: Manual DISARM (if still armed)
ros2 service call /lyra/disarm std_srvs/srv/Trigger
```

**What you learned:**

* Robot automatically DISARMs after 500ms without commands
* Must continuously publish commands to maintain motion
* Services provide control over robot state

***

### Part 6: Understanding the Communication Graph

#### Using rqt\_graph

**Visualize node connections:**

```bash
# Launch rqt_graph
rqt_graph

# If graph appears empty:
rqt_graph --force-discover

# Or wait 10-15 seconds for discovery
```

**What you'll see:**

```
Nodes (ovals):
- /joy_node (joystick input)
- /teleop_twist_joy_node (joystick → cmd_vel_joy)
- /joy_teleop_wrapper (ARM/DISARM on button press)
- /lyra_bridge (motor controller bridge)
- /wheel_odometry (encoders → odometry)
- /ekf_filter_node (sensor fusion)
- /sllidar_node (LiDAR driver)

Topics (rectangles):
- /joy
- /cmd_vel_joy
- /cmd_vel
- /odom
- /odometry/filtered
- /scan

Connections (arrows):
- joy_node → /joy → teleop_twist_joy_node
- teleop_twist_joy_node → /cmd_vel_joy → cmd_vel_gate
- cmd_vel_gate → /cmd_vel → lyra_bridge
```

\[PLACEHOLDER: Screenshot of rqt\_graph showing Beetlebot nodes]

***

#### Exercise 2.5: Trace a Command

**Task:** Follow /cmd\_vel from joystick to motors

```bash
# In rqt_graph:
# 1. Find /joy_node (reads USB controller)
# 2. Follow arrow to /joy topic
# 3. Follow to /teleop_twist_joy_node (converts joy → velocity)
# 4. Follow to /cmd_vel_joy topic
# 5. Follow to /cmd_vel_gate (safety checks)
# 6. Follow to /cmd_vel topic
# 7. Follow to /lyra_bridge (sends to STM32)

# Questions:
# 1. How many nodes process joystick input before reaching motors?
# 2. What happens if /cmd_vel_gate node crashes?
# 3. Why separate /cmd_vel_joy and /cmd_vel topics?
```

<details>

<summary>Answers</summary>

1. **3 nodes:** joy\_node → teleop\_twist\_joy\_node → cmd\_vel\_gate → lyra\_bridge
2. **Robot stops:** cmd\_vel\_gate provides safety (ARM check, limits), without it, no commands reach motors
3. **Multiple sources:** /cmd\_vel\_joy (joystick), /cmd\_vel\_nav (autonomous), /cmd\_vel (keyboard/manual) all merge into single /cmd\_vel topic via multiplexer

</details>

***

### Part 7: Recording and Playback (rosbag)

#### Recording Data

**Record specific topics:**

```bash
# Record LiDAR and odometry
ros2 bag record -o test_data /scan /odometry/filtered

# Output:
# [INFO] [rosbag2_storage]: Opened database 'test_data/test_data_0.db3' for writing.
# [INFO] [rosbag2_transport]: Listening for topics...
# [INFO] [rosbag2_transport]: Subscribed to topic '/scan'
# [INFO] [rosbag2_transport]: Subscribed to topic '/odometry/filtered'
# [INFO] [rosbag2_transport]: All requested topics are subscribed. Stopping discovery...

# Drive robot around for 30 seconds
# Press Ctrl+C to stop recording
```

**Record all topics:**

```bash
# Record everything (⚠️ large file!)
ros2 bag record -a -o full_session

# Not recommended for long sessions (GBs of data)
```

**Record with compression:**

```bash
# Compress on-the-fly (smaller files)
ros2 bag record --compression-mode file --compression-format zstd \
  -o compressed_data /scan /odometry/filtered /imu/data
```

***

#### Playback Data

**Play recorded bag:**

```bash
# Info about bag
ros2 bag info test_data

# Output:
# Files:             test_data_0.db3
# Bag size:          15.2 MiB
# Storage id:        sqlite3
# Duration:          30.5s
# Start:             Jan  5 2026 14:30:00.123
# End:               Jan  5 2026 14:30:30.654
# Messages:          3050
# Topic information: Topic: /scan | Type: sensor_msgs/msg/LaserScan | Count: 305 | Serialization Format: cdr
#                    Topic: /odometry/filtered | Type: nav_msgs/msg/Odometry | Count: 915 | Serialization Format: cdr

# Play bag (default speed)
ros2 bag play test_data

# Play at 2x speed
ros2 bag play test_data --rate 2.0

# Play at 0.5x speed (slow motion)
ros2 bag play test_data --rate 0.5

# Play in loop
ros2 bag play test_data --loop

# Play starting from specific time
ros2 bag play test_data --start-offset 5.0  # Skip first 5 seconds
```

***

#### Exercise 2.6: Record and Analyze

**Task:** Record driving session, analyze offline

**Recording:**

```bash
# Record sensors while driving
ros2 bag record -o driving_session \
  /scan /odometry/filtered /imu/data /cmd_vel_joy /battery_voltage

# Drive robot:
# - Forward 2m
# - Turn 90° left
# - Forward 2m
# - Turn 90° left
# - Continue until back at start (square pattern)

# Stop recording (Ctrl+C)
```

**Analysis:**

```bash
# Get bag info
ros2 bag info driving_session

# Play back and visualize
# Terminal 1: Play bag
ros2 bag play driving_session

# Terminal 2: Echo odometry
ros2 topic echo /odometry/filtered --field pose.pose.position

# Terminal 3: Echo velocity commands
ros2 topic echo /cmd_vel_joy

# Questions:
# 1. What was max speed achieved?
# 2. How far did robot drift from start?
# 3. What was battery voltage change?
```

***

### Part 8: RQT Tools

#### rqt\_plot (Time Series)

**Plot data over time:**

```bash
rqt_plot
```

**Add topics to plot:**

```
Topic field 1: /odometry/filtered/pose/pose/position/x
Topic field 2: /odometry/filtered/pose/pose/position/y
Topic field 3: /battery_voltage/data

# See position and battery change over time
```

\[PLACEHOLDER: Screenshot of rqt\_plot showing odometry]

***

#### rqt\_image\_view (Camera)

**View camera stream:**

```bash
rqt_image_view

# Dropdown: Select /pi_camera/image_raw/compressed
# Camera feed appears
```

***

#### rqt\_console (Logs)

**View system logs:**

```bash
rqt_console

# Shows all ROS2 log messages:
# - DEBUG (gray)
# - INFO (white)
# - WARN (yellow)
# - ERROR (red)
# - FATAL (red, bold)

# Filter by node, severity, message content
```

***

#### rqt\_topic (Topic Monitor)

**Monitor multiple topics:**

```bash
rqt_topic

# Shows all topics with:
# - Message type
# - Bandwidth
# - Publish rate
# - Echo current value
```

***

#### Exercise 2.7: Multi-Tool Monitoring

**Task:** Monitor robot with multiple tools

**Setup:**

```bash
# Terminal 1: rqt_plot (position)
rqt_plot /odometry/filtered/pose/pose/position/x:y

# Terminal 2: rqt_console (logs)
rqt_console

# Terminal 3: rqt_topic (monitor)
rqt_topic

# Terminal 4: Drive robot
ros2 service call /lyra/arm std_srvs/srv/Trigger
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

**Observe:**

* rqt\_plot shows position changing
* rqt\_console shows any warnings/errors
* rqt\_topic shows bandwidth and rates

***

### Part 9: Troubleshooting Communication

#### Problem: Topic Not Publishing

**Symptoms:** `ros2 topic hz /scan` shows nothing

**Debug steps:**

```bash
# 1. Check if topic exists
ros2 topic list | grep scan

# 2. Check which nodes publish it
ros2 topic info /scan
# Should show Publisher count > 0

# 3. Check if node is running
ros2 node list | grep sllidar

# 4. Check for errors in logs
ros2 topic echo /rosout | grep -i error

# 5. Power cycle robot
# ⚡ This fixes 90% of issues
```

***

#### Problem: Can't Send Commands

**Symptoms:** Robot doesn't respond to /cmd\_vel

**Debug steps:**

```bash
# 1. Check if ARMED
ros2 topic echo /lyra/armed --once
# If false, ARM it:
ros2 service call /lyra/arm std_srvs/srv/Trigger

# 2. Verify publishing continuously (not --once)
# ❌ Wrong:
ros2 topic pub --once /cmd_vel ...
# ✅ Right:
ros2 topic pub --rate 10 /cmd_vel ...

# 3. Check command timeout (500ms)
# Must publish at least 2 Hz

# 4. Check if another node controlling
ros2 topic info /cmd_vel
# Multiple publishers? One might override

# 5. Check for errors
ros2 topic echo /rosout | grep cmd_vel
```

***

#### Problem: Services Not Responding

**Symptoms:** Service call hangs or fails

```bash
# 1. Check service exists
ros2 service list | grep lyra/arm

# 2. Check node providing service
ros2 service find std_srvs/srv/Trigger

# 3. Check if node alive
ros2 node list | grep lyra_bridge

# 4. Try with timeout
timeout 5 ros2 service call /lyra/arm std_srvs/srv/Trigger

# 5. Restart node or power cycle
```

***

### Part 10: Knowledge Check

#### Concept Quiz

1. **What's the difference between topics and services?**
2. **Why must cmd\_vel be published continuously?**
3. **What does /odometry/filtered provide that /wheel/odom doesn't?**
4. **When would you use rqt\_graph?**
5. **What information does rosbag store?**

***

#### Hands-On Challenge

**Task:** Record, analyze, and report driving behavior

**Requirements:**

1. Record 60-second driving session with:
   * /scan
   * /odometry/filtered
   * /imu/data
   * /cmd\_vel
   * /battery\_voltage
2. Include in recording:
   * Forward motion
   * Rotation in place
   * Arc motion
   * Full stop
3. Analyze recording:
   * Maximum linear velocity achieved
   * Maximum angular velocity achieved
   * Total distance traveled (from odometry)
   * Battery voltage drop
   * Any anomalies (gaps, errors)
4. Create report:
   * Bag file statistics
   * Plots of key data (position, velocity)
   * Summary of findings
   * Recommendations

***

### Part 11: What You've Learned

#### ✅ Congratulations!

You now understand:

**Communication Basics:**

* ✅ Topics, services, and actions
* ✅ When to use each paradigm
* ✅ Publish-subscribe architecture

**Command Line Tools:**

* ✅ Listing and inspecting topics/services/nodes
* ✅ Publishing to topics (with correct --rate!)
* ✅ Calling services
* ✅ Reading topic data

**Robot Control:**

* ✅ ARM/DISARM mechanism
* ✅ Velocity command structure
* ✅ Command timeout (500ms)
* ✅ Safety systems

**Debugging:**

* ✅ rqt\_graph visualization
* ✅ rosbag recording/playback
* ✅ rqt tools (plot, console, topic)
* ✅ Common issues and solutions

***

### Next Steps

#### 🎯 You're Now Ready For:

**Immediate Next:** → Robot Simulation with Gazebo - Test safely in simulation

**Hardware Tutorials:** → Sensor Data Visualization - Deep dive into sensor topics\
→ Teleoperation Control - Advanced driving techniques

**Advanced Topics:**

* Custom node development (Python/C++)
* Message type creation
* Action servers/clients
* Parameter management

***

### Quick Reference

#### Essential Commands

```bash
# --- Topics ---
ros2 topic list                          # List all topics
ros2 topic type /cmd_vel                 # Get message type
ros2 topic hz /scan                      # Check publish rate
ros2 topic echo /odometry/filtered --once # View single message
ros2 topic pub --rate 10 /cmd_vel ...    # Publish continuously

# --- Services ---
ros2 service list | grep lyra            # List robot services
ros2 service type /lyra/arm              # Get service type
ros2 service call /lyra/arm std_srvs/srv/Trigger  # Call service

# --- Nodes ---
ros2 node list                           # List all nodes
ros2 node info /lyra_bridge              # Node details

# --- Recording ---
ros2 bag record -o name /topic1 /topic2  # Record topics
ros2 bag info name                       # Bag statistics
ros2 bag play name                       # Playback

# --- Visualization ---
rqt_graph --force-discover               # Node graph
rqt_plot                                 # Time series
rqt_console                              # Logs
rqt_image_view                           # Camera

# --- Interfaces ---
ros2 interface show geometry_msgs/msg/Twist  # Message structure
ros2 interface show std_srvs/srv/Trigger     # Service structure
```

***

#### Key Topics Reference

| Topic                             | Type            | Rate    | Purpose               |
| --------------------------------- | --------------- | ------- | --------------------- |
| `/cmd_vel`                        | Twist           | 10 Hz   | Main velocity control |
| `/scan`                           | LaserScan       | 10 Hz   | LiDAR data            |
| `/odometry/filtered`              | Odometry        | 30 Hz   | Fused position (EKF)  |
| `/wheel/odom`                     | Odometry        | 20 Hz   | Wheel-only position   |
| `/imu/data`                       | Imu             | 100 Hz  | IMU filtered          |
| `/battery_voltage`                | Float32         | 1-10 Hz | Battery status        |
| `/joy`                            | Joy             | 50 Hz   | Joystick input        |
| `/pi_camera/image_raw/compressed` | CompressedImage | 30 Hz   | Camera stream         |

***

#### Important Services

| Service                | Type    | Purpose        |
| ---------------------- | ------- | -------------- |
| `/lyra/arm`            | Trigger | Enable motors  |
| `/lyra/disarm`         | Trigger | Disable motors |
| `/lyra/emergency_stop` | Trigger | Emergency stop |

***

**Completed ROS2 Communication & Tools!** 🎉

→ Continue to Robot Simulation with Gazebo\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 2 of 11 - Beginner Level*\
*Estimated completion time: 115 minutes*
