# Teleoperation Control

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand teleoperation architecture
* ✅ Master joystick control techniques
* ✅ Implement keyboard teleoperation
* ✅ Create custom control interfaces
* ✅ Understand velocity ramping and safety systems
* ✅ Tune motion control parameters
* ✅ Debug control issues
* ✅ Compare different control methods

#### ⏱️ Time Required

* **Reading & Theory:** 20 minutes
* **Joystick Control Practice:** 25 minutes
* **Keyboard Implementation:** 30 minutes
* **Custom Control:** 25 minutes
* **Parameter Tuning:** 20 minutes
* **Total:** \~120 minutes

#### 📚 Prerequisites

* ✅ Completed ROS2 Communication & Tools
* ✅ Can visualize robot in RViz
* ✅ Understand topics and services
* ✅ Comfortable with command line
* ✅ Basic Python knowledge (for custom control)

#### 🛠️ What You'll Need

* ✅ Beetlebot (powered, fully charged)
* ✅ Laptop with ROS2 Jazzy
* ✅ Wireless controller (Cosmic Byte Nexus)
* ✅ USB keyboard
* ✅ Open space (3m × 3m minimum)
* ✅ RViz for visualization

***

### Part 1: Teleoperation Architecture

#### Understanding the Control Chain

**Complete signal flow:**

```
Controller (Cosmic Byte)
    ↓ USB RF Dongle
    ↓ /joy topic (sensor_msgs/Joy)
Joy Node (joy_node)
    ↓ Button/axis values
Teleop Node (lyra_teleop_node)
    ↓ /cmd_vel_joy topic (geometry_msgs/Twist)
    ↓ Converts joy → velocity
Cmd Vel Mux (mux_node)
    ↓ Arbitrates multiple cmd_vel sources
    ↓ /cmd_vel topic (geometry_msgs/Twist)
Safety Gate (lyra_cmd_vel_gate_node)
    ↓ Checks ARM status, applies limits
    ↓ /cmd_vel_safe topic
Lyra Node (lyra_node)
    ↓ Velocity ramping (smooth acceleration)
    ↓ PID control at 20 Hz
STM32 Motor Controllers
    ↓ PWM signals
DRV8874 Motor Drivers
    ↓ Current to motors
Motors → Wheels → Motion!
```

***

#### Key Nodes Explained

**1. joy\_node (ROS2 standard)**

* Reads USB controller via Linux input system
* Publishes raw button/axis data
* Topic: `/joy`
* Rate: \~50-100 Hz (when buttons pressed)

**2. lyra\_teleop\_node (Beetlebot-specific)**

* Maps joystick axes to velocities
* Handles deadman switch (LB button)
* Publishes velocity commands
* Topic: `/cmd_vel_joy`

**3. cmd\_vel\_mux (multiplexer)**

* Combines multiple velocity sources:
  * `/cmd_vel_joy` (joystick - highest priority)
  * `/cmd_vel_nav` (autonomous navigation)
  * `/cmd_vel` (keyboard/external)
* Joystick always wins (safety!)
* Output: `/cmd_vel`

**4. lyra\_cmd\_vel\_gate\_node (safety)**

* Checks if robot is ARMED
* Applies velocity limits
* Emergency stop logic
* Topic: `/cmd_vel_safe`

**5. lyra\_node (motor control)**

* **Velocity ramping** (smooth acceleration)
* PID control for each wheel
* Sends commands to STM32
* Receives encoder feedback

***

#### Velocity Ramping Deep Dive

**Critical feature:** Beetlebot doesn't jump to commanded velocity instantly!

**How it works:**

```
Target speed: 1.0 m/s (from joystick)
Current speed: 0.0 m/s (robot stationary)

Control cycle 1 (t=0.00s): Current = 0.0 m/s
  → Ramp up by max_accel (5 RPM/cycle)
  → New speed = 0.03 m/s

Control cycle 2 (t=0.05s): Current = 0.03 m/s
  → Ramp up by 5 RPM/cycle
  → New speed = 0.07 m/s

... (continue ramping)

Control cycle ~20 (t=1.00s): Current reaches target
  → Ramp up
  → New speed = 1.00 m/s ← Target reached!
```

