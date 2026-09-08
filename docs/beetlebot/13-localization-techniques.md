# Localization Techniques

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand localization vs SLAM
* ✅ Use AMCL (Adaptive Monte Carlo Localization)
* ✅ Initialize robot pose on known map
* ✅ Monitor localization quality
* ✅ Recover from kidnapped robot problem
* ✅ Tune AMCL parameters
* ✅ Compare localization methods
* ✅ Troubleshoot localization failures

#### ⏱️ Time Required

* **Reading & Theory:** 25 minutes
* **Setup & First Localization:** 30 minutes
* **Quality Assessment:** 25 minutes
* **Parameter Tuning:** 30 minutes
* **Advanced Scenarios:** 35 minutes
* **Total:** \~145 minutes

#### 📚 Prerequisites

* ✅ Completed SLAM Mapping
* ✅ Have at least one saved map
* ✅ Understanding of particle filters (helpful)
* ✅ Completed Sensor Fusion with EKF
* ✅ Can drive robot smoothly
* ✅ Can visualize in RViz

#### 🛠️ What You'll Need

* ✅ Beetlebot (fully charged)
* ✅ Laptop with ROS2 Jazzy
* ✅ Wireless controller
* ✅ Previously created map files (.pgm + .yaml)
* ✅ Mapped environment (unchanged since mapping)
* ✅ Clear space to operate

***

### Part 1: Localization Fundamentals

#### What is Localization?

**Definition:** Determining robot's position on a **known** map

**Key difference from SLAM:**

| Aspect         | SLAM                    | Localization               |
| -------------- | ----------------------- | -------------------------- |
| **Map**        | Unknown (building it)   | Known (already have it)    |
| **Position**   | Unknown (estimating it) | Unknown (estimating it)    |
| **Complexity** | High (2 unknowns)       | Medium (1 unknown)         |
| **Accuracy**   | Good (but drifts)       | Excellent (bounded by map) |
| **Use Case**   | Exploring new areas     | Operating in known areas   |

**Why localization matters:**

* Navigation requires knowing position on map
* Planning paths needs current location
* Avoid obstacles relative to map
* Return to specific locations (charging station, home)

***

#### The Three Localization Problems

**1. Position Tracking**

* Know approximate starting position
* Track motion from there
* Easiest problem
* Example: Start at (0, 0), track from there

**2. Global Localization**

* No idea where robot is on map
* Must determine position from scratch
* Harder problem
* Example: Robot placed randomly in environment

**3. Kidnapped Robot**

* Robot localized, then suddenly moved
* Must detect and recover
* Hardest problem
* Example: Robot picked up and moved while running

**AMCL handles all three!** (with varying difficulty)

***

#### Particle Filter Concept

**How AMCL works:**

**Particles = Hypotheses about robot position**

```
Each particle represents:
  - x position
  - y position
  - θ orientation (yaw)
  - Weight (how likely this hypothesis is)

Initial: 1000s of particles spread across map
Motion: Particles move based on odometry
Measurement: Particles weighted by scan match quality
Resampling: Keep good particles, discard bad ones
Converged: Particles cluster around true position
```

**Visual analogy:**

* Start: Particle cloud covers entire map (no idea where robot is)
* Drive: Cloud moves and spreads (motion uncertainty)
* See wall: Particles near walls get high weight
* Resample: Cloud shrinks toward high-weight area
* Converged: Tight cluster = confident position estimate

\[PLACEHOLDER: Diagram showing particle filter convergence]

***

### Part 2: Setting Up AMCL

#### Install AMCL (if not already)

```bash
# Check if installed
ros2 pkg list | grep nav2_amcl

# If not installed:
sudo apt install ros-jazzy-nav2-amcl
```

***

#### Load Your Map

**First, you need a map running:**

```bash
# On robot (via SSH) or laptop
cd ~/maps  # Directory where you saved maps

# Launch map server
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=$(pwd)/my_first_map.yaml

# Verify map loaded
ros2 topic echo /map_metadata --once
```

**In another terminal, verify in RViz:**

```bash
rviz2

# Configure:
# Fixed Frame: "map"
# Add → Map
#   Topic: /map
#
# You should see your saved map!
```

***

#### Launch AMCL

**Your robot likely has AMCL configured to launch automatically with navigation. Check:**

