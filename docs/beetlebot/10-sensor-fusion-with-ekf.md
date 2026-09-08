# Sensor Fusion with EKF

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand why sensor fusion is necessary
* ✅ Learn Extended Kalman Filter (EKF) principles
* ✅ Configure robot\_localization package
* ✅ Fuse wheel odometry with IMU data
* ✅ Compare fused vs. unfused odometry
* ✅ Tune EKF parameters for optimal performance
* ✅ Diagnose fusion issues
* ✅ Understand covariance and uncertainty

#### ⏱️ Time Required

* **Reading & Theory:** 30 minutes
* **Configuration:** 20 minutes
* **Testing & Comparison:** 35 minutes
* **Parameter Tuning:** 25 minutes
* **Advanced Topics:** 20 minutes
* **Total:** \~130 minutes

#### 📚 Prerequisites

* ✅ Completed Sensor Data Visualization
* ✅ Completed IMU Signal Processing
* ✅ Understanding of wheel odometry drift
* ✅ Understanding of IMU characteristics
* ✅ Can visualize data in RViz
* ✅ Can record and analyze rosbags

#### 🛠️ What You'll Need

* ✅ Beetlebot (powered, all sensors working)
* ✅ Laptop with ROS2 Jazzy
* ✅ Wireless controller
* ✅ Open space (5m × 5m minimum)
* ✅ Measuring tape or marked floor
* ✅ Protractor (optional, for angle validation)

***

### Part 1: Why Sensor Fusion?

#### The Problem with Individual Sensors

**Wheel Odometry Alone:**

✅ **Strengths:**

* Accurate short-term (seconds to minutes)
* Provides position (x, y) and orientation (yaw)
* High update rate (20 Hz)
* Not affected by dynamics

❌ **Weaknesses:**

* **Drifts over time** (wheel slip, encoder errors)
* Linear drift: ±3-5% of distance traveled
* Angular drift: ±5-10° per full rotation
* Worse on slippery surfaces
* Turns accumulate most error

***

**IMU Alone:**

✅ **Strengths:**

* Very high update rate (100 Hz)
* Accurate short-term angular velocity
* Not affected by wheel slip
* Detects tilt and acceleration

❌ **Weaknesses:**

* **Cannot measure position directly** (only acceleration)
* Gyro drifts over time (integration error)
* Accelerometer noisy in dynamic motion
* Can't distinguish tilt from acceleration
* No absolute reference (unless magnetometer added)

***

#### The Solution: Sensor Fusion

**Combine strengths, compensate for weaknesses!**

**Key insight:**

* Wheels provide **position** (but drift)
* IMU provides **motion dynamics** (but drifts differently)
* Fusion: Use IMU to **correct wheel slip**, wheels to **bound IMU drift**

**Example scenario:**

```
Robot drives forward 5 meters, then turns 90° left

Wheel odometry says:
  - Position: (4.85, 0.15) ← Should be (5.0, 0.0)
  - Heading: 92° ← Should be 90°
  - Error: Wheel slip during turn

IMU says:
  - Angular velocity integrated: 89.5° ← Close!
  - Position: Cannot calculate (no position sensor)

Fused estimate:
  - Position: (4.93, 0.08) ← Better!
  - Heading: 90.2° ← Much better!
  - Combined error: ~60% reduction
```

***

#### Real-World Benefits

**Without fusion:**

```
Drive 10 meter square:
- Wheel odom final position: 15cm from start
- Heading error: ±8°
```

**With fusion:**

```
Drive 10 meter square:
- Fused odom final position: 6cm from start
- Heading error: ±3°
```

**\~60% error reduction is typical!**

***

### Part 2: Extended Kalman Filter Basics

#### What is a Kalman Filter?

**Simple explanation:**

Imagine you're trying to find your location:

* Your phone GPS says: "You're at (10.5, 20.3)"
* Your step counter says: "You walked 5 meters north"

Which to believe?

**Kalman Filter:**