**Ramp rate:** 5 RPM per control cycle (`MAX_RPM_STEP_PER_CYCLE` in `robot_config.h`)

* Control frequency: 20 Hz (every 50ms)
* Total ramp time: \~1 second (0 → max speed)
* Equivalent linear acceleration: \~0.68 m/s²

***

#### **CRITICAL: Emergency Stop Behavior**

**LB button (deadman switch) has special behavior:**

**While LB held:** Smooth ramping (as described above)

**LB released:** ⚠️ **IMMEDIATE STOP**

* No ramping! Motors stop instantly
* Robot disarms (requires re-pressing LB to move again)
* Safety feature: operator must maintain control

**Why immediate stop on LB release?**

* Deadman switch must be instant (safety requirement)
* Operator losing control = robot must stop NOW
* Cannot wait 1 second for ramp-down

**Example scenario:**

```
1. Driving forward at 1.0 m/s
2. Release LB button
3. Robot stops in ~0.1 seconds (not 1 second)
4. Must press LB again to resume control
```

***

### Part 2: Mastering Joystick Control

#### Controller Layout Review

**Cosmic Byte Nexus controller:**

```
        [LB]               [RB]

    [Left Stick]      [Right Stick]

    [D-Pad]           [A][B]
                      [X][Y]
```

**Beetlebot mapping:**

* **LB (Left Bumper):** ARM/Deadman switch (MUST hold!)
* **Left Stick Y-axis:** Forward/backward speed
* **Right Stick X-axis:** Turning (left/right)
* **RB (Right Bumper):** Turbo mode (2× speed)
* **Other buttons:** Currently unused

***

#### Basic Control Techniques

**Exercise 6.1: Smooth Acceleration**

**Task:** Feel the velocity ramping

```
Setup:
1. Place robot in open area
2. Launch RViz with odometry display
3. Power on robot, let it boot (90 seconds)

Test:
1. Press and hold LB
2. Gently push left stick forward (50%)
3. Observe in RViz:
   - Velocity doesn't jump instantly
   - Smooth ramp-up over ~0.5 seconds
   - Steady velocity achieved

4. Release left stick (keep LB held!)
5. Observe:
   - Smooth ramp-down to zero
   - Not instant stop

6. Now release LB
7. Observe:
   - INSTANT stop (no ramp!)
   - Robot disarms
```

**What you learned:**

* Ramping makes motion smooth and predictable
* LB release = emergency stop (no ramp)
* Robot feels professional (not jerky like toy robots)

***

#### Advanced Driving Patterns

**Exercise 6.2: Precision Maneuvering**

**Task 1: Straight line**

```
Goal: Drive exactly 2 meters in straight line

Technique:
1. Hold LB + push left stick forward 30% (slow speed)
2. Keep right stick centered (no turn input)
3. Watch odometry in RViz
4. Stop when x = 2.0 meters

Challenge: Can you stay within ±5cm of straight line?

Tip: Small right stick movements for course corrections
```

**Task 2: 90° turn**

```
Goal: Turn exactly 90° left

Technique:
1. Robot stationary (LB held, sticks centered)
2. Push right stick left ~40%
3. Watch orientation in RViz (or use protractor on floor)
4. Release right stick when yaw = 90°

Challenge: Can you achieve 90° ±3°?

Tip: Use slow turn speed for precision
```

**Task 3: Figure-8 pattern**

```
Goal: Drive smooth figure-8 (each loop 1m diameter)

Technique:
1. Forward + gentle left turn (left stick forward + right stick left)
2. Maintain constant speed throughout
3. Smooth transition at crossover point
4. Complete 3 figure-8s

Challenge: Keep loops symmetrical

Tip: Constant gentle inputs, no jerking
```

**Task 4: Parallel parking**

```
Goal: Park robot parallel to wall, 20cm away

Setup:
1. Place two obstacles 80cm apart (robot length + margin)
2. Start perpendicular to "parking spot"

Technique:
1. Drive forward past first obstacle
2. Turn sharp left while reversing (left stick back + right stick left)
3. Straighten out parallel to wall
4. Adjust distance with small forward/back movements

Challenge: Park within 20cm ±2cm from wall
```

***

#### Exercise 6.3: Turbo Mode

**RB button doubles max speed (safety feature disabled!)**

