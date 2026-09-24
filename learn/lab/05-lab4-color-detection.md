# 05 — Lab 4: colour-based control node

**Goal of this lab:** deploy a Python `rclpy` node that reads the Pi Camera feed, decides
what colour dominates the centre of the frame, and drives the robot accordingly — no LiDAR,
pure vision. Source: `docs/color_detection_beetlebot` (kl mithunvel's own node, not an
instructor handout — see the note at the end of this file). This maps to Experiment 5 of the
official syllabus ("Object detection/recognition using ROS perception libraries (OpenCV,
PCL)" — `00-course-and-lab-map.md` §1).

Runs entirely **on the robot, via SSH** (two terminals, same shape as Lab 2/3).

---

## What the node does

`ColorControlNode` (in `docs/color_detection_beetlebot`):

- Subscribes `sensor_msgs/Image` on **`/pi_camera/image_raw`**.
- Converts each frame BGR→HSV via `cv_bridge` + OpenCV, crops the **centre 50%** of the
  frame (25%–75% in both x and y) as the region of interest — ignores colour at the edges.
- Thresholds three HSV ranges in that ROI: green, red (two ranges, since red wraps `0°`/`180°`
  on the OpenCV hue wheel), blue.
- Whichever colour covers **>20% of the ROI** wins (checked green → red → blue, in that
  order); if none clears 20%, the robot **keeps its previous command** instead of stopping —
  a one-frame dropout doesn't jerk the robot.
- Publishes `geometry_msgs/Twist` on **`/cmd_vel_nav`** (same topic Lab 2/3 use):
  - **GREEN → forward** (`linear.x = 0.2`)
  - **RED → stop** (zero Twist) — also the default/initial state
  - **BLUE → backward** (`linear.x = -0.15`)

## Shutdown safety — different from the obstacle-avoidance node

`04-lab3-obstacle-avoidance.md` covers a node that installs a `signal.signal(SIGINT, ...)`
handler. This node does **not** — it relies on the `try/except KeyboardInterrupt` /
`finally:` block around `rclpy.spin()` in `main()`, which publishes a zero `Twist` 10 times
before calling `destroy_node()`. Functionally similar end result (motors get a stop command
before the process exits), but if asked in the viva **"how does this node handle Ctrl+C?"**,
the answer is "`KeyboardInterrupt` caught around `spin()`, safety-stop in `finally`" — not
"`SIGINT` handler". Either way: **`Ctrl+C` this node directly**, don't just kill the SSH
session.

---

## Step 1 — Terminal 1: bringup, with the camera on

```bash
ssh veerobot@192.168.0.<robotNumber>
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<robotNumber>
ros2 launch lyra_bringup robot.launch.py camera:=true
```
`camera:=true` is required — this node has nothing to subscribe to without it. (LiDAR/`mode:=slam`
aren't needed for this lab; add them only if you're combining with SLAM.) Leave this running.

Sanity-check the camera topic exists before moving on:
```bash
ros2 topic list | grep pi_camera
ros2 topic hz /pi_camera/image_raw
```

## Step 2 — Terminal 1 (or a third SSH session): confirm dependencies

The node imports `cv_bridge`, `cv2` (OpenCV) and `numpy`. These are normally already on the
robot's image, but if `ros2 run` later fails on an `ImportError`:
```bash
sudo apt install ros-jazzy-cv-bridge python3-opencv
```

## Step 3 — Terminal 2: place the node's source file

```bash
ssh veerobot@192.168.0.<robotNumber>
cd ~/lyra_ws/src/lyra_control/lyra_control/
nano color_control.py
```
Paste in the contents of `docs/color_detection_beetlebot`, save (`Ctrl+O`, `Enter`), exit
(`Ctrl+X`), then:
```bash
chmod +x color_control.py
```

## Step 4 — Register it as a runnable command

