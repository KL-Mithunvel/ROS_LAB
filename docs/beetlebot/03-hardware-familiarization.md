# Hardware Familiarization

## Hardware Familiarization

**Understanding your Beetlebot's architecture and components**

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand Beetlebot's hardware architecture
* ✅ Know what the Lyra controller does vs. Raspberry Pi
* ✅ Identify all major components and their functions
* ✅ Understand the sensor suite and capabilities
* ✅ Navigate the ROS2 software architecture
* ✅ Use ROS2 command-line tools to explore your robot
* ✅ Understand data flow from sensors to actuators

#### ⏱️ Time Required

* **Reading:** 20 minutes
* **Hands-on exercises:** 30 minutes
* **Total:** \~50 minutes

#### 📚 Prerequisites

* ✅ Completed Getting Started (robot powered on and responding)
* ✅ Robot connected to controller (can drive with joystick)
* ⚠️ **System Setup NOT required yet!** (WiFi, SSH can wait)
* ⚠️ This tutorial uses ONLY the joystick - no laptop needed

#### 🛠️ What You'll Need

* ✅ Beetlebot robot (powered and ready)
* ✅ Wireless controller (connected)
* ✅ Clear space to observe robot
* ⏸️ Laptop (optional for this tutorial)

***

### Part 1: Physical Hardware Tour

#### Component Overview

Let's identify every major component on your robot.

\[PLACEHOLDER: Top-down labeled diagram of Beetlebot showing all components]

#### 🔝 Top Plate Components

Walk around your robot and locate:

**1. RPLidar C1 (Front Center)**

\[PLACEHOLDER: Close-up photo of LiDAR]

**What it is:** 360° laser range finder\
**What it does:** Scans environment, detects obstacles, builds maps\
**Specifications:**

* Range: 12 meters maximum, 8-10m practical indoors
* Scan rate: 10 Hz (10 complete rotations per second)
* Resolution: \~0.5° angular resolution
* Height: 20.6cm from ground

**Key features:**

* Spinning motor visible (rotates continuously when active)
* Transparent dome protects laser assembly
* Connected via USB to Raspberry Pi

**What you'll use it for:**

* SLAM mapping (Tutorial 8)
* Obstacle detection during navigation
* Localization (knowing where you are)
* Path planning around obstacles

***

**2. Metal Top Plate**

**What it is:** 2mm metal platform\
**What it does:** Mounting surface for sensors and accessories\
**Features:**

* Rear-hinged articulated plate with a back-mounted rod acting as a pivot
* Allows the front of the plate to rotate upward and lock into a vertical or angled position
* Multiple mounting holes for accessories
* Protects internal components

**What you can add:**

* Additional sensors (GPS, ultrasonic, etc. on optional mounting plate upgrade)
* Compute modules (Jetson, cameras)
* Your custom hardware

***

**3. Depth Camera Mount (Optional)**

\[PLACEHOLDER: Photo of rear camera mount bracket]

**Location:** Rear of top plate\
**What it is:** Metal U-bracket for mounting depth cameras\
**Compatible with:** Intel RealSense, Orbbec Astra, etc. (not included)\
**Features:**

* Cable routing hole through top plate
* Sturdy metal construction

**Status:** Empty (mount included, camera optional upgrade)

***

#### 🔷 Front Components

**4. Raspberry Pi Camera V1.3**

\[PLACEHOLDER: Close-up of camera on front panel]

**What it is:** 5MP camera module\
**What it does:** Visual perception, image processing\
**Specifications:**

* Resolution: 5MP (2592×1944 max), typically use 1080p/720p
* Sensor: OmniVision OV5647
* Connection: CSI ribbon cable to Pi
* Height: 8.8cm from ground
* Field of view: \~54° horizontal

**Mounting:**

* Fixed forward-facing (horizontal, no tilt)
* Behind front metal protective plate
* Cable routed internally

**What you'll use it for:**

* Object detection
* Line following (advanced projects)
* Visual servoing (follow objects)
* Environment recognition

***

#### ⚙️ Back Panel Components

\[PLACEHOLDER: Back panel photo with numbered labels]

Walk to the back of your robot and locate:

**5. RJ45 Ethernet Port**

