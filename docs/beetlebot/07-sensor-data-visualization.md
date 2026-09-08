# Sensor Data Visualization

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Visualize LiDAR scans in real-time with RViz
* ✅ View camera images and understand image topics
* ✅ Monitor IMU data and interpret motion
* ✅ Track wheel odometry and observe drift
* ✅ Use rqt tools for multi-sensor visualization
* ✅ Record sensor data for offline analysis
* ✅ Understand coordinate frames and sensor fusion basics
* ✅ Identify sensor issues through visualization

#### ⏱️ Time Required

* **Reading & Setup:** 15 minutes
* **LiDAR Visualization:** 20 minutes
* **Camera & IMU:** 20 minutes
* **Odometry Analysis:** 15 minutes
* **Multi-Sensor Integration:** 20 minutes
* **Total:** \~90 minutes

#### 📚 Prerequisites

* ✅ Completed ROS2 Communication & Tools
* ✅ System setup complete (laptop ↔ robot communication)
* ✅ Robot powered, connected to WiFi
* ✅ Can see robot's topics from laptop
* ✅ RViz installed on laptop

#### 🛠️ What You'll Need

* ✅ Beetlebot (powered, sensors active)
* ✅ Laptop on same network
* ✅ Wireless controller
* ✅ Open space (3m × 3m minimum)
* ✅ Various objects/obstacles for testing
* ✅ Measuring tape (optional, for validation)

***

### Part 1: Understanding the Sensor Suite

#### Sensors on Beetlebot

**Your robot has 5 sensor systems:**

1. **RPLidar C1** - 360° laser scanner
   * Range: 12m max, 8-10m typical indoors
   * Update rate: 10 Hz
   * Topic: `/scan`
2. **Raspberry Pi Camera V1.3** - Visual perception
   * Resolution: 5MP (2592×1944), typically 1080p/720p
   * Update rate: 30 fps
   * Topics: `/pi_camera/image_raw`, `/pi_camera/camera_info`
3. **LSM6DSRTR IMU** - Motion sensing
   * 6-axis: 3-axis accelerometer + 3-axis gyroscope
   * Update rate: 100 Hz
   * Topics: `/imu/data`, `/imu/data_raw`
4. **Wheel Encoders (4×)** - Position feedback
   * Resolution: 3600 ticks/wheel revolution (900 CPR × X4 quadrature)
   * Update rate: 20 Hz
   * Topics: `/wheel_rpm`, `/wheel_ticks`
5. **Battery Monitor** - Power management
   * Voltage monitoring via ADC
   * Update rate: 10 Hz
   * Topic: `/battery_voltage`

***

#### Sensor Coordinate Frames

**Every sensor has a position and orientation relative to the robot:**

\[PLACEHOLDER: Diagram showing sensor positions on robot]

**Frame hierarchy:**

```
odom (world frame)
  └─ base_link (robot center)
      ├─ lidar_link (8.5cm forward, 20.6cm up)
      ├─ camera_link (15cm forward, 8.8cm up)
      ├─ camera_optical_link (camera's view frame)
      └─ imu_link (center, 2cm down)
```

**Why frames matter:**

* Sensor data is reported in sensor's own frame
* Must transform to common frame for fusion
* RViz needs correct frames to display properly

***

### Part 2: LiDAR Visualization

#### Launch Robot with LiDAR

**On robot (via SSH):**

```bash
# Check if LiDAR already running (auto-launch)
ros2 topic list | grep scan

# If /scan exists, LiDAR is already active
# If not, launch manually:
ros2 launch lyra_bringup lidar.launch.py
```

**Verify LiDAR data:**

```bash
# Check topic rate
ros2 topic hz /scan

# Should show:
# average rate: 10.xxx Hz

# Quick peek at data
ros2 topic echo /scan --once
```

***

#### Visualize LiDAR in RViz

**On laptop:**

```bash
# Launch RViz
rviz2
```

**Configure RViz for LiDAR:**

1. **Set Fixed Frame:**
   * Left panel: Global Options
   * Fixed Frame: Change "map" → **"base\_link"**
2. **Add LaserScan Display:**
   * Bottom left: Click "Add"
   * By topic → `/scan` → LaserScan
   * Click OK