* Weighs both based on **uncertainty**
* GPS accurate to ±5m? Less trust
* Step counter accurate to ±0.5m? More trust
* Optimal combination: Weighted average

***

#### EKF Algorithm (Simplified)

**Two-step process:**

**1. Prediction Step (Motion Model)**

```
"Based on wheel velocities, robot probably moved forward 0.1m"

Prediction:
  - New position = old position + velocity × time
  - Uncertainty INCREASES (motion is uncertain)
```

**2. Update Step (Measurement)**

```
"IMU says angular velocity was 0.5 rad/s"

Update:
  - Compare prediction to measurement
  - Calculate correction (Kalman Gain)
  - New estimate = prediction + correction
  - Uncertainty DECREASES (measurement adds info)
```

**Repeat at high frequency (20-50 Hz)**

***

#### State Vector

**What does EKF track?**

For Beetlebot:

```
State vector (15 elements):
  - Position: x, y, z (z=0 for ground robot)
  - Orientation: roll, pitch, yaw (Euler angles or quaternion)
  - Linear velocity: vx, vy, vz
  - Angular velocity: ωx, ωy, ωz
  - Linear acceleration: ax, ay, az (optional)
```

**robot\_localization tracks all of these simultaneously!**

***

#### Covariance Matrix

**Uncertainty representation:**

```
Each state variable has uncertainty:
  - x position: ±0.05m
  - y position: ±0.03m
  - yaw: ±0.02 rad

Covariance matrix: 15×15 matrix encoding:
  - Individual uncertainties (diagonal)
  - Correlations between states (off-diagonal)
```

**Visualized in RViz as ellipses:**

* Small ellipse = high certainty
* Large ellipse = low certainty

***

### Part 3: Beetlebot's EKF Configuration

#### Already Running!

**Your robot has EKF pre-configured:**

```bash
# Check if running
ros2 node list | grep ekf

# Should show:
# /ekf_filter_node
```

**Input topics:**

* `/odom` - Wheel odometry (position, velocity)
* `/imu/data` - IMU (orientation, angular velocity, linear acceleration)

**Output topic:**

* `/odometry/filtered` - Fused estimate (best of both!)

***

#### View Current Configuration

```bash
# On robot (via SSH)
cat ~/lyra_ws/src/lyra_bringup/config/ekf.yaml
```

**Key sections:**

```yaml
ekf_filter_node:
  ros__parameters:
    frequency: 30.0  # EKF runs at 30 Hz

    odom0: /odom  # Wheel odometry input
    odom0_config: [true,  true,  false,   # x, y, z (use x,y only)
                   false, false, true,    # roll, pitch, yaw (use yaw only)
                   true,  true,  false,   # vx, vy, vz (use vx, vy)
                   false, false, true,    # ωx, ωy, ωz (use ωz only)
                   false, false, false]   # ax, ay, az (not used)

    imu0: /imu/data  # IMU input
    imu0_config: [false, false, false,   # x, y, z (IMU doesn't provide)
                  true,  true,  true,    # roll, pitch, yaw (use all)
                  false, false, false,   # vx, vy, vz (IMU doesn't provide)
                  true,  true,  true,    # ωx, ωy, ωz (use all)
                  true,  true,  true]    # ax, ay, az (use all)
```

***

#### Understanding the Configuration

**What each sensor contributes:**

**Wheel Odometry (`/odom`):**

* ✅ x position (forward/back)
* ✅ y position (left/right)
* ✅ yaw (heading)
* ✅ vx (forward velocity)
* ✅ vy (sideways velocity)
* ✅ ωz (turn rate)
* ❌ z, roll, pitch (not measured by wheels)

**IMU (`/imu/data`):**