**What it is:** Direct Ethernet connection to Raspberry Pi\
**What it does:** High-speed wired network (alternative to WiFi)\
**Speed:** Gigabit (1000 Mbps)\
**Usage:**

* Backup if WiFi fails
* Lower latency for real-time control
* Large data transfers (rosbag recordings)
* Development in crowded WiFi environments

**Note:** Not configured by default - requires setup

***

**6. Power Switch**

**What it is:** Main power ON/OFF button\
**Appearance:** Flat button with red LED ring\
**Function:** Controls MOSFET that gates battery power

**LED Indicator:**

* **Red glowing:** Robot powered ON
* **Off:** Robot powered OFF

**How it works:**

1. Press switch → triggers low-current signal
2. MOSFET opens → allows high-current battery power to flow
3. Power reaches Pi, STM32, motors

**Why MOSFET?** Switch only handles 2A - battery can supply 50A+. MOSFET handles high current safely.

***

**7. Reset Button**

**What it is:** Tactile button (raised knob, unlabeled)\
**What it does:** Reboots Raspberry Pi (and indirectly, STM32)

**When to use:**

* System frozen/unresponsive
* After software changes
* Network configuration issues

**How it works:**

* Triggers GPIO on Raspberry Pi
* Pi initiates graceful shutdown → reboot
* STM32 powered via Pi USB → also reboots

**Note:** NOT an emergency stop! Use power switch for that.

***

**8. Charging Port**

**What it is:** 2.1mm center-positive power jack\
**Input:** 12V 2A from included smart charger\
**Function:** Charges 3S Li-Ion battery pack

**Charging:**

* Can charge while powered ON or OFF
* Smart charger prevents overcharging
* LED on charger: Red = charging, Green = full

***

**9. OLED Display \_(Optional Feature)**\_

\[PLACEHOLDER: Photo showing OLED location OR empty mounting area]

**Size:** 0.91" (wide aspect ratio)\
**Type:** I2C OLED (if present)\
**Display info:**

* Battery voltage
* IP address
* System status
* Current operation mode

**Note:** May not be present on all units. All information also available via ROS2 topics.

***

#### 🔄 Side Components

**10. USB Port (RF Dongle)**

\[PLACEHOLDER: Side panel photo showing USB slot]

**Location:** Right side panel\
**Function:** Houses RF dongle for wireless controller\
**Features:**

* Dongle is removable (can use on laptop for Gazebo)
* Direct USB connection to Raspberry Pi
* LED indicators visible on dongle

**LED Meanings:**

* **Green:** Power (always on when robot powered)
* **Red ON:** Raspberry Pi still booting
* **Red OFF:** Pi booted and ready

***

**11. USB/HDMI Placeholder \_(Optional Access)**\_

**Location:** Left side panel\
**Function:** Access point for additional connectors\
**Status:** Hole in chassis, no connectors populated

**Potential uses:**

* External HDMI for monitor
* Additional USB ports
* Debug interfaces

***

#### 🚗 Wheels & Motors

**12. Wheels (4×)**

\[PLACEHOLDER: Close-up of wheel showing tread pattern]

**Specifications:**

* **Diameter:** 130mm
* **Width:** \~40mm
* **Material:** Rubber with aggressive tread
* **Color:** Blue hubs, black tread
* **Type:** All-terrain (indoor/outdoor)

**Features:**

* Deep tread for traction
* Suitable for carpet, tile, concrete, pavement
* Metal wheel hubs (durable)

**Configuration:**

* Front left (FL)
* Front right (FR)
* Back left (BL)
* Back right (BR)

All wheels independently driven (4WD).

***

**13. Motors (4×)**

**Hidden inside chassis - you can't see them, but here's what's there:**

**Model:** JGB37-3530\
**Type:** DC metal gear motors\
**Rated voltage:** 12V DC\
**Gear ratio:** 37:1 (motor to output shaft)\
**Output:** Shaft directly drives wheel\
**Max RPM:** 150 RPM (software-limited; see `robot_config.h`)

**Why metal gears?**

* Durability - won't strip under load
* Continuous operation rated
* Consistent torque delivery

***

**14. Encoders (4×)**

**Also hidden - one per motor:**

