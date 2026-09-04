# 06 — Lab 2: connecting to BeetleBot and movement commands

**Goal of this lab:** connect to the real robot, arm it, and drive it — one-shot pulses,
timed recipes, and live keyboard teleop. Source: `docs/VEEROBOT BEETLE BOT LYRA.txt` +
`docs/Beetlebot Manual.docx` Phases 3–4. Full reconciled procedure (all handout conflicts
resolved) is `03-beetlebot-runbook.md` Phases 1–5 — this file is the "why" companion to it,
walked in lab order.

**PC vs robot matters here** — every step below says which machine it runs on.

---

## Step 1 — Network (on the PC)

```bash
ping 192.168.0.<robotNumber>            # confirm reachable; Ctrl+C once you see replies
```
PC and robot must be on the same Wi-Fi (`BEETLEBOT_5G`) and subnet. A ping timeout means
wrong network, robot not booted, or wrong IP — fix this before anything else (see
`03-beetlebot-runbook.md` "Common failures").

## Step 2 — Terminal 1: SSH in and bring up hardware (on the robot, via SSH)

```bash
ssh veerobot@192.168.0.<robotNumber>
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<robotNumber>
ros2 launch lyra_bringup robot.launch.py
```
**Leave this terminal running for the whole session.** It owns the LiDAR driver and the
UART bridge to the STM32 motor controller — closing it kills both. `ROS_DOMAIN_ID` is what
lets your PC's nodes and the robot's nodes discover each other over DDS; it must be the
**same number in every terminal, on both machines** (`02-ros2-concepts.md` §1).

## Step 3 — Terminal 2: arm the robot (on the robot, second SSH session)

```bash
ssh veerobot@192.168.0.<robotNumber>
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<robotNumber>

ros2 service call /lyra/arm std_srvs/srv/Trigger
```
The Lyra controller boots **DISARMED** on purpose — a safety interlock so a stray velocity
message can't spin the wheels before you're ready. `/lyra/arm` is a **service**
(request/response, not a topic): you call it once, it returns `success: true` + a message,
and the motor controller starts accepting `/cmd_vel_nav` commands. `std_srvs/srv/Trigger` is
the generic "just do the thing" service type — empty request, boolean + string response.
Mirror it with `/lyra/disarm` when you're done driving.

## Step 4 — Understand the message you're about to send

Every movement command below publishes a `geometry_msgs/msg/Twist`:
```yaml
linear:  {x: 0.0, y: 0.0, z: 0.0}   # metres/second
angular: {x: 0.0, y: 0.0, z: 0.0}   # radians/second
```
BeetleBot is a **skid-steer, non-holonomic** ground robot — it can only move forward/back
and rotate about its own vertical axis. That means only two of the six fields ever matter:
- **`linear.x`** — forward (+) / backward (−) speed in m/s.
- **`angular.z`** — turn rate in rad/s, **positive = left (counter-clockwise)**.
`linear.y`/`linear.z` and `angular.x`/`angular.y` are always 0 for this robot (it can't
strafe sideways or tilt) — the handouts include them for completeness since `Twist` is a
generic message shared by every robot type.

## Step 5 — One-shot test pulse

```bash
ros2 topic pub --once /cmd_vel_nav geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```
`--once` sends exactly one message. **Watch what happens next**: the robot moves briefly
then stops on its own — the motor bridge has a `cmd_vel` timeout (if no fresh command
arrives within a short window, it zeros the motors as a safety measure). A single message is
enough to *test* the link, but not enough to *drive* — hence Step 6.

## Step 6 — Timed movement recipes (the `-r`/`-t` pattern)

```bash
# forward 5 s, then a forced stop for 1.5 s
ros2 topic pub -r 10 -t 50 /cmd_vel_nav geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" && \
ros2 topic pub -r 10 -t 15 /cmd_vel_nav geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```
- **`-r 10`** = republish at 10 Hz — this is what defeats the `cmd_vel` timeout from Step 5;
  the motor bridge always has a fresh message.
- **`-t 50`** = stop after sending 50 messages. At 10 Hz that's `50 / 10 = 5` seconds.
- **`&&`** chains the two commands: the second (the stop) only starts once the first
  finishes — you always end a movement recipe with an explicit zero-Twist stop, never let it
  just trail off, or residual queued messages can keep the wheels turning slightly longer
  than you expect.

Same pattern scales to any sequence — the handout's other recipes are all built from these
same two building blocks:
- **Move backward**: same as above with `linear.x: -0.3`.
- **Emergency flood-stop**: `-r 20 -t 40` (20 Hz for 2 s) of an all-zero `Twist` — the higher
  rate is deliberate, so this stop message wins the race against whatever is still being
  queued.
- **Advanced sequence** (forward → stop → backward → stop) and **square path** (drive → stop
  → turn `angular.z: 0.5` → stop, ×4) are just more `&&`-chained pairs/quadruples of the
  same publish command. A turn's actual angle depends on the robot's real angular velocity
  at that `angular.z`, not just the wall-clock duration — treat 90°-per-turn as approximate
  and expect to tune the timing on the day.

## Step 7 — Live keyboard teleop (usually easier than scripted recipes)

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=cmd_vel_nav
```
`-r cmd_vel:=cmd_vel_nav` **remaps** the tool's default output topic (`cmd_vel`) onto the
robot's actual drive topic (`cmd_vel_nav`) — see technical debt #3 in `.CLAUDE/CLAUDE.md`
for why the lab uses `/cmd_vel_nav` instead of the upstream repo's plain `/cmd_vel`. This
remap is the only thing that makes a generic, un-modified tool work with this specific
robot — you never need to edit or fork `teleop_twist_keyboard` itself.

Keys: `i`=forward, `,`=backward, `j`=turn left, `l`=turn right, `k`=stop.
`q`/`z` = all speeds ±10%, `w`/`x` = linear only, `e`/`c` = angular only.

Verify what's actually being sent, from a third terminal:
```bash
ros2 topic echo /cmd_vel_nav
```

## Step 8 — Disarm when done

```bash
ros2 service call /lyra/disarm std_srvs/srv/Trigger
```
Do this every time you're finished driving, even if the robot already looks stopped — it's
the difference between "wheels are at zero velocity" and "wheels physically cannot receive
a velocity command". Full emergency-stop ladder (what to do if this *isn't* enough) is in
`03-beetlebot-runbook.md`, "Emergency stops — know all of these cold".

---

## Checklist — can you do this from memory?

- [ ] `ping` the robot before anything else
- [ ] Two separate SSH sessions: Terminal 1 = bringup (leave running), Terminal 2 = drive
- [ ] Same `ROS_DOMAIN_ID` exported in every terminal, PC and robot
- [ ] Arm before expecting any motion; disarm when done
- [ ] Explain why only `linear.x` and `angular.z` matter for this robot
- [ ] Explain what `-r` and `-t` do and why a stop is always chained with `&&`
- [ ] Run keyboard teleop with the `cmd_vel:=cmd_vel_nav` remap
- [ ] Name at least two independent ways to force an immediate stop

Next: `07-lab3-obstacle-avoidance.md`.