```bash
cd ~/lyra_ws/src/lyra_control/
nano setup.py
```
Add a line to the `console_scripts` list in `entry_points` (same file Lab 3 edits):
```python
entry_points={
    'console_scripts': [
        'cmd_vel_mux = lyra_control.cmd_vel_mux:main',
        'joy_teleop_wrapper = lyra_control.joy_teleop_wrapper:main',
        'obstacle_avoid = lyra_control.obstacle_avoidance:main',
        'color_control = lyra_control.color_control:main',   # <-- add this line
    ],
},
```
Why this step exists: `../foundations/02-ros2-concepts.md` §3 — `ros2 run <pkg> <name>` only
resolves names listed here.

## Step 5 — Build and source

```bash
cd ~/lyra_ws
colcon build --packages-select lyra_control
source install/setup.bash
```
Re-`source` in **every** terminal that will run the node — same rule as Lab 3.

## Step 6 — Arm, then run

Driving still goes through the same arm gate as every other lab (`01-lab-day-runbook.md`):
```bash
ros2 service call /lyra/arm std_srvs/srv/Trigger
ros2 run lyra_control color_control
```
Hold up a green, red, or blue object (card, cloth, object) in front of the camera, filling
roughly a quarter or more of the frame, centred. Watch the log lines
(`GREEN detected → FORWARD`, etc. — only logged on a *change* of command, not every frame).

## Step 7 — Stop it safely

```
Ctrl+C
```
Then disarm:
```bash
ros2 service call /lyra/disarm std_srvs/srv/Trigger
```

---

## Tuning notes (if detection is flaky)

- **Lighting matters a lot for HSV thresholding.** Indoor fluorescent light shifts hue
  differently than daylight — if a colour isn't triggering, `ros2 topic echo /pi_camera/image_raw`
  won't help directly (it's raw image data); better to `rqt_image_view` the topic and eyeball
  what the camera actually sees.
- The 20% ROI-coverage `threshold` and the `green_lower/upper`, `red_lower1/2/upper1/2`,
  `blue_lower/upper` HSV ranges are all hardcoded in the node — adjust them there, not via
  parameters (this node doesn't declare ROS params, unlike the pattern in
  `../foundations/02-ros2-concepts.md` §7).
- Red is split into two HSV ranges (`0–10°` and `170–180°`) because red sits at the wrap-around
  point of OpenCV's 0–180° hue scale — a single range would miss half of "red".

---

## Checklist — can you do this from memory?

- [ ] Explain why `camera:=true` is needed in the bringup launch for this lab specifically
- [ ] State the topic chain: `/pi_camera/image_raw` (sub) → `/cmd_vel_nav` (pub)
- [ ] Explain the ROI crop (why centre 50%, not the full frame)
- [ ] Explain why red needs two HSV ranges and green/blue need only one
- [ ] Explain what happens when no colour clears the 20% threshold (holds last command, doesn't stop)
- [ ] Explain how this node's shutdown safety differs from the obstacle-avoidance node's
      `SIGINT` handler (see "Shutdown safety" above)
- [ ] Know the full deployment path from memory: `nano` script → `chmod +x` → `nano setup.py`
      → `colcon build` → `source` → arm → `ros2 run` → `Ctrl+C` → disarm

---

## A note on where the source file lives

`docs/color_detection_beetlebot` is kl mithunvel's own node, not an instructor handout —
unlike the rest of `docs/`, it isn't read-only source material, and it currently has no file
extension. It's parked there for now rather than moved into `practice/` (see
`.CLAUDE/CLAUDE.md`'s Known Technical Debt table); a broader documentation-format reformat is
planned for later and will likely relocate it alongside `practice/robot_calc/`'s pattern (own
`.venv`/`requirements.txt`/`tests/`).

---

Next: the lab track ends here for now. To go from "I can run the lab" to "I can build a ROS 2
autonomy stack for any robot", start **Track B**: `../build/01-three-bots-architecture.md`.
Full map: `../README.md`.
