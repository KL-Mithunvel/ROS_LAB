# SLAM Mapping

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand SLAM concepts and why it's needed
* ✅ Launch SLAM on Beetlebot
* ✅ Drive robot to create high-quality maps
* ✅ Save and load maps
* ✅ Interpret map quality indicators
* ✅ Troubleshoot mapping issues
* ✅ Create maps of different environments
* ✅ Understand map formats and parameters

#### ⏱️ Time Required

* **Reading & Theory:** 25 minutes
* **First Map Creation:** 30 minutes
* **Map Quality Practice:** 35 minutes
* **Advanced Mapping:** 30 minutes
* **Troubleshooting:** 20 minutes
* **Total:** \~140 minutes

#### 📚 Prerequisites

* ✅ Completed Sensor Data Visualization
* ✅ Completed Sensor Fusion with EKF
* ✅ Can drive robot smoothly
* ✅ Understanding of LiDAR data
* ✅ Can use RViz confidently
* ✅ Environment to map (room, hallway, etc.)

#### 🛠️ What You'll Need

* ✅ Beetlebot (fully charged, LiDAR working)
* ✅ Laptop with ROS2 Jazzy
* ✅ Wireless controller
* ✅ Environment with clear features:
  * Walls, furniture, doorways
  * At least 3m × 3m space
  * Avoid glass, mirrors (LiDAR can't see them well)
* ✅ Patience (good maps take practice!)

***

### Part 1: What is SLAM?

#### The Chicken-and-Egg Problem

**Classic robotics problem:**

```
To navigate, robot needs a map
  → But to build map, robot needs to know its position
    → But to know position, robot needs a map!
      → Chicken and egg! 🐔🥚
```

**SLAM Solution:** Do BOTH simultaneously!

* Build map while determining position
* Use partial map to improve position estimate
* Use improved position to refine map
* Iterate continuously

***

#### Why SLAM is Hard

**Challenges:**

1. **Data Association**
   * Is this wall same as one seen before?
   * Or a different wall that looks similar?
   * Wrong associations = bad map
2. **Loop Closure**
   * Return to previous location after long path
   * Accumulated drift makes it look different
   * Must recognize "I've been here before!"
   * Correct entire trajectory when loop closes
3. **Computational Complexity**
   * Tracking thousands of map features
   * Maintaining correlations (covariances)
   * Real-time requirements (robot keeps moving)

***

#### SLAM Approaches

**Beetlebot uses:** **SLAM Toolbox** (graph-based SLAM)

**Other common methods:**

* **GMapping** - Older, FastSLAM-based (particle filters)
* **Cartographer** - Google's SLAM (submap optimization)
* **Hector SLAM** - No odometry needed (scan matching only)
* **RTAB-Map** - RGB-D SLAM (uses depth cameras)

**Why SLAM Toolbox?**

* ✅ Modern, actively maintained
* ✅ ROS2 native
* ✅ Real-time capable
* ✅ Loop closure detection
* ✅ Map serialization (save/load)
* ✅ Good for 2D LiDAR

***

#### Map Representation

**Occupancy Grid Map:**

```
Grid of cells (typically 5cm × 5cm each)

Each cell has value:
  - 100 = Occupied (obstacle, wall)
  - 0 = Free (empty space, can drive here)
  - -1 = Unknown (not explored yet)
```

**File format:** PGM (image) + YAML (metadata)

\[PLACEHOLDER: Example map image showing occupied/free/unknown]

***

### Part 2: Your First SLAM Map

#### Check System Status

**Before starting:**

```bash
# Verify LiDAR working
ros2 topic hz /scan
# Should show ~10 Hz

# Verify odometry working
ros2 topic hz /odometry/filtered
# Should show ~20-30 Hz

# Verify robot base system running
ros2 node list | grep lyra
# Should show lyra nodes
```

***

#### Launch SLAM Toolbox

**On robot (via SSH or auto-launched):**

Your robot likely has SLAM configured to launch automatically. Check:

```bash
ros2 node list | grep slam

# If not running, launch manually:
ros2 launch lyra_bringup slam.launch.py
```

**What launches:**

* `slam_toolbox` node
* Subscribes to: `/scan`, `/odometry/filtered`
* Publishes: `/map`, `/map_metadata`
* Provides: Loop closure, graph optimization

***

#### Visualize SLAM in RViz

**On laptop:**

```bash
rviz2
```

**Configure RViz for SLAM:**

```
1. Fixed Frame: "map" (critical!)

2. Add Map display:
   - Topic: /map
   - Color Scheme: map (white=free, black=occupied, gray=unknown)
   - Alpha: 0.7

3. Add LaserScan:
   - Topic: /scan
   - Size: 0.05
   - Color: Red (shows current scan)

4. Add RobotModel:
   - Description Topic: /robot_description
   - Shows robot position on map

5. Add Odometry:
   - Topic: /odometry/filtered
   - Covariance: Position (XY)
   - Keep: 500 (shows trajectory trail)
   - Color: Green

6. Add TF:
   - Shows coordinate frames
   - Helps debug frame issues
```

\[PLACEHOLDER: Screenshot of properly configured RViz for SLAM]

***

#### Drive Pattern for Good Maps

**🎓 SLAM Driving Best Practices:**

**DO:**

* ✅ Drive **slowly** (0.3-0.5 m/s max)
* ✅ Make **long, gentle turns** (not sharp 90° turns)
* ✅ **Overlap** scans (return to previous areas)
* ✅ **Close loops** (return to start periodically)
* ✅ Keep **consistent speed** (no sudden acceleration)
* ✅ Drive in **open areas first**, then details

**DON'T:**

* ❌ Drive too fast (>0.8 m/s) - scans don't overlap enough
* ❌ Make sharp turns - causes scan matching errors
* ❌ Drive in complete darkness - LiDAR needs features
* ❌ Go near mirrors/glass - LiDAR passes through
* ❌ Have moving obstacles during initial mapping

***

#### Exercise 8.1: Create Your First Map

**Task:** Map a single room

**Preparation:**

```
1. Choose a simple room (square/rectangular ideal)
2. Remove moving obstacles (people, pets)
3. Close doors (define boundaries)
4. Ensure good lighting (optional but helps)
5. Start robot in center of room
```

**Mapping procedure:**

```bash
# Step 1: Launch SLAM (if not auto-launched)
ros2 launch lyra_bringup slam.launch.py

# Step 2: Open RViz on laptop (configured as above)
rviz2

# Step 3: Start mapping
# Drive robot slowly around perimeter of room:
1. Start from center
2. Drive to one wall slowly
3. Turn to face along wall
4. Drive parallel to wall (1m away from wall)
5. At corner, make GENTLE turn (not 90°, more like smooth arc)
6. Continue along next wall
7. Complete full perimeter
8. Return to starting position (loop closure!)

# Step 4: Fill in interior
9. Drive through middle of room in different directions
10. Ensure all areas covered
11. Return to start again

# Step 5: Observe in RViz
# - Walls should appear solid (black lines)
# - Interior should be white (free space)
# - Minimal gray (unknown areas)
```

**Expected time:** 3-5 minutes for typical room

***

#### Saving Your Map

**Once mapping complete:**

```bash
# On robot (via SSH) or laptop
cd ~/maps  # Create if doesn't exist: mkdir -p ~/maps

# Save map
ros2 run nav2_map_server map_saver_cli -f my_first_map

# Output:
# [INFO] [map_saver]: Waiting for the map
# [INFO] [map_saver]: Received a 384 X 384 map @ 0.05 m/pix
# [INFO] [map_saver]: Writing map occupancy data to my_first_map.pgm
# [INFO] [map_saver]: Writing map metadata to my_first_map.yaml
# [INFO] [map_saver]: Map saved
```

**Files created:**

* `my_first_map.pgm` - Image file (occupancy grid)
* `my_first_map.yaml` - Metadata (resolution, origin, thresholds)

***

#### Understanding the Map Files

**YAML file (metadata):**

```bash
cat my_first_map.yaml
```

**Contents:**

```yaml
image: my_first_map.pgm
resolution: 0.050000  # 5cm per pixel
origin: [-10.000000, -10.000000, 0.000000]  # Map origin in meters
negate: 0
occupied_thresh: 0.65  # Threshold for occupied
free_thresh: 0.196     # Threshold for free
```

**Key parameters:**

**resolution:** Size of each grid cell

* Smaller = more detail, larger file
* Typical: 0.05m (5cm)
* Range: 0.01-0.10m

**origin:** Where is (0,0) of image in world coordinates

* Usually bottom-left corner
* Negative values = map extends in negative x,y

**occupied\_thresh:** LiDAR hit probability → occupied

* Higher = more conservative (less marked as obstacle)
* Lower = more aggressive (more marked as obstacle)

**free\_thresh:** No hit probability → free

* Higher = more aggressive marking as free
* Lower = more conservative

***

#### Viewing Map Image

**Open PGM file:**

```bash
# On laptop (if files copied from robot)
eog my_first_map.pgm
# Or
gimp my_first_map.pgm
```

**Image colors:**

* **Black pixels:** Occupied (walls, obstacles)
* **White pixels:** Free space (can drive here)
* **Gray pixels:** Unknown (not explored)

\[PLACEHOLDER: Example saved map image]

***

### Part 3: Map Quality Assessment

#### Visual Inspection

**Good map indicators:**

✅ **Straight walls are straight** (not wavy or jagged) ✅ **Corners are sharp** (90° corners clear) ✅ **Closed spaces are closed** (rooms fully enclosed) ✅ **Symmetry preserved** (symmetric rooms look symmetric) ✅ **Minimal gray (unknown)** (most area explored) ✅ **No "ghost" walls** (false obstacles from bad scans) ✅ **Loop closures successful** (start/end positions align)

***

**Poor map indicators:**

❌ **Wavy walls** (drove too fast, scan matching failed) ❌ **Blurred edges** (inconsistent scans, moving during scan) ❌ **Disconnected rooms** (walls have gaps where shouldn't) ❌ **Overlapping walls** (double walls, loop closure failed) ❌ **Ghost obstacles** (artifacts from reflections, moving objects) ❌ **Large unknown areas** (didn't explore thoroughly)

\[PLACEHOLDER: Side-by-side comparison good map vs poor map]

***

#### Quantitative Metrics

**Check map statistics:**

```bash
# View map info
ros2 topic echo /map_metadata --once

# Output shows:
# map_load_time: <timestamp>
# resolution: 0.050000
# width: 384  # pixels
# height: 384  # pixels
# origin:
#   position: {x: -9.6, y: -9.6, z: 0.0}
```

**Calculate map coverage:**

```bash
# Count pixel types in PGM
identify -verbose my_first_map.pgm | grep -A 10 Histogram

# Or use Python:
python3 << EOF
from PIL import Image
import numpy as np

img = np.array(Image.open('my_first_map.pgm'))
total_pixels = img.size

occupied = np.sum(img == 0)  # Black
free = np.sum(img == 254)     # White
unknown = np.sum(img == 205)  # Gray

print(f"Occupied: {occupied/total_pixels*100:.1f}%")
print(f"Free: {free/total_pixels*100:.1f}%")
print(f"Unknown: {unknown/total_pixels*100:.1f}%")
EOF
```

**Good map targets:**

* Free space: 40-60%
* Occupied: 10-20%
* Unknown: <30%

***

#### Exercise 8.2: Map Quality Comparison

**Task:** Create two maps of same room, compare quality

**Map 1: Fast driving (poor technique)**

```
1. Launch SLAM
2. Drive quickly around room (0.8-1.0 m/s)
3. Make sharp 90° turns
4. Complete in <2 minutes
5. Save as: fast_map
```

**Map 2: Slow, careful driving (good technique)**

```
1. Restart SLAM (or power cycle robot)
2. Drive slowly (0.3-0.5 m/s)
3. Make gentle, arcing turns
4. Take 4-5 minutes
5. Save as: careful_map
```

**Compare:**

```bash
# Open both images side-by-side
eog fast_map.pgm &
eog careful_map.pgm &

# Which has:
# - Straighter walls?
# - Fewer artifacts?
# - Better defined corners?
# - Less unknown area?
```

**Expected result:** Careful map significantly better!

***

### Part 4: Advanced Mapping Techniques

#### Multi-Room Mapping

**Challenge:** Map entire floor with multiple rooms

**Strategy:**

```
1. Map main hallway/corridor first
   - This becomes "backbone" of map
   - Provides reference for all rooms

2. Enter each room one at a time
   - Drive into room
   - Map thoroughly
   - Return to hallway (loop closure!)
   - This corrects any drift

3. Close all loops
   - Periodically return to starting location
   - Triggers loop closure detection
   - Corrects accumulated errors

4. Final pass
   - Drive entire map one more time
   - Ensures consistency
```

***

#### Loop Closure Detection

**What is loop closure?**

When robot returns to previously mapped area:

1. SLAM detects "I've been here before!"
2. Measures difference between:
   * Where odometry says robot is
   * Where map says robot should be
3. Adjusts entire trajectory to minimize error
4. Updates map accordingly

**Visual signs of loop closure in RViz:**

* Sudden "snap" of map alignment
* Previous trajectory may shift slightly
* Console message: "\[INFO] Loop closure detected"

***

#### Exercise 8.3: Intentional Loop Closure

**Task:** Observe loop closure correction

**Procedure:**

```bash
# Setup: Launch SLAM + RViz

# Step 1: Create initial map
1. Drive in 3m × 3m square (takes ~2 minutes)
2. DON'T return to start yet
3. Note current position in RViz

# Step 2: Drive away (accumulate drift)
4. Drive 5 meters away from mapped area
5. Drive in circles for 1 minute (intentionally accumulate error)
6. Observe: odometry drifting, uncertainty growing

# Step 3: Return to mapped area
7. Drive back toward starting square
8. As you enter previously mapped area...
9. WATCH: Map may suddenly shift/align (loop closure!)
10. Robot position "snaps" to correct location
11. Console shows: "Loop closure detected"

# What you learned:
# - Drift accumulates when exploring new areas
# - Loop closure corrects entire trajectory
# - Map consistency improved
```

***

#### Mapping Large Spaces

**For spaces >100m²:**

**Challenges:**

* Computational load increases
* Memory requirements grow
* Loop closure more difficult (more potential matches)

**Solutions:**

1. **Increase map resolution** (larger cells)

```yaml
   # In SLAM config
   resolution: 0.10  # 10cm instead of 5cm
```

2. **Reduce map update rate**

```yaml
   map_update_interval: 1.0  # Update every 1 second (was 0.5)
```

3. **Split into submaps**
   * Map each area separately
   * Merge offline using map merging tools
4. **Use better computer**
   * SLAM runs on robot's Pi 5
   * For huge maps, might need more powerful PC

***

### Part 5: Common Issues and Solutions

#### Problem: Walls Look Wavy

**Cause:** Driving too fast, scan matching fails

**Solution:**

```
1. Slow down! (0.3 m/s max)
2. Make smoother turns
3. Ensure LiDAR spinning freely (check for obstructions)
4. Verify scan rate: ros2 topic hz /scan (should be ~10Hz)
```

***

#### Problem: Map Has Double Walls

**Cause:** Loop closure failed or didn't happen

**Solution:**

```
1. Return to starting position more frequently
2. Drive through same areas multiple times
3. Ensure starting area has distinctive features (corners, doorways)
4. Check odometry quality (may need EKF tuning)
```

***

#### Problem: Ghost Obstacles

**Cause:** Reflections (mirrors, glass), moving objects, or sensor noise

**Solution:**

```
1. Remove or cover mirrors during mapping
2. Ensure no moving people/objects
3. Filter isolated pixels in post-processing:

# Use map_server filter
ros2 run map_server map_saver_cli -f filtered_map --occ 65 --free 25
```

***

#### Problem: Large Gray (Unknown) Areas

**Cause:** Didn't drive in those areas, or LiDAR obstructed

**Solution:**

```
1. Drive through all areas of environment
2. Ensure LiDAR has clear view (nothing blocking sensor)
3. Check LiDAR height - should see over low obstacles
4. Verify scan range in RViz (should show ~8m radius)
```

***

#### Problem: Map Rotation/Scale Wrong

**Cause:** TF tree issues, incorrect odometry

**Solution:**

```bash
# Check TF tree
ros2 run tf2_tools view_frames

# Verify frames exist:
# - map → odom → base_link

# Check for TF errors
ros2 topic echo /rosout | grep -i "tf"

# If TF broken: ⚡ Power cycle robot
```

***

### Part 6: Map Editing and Processing

#### Cleaning Up Maps

**Remove artifacts using GIMP:**

```bash
# Install GIMP (if not already)
sudo apt install gimp

# Open map
gimp my_first_map.pgm

# Tools:
# - Pencil tool (draw obstacles)
# - Eraser tool (mark as free)
# - Bucket fill (fill large areas)
# - Clone tool (copy patterns)

# Save as PGM (overwrite original)
```

**Common edits:**

* Remove ghost obstacles (erase black pixels)
* Close gaps in walls (draw black lines)
* Clear unknown areas (fill with white if you know it's free)
* Remove robot from map (sometimes captured in scans)

***

#### Adding Virtual Walls

**Use case:** Prevent robot from entering certain areas

```bash
# Edit map in GIMP
# Draw black lines (obstacles) where you want boundaries
# Robot will treat these as real walls

# Useful for:
# - Marking off-limits areas (stairs, fragile items)
# - Creating "lanes" for robot to follow
# - Blocking shortcuts (force certain paths)
```

***

#### Inflating Obstacles

**Add safety margin around obstacles:**

```python
#!/usr/bin/env python3
# inflate_map.py

from PIL import Image
import numpy as np
from scipy.ndimage import binary_dilation

# Load map
img = Image.open('my_map.pgm')
data = np.array(img)

# Find obstacles (black pixels)
obstacles = (data < 50)

# Inflate by N pixels (radius in pixels)
inflation_radius = 4  # 4 pixels × 5cm = 20cm margin

# Create structuring element (circle)
y, x = np.ogrid[-inflation_radius:inflation_radius+1,
                -inflation_radius:inflation_radius+1]
structure = x**2 + y**2 <= inflation_radius**2

# Dilate obstacles
inflated = binary_dilation(obstacles, structure=structure)

# Create new image
new_data = data.copy()
new_data[inflated] = 0  # Mark as occupied

# Save
Image.fromarray(new_data).save('my_map_inflated.pgm')
print("Inflated map saved!")
```

**Run:**

```bash
python3 inflate_map.py
```

***

### Part 7: Using Maps for Navigation

#### Loading a Saved Map

**For next tutorial (Localization), you'll load maps:**

```bash
# Launch map server
ros2 run nav2_map_server map_server --ros-args -p yaml_filename:=my_first_map.yaml

# Map now published on /map topic

# Verify
ros2 topic echo /map_metadata --once
```

**Or use launch file:**

```bash
ros2 launch lyra_bringup map_server.launch.py map:=/path/to/my_map.yaml
```

***

#### Map Server Parameters

**Customize map serving:**

```yaml
# map_server_params.yaml
map_server:
  ros__parameters:
    yaml_filename: "my_map.yaml"
    topic_name: "map"
    frame_id: "map"
```

***

### Part 8: Best Practices Summary

#### Pre-Mapping Checklist

* [ ] Battery >50% (mapping takes time)
* [ ] LiDAR spinning and publishing /scan at \~10Hz
* [ ] Odometry stable (/odometry/filtered publishing)
* [ ] Environment prepared:
  * [ ] Remove moving obstacles
  * [ ] Close doors to define boundaries
  * [ ] Cover/remove mirrors and glass
* [ ] RViz configured and ready
* [ ] Plan rough mapping route

***

#### During Mapping

* [ ] Drive slowly (0.3-0.5 m/s)
* [ ] Make gentle turns (no sharp 90° corners)
* [ ] Overlap scans (return to same areas)
* [ ] Close loops regularly (return to start every 2-3 minutes)
* [ ] Monitor map quality in RViz
* [ ] Cover all areas systematically
* [ ] Final loop closure (return to exact start position)

***

#### Post-Mapping

* [ ] Save map with descriptive name
* [ ] Inspect map image for quality
* [ ] Check map statistics (% occupied/free/unknown)
* [ ] Edit map if needed (remove artifacts)
* [ ] Test map (load and localize - next tutorial)
* [ ] Backup map files (copy to laptop)
* [ ] Document map (name, date, environment notes)

***

### Part 9: Knowledge Check

#### Concept Quiz

1. **What does SLAM stand for and what does it solve?**
2. **Why drive slowly during SLAM?**
3. **What is loop closure and why is it important?**
4. **What do black, white, and gray pixels mean in map?**
5. **Can you create perfect maps without any drift?**

***

#### Hands-On Challenge

**Task:** Map a complex environment

**Requirements:**

1. Multi-room environment (3+ rooms)
2. Include hallways, doorways, furniture
3. Total area >50m²
4. Complete map in single session (no restarts)
5. Achieve <25% unknown area
6. Save final map with documentation

**Deliverable:**

* Map files (.pgm + .yaml)
* Screenshot of map in RViz
* Statistics (occupied/free/unknown percentages)
* Written description of environment
* Notes on challenges encountered

**Bonus:**

* Create before/after comparison (initial attempt vs. improved attempt)
* Edit map to remove artifacts
* Add inflation layer for safety margins

***

### Part 10: What You've Learned

#### ✅ Congratulations!

You now understand:

**SLAM Fundamentals:**

* ✅ Simultaneous localization and mapping concept
* ✅ Graph-based SLAM (SLAM Toolbox)
* ✅ Loop closure detection and correction
* ✅ Occupancy grid representation

**Practical Mapping:**

* ✅ Launching and configuring SLAM
* ✅ Driving techniques for quality maps
* ✅ Saving and loading maps
* ✅ Visual quality assessment
* ✅ Common issues and solutions

**Advanced Topics:**

* ✅ Multi-room mapping strategies
* ✅ Map editing and processing
* ✅ Obstacle inflation
* ✅ Map statistics and metrics

***

### Next Steps

#### 🎯 You're Now Ready For:

**Immediate Next:** → Localization Techniques - Use saved maps to localize robot

**Autonomous Navigation:** → Autonomous Navigation - Navigate using your maps

**Advanced Mapping:**

* 3D SLAM (if you add depth camera)
* Outdoor mapping (with GPS fusion)
* Dynamic environments (handle moving obstacles)
* Multi-robot SLAM (collaborative mapping)

***

### Quick Reference

#### Essential SLAM Commands

```bash
# --- Launch SLAM ---
ros2 launch lyra_bringup slam.launch.py

# --- Save Map ---
ros2 run nav2_map_server map_saver_cli -f my_map

# --- Load Map ---
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=my_map.yaml

# --- Check Topics ---
ros2 topic hz /scan          # LiDAR rate (~10Hz)
ros2 topic hz /map           # Map updates
ros2 topic echo /map_metadata --once

# --- Visualize ---
rviz2  # Configure Fixed Frame = "map"

# --- Map Statistics (Python) ---
python3 << EOF
from PIL import Image
import numpy as np
img = np.array(Image.open('my_map.pgm'))
print(f"Occupied: {np.sum(img==0)/img.size*100:.1f}%")
print(f"Free: {np.sum(img==254)/img.size*100:.1f}%")
print(f"Unknown: {np.sum(img==205)/img.size*100:.1f}%")
EOF
```

***

#### SLAM Driving Checklist

| Action            | Speed       | Turn Style           | Notes             |
| ----------------- | ----------- | -------------------- | ----------------- |
| Initial perimeter | 0.3-0.5 m/s | Gentle arcs          | Define boundaries |
| Interior coverage | 0.3-0.5 m/s | Smooth curves        | Fill in details   |
| Loop closures     | 0.3 m/s     | Gentle               | Every 2-3 minutes |
| Final pass        | 0.3 m/s     | Follow previous path | Consistency check |

***

#### Troubleshooting Flowchart

```
Map quality poor?
  ├─ Wavy walls? → Drive slower, smoother turns
  ├─ Double walls? → More loop closures
  ├─ Ghost obstacles? → Remove mirrors, check for moving objects
  ├─ Large unknown? → Cover all areas, check LiDAR
  └─ All else fails? → ⚡ Power cycle robot, start fresh
```

***

**Completed SLAM Mapping!** 🎉

→ Continue to Localization Techniques\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 8 of 11 - Advanced Level*\
*Estimated completion time: 140 minutes*