**Type:** Quadrature incremental encoders\
**Resolution:** 900 CPR (counts per revolution on motor shaft)\
**Mode:** X4 quadrature decoding = **3600 ticks per wheel revolution**\
**Function:** Measure wheel rotation for odometry

**How it works:**

1. Magnetic disk on motor shaft
2. Hall effect sensors detect rotation
3. A/B phase signals → direction + speed
4. STM32 reads encoder ticks → calculates wheel RPM

**Why so precise?**

* 3600 ticks/wheel rev = 0.1° effective resolution
* Essential for accurate odometry
* Enables closed-loop PID speed control

***

#### Hardware Timer-Based Encoders

**Critical distinction:** Beetlebot uses **hardware timer-based encoder counting**, not software interrupts.

**What this means:**

**Hardware Timers (STM32 TIM1, TIM2, TIM4, TIM8):**

* Dedicated hardware peripherals count encoder pulses
* **Zero CPU overhead** - happens in silicon, not software
* Counts continuously at full 168 MHz speed (MCU clock)
* Cannot miss pulses even under heavy CPU load
* 32-bit hardware counters with overflow handling

**vs. Software Interrupts (common in Arduino, ESP32):**

* Each encoder pulse triggers interrupt
* CPU must stop current task and handle pulse
* Can miss pulses if interrupts disabled or CPU busy
* Significant CPU overhead at high speeds
* Typically 16-bit counters (limited range)

**Why hardware encoders matter:**

✅ **Accuracy:** Never misses a pulse, even at max 150 RPM\
✅ **Reliability:** Works perfectly even when motor control loop is running\
✅ **CPU efficiency:** Zero interrupt overhead = more CPU for control algorithms\
✅ **High resolution:** 3600 ticks/wheel rev with no performance penalty\
✅ **Overflow protection:** 32-bit counters + firmware overflow detection

**Technical implementation:**

* **TIM1** (Channel A/B): Motor 1 encoder (PA8, PA9)
* **TIM2** (Channel A/B): Motor 2 encoder (PA0, PA1)
* **TIM4** (Channel A/B): Motor 3 encoder (PB6, PB7)
* **TIM8** (Channel A/B): Motor 4 encoder (PC6, PC7)
* Each timer configured in **X4 quadrature mode** (4× resolution)
* Direction detection handled by hardware (up/down counting)

**Reading encoders:**

```c
// In STM32 firmware (example - you don't need to write this)
int32_t ticks = __HAL_TIM_GET_COUNTER(&htim1);  // Read hardware counter
// No interrupts, no CPU cycles, instant read
```

**Result:** Professional-grade encoder performance typically found in industrial servo systems, not hobby robots.

***

#### OLED Display

**Type:** 0.96" SSD1306 OLED (I2C) **Resolution:** 128x64 pixels **Function:** Real-time visual status indicator

**What it shows:**

* Battery voltage and percentage
* Current ROS mode status
* Motor armed/disarmed state

**Why it's useful:** You don't need to SSH into the robot to check its battery or status; just look at the screen!

***

### Part 2: Internal Architecture

#### What's Inside? (Don't Open really - Here's What's There)

\[PLACEHOLDER: Internal wiring diagram OR transparent view render]

**Computing Stack:**

**Raspberry Pi 5 (8GB)**

* **Location:** Center of chassis
* **Function:** Main ROS2 brain
* **Runs:** Ubuntu 24.04, ROS2 Jazzy, all high-level software
* **Cooling:** Active fan with temperature-based PWM control
* **Power:** 5V 5A from buck converter

**Lyra Controller (STM32F405)**

* **Location:** Mounted near motors
* **Function:** Real-time motor control, sensor interface
* **Runs:** FreeRTOS + Lyra firmware v2025.11
* **Cooling:** Not required. Motor drivers never get hot to damage
* **Power:** 5V from buck converter (via Pi USB during normal operation)

***

**Power Distribution:**

```
Battery (3S4P Li-Ion)
  11.1V nominal, 10Ah
  └─> Power Switch
      └─> MOSFET Gate
          └─> Buck Converter (5V 5A)
              ├─> Raspberry Pi 5
              │   └─> USB → STM32 (powers Lyra)
              │
              └─> Direct Battery (12V)
                  └─> STM32 Motor Pins
                      └─> DRV8874 Motor Drivers (4×)
                          └─> Motors (4×)
```