```bash
ros2 node list | grep amcl

# If running, should show:
# /amcl

# If not running, launch manually:
ros2 launch lyra_bringup localization.launch.py map:=$(pwd)/my_first_map.yaml
```

**What AMCL does:**

* Subscribes to: `/scan` (LiDAR), `/odom` (wheel odometry)
* Publishes: `/amcl_pose` (estimated position)
* Provides: `map` → `odom` transform
* Updates: Particle cloud on `/particlecloud`

***

#### Configure RViz for Localization

**Full RViz setup:**

```
1. Fixed Frame: "map"

2. Add Map:
   Topic: /map
   Color Scheme: map

3. Add LaserScan:
   Topic: /scan
   Color: Red
   Size: 0.05

4. Add PoseArray (particle cloud):
   Topic: /particlecloud
   Arrow Length: 0.15
   Color: Green (shows particle hypotheses)

5. Add PoseWithCovariance (robot pose):
   Topic: /amcl_pose
   Covariance: Position
   Color: Blue
   Shaft Length: 0.5
   Head Length: 0.2

6. Add RobotModel:
   Description Topic: /robot_description

7. Add TF:
   Show Names: true (helps debugging)
```

\[PLACEHOLDER: Screenshot of RViz configured for localization]

***

### Part 3: Initial Pose Estimation

#### Setting Initial Pose

**Robot needs to know approximate starting position:**

**Method 1: 2D Pose Estimate (RViz)**

```
1. In RViz, click "2D Pose Estimate" button (top toolbar)
2. Click on map where robot actually is
3. Drag to set orientation
4. Release

Particle cloud should appear around that position
```

**Method 2: Command Line**

```bash
ros2 topic pub --once /initialpose geometry_msgs/PoseWithCovarianceStamped "
header:
  frame_id: 'map'
pose:
  pose:
    position: {x: 0.0, y: 0.0, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
  covariance: [0.25, 0.0, 0.0, 0.0, 0.0, 0.0,
               0.0, 0.25, 0.0, 0.0, 0.0, 0.0,
               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
               0.0, 0.0, 0.0, 0.0, 0.0, 0.06854]"
```

**Method 3: Known Position (Launch File)**

```bash
# If you always start at same location, can set in config
# Edit AMCL config file to set initial_pose_x, initial_pose_y, initial_pose_a
```

***

#### Convergence Process

**After setting initial pose:**

```
1. Particles spread around initial estimate
2. Drive robot slowly (0.3 m/s)
3. AMCL compares scans to map
4. Particles converge toward true position
5. Usually takes 10-30 seconds of motion
6. Final cluster = confident estimate
```

**Signs of convergence:**

* ✅ Particle cloud shrinks (concentrated)
* ✅ LiDAR scans align with map walls
* ✅ Robot model stays aligned on map
* ✅ Covariance ellipse small

**Signs of divergence (failure):**

* ❌ Particles spread apart
* ❌ Scans don't match map
* ❌ Robot drifting on map
* ❌ Multiple particle clusters

***

#### Exercise 10.1: First Localization

**Task:** Successfully localize robot

**Procedure:**

```
Setup:
1. Ensure robot in mapped environment
2. Launch map server with saved map
3. Launch AMCL
4. Open RViz (configured as above)

Localization:
1. Identify robot's actual position in environment
2. Set 2D Pose Estimate in RViz (approximately correct)
3. Drive robot forward slowly (~0.3 m/s)
4. Watch particle cloud converge
5. Drive in small circle
6. Observe particles clustering

Success criteria:
- Particle cloud < 0.5m diameter
- LiDAR scans align with map walls
- Robot position stable (not drifting)
```

**Estimated time:** 2-3 minutes to converge

***

### Part 4: Monitoring Localization Quality

#### Particle Cloud Size

**Check particle spread:**

```bash
# View particle cloud
ros2 topic echo /particlecloud --once

# Count particles (typically 500-2000)
# Check spread (distance between farthest particles)
```

**Interpretation:**

* Small, tight cloud = good localization
* Large, spread cloud = uncertain localization
* Multiple clusters = ambiguous (similar features)

***

#### Covariance (Uncertainty)

**Check pose covariance:**

```bash
ros2 topic echo /amcl_pose --once

# Look at covariance matrix (36 values)
# Main diagonal values indicate uncertainty:
# [0]: x variance (m²)
# [7]: y variance (m²)
# [35]: yaw variance (rad²)
```