3. **Configure LaserScan Display:**
   * Expand LaserScan in left panel
   * Size (m): **0.05** (point size)
   * Style: **Flat Squares** (easier to see)
   * Color Transformer: **Intensity** or **FlatColor**
   * If Intensity: Color scheme = **Rainbow**

\[PLACEHOLDER: Screenshot of RViz showing LiDAR scan]

**What you see:**

* Red/orange dots = close objects (< 1m)
* Green dots = medium distance (1-3m)
* Blue dots = far objects (3m+)
* Robot center at origin (coordinate axes)

***

#### Exercise 4.1: LiDAR Exploration

**Task:** Understand LiDAR capabilities

**Step 1: Range Test**

```
1. Place robot in clear area
2. Hold flat object (book, clipboard) at various distances
3. Move slowly toward robot from 5m away
4. Watch RViz - when do points appear?

Expected: Points appear around 8-10m indoors, 12m in ideal conditions
```

**Step 2: Resolution Test**

```
1. Place two thin objects (pens) 5cm apart at 2m distance
2. Can LiDAR distinguish them as separate objects?
3. Move to 5m - still separate?

Expected: At 2m, should see gap. At 5m, might merge into one blob.
```

**Step 3: Material Test**

```
1. Test different materials at 1m distance:
   - Flat cardboard (strong return)
   - Mirror/glass (weak/no return)
   - Black fabric (weak return)
   - White wall (strong return)

Expected: Shiny/dark/transparent surfaces give poor returns
```

**What you learned:**

* LiDAR range limitations
* Angular resolution (\~0.5°)
* Material reflectivity affects detection

***

#### Advanced LiDAR Visualization

**Add more information to RViz:**

**1. Robot Model:**

```
Add → RobotModel
- Description Topic: /robot_description
- Now see robot chassis + LiDAR position
```

**2. TF Frames:**

```
Add → TF
- Shows coordinate frames as RGB axes
- See lidar_link position relative to base_link
```

**3. LaserScan with Decay:**

```
LaserScan settings:
- Decay Time: 5 seconds
- Shows last 5 seconds of scans (motion trail)
- Useful for seeing paths through environment
```

\[PLACEHOLDER: Screenshot showing robot model + LiDAR + TF frames]

***

#### Exercise 4.2: Obstacle Detection

**Task:** Map your surroundings

**Setup:**

```
1. Place robot in center of room
2. Configure RViz:
   - Fixed Frame: "odom"
   - Add Odometry display (/odom)
   - Add LaserScan (/scan)
   - LaserScan Decay Time: 30 seconds
```

**Action:**

```
1. Drive robot in complete circle (360°)
2. Drive slowly (0.2 m/s)
3. Watch scan build up in RViz
4. Complete 2-3 circles for good coverage
```

**Observe:**

* Walls appear as solid lines
* Furniture shows as distinct blobs
* Doorways appear as gaps
* Moving objects (people) may appear inconsistent

**Analysis Questions:**

1. Can you identify room shape from scans?
2. Are corners clearly defined?
3. Any areas with no returns? (windows, mirrors)

***

### Part 3: Camera Visualization

#### Camera Topics Overview

**Available topics:**

```bash
ros2 topic list | grep camera

# Output:
# /pi_camera/camera_info
# /pi_camera/image_raw
# /pi_camera/image_raw/compressed
```

**Topic explanations:**

**`/pi_camera/image_raw`** (sensor\_msgs/Image)

* Uncompressed image data
* Large bandwidth (\~30 MB/s at 30fps)
* Best quality
* Use on local network

**`/pi_camera/image_raw/compressed`** (sensor\_msgs/CompressedImage)

* JPEG compressed
* Smaller bandwidth (\~3 MB/s)
* Slight quality loss
* Better for remote viewing

**`/pi_camera/camera_info`** (sensor\_msgs/CameraInfo)

* Camera calibration data
* Lens distortion parameters
* Used for 3D perception

***

#### View Camera Feed

**Method 1: rqt\_image\_view (Simple)**

```bash
# On laptop
ros2 run rqt_image_view rqt_image_view

# Window opens
# Dropdown: Select "/pi_camera/image_raw"
# Image appears!
```

\[PLACEHOLDER: Screenshot of camera view in rqt\_image\_view]

***

**Method 2: RViz (Integrated)**