**Task:** Compare normal vs turbo

```
Test 1: Normal speed (no RB)
1. Hold LB, push left stick 100% forward
2. Observe speed in RViz (/cmd_vel topic)
3. Note: Max linear.x = ~1.0 m/s

Test 2: Turbo mode (RB pressed)
1. Hold LB + RB
2. Push left stick 100% forward
3. Observe speed
4. Note: Max linear.x = ~2.0 m/s

⚠️ Warning: Turbo mode increases:
- Crash risk (less reaction time)
- Wheel slip (especially on turns)
- Odometry drift (encoders may skip)

Use turbo only in large open areas!
```

***

#### Understanding Joystick Dead Zones

**Problem:** Joystick resting position isn't exactly centered

* Reads \~0.02 instead of 0.00
* Would cause slow creep

**Solution:** Dead zone

* Values < threshold treated as zero
* Typical: ±5% dead zone

**Check dead zone:**

```bash
# Echo joystick values
ros2 topic echo /joy

# With sticks centered, observe axes values
# Should be very close to 0.0 (within ±0.05)

# If robot creeps with sticks centered → dead zone too small
# If robot doesn't respond to gentle stick push → dead zone too large
```

***

### Part 3: Keyboard Teleoperation

#### Using Built-in Keyboard Teleop

**Standard ROS2 tool:**

```bash
# On laptop (robot on same network)
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Output:
# Reading from the keyboard and publishing to Twist!
# ---------------------------
# Moving around:
#    u    i    o
#    j    k    l
#    m    ,    .
#
# u/o : forward + turn
# i   : forward
# j/l : turn left/right in place
# m/. : backward + turn
# ,   : backward
# k   : stop
#
# q/z : increase/decrease max speeds by 10%
# w/x : increase/decrease linear speed by 10%
# e/c : increase/decrease angular speed by 10%
```

**Try driving patterns:**

```
1. Straight forward: Press 'i' repeatedly
2. Turn left: Press 'j' once (turns in place)
3. Circle: Press 'u' repeatedly (forward + left turn)
4. Stop: Press 'k' (or spacebar)
```

***

#### Creating Custom Keyboard Control

> \[!WARNING] **TODO: Exercise Script Not Included in Core Repository** The `custom_teleop.py` script below is an exercise for the user to practice writing ROS2 publishers. It does *not* come pre-installed in the Beetlebot ROS2 packages. You are encouraged to follow the steps to create it yourself!

**More ergonomic layout: WASD + arrow keys**

```bash
nano ~/custom_teleop.py
```

**Script:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import select
import termios
import tty