**Good values:**

```
x, y variance: < 0.01 (±10cm standard deviation)
yaw variance: < 0.01 (±5.7° standard deviation)
```

**Poor values:**

```
x, y variance: > 0.1 (±30cm+ standard deviation)
yaw variance: > 0.05 (±12.8°+ standard deviation)
```

***

#### Visual Alignment Check

**In RViz, verify:**

1. **Scan alignment:**
   * LiDAR red dots should overlay map walls
   * Corners should line up precisely
   * Doorways should match
2. **Robot model position:**
   * Should be inside free space (white)
   * Not inside walls (black)
   * Realistic position in environment
3. **Motion consistency:**
   * Drive forward → robot moves forward on map
   * Turn left → robot rotates left on map
   * No jumping or jittering

\[PLACEHOLDER: Screenshot showing good vs poor alignment]

***

#### Exercise 10.2: Quality Assessment

**Task:** Quantify localization quality

**Test scenarios:**

**Scenario 1: Good localization**

```
1. Localize in open area with clear wall features
2. Record covariance values
3. Drive square pattern, return to start
4. Measure final position error

Expected:
- Covariance < 0.01
- Final error < 10cm
```

**Scenario 2: Ambiguous localization**

```
1. Localize in symmetric area (long hallway, square room)
2. Record covariance values
3. Note multiple particle clusters?

Expected:
- Higher covariance (0.01-0.05)
- Particles may split into multiple clusters
```

**Scenario 3: Featureless area**

```
1. Drive into large open area (minimal walls visible)
2. Watch covariance grow
3. Return to feature-rich area
4. Watch covariance shrink again

Expected:
- Covariance increases in open areas
- Decreases near walls/corners
```

***

### Part 5: Global Localization

#### No Initial Pose

**Challenge:** Robot doesn't know where it is at all

**AMCL solution:** Spread particles across **entire** map

**Launch with global localization:**

```bash
# Stop AMCL if running
ros2 lifecycle set /amcl deactivate

# Restart with global localization parameters
ros2 param set /amcl global_localization_min_particles 5000
ros2 param set /amcl initial_pose_x 0.0
ros2 param set /amcl initial_pose_y 0.0
ros2 param set /amcl initial_pose_a 0.0

# Or launch with global config:
ros2 launch lyra_bringup localization.launch.py \
  map:=my_map.yaml \
  global_localization:=true
```

***

#### Convergence Strategy

**How to help global localization converge:**

```
1. Start in area with distinctive features
   - Near corners (not in middle of hallway)
   - Near unique furniture arrangement
   - Avoid symmetric locations

2. Rotate in place (360°)
   - Gives AMCL views of surroundings
   - Eliminates particles facing wrong directions
   - Usually converges after 1-2 rotations

3. Drive toward distinctive features
   - Doorways, corners, specific furniture
   - Helps disambiguate position

4. Watch particle cloud collapse
   - May take 30-60 seconds
   - Multiple clusters at first
   - Eventually single cluster remains
```

***

#### Exercise 10.3: Global Localization Challenge

**Task:** Localize without initial pose

**Procedure:**

```
Setup:
1. Launch AMCL with global localization
2. Robot at unknown position
3. DO NOT set initial pose estimate

Challenge:
1. Observe particle cloud (covers entire map)
2. Rotate in place 360° (slowly)
3. Watch particles collapse
4. If multiple clusters remain:
   - Drive toward nearest corner
   - Rotate again
5. Repeat until converged

Success:
- Single tight particle cluster
- Scans align with map
- Covariance < 0.02
```

**Typical time:** 1-3 minutes

***

### Part 6: Kidnapped Robot Problem

#### What is Kidnapped Robot?

**Scenario:**

```
1. Robot localized and driving
2. Someone picks up robot
3. Moves it to different location
4. Sets it down
5. Robot still thinks it's at old location!
```

**Challenge:** Detect this happened and re-localize

***

#### AMCL's Recovery

**How AMCL detects kidnapping:**

1. **Scan mismatch increases**
   * LiDAR sees walls that shouldn't be there
   * Particle weights drop dramatically
2. **Insert random particles**
   * AMCL periodically adds random particles
   * If one matches new location, it survives
   * Others die off quickly
3. **Recovery mode triggered**
   * Increases particle spread
   * Accelerates resampling
   * Similar to mini global localization