**Key points:**

* Motors powered directly from battery (12V)
* Logic (Pi, STM32) powered from 5V buck converter
* STM32 gets 5V from Pi USB (simple, clean)
* MOSFET prevents inrush current damage to switch

***

**Communication Paths:**

```
Wireless Controller
  └─> RF Dongle (USB)
      └─> Raspberry Pi
          └─> ROS2 teleop_twist_joy node
              └─> /cmd_vel topic
                  └─> lyra_bridge node
                      └─> UART3 (GPIO 14/15)
                          └─> Lyra STM32
                              └─> Motor Control Loop (20Hz)
                                  └─> Motors

Encoders → STM32 → UART3 → Pi → ROS2 topics
LiDAR → USB → Pi → ROS2 /scan
Camera → CSI → Pi → ROS2 /image_raw
IMU → I2C → STM32 → UART3 → Pi → ROS2 /imu
```

***

### Part 3: The Lyra Controller Deep Dive

#### What is Lyra?

**Lyra is the name of the STM32-based motor controller inside Beetlebot.**

\[PLACEHOLDER: Photo of Lyra board OR block diagram]

Think of Beetlebot as having TWO computers:

1. **Raspberry Pi** - The "smart" brain (planning, navigation, vision)
2. **Lyra (STM32)** - The "reflex" brain (motors, sensors, safety)

#### Why Two Computers?

**Question:** Why not just use the Raspberry Pi for everything?

**Answer:** Linux is NOT real-time.

**What does this mean?**

Linux can be interrupted at any time:

* WiFi packet arrives → interrupt
* Disk write completes → interrupt
* Screen updates → interrupt
* Process scheduler → switches tasks

**Result:** Your motor control code might run every 50ms... or 53ms... or 47ms... unpredictable!

**Motors need:** Exactly 50ms update rate (20 Hz), not "approximately 50ms"

**Solution:** Lyra runs FreeRTOS (real-time OS) → guaranteed 50.000ms control loop

***

#### Lyra's Responsibilities

**Real-Time Motor Control:**

* 20 Hz PID loop per motor (50ms period, exact)
* Encoder reading (3600 ticks/wheel revolution, 900 CPR × X4 quadrature)
* PWM generation (20 kHz frequency)
* Stall detection and recovery
* Safety timeouts

**Sensor Interface:**

* IMU (LSM6DSRTR) via I2C @ 100 Hz
* Battery voltage via ADC
* Motor fault detection (DRV8874 fault pins)

**Safety Systems:**

* Independent watchdog timer (16.4s)
* Command timeout (500ms → auto-stop)
* Motor fault response (immediate all-stop)
* Emergency stop handling

**Communication:**

* Binary protocol over UART3 @ 115200 baud
* 10 Hz telemetry to Raspberry Pi
* CRC16 validation on all packets

***

#### Raspberry Pi's Responsibilities

**High-Level Intelligence:**

* ROS2 Jazzy navigation stack
* SLAM mapping (SLAM Toolbox)
* Path planning (Nav2)
* Localization (AMCL)
* Sensor fusion (EKF)

**Sensor Processing:**

* LiDAR data (RPLidar driver)
* Camera images (V4L2)
* Point cloud processing
* Image processing

**User Interface:**

* Joystick control (teleop\_twist\_joy)
* RViz visualization (when connected)
* Launch file management
* Network communication

**Coordination:**

* Receives sensor data from Lyra
* Sends motor commands to Lyra
* Manages overall robot behavior

***

#### Division of Labor Example

**User presses joystick forward:**

1. **Raspberry Pi** (takes \~20-30ms):
   * Reads joystick USB HID device
   * `joy_node` publishes `/joy` message
   * `teleop_node` converts to `/cmd_vel` (geometry\_msgs/Twist)
   * `lyra_bridge` converts Twist → wheel velocities (rad/s)
   * Packages into binary protocol packet
   * Sends via UART3 to Lyra
2. **Lyra STM32** (every 50ms, exactly):
   * Receives packet, validates CRC
   * Extracts target wheel velocities
   * Updates `target_rpm[4]` array
   * **PID Control Loop** (runs regardless of new commands):
     * Read 4 encoders → current RPM
     * Calculate error (target - actual)
     * PID math → PWM output
     * Apply PWM to motors
   * Send telemetry back to Pi (10 Hz)