class CustomTeleop(Node):
    def __init__(self):
        super().__init__('custom_teleop')

        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)

        # Velocity settings
        self.linear_speed = 0.5   # m/s
        self.angular_speed = 1.0  # rad/s
        self.speed_increment = 0.1

        self.current_linear = 0.0
        self.current_angular = 0.0

        # Key mappings
        self.move_bindings = {
            'w': (1, 0),    # Forward
            's': (-1, 0),   # Backward
            'a': (0, 1),    # Turn left
            'd': (0, -1),   # Turn right
            'q': (1, 1),    # Forward + left
            'e': (1, -1),   # Forward + right
            'z': (-1, 1),   # Backward + left
            'c': (-1, -1),  # Backward + right
        }

        self.speed_bindings = {
            '+': (1.1, 1.1),   # Increase both
            '-': (0.9, 0.9),   # Decrease both
            '[': (1.1, 1.0),   # Increase linear only
            ']': (0.9, 1.0),   # Decrease linear only
            '{': (1.0, 1.1),   # Increase angular only
            '}': (1.0, 0.9),   # Decrease angular only
        }

        self.get_logger().info("Custom Teleop Ready!")
        self.print_instructions()

        # Timer for velocity decay (stop if no key pressed)
        self.timer = self.create_timer(0.1, self.velocity_decay)

        self.settings = termios.tcgetattr(sys.stdin)

    def print_instructions(self):
        print("\n" + "="*50)
        print("Custom Keyboard Teleop - WASD Controls")
        print("="*50)
        print("\nMovement:")
        print("  W : Forward")
        print("  S : Backward")
        print("  A : Turn Left")
        print("  D : Turn Right")
        print("  Q : Forward + Left")
        print("  E : Forward + Right")
        print("  Z : Backward + Left")
        print("  C : Backward + Right")
        print("  Spacebar : Stop")
        print("\nSpeed adjustment:")
        print("  + / - : Increase/decrease all speeds")
        print("  [ / ] : Increase/decrease linear speed")
        print("  { / } : Increase/decrease angular speed")
        print("\nCurrent speeds:")
        print(f"  Linear: {self.linear_speed:.2f} m/s")
        print(f"  Angular: {self.angular_speed:.2f} rad/s")
        print("\nPress Ctrl+C to quit\n")

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        select.select([sys.stdin], [], [], 0)
        key = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def velocity_decay(self):
        # Gradually reduce velocity if no input (simulates key release)
        if abs(self.current_linear) > 0.01 or abs(self.current_angular) > 0.01:
            self.current_linear *= 0.8
            self.current_angular *= 0.8
            self.publish_velocity()

    def publish_velocity(self):
        msg = Twist()
        msg.linear.x = self.current_linear
        msg.angular.z = self.current_angular
        self.publisher.publish(msg)

    def run(self):
        try:
            while True:
                key = self.get_key()

                if key in self.move_bindings:
                    linear_dir, angular_dir = self.move_bindings[key]
                    self.current_linear = linear_dir * self.linear_speed
                    self.current_angular = angular_dir * self.angular_speed
                    self.publish_velocity()

                elif key in self.speed_bindings:
                    linear_mult, angular_mult = self.speed_bindings[key]
                    self.linear_speed *= linear_mult
                    self.angular_speed *= angular_mult
                    print(f"Speeds: Linear={self.linear_speed:.2f} m/s, Angular={self.angular_speed:.2f} rad/s")

                elif key == ' ':
                    # Spacebar = stop
                    self.current_linear = 0.0
                    self.current_angular = 0.0
                    self.publish_velocity()

                elif key == '\x03':  # Ctrl+C
                    break

        except Exception as e:
            print(e)

        finally:
            # Stop robot on exit
            msg = Twist()
            self.publisher.publish(msg)
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)

def main(args=None):
    rclpy.init(args=args)
    node = CustomTeleop()
    node.run()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Run custom teleop:**

```bash
chmod +x ~/custom_teleop.py
python3 ~/custom_teleop.py
```

**Drive with WASD keys!**

***

#### Exercise 6.4: Compare Control Methods

**Task:** Drive same path with different control methods

**Path:** 2m × 2m square

**Method 1: Joystick**

* Time yourself
* Count how many "corrections" needed
* Rate smoothness (1-10)

**Method 2: Standard keyboard (i/j/k/l)**

* Time yourself
* Count corrections
* Rate smoothness

**Method 3: Custom keyboard (WASD)**

* Time yourself
* Count corrections
* Rate smoothness

**Analysis:**

* Which was fastest?
* Which was smoothest?
* Which required most corrections?
* Which did you prefer?

<details>

<summary>Typical results</summary>

**Joystick:**

* Fastest (analog control)
* Smoothest (continuous input)
* Fewest corrections
* Best for general driving

**Keyboard:**

* Slower (discrete steps)
* Less smooth (on/off inputs)
* More corrections needed
* Good for precise positioning (step-by-step)
* 500ms safety timer will make it jerky as it auto disarms and rearms

**Best practice:** Joystick for driving, keyboard for quick testing

</details>

***

### Part 4: Understanding /cmd\_vel Topic

#### Twist Message Structure

**Topic:** `/cmd_vel`\
**Type:** `geometry_msgs/msg/Twist`

**Message definition:**

```bash
ros2 interface show geometry_msgs/msg/Twist

# Output:
# Vector3 linear
#   float64 x
#   float64 y
#   float64 z
# Vector3 angular
#   float64 x
#   float64 y
#   float64 z
```

**For Beetlebot (4-wheel skid-steer drive):**