**Parameters controlling recovery:**

```yaml
# In AMCL config
recovery_alpha_slow: 0.001  # Slow average weight decay
recovery_alpha_fast: 0.1    # Fast average weight decay

# If fast_avg < slow_avg: Possible kidnapping!
```

***

#### Exercise 10.4: Kidnapped Robot Test

**Task:** Force and recover from kidnapping

**Procedure:**

```
Setup:
1. Localize robot normally (converged)
2. Drive around briefly to confirm stable

Kidnapping:
1. While robot stationary, pick it up physically
2. Move to completely different location (>2m away)
3. Set down facing different direction
4. Resume driving

Observe:
1. Initial confusion (scans don't match)
2. Particle cloud starts spreading
3. Random particles appear at new location
4. Gradual convergence to correct position
5. Recovery complete (scans align again)

Expected recovery time: 30-90 seconds
```

***

### Part 7: Parameter Tuning

#### Key AMCL Parameters

**Particle filter parameters:**

```yaml
# Number of particles
min_particles: 500           # Minimum
max_particles: 5000          # Maximum

# More particles:
#   + Better global localization
#   + Better accuracy
#   - Slower computation

# Resampling
resample_interval: 1         # Resample every N updates

# Motion model (how much to trust odometry)
odom_alpha1: 0.2            # Rotation noise from rotation
odom_alpha2: 0.2            # Rotation noise from translation
odom_alpha3: 0.2            # Translation noise from translation
odom_alpha4: 0.2            # Translation noise from rotation

# Higher values = less trust in odometry (more particle spread)
```

***

**Laser model parameters:**

```yaml
# Scan processing
laser_max_range: 12.0        # Max range to consider (meters)
laser_min_range: 0.1         # Min range to consider (meters)

# Likelihood field parameters
laser_likelihood_max_dist: 2.0  # Max distance for obstacle match
laser_sigma_hit: 0.2            # Laser scan noise

# Smaller sigma_hit:
#   + Requires tighter scan matching
#   - May fail in noisy environments

# Scan decimation
laser_max_beams: 60         # Downsample scans (360 → 60 beams)
                            # Faster computation, less accuracy
```

***

#### Exercise 10.5: Tune for Your Environment

**Scenario 1: Symmetric hallway (ambiguous features)**

**Problem:** Multiple particle clusters persist

**Solution:** Increase particles, stricter matching

```yaml
max_particles: 8000          # Was 5000
laser_likelihood_max_dist: 1.0  # Was 2.0 (stricter matching)
laser_max_beams: 120         # Was 60 (more scan data)
```

***

**Scenario 2: Open warehouse (few features)**

**Problem:** Localization drifts in open areas

**Solution:** More particle spread, trust odometry less

```yaml
min_particles: 1000          # Was 500
odom_alpha3: 0.4            # Was 0.2 (less trust in translation)
laser_max_range: 15.0       # Was 12.0 (use longer range scans)
```

***

**Scenario 3: Dynamic environment (moving obstacles)**

**Problem:** False obstacles confuse AMCL

**Solution:** Increase noise tolerance

```yaml
laser_sigma_hit: 0.3        # Was 0.2 (more tolerant)
laser_likelihood_max_dist: 2.5  # Was 2.0
```

***

#### Testing Parameter Changes

**Systematic approach:**

```
1. Baseline test:
   - Record localization performance with defaults
   - Metrics: convergence time, final covariance, error

2. Change ONE parameter at a time
   - Don't change multiple simultaneously!
   - Document what you changed and why

3. Repeat test:
   - Same starting conditions
   - Same driving pattern
   - Compare metrics

4. Keep or revert:
   - If improved → keep change
   - If worse → revert
   - If neutral → revert (simpler is better)

5. Iterate:
   - Try next parameter
   - Build up optimized config
```

***

### Part 8: Advanced Localization Topics

#### Multi-Hypothesis Tracking

**When environment is symmetric:**

AMCL may maintain multiple particle clusters (each a hypothesis)

**Example:**

```
Long hallway with identical rooms:
- Cluster 1: "I'm in room 1"
- Cluster 2: "I'm in room 2"
- Cluster 3: "I'm in room 3"

As robot explores:
- Enters unique feature (door with window)
- Clusters at wrong rooms collapse
- Only correct cluster remains
```

**Viewing multiple hypotheses:**