```bash
# In RViz (already running)
# Add → Camera
# Image Topic: /pi_camera/image_raw
# Camera Info Topic: /pi_camera/camera_info

# New window shows camera view
```

**Benefits of RViz method:**

* See camera + LiDAR simultaneously
* Overlay detection results
* 3D context visible

***

#### Exercise 4.3: Camera Exploration

**Task:** Understand camera capabilities

**Test 1: Field of View**

```
1. Place robot facing wall at 1m distance
2. Measure width of wall visible in camera
3. Calculate horizontal FOV

Expected: ~54° horizontal FOV
Math: FOV = 2 × arctan(width / (2 × distance))
```

**Test 2: Focus Range**

```
1. Hold object at various distances:
   - 10cm (very close)
   - 30cm (near)
   - 1m (medium)
   - 3m+ (far)
2. Which distances are in focus?

Expected: Best focus 30cm - 3m (Pi Camera V1.3 fixed focus)
```

**Test 3: Lighting Conditions**

```
1. Test in bright room (good)
2. Test in dim lighting (auto-adjusts exposure)
3. Test with backlight (camera facing window)
4. Test with point light source (flashlight)

Note effects on image quality
```

***

#### Image Topic Performance

**Check image publishing rate:**

```bash
# Should be 30 fps
ros2 topic hz /pi_camera/image_raw

# If much lower, check:
# 1. Network bandwidth
# 2. Compression settings
# 3. Camera configuration
```

**Bandwidth usage:**

```bash
# Check topic bandwidth
ros2 topic bw /pi_camera/image_raw

# Typical: 30-40 MB/s (uncompressed)
# Compressed: 2-5 MB/s
```

**Use compressed for remote viewing!**

***

### Part 4: IMU Data Visualization

#### IMU Topics

**Available topics:**

```bash
ros2 topic list | grep imu

# Output:
# /imu/data          ← Filtered, calibrated data
# /imu/data_raw      ← Raw sensor readings
```

**Difference:**

* `/imu/data_raw`: Direct from sensor (noisy)
* `/imu/data`: After filtering and calibration (smoother)

**Message contents:**

```
orientation: [x, y, z, w]        ← Quaternion (not directly usable yet)
angular_velocity: [x, y, z]      ← Rotation rates (rad/s)
linear_acceleration: [x, y, z]   ← Accelerations (m/s²)
```

***

#### Visualize IMU in RViz

**Add IMU display:**

```bash
# In RViz
# Add → Imu
# Topic: /imu/data
```

**What you see:**

* Arrow shows acceleration vector
* Box shows orientation
* Color indicates magnitude

\[PLACEHOLDER: Screenshot of IMU visualization in RViz]

***

#### Exercise 4.4: IMU Experimentation

**Task:** Understand IMU measurements

**Test 1: Static Robot**

```
1. Robot sitting still on level ground
2. Echo IMU data:

ros2 topic echo /imu/data --field linear_acceleration

# Expected:
# x: ~0.0 (no forward acceleration)
# y: ~0.0 (no sideways acceleration)
# z: ~9.81 (gravity pulling down!)

# Even stationary, accelerometer reads gravity
```

**Test 2: Forward Acceleration**

```
1. ARM robot, drive forward gently
2. Watch linear_acceleration.x
3. Should spike positive during acceleration
4. Return to ~0 at constant speed
5. Spike negative during braking
```

**Test 3: Rotation**

```
1. Spin robot in place (right stick)
2. Watch angular_velocity.z
3. Positive = counterclockwise
4. Negative = clockwise
5. Magnitude = rotation speed (rad/s)
```

***

#### Plotting IMU Data with rqt\_plot

**Real-time graphing:**

```bash
# Launch rqt_plot
rqt_plot

# Add topics to plot:
# /imu/data/angular_velocity/z
# /imu/data/linear_acceleration/x

# Drive robot - see live graphs!
```

\[PLACEHOLDER: Screenshot of rqt\_plot showing IMU data]

**Try these patterns:**

* Forward → Stop (see accel spike)
* Turn left → Turn right (see angular velocity)
* Figure-8 pattern (see both signals)

***

#### Understanding IMU Noise

**Compare raw vs filtered:**