```
linear.x:  Forward/backward speed (m/s)
  - Positive = forward
  - Negative = backward
  - Range: -1.0 to +1.0 m/s (normal mode)

linear.y:  UNUSED (skid-steer can't strafe sideways)

linear.z:  UNUSED (robot doesn't fly!)

angular.x: UNUSED (robot doesn't roll)

angular.y: UNUSED (robot doesn't pitch)

angular.z: Turn rate (rad/s)
  - Positive = turn left (counterclockwise)
  - Negative = turn right (clockwise)
  - Range: -2.0 to +2.0 rad/s
```

***

#### Publishing Manual Commands

**Test commands via command line:**

```bash
# Forward at 0.5 m/s
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Turn left (in place) at 1.0 rad/s
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.0}}"

# Forward + turn (arc motion)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"
```

**⚠️ Important:** These are single commands! Robot executes then stops. **Note:** These are controller limits. Robot's Lyra controller also has hardware ramping (5 RPM/cycle, `MAX_RPM_STEP_PER_CYCLE` in firmware)!

**For continuous motion:**

```bash
# Publish at 10 Hz
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Press Ctrl+C to stop
```

***

#### Exercise 6.5: Command Line Control Patterns

**Task:** Drive patterns using only CLI

**Pattern 1: Drive 1 meter forward**

```bash
# Calculate: At 0.5 m/s, takes 2 seconds
ros2 topic pub --rate 20 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Wait 2 seconds, then Ctrl+C
```

**Pattern 2: Turn 180°**

```bash
# 180° = π radians
# At 1.0 rad/s, takes π/1.0 = 3.14 seconds

ros2 topic pub --rate 20 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.0}}"

# Wait ~3.14 seconds, then Ctrl+C
```

**Pattern 3: Circle (radius 1m)**

```bash
# Circle equation: v = ω × r
# For r=1m circle, v = ω
# Choose ω=0.5 rad/s → v=0.5 m/s
# Circumference = 2πr = 6.28m
# Time = 6.28 / 0.5 = 12.56 seconds

ros2 topic pub --rate 20 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"

# Wait 12.56 seconds for complete circle
```

***

### Part 5: Safety Systems

#### ARM/DISARM Mechanism

**Purpose:** Prevent accidental motion

**ARM = Motors enabled**

* Can respond to /cmd\_vel commands
* Joystick LB button pressed
* Or service call: `/lyra/arm`

**DISARM = Motors disabled**

* Ignores /cmd\_vel commands (for safety)
* Joystick LB button released
* Or service call: `/lyra/disarm`
* Or timeout: No cmd\_vel for 500ms

***

#### Check ARM Status

```bash
# Check current status
ros2 topic echo /lyra/armed --once

# Output:
# data: true  ← Armed (can move)
# data: false ← Disarmed (won't move)
```

***

#### Manual ARM/DISARM

```bash
# ARM robot
ros2 service call /lyra/arm std_srvs/srv/Trigger

# Response:
# success: True
# message: 'Motors armed'

# DISARM robot
ros2 service call /lyra/disarm std_srvs/srv/Trigger

# Response:
# success: True
# message: 'Motors disarmed'
```

***

#### Command Timeout Safety

**Built-in safety:** If no cmd\_vel received for 500ms → DISARM

**Test:**

```bash
# 1. ARM robot (with joystick LB or service)
ros2 service call /lyra/arm std_srvs/srv/Trigger

# 2. Send single velocity command
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 3. Robot moves briefly, then stops after 500ms
# 4. Check ARM status
ros2 topic echo /lyra/armed --once
# data: false ← Automatically disarmed!
```

**Why?** Safety! If controller disconnects or node crashes, robot stops.

***

#### Emergency Stop

**Immediately stop robot:**

```bash
ros2 service call /lyra/emergency_stop std_srvs/srv/Trigger

# Robot stops instantly
# Disarms
# Requires manual re-arm to move again
```

**When to use:**

* Robot behaving unexpectedly
* About to collide
* Software error
* Any emergency situation

***

#### Velocity Limits (Safety Gate)

**Safety gate node enforces maximum speeds:**

```bash
# Check current limits
ros2 param get /lyra_cmd_vel_gate_node max_linear_velocity
# Response: 1.0 (m/s)

ros2 param get /lyra_cmd_vel_gate_node max_angular_velocity
# Response: 2.0 (rad/s)
```

**Even if cmd\_vel requests faster, these limits are enforced!**

**Example:**