**Key insight:** Even if Pi stops sending commands, Lyra continues controlling motors smoothly for up to 500ms (timeout), then safe-stops.

***

### Part 4: ROS2 Software Architecture

#### Node Graph Overview

\[PLACEHOLDER: ROS2 node graph diagram]

When your Beetlebot boots, these ROS2 nodes start automatically:

```
/lyra_bridge
  Publishes: /wheel_rpm, /wheel_ticks, /battery_voltage, /imu/data_raw, /lyra/armed
  Subscribes: /cmd_vel
  Services: /lyra/arm, /lyra/disarm, /lyra/emergency_stop

/wheel_odometry (lyra_localization)
  Subscribes: /wheel_rpm, /wheel_ticks
  Publishes: /odom

/joy_teleop_wrapper (lyra_control)
  Subscribes: /joy
  Calls: /lyra/arm, /lyra/disarm (on button press)

/teleop_twist_joy_node
  Subscribes: /joy
  Publishes: /cmd_vel_joy

/cmd_vel_gate (lyra_cmd_vel_gate)
  Subscribes: /cmd_vel_joy, /lyra/armed
  Publishes: /cmd_vel

/robot_state_publisher
  Publishes: TF transforms (static)

/ekf_filter_node (robot_localization)
  Subscribes: /odom, /imu/data (via imu_filter)
  Publishes: /odometry/filtered, TF (odom → base_link)

/rplidar_composition (optional, if LiDAR enabled)
  Publishes: /scan

/joy_node
  Publishes: /joy
```

#### Understanding Topics

**Topics are like radio stations** - nodes "broadcast" on topics, other nodes "listen"

**Key topics on your robot:**

**/cmd\_vel** (geometry\_msgs/Twist)

* Published by: teleop, nav2, your code
* Contains: Linear velocity (m/s), Angular velocity (rad/s)
* Purpose: "Go this fast, turn this fast"

**/lyra/cmd\_vel\_safe** (geometry\_msgs/Twist)

* Published by: cmd\_vel\_gate (after safety checks)
* Contains: Clamped velocities
* Purpose: Safe version of cmd\_vel

**/lyra/wheel\_states** (custom message)

* Published by: lyra\_node
* Contains: RPM, encoder ticks per wheel
* Purpose: Raw motor feedback

**/odom** (nav\_msgs/Odometry)

* Published by: lyra\_odometry\_node
* Contains: Robot position (x, y, θ), velocity
* Purpose: "Where am I?" (relative to start)

**/scan** (sensor\_msgs/LaserScan)

* Published by: rplidar\_composition
* Contains: 360° distance measurements
* Purpose: "What's around me?"

**/lyra/imu** (sensor\_msgs/Imu)

* Published by: lyra\_node (from STM32)
* Contains: Acceleration, angular velocity
* Purpose: Motion sensing

***

#### Understanding Services

**Services are like phone calls** - you call, wait for answer

**Key services:**

**/lyra/arm** (std\_srvs/Trigger)

* What it does: Enables motor control
* Called by: teleop (when LB pressed)
* Response: Success/failure

**/lyra/disarm** (std\_srvs/Trigger)

* What it does: Disables motors (safety)
* Called by: teleop (when LB released), timeout
* Response: Success/failure

**/lyra/emergency\_stop** (std\_srvs/Trigger)

* What it does: Immediate stop + disarm
* Called by: Emergency situations
* Response: Success/failure

***

### Part 5: Hands-On Exploration

#### Exercise 1: Node Discovery (Optional - Requires Laptop)

**If you have laptop connected via SSH:**

```bash
# List all running nodes
ros2 node list

# You should see:
# /lyra_bridge
# /wheel_odometry
# /joy_teleop_wrapper
# /teleop_twist_joy_node
# /cmd_vel_gate
# /robot_state_publisher
# /ekf_filter_node
# /joy_node
```

**What this tells you:** These 8 nodes make your robot work!

***

#### Exercise 2: Topic Discovery (Optional)

```bash
# List all topics
ros2 topic list

# See live data from a topic:
ros2 topic echo /lyra/wheel_states

# Now drive robot with joystick - see values change!
```

