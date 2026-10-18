# Experiment 1 — Workspace setup and turtlesim publish/subscribe

## 1. Aim
To set up a ROS 2 (Jazzy) workspace and demonstrate the publish/subscribe model by driving the simulated turtle in `turtlesim`.

## 2. Learning outcomes
After this experiment you can: create and build a colcon workspace; explain underlay vs overlay; start nodes and inspect topics with the `ros2` CLI; identify publisher and subscriber in a running system; record topic data to a bag.

## 3. Apparatus
- Linux PC (Ubuntu 22.04/24.04) with ROS 2 Jazzy, **or** `docker run -it ros:jazzy`
- Packages: `ros-jazzy-turtlesim`, `ros-jazzy-teleop-twist-keyboard`
- No robot needed.

## 4. Theory
ROS 2 is a set of **nodes** (processes) that exchange typed messages over **topics** using DDS.
A **publisher** writes messages to a named topic; every **subscriber** to that topic receives
them through a callback. Nodes do not know each other — they agree only on topic name and
message type. Here, `turtle_teleop_key` publishes `geometry_msgs/msg/Twist` (linear velocity in
m/s, angular velocity in rad/s) on `/turtle1/cmd_vel`; `turtlesim_node` subscribes and moves the
turtle, and publishes its pose on `/turtle1/pose`.

A **workspace** is a folder with `src/` where packages are built by `colcon`, producing
`install/`. Sourcing `install/setup.bash` adds it as an **overlay** on top of the system
**underlay** (`/opt/ros/jazzy`). See `learn/foundations/02-ros2-concepts.md`.

## 5. Pre-lab questions
1. What is the difference between a topic and a service?
2. What fields of `Twist` matter for a differential-drive robot?
3. Why build an empty workspace before you have any code?

## 6. Procedure
**[PC]** — all steps.

1. Create and build the workspace:
   ```bash
   mkdir -p ~/<registerNumber>_ws/src
   cd ~/<registerNumber>_ws
   source /opt/ros/jazzy/setup.bash
   colcon build
   echo "source ~/<registerNumber>_ws/install/setup.bash" >> ~/.bashrc
   source ~/.bashrc
   ```
2. Install and start turtlesim (Terminal 1):
   ```bash
   sudo apt update && sudo apt install ros-jazzy-turtlesim
   ros2 run turtlesim turtlesim_node
   ```
3. Drive it with the keyboard (Terminal 2):
   ```bash
   ros2 run turtlesim turtle_teleop_key
   ```
4. Inspect from Terminal 3:
   ```bash
   ros2 node list
   ros2 topic list
   ros2 topic info /turtle1/cmd_vel
   ros2 topic echo /turtle1/cmd_vel
   ros2 topic hz /turtle1/pose
   ros2 run rqt_graph rqt_graph
   ```
5. Drive without the keyboard node:
   ```bash
   ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
     "{linear: {x: 2.0}, angular: {z: 1.8}}"
   ```
6. Try the general teleop with a remap:
   ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=turtle1/cmd_vel
   ```
7. Record and replay:
   ```bash
   ros2 bag record -o my_cmd_vel_bag /turtle1/cmd_vel      # Ctrl+C to stop
   ros2 bag info my_cmd_vel_bag
   ros2 bag play my_cmd_vel_bag                             # with turtlesim running
   ```

## 7. Observations

| Item | Observed |
|---|---|
| `ros2 node list` output | |
| `ros2 topic list` output | |
| `ros2 topic info /turtle1/cmd_vel` — publisher count / subscriber count | |
| Type of `/turtle1/cmd_vel` | |
| Publish rate of `/turtle1/pose` (`topic hz`) | |
| `Twist` values seen when pressing ↑ / ← | |
| Effect of `topic pub --once` with `{linear: {x: 2.0}, angular: {z: 1.8}}` | |
| Bag: duration, message count (`bag info`) | |
| Screenshot of `rqt_graph` | (attach) |

## 8. Result
☐ State that the workspace built, turtlesim ran, which node was publisher and which subscriber, and that the bag replayed the motion.

## 9. Viva questions
1. Which node is the publisher and which the subscriber in step 3? How do you prove it from the CLI?
2. What happens if two nodes publish to `/turtle1/cmd_vel` at once?
3. Explain `--remap cmd_vel:=turtle1/cmd_vel`.
4. Underlay vs overlay — what happens if you forget to `source` your workspace?
5. What replaced `roscore` in ROS 2?