```bash
# Terminal 1: Raw IMU
ros2 topic echo /imu/data_raw --field angular_velocity

# Terminal 2: Filtered IMU
ros2 topic echo /imu/data --field angular_velocity

# Notice: Raw data is noisy, filtered is smoother
```

**Why filter?**

* Raw sensor has electrical noise
* Quantization errors
* Temperature drift
* Vibrations from motors

**Filtering trade-off:**

* Smoother signal (good for control)
* Slight delay (bad for fast response)

*Next tutorial (IMU Signal Processing) covers filtering in depth!*

***

### Part 5: Wheel Odometry Visualization

#### Odometry Topics

**Available topics:**

```bash
ros2 topic list | grep odom

# Output:
# /odom                    ← Wheel-only odometry
# /wheel/odom             ← Alternative name (same data)
# /odometry/filtered      ← Fused odom (wheel + IMU via EKF)
```

**Key difference:**

* `/odom`: Based only on wheel encoders
* `/odometry/filtered`: Wheel encoders + IMU fusion (better!)

***

#### Visualize Odometry

**Add to RViz:**

```bash
# Already in RViz
# Add → Odometry
# Topic: /odometry/filtered
```

**Configuration:**

```
Odometry Display settings:
- Covariance: Keep Last 50
- Position Tolerance: 0.1
- Angle Tolerance: 0.1
- Color: 25, 255, 0 (green)
```

**What you see:**

* Green arrow = robot's pose (position + orientation)
* Ellipse = uncertainty covariance
* Trail = path history

\[PLACEHOLDER: Screenshot of odometry trail in RViz]

***

#### Exercise 4.5: Odometry Drift Observation

**Task:** Measure odometry accuracy

**Test 1: Straight Line**

```
Setup:
1. Mark starting position with tape
2. Measure exactly 2 meters ahead
3. Mark target position

Procedure:
1. Reset odometry (power cycle robot)
2. Record starting odom:
   ros2 topic echo /odom --once
3. Drive exactly to 2m mark (use tape as guide)
4. Record ending odom
5. Compare:
   - Odometry says: X meters
   - Reality is: 2.000 meters
   - Error: ____%

Expected error: ±3-5% (1.94-2.06m reported)
```

**Test 2: Square Path**

```
Setup:
1. Mark 1m × 1m square on floor with tape

Procedure:
1. Start at corner
2. Drive square: 1m forward, turn 90° left, repeat 4×
3. Should return to start
4. Measure final position error

Expected: upto 50cm drift after 4m + 4 turns
Why drift? Wheel slip during turns, encoder quantization
```

**Test 3: Rotation**

```
Procedure:
1. Note starting orientation (use compass or fixed reference)
2. Spin 360° in place (count full rotations)
3. Check final orientation

Expected: ±5-20° error after full rotation
Why? Wheelbase calibration, floor friction variations
```

***

#### Comparing Wheel vs Fused Odometry

**Plot both simultaneously:**

```bash
# Terminal 1
rqt_plot /odom/pose/pose/position/x /odometry/filtered/pose/pose/position/x

# Drive robot forward slowly
# See how trajectories compare
```

**Typically observe:**

* `/odometry/filtered` is smoother (IMU helps)
* `/odom` may have small jumps (encoder quantization)
* Both drift over time, but fused drifts less

***

### Part 6: Multi-Sensor Visualization

#### The Complete Perception Picture

**Configure RViz with all sensors:**

**Displays to add:**

1. ✅ RobotModel (`/robot_description`)
2. ✅ LaserScan (`/scan`)
3. ✅ Camera (`/pi_camera/image_raw`)
4. ✅ Imu (`/imu/data`)
5. ✅ Odometry (`/odometry/filtered`)
6. ✅ TF (coordinate frames)

**Save configuration:**

```
File → Save Config As
Save to: ~/beetlebot_full.rviz

# Next time:
rviz2 -d ~/beetlebot_full.rviz
```

\[PLACEHOLDER: Screenshot of RViz with all sensors displayed]

***

#### Exercise 4.6: Multi-Sensor Correlation

**Task:** See how sensors relate during motion

**Setup:**

```
1. Launch full RViz config (all sensors)
2. Position robot facing open space with obstacles
3. Arrange RViz windows:
   - Main 3D view: Large, showing LiDAR + robot
   - Camera view: Smaller, top-right corner
   - IMU: Visible in 3D view
```