**Try echoing different topics:**

* `/cmd_vel` - See your joystick commands
* `/odom` - See odometry updating
* `/lyra/battery` - Check battery voltage

***

#### Exercise 3: Physical Inspection While Running

**With robot powered and responding:**

1. **Observe LiDAR spinning**
   * Should rotate continuously and smoothly
   * \~10 rotations per second (hard to see - it's fast!)
2. **Drive forward slowly (hold LB + push left stick)**
   * Watch all 4 wheels turn in same direction
   * Listen for motor noise (should be quiet, smooth)
   * Observe smooth acceleration (not jerky)
3. **Turn in place (hold LB + push right stick)**
   * Left wheels turn one direction
   * Right wheels turn opposite direction
   * Robot rotates smoothly
4. **Release LB button**
   * Robot stops immediately
   * Wheels don't coast (active braking)

***

#### Exercise 4: Understanding the TF Tree (Optional - Advanced)

**TF = Transform Tree** - how robot parts relate in 3D space

```bash
# View transform tree
ros2 run tf2_tools view_frames

# Creates frames.pdf - shows relationship between:
# - base_footprint (ground)
# - base_link (robot center)
# - wheels (fl_link, fr_link, bl_link, br_link)
# - lidar_link (sensor position)
# - camera_link (camera position)
# - imu_link (IMU position)
```

**Key concept:** ROS2 needs to know where each sensor is relative to robot center!

Example:

* Camera is 15cm forward, 8.8cm high
* LiDAR is 8.5cm forward, 20.6cm high
* This info is in URDF (robot description file)

***

### Part 6: Understanding the Startup Sequence

#### What Happens When You Power On?

**Detailed boot sequence (90 seconds):**

**T+0s:** Press power switch

* MOSFET opens
* Power flows to buck converter
* Pi receives 5V, begins boot

**T+5s:** Raspberry Pi bootloader

* Loads from microSD card
* Shows rainbow screen (if display connected)
* Starts Ubuntu kernel

**T+30s:** Ubuntu boots

* System services start
* Network stack initializes
* Systemd launches

**T+35s:** Auto-launch service runs: `ros2 launch lyra_bringup robot.launch.py mode:=teleop`

* This starts all core nodes
* **Note on Launch Files:** The `robot.launch.py` file disables the camera and IMU by default to save power and CPU when just teleoperating. If you need everything (Camera/IMU enabled), you can launch `base.launch.py` directly, which turns all sensors on by default.

**T+40s:** Lyra node initializes

* Opens UART3 to STM32
* STM32 already running (powered via USB)
* Binary protocol handshake

**T+45s:** STM32 Lyra firmware ready

* Motors initialized
* Encoders zeroed
* IMU calibrated
* Safety systems armed

**T+50s:** Odometry node starts

* Subscribes to wheel\_states
* Begins position integration

**T+55s:** EKF node starts

* Fuses wheel odom + IMU
* Publishes filtered odometry

**T+60s:** Teleop node starts

* Subscribes to /joy (joystick)
* Publishes /cmd\_vel
* Robot ready for joystick control!

**T+90s:** System fully booted

* All nodes running
* RF dongle red LED turns OFF
* **Ready to drive!**

***

### Part 7: Safety Systems Explained

#### Multi-Layer Protection

Beetlebot has 5 independent safety layers:

**Layer 1: Hardware (DRV8874 Motor Drivers)**

* Overcurrent protection (>3.5A per motor)
* Thermal shutdown (>150°C)
* Under-voltage lockout (<7V)
* Over-voltage protection (>16V)
* **Response time:** Microseconds

**Layer 2: STM32 Firmware**

* Watchdog timer (16.4s - resets if software hangs)
* Command timeout (500ms - stops if no new commands)
* Stall detection (10 cycles @ 5 RPM threshold)
* Fault monitoring (checks fault pins every cycle)
* **Response time:** 50ms (one control cycle)

**Layer 3: ROS2 Bridge (lyra\_node)**

* UART connection monitoring
* CRC validation (discards corrupted packets)
* Sequence number checking (detects packet loss)
* **Response time:** 100ms (one telemetry cycle)

**Layer 4: Safety Gate (cmd\_vel\_gate)**

* Velocity clamping (max 1.0 m/s linear, 2.0 rad/s angular)
* ARM status checking (blocks commands if DISARMED)
* Emergency stop handling
* **Response time:** \~10ms (ROS2 callback)

**Layer 5: Mechanical**

* Ground clearance (16.3cm - avoids getting stuck)
* Wheel traction (rubber treads prevent uncontrolled sliding)
* Battery BMS (prevents over-discharge, short circuit)

**All layers work independently** - if one fails, others still protect!

***

### Part 8: Key Specifications Summary

#### Quick Reference Table

| Specification        | Value                | Notes                               |
| -------------------- | -------------------- | ----------------------------------- |
| **Compute**          | Raspberry Pi 5 (8GB) | Ubuntu 24.04, ROS2 Jazzy            |
| **Motor Controller** | STM32F405 (Lyra)     | FreeRTOS, 168 MHz                   |
| **Motors**           | 4× JGB37-3530        | 12V DC metal gear                   |
| **Encoders**         | 4× Quadrature        | 3600 ticks/wheel rev (900 CPR × X4) |
| **LiDAR**            | RPLidar C1           | 12m range, 10 Hz scan               |
| **Camera**           | Pi Camera V1.3       | 5MP, 1080p @ 30fps                  |
| **IMU**              | LSM6DSRTR            | 6-axis (accel + gyro)               |
| **Battery**          | 3S Li-Ion 10Ah       | 11.1V nominal                       |
| **Max Speed**        | 1.0 m/s              | 3.6 km/h                            |
| **Runtime**          | 5-6 hours            | Typical mixed use                   |
| **Weight**           | 2.2 kg               | With battery                        |
| **Dimensions**       | 375×360×245mm        | L×W×H                               |
| **Control Loop**     | 20 Hz                | 50ms period (exact)                 |
| **Telemetry**        | 10 Hz                | Binary protocol                     |
| **Communication**    | UART3 @ 115200       | Pi ↔ STM32                          |

***

### Part 9: Knowledge Check

#### Self-Assessment Quiz

**Answer these to verify understanding:**

1. **What are the two computers in Beetlebot?**
2. **Why can't Raspberry Pi control motors directly?**
3. **What does the deadman switch (LB button) do?**
4. **How many safety layers does Beetlebot have?**
5. **What's the resolution of the encoders?**
6. **What protocol does Lyra use to communicate with Pi?**
7. **Name 3 sensors on Beetlebot.**
8. **What happens if controller disconnects while driving?**

***

### Part 10: What You've Learned

#### ✅ Congratulations!

You now understand:

**Hardware:**

* ✅ All physical components and their locations
* ✅ What's inside the chassis (without opening it)
* ✅ How power flows from battery to motors
* ✅ Where sensors are mounted and what they do

**Software:**

* ✅ Why two computers are needed (real-time vs. high-level)
* ✅ What Lyra (STM32) does vs. Raspberry Pi
* ✅ ROS2 node architecture (8 key nodes)
* ✅ How joystick commands become motor motion

**Safety:**

* ✅ 5 independent safety layers
* ✅ Deadman switch operation
* ✅ Timeout protection
* ✅ Emergency stop capability

**Communication:**

* ✅ Binary protocol (Pi ↔ STM32)
* ✅ ROS2 topics (inter-node communication)
* ✅ Services (request/response actions)
* ✅ TF tree (spatial relationships)

***

### Next Steps

#### 🎯 Ready for More?

**Recommended progression:**

**Option A: Continue Learning Path**\
→ Next tutorial: **ROS2 Communication & Tools**\
→ Learn to use ROS2 command-line tools\
→ Understand topics, services, parameters\
→ Debug robot behavior

**Option B: Configure Your System**\
→ Go to **System Setup Guide**\
→ Configure WiFi and SSH\
→ Set up laptop development environment\
→ Then return to tutorials

**Option C: Just Keep Driving!**\
→ Practice more with joystick\
→ Get comfortable with controls\
→ Learn robot's handling characteristics\
→ Setup can wait!

***

### Troubleshooting

#### Common Questions

**Q: Can I open the chassis to see inside?**\
A: Yes, but not necessary and not recommended during warranty. All internals are documented here. If you must open it, power OFF first and disconnect battery!

**Q: What if I want to add more sensors?**\
A: Top plate has mounting holes. USB and GPIO available on Pi. Advanced tutorial covers sensor integration.

**Q: How do I know battery voltage?**\
A: If OLED present, it shows on screen. Otherwise, use ROS2: `ros2 topic echo /lyra/battery`

**Q: Robot sometimes stops moving mid-drive?**\
A: This is command timeout (500ms safety). Keep sending commands (hold joystick stick) or increase timeout in parameters.

**Q: Can I update the Lyra (STM32) firmware?**

**A: Yes, but firmware is proprietary:**

**Firmware distribution:**

* Lyra STM32 firmware is proprietary/closed source
* Source code not available to customers
* VEEROBOT® provides firmware updates as compiled `.hex` files when available
* Updates include bug fixes, new features, performance improvements

**Update process:**

1. **Obtain firmware file** from VEEROBOT® support (<support@veerobot.com>)
   * Provided as `.hex` or `.bin` file
   * Includes version number and changelog
2. **Purchase ST-Link V2 programmer** (not included with robot)
   * Available on Amazon, AliExpress, Digi-Key
   * Cost: \~$10-30 USD
   * USB interface for firmware flashing
3. **Connect ST-Link to Lyra board**
   * Requires opening robot chassis
   * Connect SWD pins: SWDIO, SWCLK, GND, 3.3V
   * Contact support for exact pin locations
4. **Flash firmware using STM32CubeProgrammer** (free from ST)
   * Download: <https://www.st.com/stm32cubeprog>
   * Load `.hex` file
   * Click "Program"
   * Verify successful flash
5. **Test robot operation** after flashing

**⚠️ Warnings:**

* Incorrect firmware can brick controller (recoverable but requires support)
* Warranty void if damaged during customer flashing attempt
* Power off robot before connecting ST-Link
* Never disconnect ST-Link during programming

**When to update:**

* VEEROBOT® notifies of critical bug fixes
* New features announced
* Experiencing known issue with firmware fix available

**Q: What about updating ROS2 code in Raspberry pi?**\
A: ROS code is available on GitHub. Users can always refer to our GitHub page and update the code from there

***

#### The Universal Fix: Power Cycle

**Most common solution to various issues:**

**When to power cycle:**

* ROS2 nodes not appearing
* Topics not updating
* RViz shows stale data
* SLAM map looks corrupted
* Navigation behaving strangely
* General "weirdness"

**How to properly power cycle:**

1. **Stop robot motion** (release LB, ensure stationary)
2. **Press power button on back panel** (red LED turns off)
3. **Wait 10 seconds** (allows capacitors to discharge, Pi to fully shutdown)
4. **Press power button again** (red LED turns on)
5. **Wait 90 seconds** for full boot
6. **Verify operation** (drive with joystick, check RViz)

**⚠️ Important: Use Power Button, NOT Reset Button**

**Power button:**

* ✅ Proper shutdown sequence
* ✅ Clears all software state
* ✅ Re-initializes all hardware
* ✅ Fixes 90% of issues

**Reset button:**

* ⏸️ Only restarts Raspberry Pi
* ⏸️ STM32 may stay in weird state
* ⏸️ Doesn't clear all hardware buffers
* ⏸️ Use only when Pi frozen (rare)

**Why power cycling works:**

Software bugs can leave system in inconsistent states:

* DDS discovery cache corrupted
* ROS2 daemon stuck
* Hardware buffers full
* Timing issues accumulated
* Network state confused

Full power cycle clears everything and starts fresh.

**Pro tip:** When in doubt, power cycle! It's quick (2 minutes) and solves most issues.

***

### Resources

**Related Documentation:**

* System Setup Guide - Configure WiFi, SSH
* ROS2 Communication & Tools - Next tutorial
* Technical Reference Manual - Deep dive into every detail

**External Resources:**

* [ROS2 Jazzy Documentation](https://docs.ros.org/en/jazzy/)
* [RPLidar C1 Datasheet](https://www.slamtec.com)
* [STM32F405 Reference Manual](https://www.st.com)

***

**Completed Hardware Familiarization?**

→ Continue to ROS2 Communication & Tools\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 1 of 11 - Beginner Level*\
*Estimated completion time: 50 minutes*
