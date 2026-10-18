# Experiment 2 — Connecting to BeetleBot and movement commands

## 1. Aim
To connect to the BeetleBot over Wi-Fi/SSH, arm its motor controller, and drive it using single messages, timed message streams and keyboard teleoperation.

## 2. Learning outcomes
Connect and verify a ROS 2 network between PC and robot; explain why the controller is disarmed by default; build `Twist` commands for a skid-steer robot; use `-r`/`-t` to publish timed motions; stop the robot safely in several independent ways.

## 3. Apparatus
- BeetleBot "Lyra": 4-wheel skid-steer, Raspberry Pi 5 (ROS 2 Jazzy), STM32F405 motor controller, RPLiDAR C1, max 1.0 m/s
- Lab PC with ROS 2 Jazzy on the `BEETLEBOT_5G` network
- Clear floor area (≥2 m × 2 m)

## 4. Theory
**Architecture.** The Pi runs the ROS 2 stack; `lyra_bridge` talks to the STM32 over UART. The
STM32 (FreeRTOS) runs the real-time PID wheel control. ROS-side code never has deterministic
motor timing.

**Skid-steer kinematics.** Wheels on a side turn together; turning is done by a speed
difference, so the robot is non-holonomic: only `linear.x` (m/s, forward +) and `angular.z`
(rad/s, left +) are meaningful. For a differential model with track width *b*:
v_left = v − ω·b/2, v_right = v + ω·b/2 (see `practice/robot_calc`, set `dd_kinematics`).

**Safety interlocks.** The controller boots **disarmed**; `/lyra/arm` (`std_srvs/srv/Trigger`)
enables motion. The bridge also has a `cmd_vel` **timeout**: if no fresh command arrives soon,
wheels are zeroed.

**DDS discovery.** PC and robot nodes find each other only on the same subnet **and** same
`ROS_DOMAIN_ID`.

## 5. Pre-lab questions
1. Why only two of the six `Twist` fields matter here?
2. Why does a single `topic pub --once` move the robot only briefly?
3. Why is a service (not a topic) used to arm?

## 6. Procedure
1. **[PC]** Connect to Wi-Fi, then:
   ```bash
   ip a                                   # address should be 192.168.0.x
   ping 192.168.0.<robotNumber>
   ```
2. **[Robot] Terminal 1 — bring-up (leave running):**
   ```bash
   ssh veerobot@192.168.0.<robotNumber>
   source /opt/ros/jazzy/setup.bash
   source ~/lyra_ws/install/setup.bash
   export ROS_DOMAIN_ID=<robotNumber>
   ros2 launch lyra_bringup robot.launch.py
   ```
3. **[PC]** Verify discovery:
   ```bash
   source /opt/ros/jazzy/setup.bash
   export ROS_DOMAIN_ID=<robotNumber>
   ros2 node list
   ros2 topic list
   ros2 topic hz /scan
   ```
4. **[Robot] Terminal 2** (new SSH, same three source/export lines) — arm:
   ```bash
   ros2 service call /lyra/arm std_srvs/srv/Trigger
   ```
5. Single pulse:
   ```bash
   ros2 topic pub --once /cmd_vel_nav geometry_msgs/msg/Twist \
     "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
   ```
6. Timed motion (5 s forward then stop):
   ```bash
   ros2 topic pub -r 10 -t 50 /cmd_vel_nav geometry_msgs/msg/Twist "{linear: {x: 0.3}, angular: {z: 0.0}}" && \
   ros2 topic pub -r 10 -t 15 /cmd_vel_nav geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
   ```
7. Repeat for: backward (`x: -0.3`), spin in place (`x: 0.0, z: 0.5`), and a square path (drive → stop → turn → stop, ×4).
8. Keyboard teleop:
   ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=cmd_vel_nav
   ```
   `i` forward · `,` back · `j`/`l` turn · `k` stop · `q`/`z` speed ±10%.
9. **[PC]** Watch the commands: `ros2 topic echo /cmd_vel_nav`.
10. Practise the stops: flood-stop `ros2 topic pub -r 20 -t 40 /cmd_vel_nav … zeros`, then
    **disarm**: `ros2 service call /lyra/disarm std_srvs/srv/Trigger`.

## 7. Observations

| Test | Command (v, ω, rate, count) | Expected duration (count/rate) | Measured distance / angle | Remarks |
|---|---|---|---|---|
| Single pulse | `x: 0.3`, once | — | | |
| Forward 5 s | 0.3 m/s, 10 Hz, 50 | 5 s | | |
| Backward 5 s | −0.3 m/s | 5 s | | |
| Spin in place | ω = 0.5 rad/s, 10 Hz, ___ | | angle turned: | |
| Square path | | | closing error: | |

| Check | Result |
|---|---|
| `ping` round-trip time | |
| `/scan` rate (`topic hz`) | |
| Does the robot move **before** arming? | |
| Stop methods tried and time to stop | |

## 8. Result
☐ State that the robot was armed, driven by pulses, timed streams and teleop, and compare expected vs measured distance (explain the difference: wheel slip, ramping, timeout).

## 9. Viva questions
1. Why is the controller disarmed at boot? What does arming change?
2. Explain `-r 10 -t 50`. How long does the robot move?
3. Why chain a zero-velocity stop with `&&`?
4. Why `/cmd_vel_nav` and not `/cmd_vel`? (handouts vs upstream repo)
5. What do `ROS_DOMAIN_ID` and the subnet do for discovery?
6. List four independent ways to stop the robot.
7. Why can the PC be Linux while the real-time motor loop is on an STM32?