**Test Scenario:**

```
1. Drive toward obstacle
2. Observe simultaneously:
   - LiDAR: Points getting closer (red/orange)
   - Camera: Object getting larger
   - Odometry: Position advancing
   - IMU: Acceleration spike when starting

3. Stop before obstacle
4. Turn 90° left
5. Observe:
   - LiDAR: Scan rotates (walls move)
   - Camera: View rotates
   - IMU: angular_velocity.z spikes
   - Odometry: Orientation changes

6. Drive parallel to wall
7. Observe:
   - LiDAR: Wall appears as flat line at constant distance
   - Camera: May or may not see wall (depends on position)
   - Odometry: Smooth trajectory
```

**Questions to answer:**

1. Do all sensors agree on motion?
2. Which sensor updates fastest? (IMU: 100Hz)
3. Which is most accurate for distance? (LiDAR)
4. Which gives most information? (Camera: colors, textures)

***

### Part 7: Recording Sensor Data

#### Why Record Data?

**Use cases:**

* **Debugging:** Replay issues offline
* **Analysis:** Process data in Python/MATLAB
* **Sharing:** Send to colleagues/support
* **Comparison:** Before/after calibration
* **Development:** Train ML models
* **Documentation:** Demonstrate capabilities

***

#### Recording with ros2 bag

**Record all sensors:**

```bash
# Record everything
ros2 bag record -a -o full_sensor_test

# Or record specific topics (smaller file):
ros2 bag record -o sensor_test \
  /scan \
  /pi_camera/image_raw/compressed \
  /imu/data \
  /odometry/filtered \
  /wheel_rpm \
  /battery_voltage
```

**While recording:**

* Drive predetermined path (square, circle)
* Test various speeds
* Include static periods
* Document what you're testing

**Stop recording:** Ctrl+C

***

#### Analyzing Recorded Data

**Get bag info:**

```bash
ros2 bag info sensor_test

# Shows:
# Duration: 45.3s
# Start: Jan 05 2026 15:23:10
# End: Jan 05 2026 15:23:55
# Messages: 8452
# Topics:
#   /scan: 453 messages (10 Hz)
#   /imu/data: 4530 messages (100 Hz)
#   ...
```

**Play back data:**

```bash
# Play at normal speed
ros2 bag play sensor_test

# Play at half speed (better for observation)
ros2 bag play sensor_test --rate 0.5

# Play specific time range
ros2 bag play sensor_test --start-offset 10 --duration 15
```

**While playing back:**

* RViz visualizes as if robot was live
* Can pause, rewind (by replaying)
* No robot needed!

***

#### Exercise 4.7: Data Collection Project

**Task:** Record and analyze driving patterns

**Collect data:**

```bash
# Test 1: Straight line at 0.3 m/s
ros2 bag record -o straight_slow /odom /wheel_rpm /imu/data
# Drive 3 meters straight
# Stop recording

# Test 2: Straight line at 0.8 m/s (faster)
ros2 bag record -o straight_fast /odom /wheel_rpm /imu/data
# Drive 3 meters straight (faster)
# Stop recording

# Test 3: Figure-8 pattern
ros2 bag record -o figure8 /odom /wheel_rpm /imu/data
# Drive smooth figure-8
# Stop recording
```

**Analyze:**

```bash
# Play back and compare in RViz
ros2 bag play straight_slow
# Note final position error

ros2 bag play straight_fast
# Compare error to slow speed

ros2 bag play figure8
# Observe complex trajectory

# Questions:
# 1. Which test had most odometry drift?
# 2. Did faster speed increase error?
# 3. How smooth were the curves in figure-8?
```

***

### Part 8: Diagnostic Tools

#### rqt\_multiplot - Advanced Plotting

**Install (if not already):**

```bash
sudo apt install ros-jazzy-rqt-multiplot
```

**Launch:**

```bash
rqt_multiplot
```

**Create multi-panel plots:**

```
Panel 1: IMU angular velocity (all axes)
- /imu/data/angular_velocity/x
- /imu/data/angular_velocity/y
- /imu/data/angular_velocity/z

Panel 2: Wheel speeds
- /wheel_rpm (all 4 wheels if available)

Panel 3: Battery voltage
- /battery_voltage
```