* ✅ roll (tilt side-to-side)
* ✅ pitch (tilt forward/back)
* ✅ yaw (heading - from integrating ωz)
* ✅ ωx, ωy, ωz (all rotation rates)
* ✅ ax, ay, az (accelerations)
* ❌ x, y, z position (can't measure absolute position)

**Fused output (`/odometry/filtered`):**

* ✅ All of the above, optimally combined!

***

### Part 4: Comparing Unfused vs Fused

#### Exercise 7.1: Straight Line Test

**Task:** Measure drift with and without fusion

**Setup:**

```
1. Mark start position
2. Measure exactly 5 meters ahead
3. Mark target position
4. Clear path
```

**Test procedure:**

```bash
# Terminal 1: Record data
ros2 bag record -o straight_line_test /odom /odometry/filtered /imu/data

# Terminal 2: Monitor positions
rqt_plot /odom/pose/pose/position/x /odometry/filtered/pose/pose/position/x

# Drive robot:
1. Start at marked position
2. Drive straight to 5m mark (use measuring tape)
3. Stop at target
4. Stop recording (Ctrl+C)
```

**Analysis:**

```bash
# Play back data
ros2 bag play straight_line_test

# Check final positions:

# Wheel odom:
ros2 topic echo /odom --once | grep "x:"
# Expected: ~4.85 - 5.15 (±3-5% error)

# Fused odom:
ros2 topic echo /odometry/filtered --once | grep "x:"
# Expected: ~4.90 - 5.10 (±2-3% error)

# Improvement: ~40-50% error reduction
```

***

#### Exercise 7.2: Square Path Test

**Task:** Classic odometry test - return to start

**Setup:**

```
1. Mark 2m × 2m square on floor with tape
2. Mark corners clearly
3. Label start position
```

**Test procedure:**

```bash
# Record all data
ros2 bag record -o square_test /odom /odometry/filtered /imu/data /cmd_vel

# Drive square (stay on tape lines):
1. 2m forward
2. Turn 90° left
3. 2m forward
4. Turn 90° left
5. 2m forward
6. Turn 90° left
7. 2m forward
8. Turn 90° left (back to start)

# Stop recording
```

**Analysis:**

```bash
# Play back in RViz
rviz2

# Add two Odometry displays:
# - /odom (color: red)
# - /odometry/filtered (color: green)

# Play bag:
ros2 bag play square_test

# Observe:
# - Red path (unfused): Drifts, doesn't close loop
# - Green path (fused): Much closer to start

# Measure final error:
ros2 topic echo /odom --once
# Note x, y values

ros2 topic echo /odometry/filtered --once
# Note x, y values

# Calculate distance from start (0,0):
# Unfused error: sqrt(x² + y²)
# Fused error: sqrt(x² + y²)
```

**Typical results:**

```
Unfused (/odom):
  - Final position: (0.15, -0.12)
  - Error: 19.2cm from start
  - Heading error: ±8°

Fused (/odometry/filtered):
  - Final position: (0.07, -0.05)
  - Error: 8.6cm from start
  - Heading error: ±3°

Improvement: ~55% error reduction
```

***

#### Exercise 7.3: Rotation Test

**Task:** Spin 360° and check heading drift

**Test procedure:**

```bash
# Record
ros2 bag record -o rotation_test /odom /odometry/filtered /imu/data

# Test:
1. Note starting orientation (use compass or fixed reference)
2. Spin 360° clockwise slowly (~10 seconds for full rotation)
3. Stop exactly at starting orientation
4. Stop recording

# Check heading errors:
ros2 topic echo /odom --once | grep "z:"  # Quaternion z component
ros2 topic echo /odometry/filtered --once | grep "z:"

# Or in RViz, read yaw angle from TF display
```

**Expected results:**

```
Unfused: ±5-8° error after 360°
Fused: ±2-3° error after 360°

Why? IMU corrects gyro bias and wheel slip during rotation
```

***

### Part 5: Visualizing Uncertainty

#### Covariance Ellipses in RViz

**Setup RViz to show uncertainty:**

```bash
rviz2

# Add Odometry displays:

# Unfused odometry:
Add → Odometry
  Topic: /odom
  Covariance: Position (XY)
  Color: Red
  Covariance Color: Pink
  Scale: 2.0

# Fused odometry:
Add → Odometry
  Topic: /odometry/filtered
  Covariance: Position (XY)
  Color: Green
  Covariance Color: Light Green
  Scale: 2.0
```

\[PLACEHOLDER: Screenshot of RViz showing covariance ellipses]

***

#### Interpreting Covariance

**What the ellipses mean:**

**Small ellipse:**

* High confidence in position
* Typical at start or after good measurements

**Large ellipse:**

* Lower confidence
* Grows during motion (prediction step)
* Shrinks when measurements arrive (update step)

**Ellipse shape:**

* Circular: Equal uncertainty in all directions
* Elongated: More uncertain in one direction (e.g., forward motion)

***

#### Exercise 7.4: Watch Uncertainty Grow and Shrink

**Task:** Observe covariance dynamics

```bash
# Setup RViz with covariance displays (as above)

# Test 1: Stationary robot
1. Let robot sit still for 30 seconds
2. Observe: Ellipse stays small (measurements keep refining)

# Test 2: Constant motion
1. Drive straight at constant speed
2. Observe: Ellipse grows (prediction uncertainty accumulates)

# Test 3: Stop and go
1. Drive forward 1m, stop 5 seconds
2. Repeat 5 times
3. Observe: Ellipse grows during motion, shrinks when stopped

# Test 4: Fast turns
1. Spin quickly in place
2. Observe: Large uncertainty spike (rapid dynamics, wheel slip)
```

***

### Part 6: Parameter Tuning

#### When to Tune Parameters

**Default configuration works well for most cases!**

**Consider tuning if:**

* Unusual surface (carpet, gravel, ice)
* Different speeds (very slow or very fast)
* Modified robot (different wheels, weight)
* Specific application needs (prioritize smoothness vs. responsiveness)

***

#### Key Parameters to Tune

**Process Noise Covariance (Q matrix)**

Represents: "How much do we trust the motion model?"

```yaml
process_noise_covariance: [
  0.05,  0.0,   0.0,   ...  # x position variance
  0.0,   0.05,  0.0,   ...  # y position variance
  ...
]
```

**Higher values = "Motion model is unreliable, trust measurements more"** **Lower values = "Motion model is reliable, don't overreact to measurements"**

***

**Measurement Noise (odom0\_relative, imu0\_relative)**

```yaml
# Wheel odometry
odom0_relative: true  # Measure velocity, not absolute position
odom0_differential: false
odom0_queue_size: 10

# IMU
imu0_relative: true  # Measure angular velocity, not absolute orientation
imu0_differential: false
imu0_queue_size: 10
```

***

#### Exercise 7.5: Tune for Slippery Surface

**Scenario:** Robot on smooth tile (more wheel slip)

**Modification:**

```bash
# Edit EKF config
nano ~/lyra_ws/src/lyra_bringup/config/ekf.yaml

# Increase process noise for positions (less trust in wheels)
process_noise_covariance: [
  0.1,   0.0,   0.0,   ...  # x (was 0.05, now 0.1)
  0.0,   0.1,   0.0,   ...  # y (was 0.05, now 0.1)
  ...
]

# Rebuild and restart
cd ~/lyra_ws
colcon build
source install/setup.bash

# Restart robot (power cycle)
```

**Test:** Repeat square test on slippery surface, compare error

***

#### Exercise 7.6: Tune for High-Speed Operation

**Scenario:** Robot operating at max speed (more dynamic)

**Modification:**

```yaml
# Increase EKF frequency for faster updates
frequency: 50.0  # Was 30.0

# Increase process noise for velocities
process_noise_covariance: [
  ...
  0.1,   0.0,   0.0,   ...  # vx (was 0.03)
  0.0,   0.1,   0.0,   ...  # vy (was 0.03)
  ...
]
```

***

### Part 7: Troubleshooting Fusion

#### Problem: Fused Odometry Jumps or Unstable

**Symptoms:** /odometry/filtered has sudden jumps

**Possible causes:**

1. **Sensor disagreement (wheels vs IMU say different things)**

```bash
# Check if sensors agree:
ros2 topic echo /odom --field twist.twist.angular.z
ros2 topic echo /imu/data --field angular_velocity.z

# While turning, both should show similar values
# If wildly different → sensor calibration issue
```

2. **Poor covariance tuning**

```bash
# Check published covariances:
ros2 topic echo /odom --field pose.covariance

# If all zeros or very small → sensors over-trusted
# Solution: Increase measurement noise
```

3. **Transform (TF) issues**

```bash
# Check TF tree
ros2 run tf2_tools view_frames

# Ensure base_link → odom and base_link → imu_link exist
```

***

#### Problem: Fused Estimate Still Drifts

**Not eliminated, just reduced!** Drift is inherent without external reference.

**To further reduce drift:**

1. **Add more sensors**
   * GPS (outdoor)
   * Visual odometry (camera-based)
   * Laser scan matching (AMCL in next tutorial)
2. **Calibrate sensors better**
   * Wheel radius calibration
   * IMU bias calibration (see IMU tutorial)
3. **Tune covariances**
   * Trust best sensor more

***

#### Problem: EKF Node Crashes

**Debug:**

```bash
# Check node status
ros2 node info /ekf_filter_node

# Check for errors
ros2 topic echo /rosout | grep -i ekf

# Common issues:
# - Missing TF frames → check robot_state_publisher
# - Incompatible QoS → verify topic QoS settings
# - Malformed messages → check sensor message validity
```

**Solution: ⚡ Power cycle robot (fixes 90% of issues)**

***

### Part 8: Advanced Topics

#### Two-Stage Fusion (Optional)

**Some systems use:**

**Stage 1: Local fusion (robot frame)**

* Fuse wheel + IMU
* Output: `/odometry/local`

**Stage 2: Global fusion (world frame)**

* Fuse local + GPS/map
* Output: `/odometry/global`

**Beetlebot uses single-stage (sufficient for indoor use)**

***

#### Understanding Frames

**Critical frames:**

```
map (global, fixed)
  └─ odom (local, drifts)
      └─ base_link (robot)
          ├─ imu_link (IMU sensor)
          └─ lidar_link (LiDAR)
```

**Why two odometry frames?**

**odom frame:**

* Robot's local reference
* Continuous, smooth
* Drifts over time
* Used by EKF

**map frame:**

* Global reference
* Corrected by SLAM/localization
* Can jump (when loop closure)
* Used by navigation (next tutorials)

***

#### Quaternions vs Euler Angles

**ROS2 uses quaternions for orientation:**

```
Quaternion: [x, y, z, w]
  - 4 numbers
  - No gimbal lock
  - Math is complex

Euler angles: [roll, pitch, yaw]
  - 3 numbers (easier to understand)
  - Has gimbal lock at ±90° pitch
  - Math is simpler
```

**Convert quaternion → Euler in Python:**

```python
from tf_transformations import euler_from_quaternion

# From odometry message
quat = [msg.pose.pose.orientation.x,
        msg.pose.pose.orientation.y,
        msg.pose.pose.orientation.z,
        msg.pose.pose.orientation.w]

roll, pitch, yaw = euler_from_quaternion(quat)
print(f"Yaw (heading): {yaw * 180 / 3.14159:.1f}°")
```

***

### Part 9: Real-World Applications

#### Application 1: Path Following

**Accurate odometry essential for following paths:**

```python
# With fused odometry, can track path accurately
desired_path = [(0, 0), (1, 0), (1, 1), (0, 1)]
current_pose = get_fused_odometry()

error = calculate_cross_track_error(desired_path, current_pose)
steering_command = pid_controller(error)
```

***

#### Application 2: Return to Home

**Fusion allows reliable "return to start" behavior:**

```python
# Record start position from /odometry/filtered
start_pose = current_pose

# Drive around...

# Return to start:
error_distance = distance(current_pose, start_pose)
error_heading = angle_difference(current_pose, start_pose)

# Navigate back with closed-loop control
```

***

#### Application 3: Multi-Robot Coordination

**Sharing positions between robots requires accurate odometry:**

```python
# Robot 1 publishes position
robot1_pose = fused_odometry  # Accurate

# Robot 2 receives and uses
distance_to_robot1 = distance(robot2_pose, robot1_pose)
if distance_to_robot1 < safe_distance:
    stop()
```

***

### Part 10: Knowledge Check

#### Concept Quiz

1. **Why can't IMU provide position directly?**
2. **What does the Kalman Filter do?**
3. **Why is wheel odometry good short-term but drifts long-term?**
4. **What do covariance ellipses represent?**
5. **Can sensor fusion eliminate drift completely?**

***

#### Hands-On Challenge

**Task:** Quantify fusion improvement

**Requirements:**

1. Drive predetermined 10-meter path (complex: straight, turns, curves)
2. Record /odom and /odometry/filtered
3. Measure final position error for both
4. Calculate improvement percentage
5. Plot both trajectories in RViz
6. Generate report with screenshots and data

**Bonus:**

* Test on multiple surface types
* Compare at different speeds
* Intentionally induce wheel slip (wet floor), measure fusion's correction

***

### Part 11: What You've Learned

#### ✅ Congratulations!

You now understand:

**Sensor Fusion Fundamentals:**

* ✅ Why fusion needed (complementary sensor strengths)
* ✅ Kalman Filter principles (prediction + update)
* ✅ State estimation and covariance
* ✅ How EKF combines wheel odom + IMU

**Practical Skills:**

* ✅ Comparing fused vs unfused odometry
* ✅ Measuring drift reduction (\~40-60%)
* ✅ Visualizing uncertainty (covariance ellipses)
* ✅ Configuring robot\_localization
* ✅ Tuning EKF parameters

**Advanced Concepts:**

* ✅ Process noise vs measurement noise
* ✅ Reference frames (odom vs map)
* ✅ Quaternions and orientations
* ✅ When fusion isn't enough (need SLAM)

***

### Next Steps

#### 🎯 You're Now Ready For:

**Immediate Next:** → SLAM Mapping - Create maps to provide absolute reference

**Advanced Navigation:** → Localization - Use known map to eliminate drift\
→ Autonomous Navigation - Navigate with fused odometry

**Research Topics:**

* Multi-sensor fusion (add cameras, GPS)
* Adaptive filtering (change parameters dynamically)
* Fault detection (identify sensor failures)

***

### Quick Reference

#### Essential Fusion Commands

```bash
# --- Check Fusion Status ---
ros2 node info /ekf_filter_node
ros2 topic hz /odometry/filtered

# --- Compare Odometry Sources ---
ros2 topic echo /odom --field pose.pose.position
ros2 topic echo /odometry/filtered --field pose.pose.position

# --- Visualize in RViz ---
rviz2
# Add Odometry displays for /odom and /odometry/filtered
# Enable covariance display

# --- Plot Time Series ---
rqt_plot /odom/pose/pose/position/x /odometry/filtered/pose/pose/position/x

# --- Record for Analysis ---
ros2 bag record /odom /odometry/filtered /imu/data

# --- Check Configuration ---
cat ~/lyra_ws/src/lyra_bringup/config/ekf.yaml

# --- Restart EKF ---
ros2 lifecycle set /ekf_filter_node deactivate
ros2 lifecycle set /ekf_filter_node activate
```

***

#### Typical Error Reductions

| Test             | Unfused Error | Fused Error | Improvement |
| ---------------- | ------------- | ----------- | ----------- |
| 5m straight      | ±3-5%         | ±2-3%       | \~40%       |
| 2m square        | 15-20cm       | 6-10cm      | \~50%       |
| 360° rotation    | ±5-8°         | ±2-3°       | \~60%       |
| 10m complex path | 20-30cm       | 8-15cm      | \~55%       |

***

**Completed Sensor Fusion with EKF!** 🎉

→ Continue to SLAM Mapping\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 7 of 11 - Advanced Level*\
*Estimated completion time: 130 minutes*