```bash
# In RViz, particle cloud shows multiple groups
# Each group = different position hypothesis

# Check number of effective particles:
ros2 topic echo /amcl_pose --field pose.covariance[0]
# Higher covariance = less certain = multiple hypotheses
```

***

#### Localization with Odometry Bias

**Problem:** Odometry has systematic error (wheel radius wrong)

**Effect:**

* Robot drifts consistently in one direction
* AMCL can compensate to some degree
* But if error too large, fails

**Solution:**

* Calibrate odometry first (wheel radius, wheelbase)
* Or increase odom\_alpha parameters (trust odometry less)

***

#### Scan Matching vs Particle Filter

**Two localization approaches:**

**Particle Filter (AMCL):**

* ✅ Handles global localization
* ✅ Handles kidnapped robot
* ✅ Multiple hypotheses
* ❌ Slower (1000s of particles)
* ❌ Needs motion to converge

**Scan Matching (ICP - Iterative Closest Point):**

* ✅ Very fast
* ✅ No motion needed
* ✅ Precise alignment
* ❌ Only local (needs good initial guess)
* ❌ No kidnapping recovery

**Beetlebot uses AMCL (particle filter)**

***

### Part 9: Troubleshooting Localization

#### Problem: Localization Won't Converge

**Symptoms:** Particles stay spread out, never form tight cluster

**Possible causes:**

1. **Map doesn't match environment**

```bash
   # Environment changed since mapping?
   # - Furniture moved
   # - Doors opened/closed differently
   # - New obstacles added

   Solution: Remap environment
```

2. **Initial pose very wrong**

```bash
   # If initial estimate off by >5 meters, may never recover

   Solution: Set better initial pose, or use global localization
```

3. **Not enough motion**

```bash
   # AMCL needs motion to observe environment

   Solution: Drive around, rotate in place
```

4. **Too few distinctive features**

```bash
   # Large open area with no walls

   Solution: Drive toward feature-rich area
```

***

#### Problem: Localization Jumps Around

**Symptoms:** Robot position jitters on map

**Possible causes:**

1. **LiDAR noise**

```bash
   # Check scan quality
   ros2 topic echo /scan --once

   # Look for:
   # - Inf or NaN values (bad)
   # - Outliers (single points far from others)

   Solution: Increase laser_sigma_hit (more tolerant)
```

2. **Particle depletion**

```bash
   # Too few particles

   Solution: Increase min_particles (500 → 1000)
```

3. **Odometry jumps**

```bash
   # Wheel slipping, encoder errors

   ros2 topic echo /odom
   # Check for sudden position jumps

   Solution: Fix odometry, or increase odom_alpha (trust less)
```

***

#### Problem: Localization Drifts Over Time

**Symptoms:** Position slowly wanders away from true location

**Possible causes:**

1. **Odometry bias**

```bash
   # Systematic error in wheel odometry

   Solution: Calibrate wheel radius and wheelbase
```

2. **Environment changed**

```bash
   # Small changes accumulate

   Solution: Remap, or increase laser_likelihood_max_dist
```

3. **Insufficient features**

```bash
   # Operating in sparse areas

   Solution: Drive near walls/corners more often
```

***

#### General Debugging Steps

**Systematic approach:**

```bash
# 1. Verify inputs
ros2 topic hz /scan        # Should be ~10 Hz
ros2 topic hz /odom        # Should be ~20 Hz
ros2 topic hz /map         # Should publish once

# 2. Check AMCL running
ros2 node list | grep amcl

# 3. Check particle cloud
ros2 topic echo /particlecloud --once
# Should have 500-5000 particles

# 4. Check pose estimate
ros2 topic echo /amcl_pose --once
# Should have reasonable x, y, theta

# 5. Visualize in RViz
# Verify scans align with map

# 6. Check TF tree
ros2 run tf2_tools view_frames
# Should show: map → odom → base_link

# 7. If all else fails
# ⚡ Power cycle robot
```

***

### Part 10: Knowledge Check

#### Concept Quiz

1. **What's the main difference between SLAM and localization?**
2. **What do particles represent in AMCL?**
3. **Why rotate in place for global localization?**
4. **What is the kidnapped robot problem?**
5. **Can localization work in completely featureless environment (empty room)?**

***

#### Hands-On Challenge

**Task:** Robust localization system

**Requirements:**