\[PLACEHOLDER: Screenshot of rqt\_multiplot with 3 panels]

**Use case:**

* Monitor all critical sensors at once
* Spot correlations between signals
* Detect anomalies

***

#### rqt\_robot\_monitor - System Health

```bash
rqt_robot_monitor
```

**Shows:**

* Battery status
* Motor health
* Sensor connectivity
* System warnings

**Set up alerts:**

* Low battery warning (<10.5V)
* Sensor timeout warnings
* Motor fault detection

***

#### Custom Monitoring Script

**Create battery alert script:**

```bash
nano ~/sensor_monitor.sh
```

**Script content:**

```bash
#!/bin/bash

while true; do
  # Battery
  BAT=$(ros2 topic echo /battery_voltage --once 2>/dev/null)

  # LiDAR rate
  LIDAR=$(ros2 topic hz /scan --window 10 2>/dev/null | grep average | awk '{print $3}')

  # IMU rate
  IMU=$(ros2 topic hz /imu/data --window 10 2>/dev/null | grep average | awk '{print $3}')

  echo "=== Sensor Status ==="
  echo "Battery: ${BAT}V"
  echo "LiDAR: ${LIDAR} Hz"
  echo "IMU: ${IMU} Hz"

  # Alert if any issues
  if (( $(echo "$BAT < 10.5" | bc -l) )); then
    echo "⚠️  LOW BATTERY!"
  fi

  if (( $(echo "$LIDAR < 8" | bc -l) )); then
    echo "⚠️  LiDAR rate low!"
  fi

  sleep 5
done
```

**Run:**

```bash
chmod +x ~/sensor_monitor.sh
./sensor_monitor.sh
```

***

### Part 9: Troubleshooting Sensor Issues

#### LiDAR Not Publishing

**Symptoms:** `/scan` topic not appearing

**Debug steps:**

```bash
# 1. Check if LiDAR node running
ros2 node list | grep rplidar

# 2. Check USB connection
lsusb | grep CP2102
# Should show Silicon Labs CP2102 (LiDAR USB chip)

# 3. Check permissions
ls -l /dev/ttyUSB*
# Should show device exists

# 4. Restart LiDAR node
ros2 lifecycle set /rplidar_node configure
ros2 lifecycle set /rplidar_node activate
```

**If still not working: ⚡ Power cycle robot**

***

#### Camera Not Streaming

**Symptoms:** No image in rqt\_image\_view

**Debug steps:**

```bash
# 1. Check if camera detected
ls /dev/video*
# Should show /dev/video0

# 2. Test with v4l2
v4l2-ctl --list-devices

# 3. Check topic publishing
ros2 topic hz /pi_camera/image_raw

# 4. Check bandwidth (may be too slow over WiFi)
ros2 topic bw /pi_camera/image_raw

# Try compressed:
ros2 run rqt_image_view rqt_image_view /pi_camera/image_raw/compressed
```

**If still not working: ⚡ Power cycle robot**

***

#### IMU Data Frozen

**Symptoms:** IMU values not changing

**Debug steps:**

```bash
# 1. Check topic rate
ros2 topic hz /imu/data
# Should be ~100 Hz

# 2. Check for errors
ros2 topic echo /rosout | grep -i imu

# 3. Check I2C connection (on robot via SSH)
sudo i2cdetect -y 1
# Should show device at address 0x6B
```

**If still not working: ⚡ Power cycle robot**

***

#### Odometry Looks Wrong

**Symptoms:** Robot drifting wildly in RViz

**Check:**

```bash
# 1. Verify encoders working
ros2 topic echo /wheel_ticks

# Drive robot - ticks should increase

# 2. Check for reversed wheels
# Left wheels should have negative ticks going forward
# Right wheels should have positive ticks going forward

# 3. Verify wheel parameters
ros2 param get /lyra_node wheel_radius
ros2 param get /lyra_node wheelbase

# Should match: 0.065m radius, 0.295m wheelbase
```

**If still not working: ⚡ Power cycle robot**

***

#### General Sensor Troubleshooting

**Most sensor issues fixed by:**

1. ⚡ **Power cycle robot** (90% of issues)
2. Check topic rates (`ros2 topic hz`)
3. Check for error messages (`ros2 topic echo /rosout`)
4. Verify nodes running (`ros2 node list`)
5. Check network connectivity (WiFi signal strength)