```bash
# Try to command 5.0 m/s (way too fast!)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 5.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Check what actually gets sent to motors:
ros2 topic echo /cmd_vel_safe --once

# Output:
# linear.x: 1.0  ← Clamped to max!
```

***

### Part 6: Motion Control Parameters

#### Key Parameters

**Location:** `/lyra_node` parameters

**Critical parameters:**

```bash
# View all parameters
ros2 param list /lyra_node

# Key parameters:
# - wheel_radius: 0.065 (meters)
# - wheelbase: 0.295 (meters)
# - max_rpm: 150 (motor speed limit)
# - control_frequency: 20 (Hz)
# - pid_kp, pid_ki, pid_kd: PID gains
```

***

#### Tuning Max Speed

**Change maximum velocity:**

```bash
# Current max
ros2 param get /lyra_node max_linear_velocity
# Response: 1.0

# Reduce for safer operation (good for beginners)
ros2 param set /lyra_node max_linear_velocity 0.5

# Now robot won't exceed 0.5 m/s, even with full joystick

# Reset to default
ros2 param set /lyra_node max_linear_velocity 1.0
```

***

#### Tuning Turn Rate

```bash
# Current max turn rate
ros2 param get /lyra_node max_angular_velocity
# Response: 2.0 (rad/s)

# Reduce for gentler turns
ros2 param set /lyra_node max_angular_velocity 1.0

# Sharp turns for tight spaces
ros2 param set /lyra_node max_angular_velocity 3.0
```

***

#### Exercise 6.6: Speed Tuning Experiment

**Task:** Find your preferred speed settings

**Test 1: Conservative (beginner-friendly)**

```bash
ros2 param set /lyra_node max_linear_velocity 0.3
ros2 param set /lyra_node max_angular_velocity 0.8

# Drive around - too slow?
```

**Test 2: Moderate (default)**

```bash
ros2 param set /lyra_node max_linear_velocity 0.8
ros2 param set /lyra_node max_angular_velocity 1.5

# Drive around - good balance?
```

**Test 3: Aggressive (advanced)**

```bash
ros2 param set /lyra_node max_linear_velocity 1.2
ros2 param set /lyra_node max_angular_velocity 2.5

# Drive around - too fast?
```

**Record your preferences!**

***

#### Making Parameter Changes Permanent

**Problem:** Parameters reset on reboot

**Solution:** Edit config file

```bash
# On robot (via SSH)
nano ~/lyra_ws/src/lyra_bringup/config/lyra_params.yaml

# Find and edit:
max_linear_velocity: 0.8  # Your preferred value
max_angular_velocity: 1.5  # Your preferred value

# Save, then rebuild workspace
cd ~/lyra_ws
colcon build
source install/setup.bash

# Power cycle robot - parameters now persistent!
```

***

### Part 7: Debugging Control Issues

#### Problem: Robot Doesn't Respond to Commands

**Systematic debug process:**

```bash
# 1. Is robot ARMED?
ros2 topic echo /lyra/armed --once
# If false → ARM it

# 2. Is joystick connected?
ros2 topic hz /joy
# Should show ~50-100 Hz when button pressed

# 3. Is teleop node running?
ros2 node list | grep teleop
# Should show /lyra_teleop_node

# 4. Are velocity commands being published?
ros2 topic hz /cmd_vel
# Should show >0 Hz when driving

# 5. Are commands reaching motor controller?
ros2 topic hz /cmd_vel_safe
# Should show >0 Hz

# 6. Check for errors
ros2 topic echo /rosout | grep -i error
```

**If still not working: ⚡ Power cycle robot**

***

#### Problem: Robot Moves When Joystick Centered

**Cause:** Joystick dead zone too small or joystick drift

**Debug:**

```bash
# Check raw joystick values
ros2 topic echo /joy

# With sticks centered, axes should be ~0.0
# If reading 0.1 or 0.2 → joystick has drift

# Solution 1: Increase dead zone in teleop config
# Solution 2: Recalibrate joystick
# Solution 3: Replace joystick (if hardware issue)
```

***

#### Problem: Jerky Motion

**Possible causes:**

1. **Low battery**

```bash
   ros2 topic echo /battery_voltage --once
   # If <10.5V → charge battery
```

2. **Network latency**

