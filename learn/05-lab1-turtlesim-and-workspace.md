# 05 — Lab 1: workspace setup + turtlesim publish/subscribe

**Goal of this lab:** prove your ROS 2 install works, and learn the publish/subscribe
pattern on a harmless simulated turtle *before* touching the real robot. Source:
`docs/Beetlebot Manual.docx`, Phases 1–2. This is a checklist — for what each command
actually does, see the linked sections in `01-linux-commands.md` / `02-ros2-concepts.md`.

Runs **on the PC** (or any Linux box / `docker run -it ros:jazzy`) — no robot needed yet.

---

## Step 1 — Make your own workspace

```bash
mkdir -p ~/<registerNumber>_ws/src        # your workspace, NOT the robot's ~/lyra_ws
cd ~/<registerNumber>_ws
source /opt/ros/jazzy/setup.bash
colcon build                               # builds an empty ws — just to create install/
echo "source ~/<registerNumber>_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

**Why a separate workspace from the robot's `~/lyra_ws`?** `~/lyra_ws` is the robot's own
built stack — you never build into it. Your workspace is a second *overlay* on top of the
same `/opt/ros/jazzy` *underlay*; ROS lets you stack multiple overlays like this (see
`02-ros2-concepts.md` §3, "Underlay vs overlay"). Building it now, even empty, catches a
broken `colcon`/environment before you're mid-lab.

## Step 2 — Install and run turtlesim

```bash
sudo apt update
sudo apt install ros-jazzy-turtlesim

# terminal 1
source /opt/ros/jazzy/setup.bash
ros2 run turtlesim turtlesim_node
```

A window opens with a turtle in the middle. This process is a **node** — it has subscribed
to a velocity topic and publishes its own position, exactly like the real robot's motor
bridge will later.

## Step 3 — Drive it (this *is* the publish/subscribe pattern)

```bash
# terminal 2
source /opt/ros/jazzy/setup.bash
ros2 run turtlesim turtle_teleop_key      # arrow keys move the turtle
```

What's happening: `turtle_teleop_key` is a **publisher** node — every arrow-key press makes
it publish one `geometry_msgs/msg/Twist` message on the topic `/turtle1/cmd_vel`.
`turtlesim_node` is a **subscriber** on that same topic — its callback fires on every
message and moves the turtle. Neither node knows the other exists directly; they only agree
on a topic name and message type. This exact pattern — one node publishes a `Twist`, another
subscribes and moves — is precisely what happens on BeetleBot with `/cmd_vel_nav` (Lab 2)
and what the obstacle-avoidance node does with `/scan` in, `/cmd_vel_nav` out (Lab 3).

Alternative teleop (the general-purpose one you'll also use on the real robot, with a
topic **remap** since its default output name doesn't match turtlesim's):
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=turtle1/cmd_vel
```

## Step 4 — Inspect the topic from a third terminal

```bash
# terminal 3
source /opt/ros/jazzy/setup.bash
ros2 topic list                                   # -> /turtle1/cmd_vel, /turtle1/pose, ...
ros2 topic echo /turtle1/cmd_vel                  # print each Twist message as it's sent
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 2.0}, angular: {z: 1.8}}"          # drive it from the CLI, no teleop needed
```
Full CLI reference (`topic info`, `hz`, `bw`, `node info`, …) is in `02-ros2-concepts.md` §2.

## Step 5 — Record what you saw

```bash
ros2 bag record /turtle1/cmd_vel                  # Ctrl+C to stop recording
ros2 bag record -o my_cmd_vel_bag /turtle1/cmd_vel # -o names the output folder
ros2 topic echo /turtle1/cmd_vel > scan_output.txt # plain-text capture instead of a bag
```
`ros2 bag` mechanics (what a bag actually is, `play`/`info`) are in `02-ros2-concepts.md` §2.

---

## Checklist — can you do this from memory?

- [ ] Create a workspace under your own register number, not `lyra_ws`
- [ ] Explain underlay vs overlay in one sentence
- [ ] Start `turtlesim_node`, then drive it with `turtle_teleop_key`
- [ ] Say, without looking, which node is the publisher and which is the subscriber
- [ ] `ros2 topic list` / `echo` / `pub --once` on `/turtle1/cmd_vel`
- [ ] Record a bag and know what `-o` does

Next: `06-lab2-beetlebot-movement.md`.
