# Experiment 4 — Colour-based control with the camera

## 1. Aim
To deploy a vision node that segments the dominant colour in the centre of the Pi Camera image using OpenCV and drives the BeetleBot accordingly (green = forward, red = stop, blue = backward).

## 2. Learning outcomes
Use `cv_bridge` to convert ROS images to OpenCV; apply HSV thresholding; explain why hue-based segmentation beats RGB under changing light; handle the red hue wrap-around; build a perception→control node with a safe shutdown.

## 3. Apparatus
BeetleBot with Pi Camera V1.3; lab PC; green, red and blue cards/objects; source `docs/color_detection_beetlebot`.

## 4. Theory
**HSV** separates colour (hue) from brightness (value) and saturation, so a threshold on hue is
more robust to lighting than one on R, G, B. OpenCV hue is 0–179, so **red wraps around** and
needs two ranges (near 0 and near 179).

The node: subscribes to `sensor_msgs/Image` on `/pi_camera/image_raw`; converts BGR→HSV;
crops the **centre 50 %** region of interest; masks green, red (two ranges) and blue;
whichever mask covers **> 20 %** of the ROI wins (checked green → red → blue). If none
qualifies it **keeps the previous command**, so a one-frame dropout does not jerk the robot.
It publishes `Twist` on `/cmd_vel_nav`: green `linear.x = 0.2`, red zero (also the initial
state), blue `linear.x = -0.15`.

**Shutdown:** `try/except KeyboardInterrupt` around `rclpy.spin()` and a `finally` that
publishes zero `Twist` 10 times — not a `SIGINT` handler as in Experiment 3.

## 5. Pre-lab questions
1. Why two hue ranges for red?
2. Why crop to a central ROI?
3. What is the risk of "keep the previous command" when the camera is blocked?

## 6. Procedure
1. **[Robot] Terminal 1** — bring-up with the camera:
   ```bash
   ssh veerobot@192.168.0.<robotNumber>
   source /opt/ros/jazzy/setup.bash && source ~/lyra_ws/install/setup.bash
   export ROS_DOMAIN_ID=<robotNumber>
   ros2 launch lyra_bringup robot.launch.py camera:=true
   ```
   Check: `ros2 topic list | grep pi_camera` and `ros2 topic hz /pi_camera/image_raw`.
2. If imports fail later: `sudo apt install ros-jazzy-cv-bridge python3-opencv`.
3. **[Robot] Terminal 2** — place the node:
   ```bash
   cd ~/lyra_ws/src/lyra_control/lyra_control/
   nano color_control.py             # paste docs/color_detection_beetlebot
   chmod +x color_control.py
   ```
4. Register in `setup.py` → `console_scripts`:
   ```python
   'color_control = lyra_control.color_control:main',
   ```
5. Build and source:
   ```bash
   cd ~/lyra_ws && colcon build --packages-select lyra_control && source install/setup.bash
   ```
6. Arm and run:
   ```bash
   ros2 service call /lyra/arm std_srvs/srv/Trigger
   ros2 run lyra_control color_control
   ```
7. Hold a green, red, then blue object to fill about a quarter or more of the centre of the frame. Record the response and the log lines.
8. **[PC]** Optional: view the camera in `rqt` (Image View) and `ros2 topic echo /cmd_vel_nav`.
9. `Ctrl+C` the node, then disarm.

## 7. Observations

| Object shown | Fraction of ROI (approx.) | Command seen on `/cmd_vel_nav` | Robot action |
|---|---|---|---|
| Green | | | |
| Red | | | |
| Blue | | | |
| Nothing / white wall | | | |
| Object at the frame edge (outside ROI) | | | |
| Under dim light | | | |

Threshold ranges used (from the source): green ______ red ______ / ______ blue ______.

## 8. Result
☐ State which colours were reliably detected, the effect of lighting, and the minimum object size that triggered a command.

## 9. Viva questions
1. Why HSV rather than RGB? Why does red need two ranges?
2. What does the 20 % threshold do? What if you lower it to 5 %?
3. How does this node stop on `Ctrl+C`, compared with Experiment 3?
4. What are the latency sources between camera and wheels?
5. Name the ROS perception libraries named in the syllabus (OpenCV, PCL) and when each is used.