```bash
   # Check WiFi signal
   iwconfig wlan0
   # Link Quality should be >40/70
```

3. **Wheel obstruction**
   * Check wheels spin freely
   * Remove any debris
4. **Parameter issues**

```bash
   # Reset to defaults
   ros2 param set /lyra_node max_linear_velocity 1.0
   ros2 param set /lyra_node max_angular_velocity 2.0
```

***

#### Problem: Robot Drifts to One Side

**Causes:**

1. **Uneven floor** (robot is fine, floor is tilted)
2. **Wheel diameter mismatch** (calibration needed)
3. **Motor power imbalance** (one motor weaker)

**Test on flat surface first!**

**If problem persists:**

```bash
# Check wheel speeds during straight drive
ros2 topic echo /wheel_rpm

# All wheels should be similar
# If one much different → mechanical issue or calibration needed
```

***

### Part 8: Advanced Control Techniques

#### Ackermann-Style Control (Simulated)

> \[!WARNING] **TODO: Feature Not Implemented** The `ackermann_style_teleop.py` script is a planned future feature and is not yet available in the Beetlebot codebase. The following code is provided as a learning exercise but may require further configuration to work correctly.

**Beetlebot is a skid-steer drive, but can simulate car-like steering:**

**Create car-style control node:**

```bash
nano ~/ackermann_style_teleop.py
```

**Script:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy

class AckermannStyleTeleop(Node):
    def __init__(self):
        super().__init__('ackermann_style_teleop')

        self.subscription = self.create_subscription(Joy, '/joy', self.joy_callback, 10)
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)

        self.max_speed = 1.0
        self.max_steering_angle = 0.5  # Virtual steering angle limit

    def joy_callback(self, msg):
        # Left trigger (axis 2) = throttle (0 to -1 range, inverted)
        # Right stick X (axis 3) = steering
        # LB (button 4) = deadman

        if len(msg.buttons) < 5 or msg.buttons[4] == 0:
            # LB not pressed, don't move
            return

        throttle = -msg.axes[2] if len(msg.axes) > 2 else 0.0  # Invert axis
        steering = msg.axes[3] if len(msg.axes) > 3 else 0.0

        # Convert throttle to linear speed
        linear_speed = throttle * self.max_speed

        # Convert steering angle to angular velocity
        # angular = v * tan(steering_angle) / wheelbase
        # Simplified: angular ∝ steering * speed
        angular_speed = steering * linear_speed * 2.0  # Scale factor

        twist = Twist()
        twist.linear.x = linear_speed
        twist.angular.z = angular_speed

        self.publisher.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = AckermannStyleTeleop()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Try car-style control!**

***

#### Velocity Smoothing Script

**Further smooth joystick input (beyond hardware ramping):**

```python
# Add to custom teleop script:

class SmoothedTeleop:
    def __init__(self):
        self.target_linear = 0.0
        self.target_angular = 0.0
        self.current_linear = 0.0
        self.current_angular = 0.0
        self.smoothing_factor = 0.3  # Lower = smoother but slower response

    def update(self, target_lin, target_ang):
        self.target_linear = target_lin
        self.target_angular = target_ang

        # Exponential smoothing
        self.current_linear += (self.target_linear - self.current_linear) * self.smoothing_factor
        self.current_angular += (self.target_angular - self.current_angular) * self.smoothing_factor

        return self.current_linear, self.current_angular
```

***

### Part 9: Performance Metrics

#### Measure Control Latency

**How long from button press to robot motion?**

**Test setup:**

```bash
# Terminal 1: Record timestamps
ros2 bag record /joy /cmd_vel /wheel_rpm

# Press joystick button sharply (LB + forward)
# Record for 5 seconds
# Ctrl+C

# Play back and analyze timestamps
ros2 bag play bagfile --rate 0.1  # Slow playback

# Compare:
# /joy timestamp (button pressed)
# /cmd_vel timestamp (command published)
# /wheel_rpm timestamp (wheels start moving)

# Typical latency: 50-100ms (very responsive!)
```

***

#### Measure Control Accuracy

**How closely does robot follow commands?**