1. Create launch file that:
   * Loads specified map
   * Launches AMCL with tuned parameters
   * Launches RViz with localization config
2. Test in 3 scenarios:
   * Known starting position (tracking)
   * Unknown starting position (global)
   * Kidnapped robot (recovery)
3. Document convergence times and final errors
4. Create tuned parameter file for your environment

**Deliverable:**

* Launch file
* Parameter config file
* Test results table (convergence time, final covariance, position error)
* Screenshots of RViz during each scenario
* Recommendations for future users

**Bonus:**

* Compare AMCL performance with different particle counts
* Test with artificially degraded odometry (simulated wheel slip)
* Create map quality metric (how "localizable" is your map?)

***

### Part 11: What You've Learned

#### ✅ Congratulations!

You now understand:

**Localization Fundamentals:**

* ✅ Localization vs SLAM
* ✅ Three localization problems (tracking, global, kidnapped)
* ✅ Particle filter concepts
* ✅ When localization is appropriate

**AMCL Operation:**

* ✅ Setting initial pose
* ✅ Monitoring convergence
* ✅ Assessing localization quality
* ✅ Understanding particle cloud behavior

**Practical Skills:**

* ✅ Loading and using saved maps
* ✅ Localizing robot in known environment
* ✅ Global localization (no initial pose)
* ✅ Recovering from kidnapping
* ✅ Tuning AMCL parameters

**Advanced Topics:**

* ✅ Multi-hypothesis tracking
* ✅ Covariance interpretation
* ✅ Scan matching principles
* ✅ Troubleshooting localization failures

***

### Next Steps

#### 🎯 You're Now Ready For:

**FINAL TUTORIAL:** → Autonomous Navigation - Put it all together!

**Beyond This Course:**

* Multi-robot localization
* Visual localization (camera-based)
* GPS integration (outdoor)
* Robust localization in dynamic environments

***

### Quick Reference

#### Essential Localization Commands

```bash
# --- Launch Map Server ---
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=/path/to/map.yaml

# --- Launch AMCL ---
ros2 launch lyra_bringup localization.launch.py map:=/path/to/map.yaml

# --- Set Initial Pose (CLI) ---
ros2 topic pub --once /initialpose geometry_msgs/PoseWithCovarianceStamped "
header: {frame_id: 'map'}
pose:
  pose:
    position: {x: 0.0, y: 0.0, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}"

# --- Check Localization Status ---
ros2 topic hz /amcl_pose           # Should update ~10 Hz
ros2 topic echo /amcl_pose --once  # Check covariance

# --- Monitor Particles ---
ros2 topic echo /particlecloud --once

# --- AMCL Parameters ---
ros2 param list /amcl
ros2 param get /amcl min_particles
ros2 param set /amcl max_particles 8000

# --- Debugging ---
ros2 run tf2_tools view_frames     # Check TF tree
rviz2                              # Visualize
```

***

#### Localization Quality Metrics

| Metric               | Good    | Fair      | Poor  |
| -------------------- | ------- | --------- | ----- |
| **X/Y Covariance**   | <0.01   | 0.01-0.05 | >0.05 |
| **Yaw Covariance**   | <0.01   | 0.01-0.05 | >0.05 |
| **Particle Spread**  | <0.5m   | 0.5-2m    | >2m   |
| **Scan Alignment**   | Perfect | Close     | Off   |
| **Convergence Time** | <30s    | 30-90s    | >90s  |

***

#### Common AMCL Parameters

```yaml
# Particle counts
min_particles: 500
max_particles: 5000

# Odometry model (trust in wheel odom)
odom_alpha1: 0.2  # rotation from rotation
odom_alpha2: 0.2  # rotation from translation
odom_alpha3: 0.2  # translation from translation
odom_alpha4: 0.2  # translation from rotation

# Laser model
laser_max_range: 12.0
laser_likelihood_max_dist: 2.0
laser_sigma_hit: 0.2
laser_max_beams: 60

# Update rates
resample_interval: 1
update_min_d: 0.2      # Min translation for update
update_min_a: 0.5      # Min rotation for update

# Recovery
recovery_alpha_slow: 0.001
recovery_alpha_fast: 0.1
```

***

**Completed Localization Techniques!** 🎉

→ Continue to **FINAL TUTORIAL:** Autonomous Navigation\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 10 of 11 - Advanced Level*\
*Estimated completion time: 145 minutes*