***

### Part 10: Knowledge Check

#### Concept Quiz

1. **Which sensor has the highest update rate?**
2. **Why does odometry drift over time?**
3. **What's the difference between /imu/data and /imu/data\_raw?**
4. **Why use compressed images instead of raw?**
5. **Which sensor is best for measuring distance to obstacles?**

***

#### Hands-On Challenge

**Task:** Create sensor validation report

**Requirements:**

1. Record 2-minute rosbag with all sensors
2. Play back and screenshot each sensor view
3. Create report with:
   * LiDAR: Max range observed
   * Camera: Field of view measurement
   * IMU: Acceleration range during maneuvers
   * Odometry: Final drift after 5m × 5m square

**Deliverable:**

* Rosbag file
* Screenshots (4-5 images)
* Text report with measurements

***

### Part 11: What You've Learned

#### ✅ Congratulations!

You now understand:

**Sensor Capabilities:**

* ✅ LiDAR: Range, resolution, materials
* ✅ Camera: FOV, focus, lighting effects
* ✅ IMU: Acceleration, rotation sensing
* ✅ Odometry: Position tracking and drift

**Visualization Tools:**

* ✅ RViz configuration for all sensors
* ✅ rqt\_image\_view for camera
* ✅ rqt\_plot for time-series data
* ✅ Multi-sensor displays

**Data Management:**

* ✅ Recording rosbags
* ✅ Playing back data
* ✅ Offline analysis
* ✅ Sharing sensor data

**Troubleshooting:**

* ✅ Diagnosing sensor issues
* ✅ Checking topic health
* ✅ Common problems and solutions

***

### Next Steps

#### 🎯 You're Now Ready For:

**Immediate Next:** → IMU Signal Processing - Filter noisy IMU data, extract orientation

**Sensor Applications:** → Teleoperation Control - Use sensors for feedback\
→ SLAM Mapping - Build maps with LiDAR\
→ Autonomous Navigation - Sensor-based obstacle avoidance

**Advanced Topics:**

* Sensor calibration
* Multi-sensor fusion
* Custom sensor integration

***

### Quick Reference

#### Essential Visualization Commands

```bash
# --- RViz ---
rviz2                                    # Launch
rviz2 -d config.rviz                    # Load config

# --- Camera ---
ros2 run rqt_image_view rqt_image_view  # View images
# Topic: /pi_camera/image_raw/compressed (use compressed!)

# --- Plotting ---
rqt_plot /imu/data/angular_velocity/z   # Plot single topic
rqt_multiplot                            # Advanced plotting

# --- Recording ---
ros2 bag record -a                       # Record all
ros2 bag record /scan /odom /imu/data   # Record specific
ros2 bag play bagfile                    # Play back
ros2 bag info bagfile                    # Get info

# --- Topic Monitoring ---
ros2 topic hz /scan                      # Check rate
ros2 topic bw /pi_camera/image_raw      # Check bandwidth
ros2 topic echo /imu/data --once        # Quick peek

# --- Troubleshooting ---
ros2 node list                           # Check nodes
ros2 topic list                          # Check topics
```

***

#### Typical Sensor Rates

| Sensor              | Topic                             | Rate   | Bandwidth  |
| ------------------- | --------------------------------- | ------ | ---------- |
| LiDAR               | `/scan`                           | 10 Hz  | \~50 KB/s  |
| Camera (raw)        | `/pi_camera/image_raw`            | 30 Hz  | 30-40 MB/s |
| Camera (compressed) | `/pi_camera/image_raw/compressed` | 30 Hz  | 2-5 MB/s   |
| IMU                 | `/imu/data`                       | 100 Hz | \~10 KB/s  |
| Odometry            | `/odometry/filtered`              | 20 Hz  | \~5 KB/s   |
| Encoders            | `/wheel_rpm`                      | 20 Hz  | \~2 KB/s   |
| Battery             | `/battery_voltage`                | 10 Hz  | <1 KB/s    |

***

**Completed Sensor Data Visualization!** 🎉

→ Continue to IMU Signal Processing\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 4 of 11 - Intermediate Level*\
*Estimated completion time: 90 minutes*