```bash
# Send precise command: 0.5 m/s for 10 seconds
ros2 topic pub --rate 20 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Simultaneously record odometry
ros2 bag record /odom

# After 10 seconds:
# - Commanded distance: 0.5 × 10 = 5.0 meters
# - Actual distance: Check final /odom position

# Accuracy = (actual / commanded) × 100%
# Typical: 95-98% (very good!)
```

***

### Part 10: Knowledge Check

#### Concept Quiz

1. **What happens when you release the LB button?**
2. **What's the purpose of velocity ramping?**
3. **Why does joystick override autonomous navigation?**
4. **What does /cmd\_vel\_safe do that /cmd\_vel doesn't?**
5. **If robot won't move, what's the first thing to check?**

***

#### Hands-On Challenge

**Task:** Create autonomous square driver

**Requirements:**

1. Python script that drives 1m × 1m square
2. No joystick input (purely programmatic)
3. ARMs robot at start
4. Uses /cmd\_vel topic
5. Accurate timing for sides and turns
6. Stops and disarms at end

**Bonus:**

* Add parameter for square size
* Visualize in RViz during execution
* Measure final position error

***

### Part 11: What You've Learned

#### ✅ Congratulations!

You now understand:

**Control Architecture:**

* ✅ Complete teleoperation signal chain
* ✅ Joy → Teleop → Mux → Safety Gate → Motor Control
* ✅ ARM/DISARM mechanism
* ✅ Emergency stop systems

**Velocity Ramping:**

* ✅ Smooth acceleration (5 RPM/cycle, defined as `MAX_RPM_STEP_PER_CYCLE`)
* ✅ LB release = immediate stop (no ramp)
* ✅ Benefits for hardware and odometry

**Control Methods:**

* ✅ Joystick (analog, smooth)
* ✅ Keyboard (discrete, precise)
* ✅ Programmatic (/cmd\_vel topic)
* ✅ Custom control interfaces

**Safety Systems:**

* ✅ Deadman switch (LB button)
* ✅ Command timeout (500ms)
* ✅ Velocity limits (safety gate)
* ✅ Emergency stop service

**Practical Skills:**

* ✅ Driving techniques (straight, turns, patterns)
* ✅ Parameter tuning (speed, turn rate)
* ✅ Debugging control issues
* ✅ Creating custom teleop nodes

***

### Next Steps

#### 🎯 You're Now Ready For:

**Immediate Next:** → Sensor Fusion with EKF - Combine wheel odom + IMU for better accuracy

**Navigation:** → SLAM Mapping - Build maps while driving\
→ Autonomous Navigation - Let robot drive itself

**Advanced Control:**

* Path following algorithms
* Obstacle avoidance behaviors
* Multi-robot coordination

***

### Quick Reference

#### Essential Control Commands

```bash
# --- ARM/DISARM ---
ros2 service call /lyra/arm std_srvs/srv/Trigger
ros2 service call /lyra/disarm std_srvs/srv/Trigger
ros2 service call /lyra/emergency_stop std_srvs/srv/Trigger
ros2 topic echo /lyra/armed --once

# --- Manual Control ---
# Forward 0.5 m/s
ros2 topic pub --rate 20 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Turn left 1.0 rad/s
ros2 topic pub --rate 20 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.0}}"

# --- Keyboard Teleop ---
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# --- Parameters ---
ros2 param get /lyra_node max_linear_velocity
ros2 param set /lyra_node max_linear_velocity 0.8

# --- Debugging ---
ros2 topic hz /joy                    # Check joystick
ros2 topic hz /cmd_vel                # Check commands
ros2 topic echo /lyra/armed --once    # Check ARM status
ros2 topic echo /battery_voltage --once  # Check battery
```

***

#### Joystick Button Reference

| Control           | Function         | Notes                     |
| ----------------- | ---------------- | ------------------------- |
| **LB**            | ARM / Deadman    | MUST hold to move         |
| **Left Stick Y**  | Forward/Backward | Push up = forward         |
| **Right Stick X** | Turn Left/Right  | Push left = turn left     |
| **RB**            | Turbo Mode       | 2× speed (use carefully!) |
| **Release LB**    | Emergency Stop   | Immediate stop, disarm    |

***

**Completed Teleoperation Control!** 🎉

→ Continue to Sensor Fusion with EKF\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 6 of 11 - Intermediate Level*\
*Estimated completion time: 120 minutes*
