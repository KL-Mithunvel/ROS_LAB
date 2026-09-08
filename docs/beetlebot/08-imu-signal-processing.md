# IMU Signal Processing

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Understand IMU sensor principles (accelerometer + gyroscope)
* ✅ Identify and characterize sensor noise
* ✅ Implement complementary filters for sensor fusion
* ✅ Calculate orientation from IMU data
* ✅ Deal with gyroscope drift and accelerometer noise
* ✅ Apply low-pass and high-pass filters
* ✅ Calibrate IMU sensors
* ✅ Compare filtering techniques

#### ⏱️ Time Required

* **Reading & Theory:** 25 minutes
* **Data Collection:** 15 minutes
* **Filtering Implementation:** 40 minutes
* **Calibration:** 20 minutes
* **Total:** \~100 minutes

#### 📚 Prerequisites

* ✅ Completed Sensor Data Visualization
* ✅ Can visualize and record IMU data
* ✅ Basic understanding of signals (helpful, not required)
* ✅ Python basics (for filtering scripts)
* ✅ Can record and analyze rosbags

#### 🛠️ What You'll Need

* ✅ Beetlebot (powered, IMU active)
* ✅ Laptop with ROS2 + Python
* ✅ Wireless controller
* ✅ Level surface for calibration
* ✅ Protractor or phone compass (optional)
* ✅ Calculator or Python for math

***

### Part 1: IMU Fundamentals

#### What's Inside an IMU?

**Your LSM6DSRTR has two sensors:**

**1. Accelerometer (3-axis)**

* Measures: Linear acceleration (m/s²)
* Axes: X (forward/back), Y (left/right), Z (up/down)
* Range: ±2g (±19.6 m/s²)
* **Measures:** Gravity + motion acceleration

**2. Gyroscope (3-axis)**

* Measures: Angular velocity (rad/s or °/s)
* Axes: Roll (X), Pitch (Y), Yaw (Z)
* Range: ±250 dps (degrees per second)
* **Measures:** Rotation rate

***

#### Understanding Accelerometer

**Key insight:** Accelerometer measures ALL accelerations, including gravity!

**Stationary robot:**

```
X-axis (forward): ~0.0 m/s² (no acceleration)
Y-axis (sideways): ~0.0 m/s² (no acceleration)
Z-axis (up/down): ~9.81 m/s² (GRAVITY!)
```

**Why Z = 9.81?**

* Gravity pulls down at 9.81 m/s²
* Accelerometer measures upward force from ground
* Sitting still = constant upward acceleration from ground support

**Moving forward:**

```
X-axis: Positive spike (accelerating forward)
Y-axis: ~0.0 m/s²
Z-axis: ~9.81 m/s² (gravity still there!)
```

**Tilted robot (nose up 30°):**

```
X-axis: ~4.9 m/s² (sin(30°) × 9.81)
Y-axis: ~0.0 m/s²
Z-axis: ~8.5 m/s² (cos(30°) × 9.81)
```

**Key point:** Accelerometer can't distinguish:

* Gravity vs. linear acceleration
* Tilt vs. acceleration
* This is why we need gyroscope!

***

#### Understanding Gyroscope

**Measures rotation rate, NOT angle!**

**Stationary robot:**

```
Roll rate (X): ~0.0 °/s (not rotating around X)
Pitch rate (Y): ~0.0 °/s (not rotating around Y)
Yaw rate (Z): ~0.0 °/s (not rotating around Z)
```

**Turning left (yaw):**

```
Roll rate (X): ~0.0 °/s
Pitch rate (Y): ~0.0 °/s
Yaw rate (Z): +45 °/s (turning left at 45°/second)
```

**To get angle, must integrate:**

```
angle = angle + (rate × time)

Example:
Start angle: 0°
Measure: 45 °/s for 1 second
New angle: 0° + (45 × 1) = 45°
```

**Problem:** Integration accumulates error!

* Small measurement error → grows over time
* Called "gyro drift"
* After 1 minute, angle could be off by 10-20°

***

#### The Complementary Problem

**Accelerometer:**

* ✅ Good long-term (doesn't drift)
* ❌ Noisy short-term (vibrations, motion)
* ✅ Measures gravity (knows "down")
* ❌ Can't distinguish tilt from acceleration

**Gyroscope:**

* ✅ Good short-term (smooth, fast)
* ❌ Drifts long-term (integration error)
* ✅ Not affected by linear motion
* ❌ Doesn't know absolute orientation

**Solution:** Combine both! (Complementary filter)

***

### Part 2: Collecting IMU Data

#### Record Raw IMU Data

**Collect baseline data:**

```bash
# Terminal 1: Record
ros2 bag record -o imu_static /imu/data_raw

# Let robot sit perfectly still for 60 seconds
# Press Ctrl+C after 1 minute
```

**Collect motion data:**

```bash
# Test 1: Forward acceleration
ros2 bag record -o imu_forward /imu/data_raw
# Drive straight forward at medium speed for 5 seconds
# Ctrl+C

# Test 2: Rotation
ros2 bag record -o imu_rotation /imu/data_raw
# Spin in place (360°) slowly
# Ctrl+C

# Test 3: Figure-8
ros2 bag record -o imu_figure8 /imu/data_raw
# Drive smooth figure-8 pattern
# Ctrl+C
```

***

#### Exercise 5.1: Noise Characterization

> \[!WARNING] **TODO: Exercise Script Not Included in Core Repository** The `imu_noise_analysis.py` script below is an exercise for the user. It is *not* pre-installed.

**Task:** Measure IMU noise levels

**Analysis script:**

```bash
# Create analysis script
nano ~/imu_noise_analysis.py
```

**Script content:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import numpy as np

class ImuNoiseAnalyzer(Node):
    def __init__(self):
        super().__init__('imu_noise_analyzer')
        self.subscription = self.create_subscription(
            Imu, '/imu/data_raw', self.imu_callback, 10)

        self.accel_x = []
        self.accel_y = []
        self.accel_z = []
        self.gyro_z = []

        self.timer = self.create_timer(10.0, self.analyze)

    def imu_callback(self, msg):
        self.accel_x.append(msg.linear_acceleration.x)
        self.accel_y.append(msg.linear_acceleration.y)
        self.accel_z.append(msg.linear_acceleration.z)
        self.gyro_z.append(msg.angular_velocity.z)

    def analyze(self):
        if len(self.accel_z) < 100:
            return

        print("\n=== IMU Noise Analysis (10 seconds) ===")
        print(f"Samples collected: {len(self.accel_z)}")

        print("\nAccelerometer (m/s²):")
        print(f"  X: mean={np.mean(self.accel_x):.3f}, std={np.std(self.accel_x):.3f}")
        print(f"  Y: mean={np.mean(self.accel_y):.3f}, std={np.std(self.accel_y):.3f}")
        print(f"  Z: mean={np.mean(self.accel_z):.3f}, std={np.std(self.accel_z):.3f}")

        print("\nGyroscope (rad/s):")
        print(f"  Z: mean={np.mean(self.gyro_z):.4f}, std={np.std(self.gyro_z):.4f}")

        # Clear data for next analysis
        self.accel_x.clear()
        self.accel_y.clear()
        self.accel_z.clear()
        self.gyro_z.clear()

def main(args=None):
    rclpy.init(args=args)
    analyzer = ImuNoiseAnalyzer()
    rclpy.spin(analyzer)
    analyzer.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Run analyzer:**

```bash
chmod +x ~/imu_noise_analysis.py
python3 ~/imu_noise_analysis.py
```

**While robot sits still, observe output every 10 seconds:**

```
=== IMU Noise Analysis (10 seconds) ===
Samples collected: 1000

Accelerometer (m/s²):
  X: mean=0.023, std=0.045  ← Should be ~0, some noise
  Y: mean=-0.015, std=0.042  ← Should be ~0, some noise
  Z: mean=9.807, std=0.053  ← Should be ~9.81 (gravity!)

Gyroscope (rad/s):
  Z: mean=0.0012, std=0.0034  ← Should be 0, small drift
```

**What you learned:**

* Standard deviation = noise level
* Typical: 0.04-0.05 m/s² accel noise, 0.003-0.004 rad/s gyro noise
* Z-axis accel reads \~9.81 (gravity)
* Gyro has small bias (mean ≠ 0)

***

### Part 3: Low-Pass Filtering

#### What is Low-Pass Filtering?

**Goal:** Remove high-frequency noise, keep low-frequency signal

**Analogy:** Smoothing bumpy data

* Sudden spikes → smoothed out
* Slow trends → preserved

**Simple method:** Moving average

```python
# Moving average (5 samples)
filtered = (sample[0] + sample[1] + sample[2] + sample[3] + sample[4]) / 5
```

***

#### Implement Moving Average Filter

> \[!WARNING] **TODO: Exercise Script Not Included in Core Repository** The `imu_filter_node.py` script below is an exercise. It is *not* pre-installed.

**Create filter node:**

```bash
nano ~/imu_filter_node.py
```

**Script:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from collections import deque

class ImuFilterNode(Node):
    def __init__(self):
        super().__init__('imu_filter_node')

        # Subscribe to raw IMU
        self.subscription = self.create_subscription(
            Imu, '/imu/data_raw', self.imu_callback, 10)

        # Publish filtered IMU
        self.publisher = self.create_publisher(Imu, '/imu/filtered', 10)

        # Moving average buffers (window size = 5)
        self.accel_x_buffer = deque(maxlen=5)
        self.accel_y_buffer = deque(maxlen=5)
        self.accel_z_buffer = deque(maxlen=5)
        self.gyro_z_buffer = deque(maxlen=5)

    def imu_callback(self, msg):
        # Add new samples to buffers
        self.accel_x_buffer.append(msg.linear_acceleration.x)
        self.accel_y_buffer.append(msg.linear_acceleration.y)
        self.accel_z_buffer.append(msg.linear_acceleration.z)
        self.gyro_z_buffer.append(msg.angular_velocity.z)

        # Calculate moving average
        filtered_msg = Imu()
        filtered_msg.header = msg.header

        filtered_msg.linear_acceleration.x = sum(self.accel_x_buffer) / len(self.accel_x_buffer)
        filtered_msg.linear_acceleration.y = sum(self.accel_y_buffer) / len(self.accel_y_buffer)
        filtered_msg.linear_acceleration.z = sum(self.accel_z_buffer) / len(self.accel_z_buffer)

        filtered_msg.angular_velocity.x = msg.angular_velocity.x
        filtered_msg.angular_velocity.y = msg.angular_velocity.y
        filtered_msg.angular_velocity.z = sum(self.gyro_z_buffer) / len(self.gyro_z_buffer)

        self.publisher.publish(filtered_msg)

def main(args=None):
    rclpy.init(args=args)
    node = ImuFilterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Run filter:**

```bash
chmod +x ~/imu_filter_node.py
python3 ~/imu_filter_node.py
```

**Compare raw vs filtered:**

```bash
# Terminal 1: Plot raw
rqt_plot /imu/data_raw/angular_velocity/z

# Terminal 2: Plot filtered
rqt_plot /imu/filtered/angular_velocity/z

# Drive robot - see filtered is smoother!
```

***

#### Exercise 5.2: Filter Tuning

**Task:** Find optimal window size

**Test different window sizes:**

```python
# Edit imu_filter_node.py
# Try these window sizes:
# deque(maxlen=3)   # Small window, less smoothing
# deque(maxlen=5)   # Medium window (default)
# deque(maxlen=10)  # Large window, more smoothing
# deque(maxlen=20)  # Very large, lots of delay
```

**For each window size:**

1. Run filter
2. Drive robot in circle
3. Plot raw vs filtered
4. Note:
   * Noise reduction (smoother?)
   * Response delay (laggy?)

**Optimal window:** Balance smoothness vs. delay

* Too small: Still noisy
* Too large: Delayed response (bad for control)

**Typical:** 5-10 samples works well

***

### Part 4: Complementary Filter

#### Theory

**Combine accelerometer + gyroscope for orientation:**

**Accelerometer angle (from gravity):**

```python
# Robot tilt from horizontal
pitch_accel = atan2(accel_x, accel_z)
roll_accel = atan2(accel_y, accel_z)
```

**Gyroscope angle (from integration):**

```python
# Integrate angular velocity
pitch_gyro = pitch_gyro + (gyro_y * dt)
roll_gyro = roll_gyro + (gyro_x * dt)
```

**Complementary filter (combine both):**

```python
# Weight: 98% gyro (short-term), 2% accel (long-term)
alpha = 0.98

pitch = alpha * (pitch + gyro_y * dt) + (1 - alpha) * pitch_accel
roll = alpha * (roll + gyro_x * dt) + (1 - alpha) * roll_accel
```

**Why this works:**

* Gyro dominates short-term (smooth, fast)
* Accel corrects long-term (prevents drift)
* Alpha balances trust between sensors

***

#### Implement Complementary Filter

> \[!WARNING] **TODO: Exercise Script Not Included in Core Repository** The `orientation_estimator.py` script below is an exercise. It is *not* pre-installed.

**Create orientation estimator:**

```bash
nano ~/orientation_estimator.py
```

**Script:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Vector3Stamped
import math

class OrientationEstimator(Node):
    def __init__(self):
        super().__init__('orientation_estimator')

        self.subscription = self.create_subscription(
            Imu, '/imu/data_raw', self.imu_callback, 10)

        self.orientation_pub = self.create_publisher(
            Vector3Stamped, '/imu/orientation_estimate', 10)

        # State variables
        self.roll = 0.0
        self.pitch = 0.0
        self.last_time = None

        # Complementary filter parameter
        self.alpha = 0.98

    def imu_callback(self, msg):
        # Calculate dt
        current_time = self.get_clock().now()
        if self.last_time is None:
            self.last_time = current_time
            return

        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time

        # Extract sensor data
        ax = msg.linear_acceleration.x
        ay = msg.linear_acceleration.y
        az = msg.linear_acceleration.z
        gx = msg.angular_velocity.x
        gy = msg.angular_velocity.y

        # Accelerometer-based angles
        roll_accel = math.atan2(ay, az)
        pitch_accel = math.atan2(ax, az)

        # Gyroscope integration
        roll_gyro = self.roll + gx * dt
        pitch_gyro = self.pitch + gy * dt

        # Complementary filter
        self.roll = self.alpha * roll_gyro + (1 - self.alpha) * roll_accel
        self.pitch = self.alpha * pitch_gyro + (1 - self.alpha) * pitch_accel

        # Publish estimate
        orientation_msg = Vector3Stamped()
        orientation_msg.header.stamp = current_time.to_msg()
        orientation_msg.vector.x = math.degrees(self.roll)
        orientation_msg.vector.y = math.degrees(self.pitch)
        orientation_msg.vector.z = 0.0  # Yaw not estimated (need magnetometer)

        self.orientation_pub.publish(orientation_msg)

        self.get_logger().info(f"Roll: {math.degrees(self.roll):.1f}° Pitch: {math.degrees(self.pitch):.1f}°",
                               throttle_duration_sec=1.0)

def main(args=None):
    rclpy.init(args=args)
    node = OrientationEstimator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Run estimator:**

```bash
chmod +x ~/orientation_estimator.py
python3 ~/orientation_estimator.py
```

**Test:**

```
1. Robot on flat ground → should read ~0° roll, ~0° pitch
2. Tilt robot forward (nose down) → pitch should go negative
3. Tilt robot sideways → roll should change
4. Rotate robot around (yaw) → roll/pitch should stay ~0°
```

***

#### Exercise 5.3: Complementary Filter Tuning

**Task:** Find optimal alpha value

**Test alpha values:**

```python
# Edit orientation_estimator.py
# Try different alpha values:

self.alpha = 0.90  # More accelerometer influence (less drift, more noise)
self.alpha = 0.95  # Balanced
self.alpha = 0.98  # More gyro influence (smooth, may drift)
self.alpha = 0.99  # Almost all gyro (smooth but drifts faster)
```

**For each alpha:**

1. Let robot sit still for 2 minutes
2. Note final roll/pitch values
3. Did it drift from 0°?

**Then test dynamic response:**

1. Tilt robot back and forth
2. Does angle follow smoothly?
3. Any lag?

**Optimal alpha:** Usually 0.96-0.98

* Higher = smoother, but drifts more
* Lower = noisier, but less drift

***

### Part 5: Gyro Drift Compensation

#### Understanding Drift

**Problem:** Gyro has small bias

* Even sitting still, reads small non-zero value
* Integration accumulates this error
* After minutes, angle is way off

**Example:**

```
Gyro bias: +0.001 rad/s
After 60 seconds: 0.001 × 60 = 0.06 rad = 3.4° error!
After 10 minutes: 34° error!
```

***

#### Calibration Solution

**Idea:** Measure bias when stationary, subtract it

**Calibration procedure:**

```bash
nano ~/gyro_calibration.py
```

**Script:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import numpy as np

class GyroCalibration(Node):
    def __init__(self):
        super().__init__('gyro_calibration')

        self.subscription = self.create_subscription(
            Imu, '/imu/data_raw', self.imu_callback, 10)

        self.samples = []
        self.num_samples = 1000  # 10 seconds at 100 Hz

        self.get_logger().info("Keep robot PERFECTLY STILL for 10 seconds...")

    def imu_callback(self, msg):
        if len(self.samples) < self.num_samples:
            self.samples.append([
                msg.angular_velocity.x,
                msg.angular_velocity.y,
                msg.angular_velocity.z
            ])

            if len(self.samples) == self.num_samples:
                self.compute_bias()

    def compute_bias(self):
        samples = np.array(self.samples)
        bias = np.mean(samples, axis=0)

        print("\n=== Gyroscope Calibration Results ===")
        print(f"Samples: {len(self.samples)}")
        print(f"Bias X: {bias[0]:.6f} rad/s")
        print(f"Bias Y: {bias[1]:.6f} rad/s")
        print(f"Bias Z: {bias[2]:.6f} rad/s")
        print("\nAdd these to your filter node to subtract bias!")

        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = GyroCalibration()
    rclpy.spin(node)
    node.destroy_node()

if __name__ == '__main__':
    main()
```

**Run calibration:**

```bash
chmod +x ~/gyro_calibration.py
python3 ~/gyro_calibration.py

# Keep robot perfectly still for 10 seconds
```

**Output:**

```
=== Gyroscope Calibration Results ===
Samples: 1000
Bias X: 0.001234 rad/s
Bias Y: -0.000987 rad/s
Bias Z: 0.002145 rad/s

Add these to your filter node to subtract bias!
```

**Update orientation estimator:**

```python
# In orientation_estimator.py, add after __init__:
self.gyro_bias_x = 0.001234  # From calibration
self.gyro_bias_y = -0.000987
self.gyro_bias_z = 0.002145

# In imu_callback, subtract bias:
gx = msg.angular_velocity.x - self.gyro_bias_x
gy = msg.angular_velocity.y - self.gyro_bias_y
gz = msg.angular_velocity.z - self.gyro_bias_z
```

***

#### Exercise 5.4: Measure Drift Improvement

**Task:** Compare drift with vs without bias compensation

**Test 1: No compensation**

```bash
# Run orientation_estimator without bias compensation
# Let robot sit still for 5 minutes
# Record final roll/pitch values
```

**Test 2: With compensation**

```bash
# Run calibration, get bias values
# Update orientation_estimator with bias values
# Let robot sit still for 5 minutes
# Record final roll/pitch values
```

**Expected results:**

* Without: 10-20° drift after 5 minutes
* With: <2° drift after 5 minutes

***

### Part 6: Accelerometer Calibration

#### Why Calibrate Accelerometer?

**Issues:**

* Sensor not perfectly aligned with robot frame
* Slight bias (reads 0.1 instead of 0.0)
* Scale factors (reads 9.7 instead of 9.81)

**Calibration finds:**

* Zero offsets (bias)
* Scale factors
* Axis alignment

***

#### Simple Calibration Method

**Six-position method:**

```bash
nano ~/accel_calibration.py
```

**Script:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import numpy as np
import time

class AccelCalibration(Node):
    def __init__(self):
        super().__init__('accel_calibration')

        self.subscription = self.create_subscription(
            Imu, '/imu/data_raw', self.imu_callback, 10)

        self.positions = {
            'z_up': [],    # Normal position
            'z_down': [],  # Upside down
            'x_up': [],    # Nose up
            'x_down': [],  # Nose down
            'y_up': [],    # Right side up
            'y_down': []   # Left side up
        }

        self.current_position = None
        self.samples_per_position = 200

    def imu_callback(self, msg):
        if self.current_position and len(self.positions[self.current_position]) < self.samples_per_position:
            self.positions[self.current_position].append([
                msg.linear_acceleration.x,
                msg.linear_acceleration.y,
                msg.linear_acceleration.z
            ])

    def collect_position(self, position_name, instruction):
        self.current_position = position_name
        self.positions[position_name] = []

        print(f"\n{instruction}")
        print("Press Enter when ready, then keep PERFECTLY STILL...")
        input()

        print("Collecting data... (2 seconds)")
        time.sleep(2)

        print(f"Collected {len(self.positions[position_name])} samples ✓")

    def run_calibration(self):
        print("\n=== Accelerometer Calibration ===")
        print("Follow instructions to position robot in 6 orientations")

        self.collect_position('z_up', "Position 1: Normal (wheels down)")
        self.collect_position('z_down', "Position 2: Upside down")
        self.collect_position('x_up', "Position 3: Nose pointing up (vertical)")
        self.collect_position('x_down', "Position 4: Nose pointing down (vertical)")
        self.collect_position('y_up', "Position 5: Right side up (vertical)")
        self.collect_position('y_down', "Position 6: Left side up (vertical)")

        self.compute_calibration()

    def compute_calibration(self):
        # Calculate means for each position
        means = {}
        for pos, samples in self.positions.items():
            means[pos] = np.mean(samples, axis=0)

        # Calculate biases (average of opposite positions should be 0)
        bias_x = (means['x_up'][0] + means['x_down'][0]) / 2
        bias_y = (means['y_up'][1] + means['y_down'][1]) / 2
        bias_z = (means['z_up'][2] + means['z_down'][2]) / 2

        # Calculate scale factors (difference should be 2g = 19.62)
        scale_x = 19.62 / (means['x_up'][0] - means['x_down'][0])
        scale_y = 19.62 / (means['y_up'][1] - means['y_down'][1])
        scale_z = 19.62 / (means['z_up'][2] - means['z_down'][2])

        print("\n=== Calibration Results ===")
        print(f"Bias X: {bias_x:.4f} m/s²")
        print(f"Bias Y: {bias_y:.4f} m/s²")
        print(f"Bias Z: {bias_z:.4f} m/s²")
        print(f"\nScale X: {scale_x:.4f}")
        print(f"Scale Y: {scale_y:.4f}")
        print(f"Scale Z: {scale_z:.4f}")
        print("\nApply in your filter:")
        print("  accel_calibrated = (accel_raw - bias) * scale")

def main(args=None):
    rclpy.init(args=args)
    node = AccelCalibration()

    # Run calibration sequence
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)

    import threading
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    node.run_calibration()

    rclpy.shutdown()
    spin_thread.join()

if __name__ == '__main__':
    main()
```

**Run calibration:**

```bash
python3 ~/accel_calibration.py

# Follow instructions to position robot 6 ways
# Each position: hold still for 2 seconds
```

**Note:** This requires physically manipulating robot (may be difficult with wired robot). Optional advanced exercise!

***

### Part 7: Advanced Filtering (Optional)

#### Kalman Filter Concept

**Better than complementary filter:**

* Dynamically adjusts trust based on noise
* Provides uncertainty estimates (covariance)
* Optimal for Gaussian noise

**Implementation:** Complex (beyond this tutorial) **Library:** `robot_localization` package (already used for `/odometry/filtered`)

**Key idea:**

* Prediction step (gyro)
* Update step (accel)
* Gain adjustment based on noise

***

#### Madgwick Filter

**Popular alternative:**

* Quaternion-based (no gimbal lock)
* Computationally efficient
* Widely used in drones/quadcopters

**Python library:**

```bash
pip3 install imufusion --break-system-packages
```

**Example usage:**

```python
import imufusion

# Initialize
ahrs = imufusion.Ahrs()

# In IMU callback:
ahrs.update_no_magnetometer(
    gyroscope=(gx, gy, gz),  # rad/s
    accelerometer=(ax, ay, az),  # m/s²
    delta_time=dt
)

# Get orientation (quaternion)
quaternion = ahrs.quaternion

# Convert to Euler angles
euler = ahrs.euler
```

***

### Part 8: Practical Applications

#### Use Case 1: Tilt Detection

**Detect if robot is stuck on obstacle:**

```python
# In filter node
if abs(self.roll) > 15.0 or abs(self.pitch) > 15.0:
    self.get_logger().warn("Robot tilted! Possible obstacle!")
```

***

#### Use Case 2: Vibration Monitoring

**Detect mechanical issues:**

```python
# Calculate vibration magnitude
vibration = math.sqrt(ax**2 + ay**2 + (az - 9.81)**2)

if vibration > 2.0:  # Threshold
    self.get_logger().warn("High vibration detected! Check wheels/motors")
```

***

#### Use Case 3: Motion Classification

**Detect driving patterns:**

```python
# Check if robot is:
# - Stationary: gyro ~0, accel = gravity only
# - Driving straight: gyro ~0, accel_x != 0
# - Turning: gyro_z != 0
# - Stopped on incline: pitch != 0, gyro ~0
```

***

### Part 9: Troubleshooting

#### IMU Readings Look Wrong

**Check coordinate frame:**

* `/imu/data_raw` may be in sensor frame
* `/imu/data` should be in base\_link frame
* Use `tf2_echo` to check transform

***

#### Filter Output Drifts

**Possible causes:**

1. Gyro bias not calibrated
2. Alpha value too high (too much gyro weight)
3. Robot actually tilting (check level surface)
4. Temperature drift (warm up motors, re-calibrate)

***

#### Accelerometer Jumpy

**Normal!** Accelerometers are noisy short-term

* Increase filter window size
* Use complementary filter (gyro smooths it)
* Check for motor vibrations

***

#### General Debugging

**Most IMU issues fixed by:**

1. ⚡ Power cycle robot
2. Re-run calibration
3. Check IMU topic rate (should be 100 Hz)
4. Verify sensor not physically damaged

***

### Part 10: Knowledge Check

#### Concept Quiz

1. **Why does accelerometer read 9.81 m/s² when stationary?**
2. **What's the main problem with gyroscope for long-term orientation?**
3. **What does alpha=0.98 mean in complementary filter?**
4. **Why calibrate gyroscope?**
5. **Can IMU measure absolute orientation (North/South/East/West)?**

***

#### Hands-On Challenge

**Task:** Implement complete IMU processing pipeline

**Requirements:**

1. Gyro calibration (measure bias)
2. Moving average low-pass filter (window=7)
3. Complementary filter (alpha=0.97)
4. Publish filtered orientation on new topic
5. Test for 5 minutes, measure final drift

**Bonus:**

* Add tilt warning (>15°)
* Add vibration detection (>2 m/s²)
* Plot raw vs filtered on same graph

***

### Part 11: What You've Learned

#### ✅ Congratulations!

You now understand:

**IMU Fundamentals:**

* ✅ Accelerometer measures gravity + motion
* ✅ Gyroscope measures rotation rate (not angle)
* ✅ Each sensor has strengths and weaknesses
* ✅ Sensor fusion combines best of both

**Signal Processing:**

* ✅ Noise characterization (mean, std dev)
* ✅ Low-pass filtering (moving average)
* ✅ Complementary filtering (sensor fusion)
* ✅ Integration and differentiation

**Calibration:**

* ✅ Gyro bias measurement
* ✅ Drift compensation
* ✅ Accelerometer calibration (optional)

**Practical Skills:**

* ✅ Implementing filters in Python/ROS2
* ✅ Tuning filter parameters
* ✅ Analyzing sensor data
* ✅ Troubleshooting IMU issues

***

### Next Steps

#### 🎯 You're Now Ready For:

**Immediate Next:** → Teleoperation Control - Drive robot with sensor feedback

**Advanced Sensor Topics:** → Sensor Fusion with EKF - Full state estimation\
→ SLAM Mapping - Use IMU to aid mapping

**Robotics Applications:**

* Balance control (tilt compensation)
* Bump detection (sudden acceleration)
* Activity recognition (walking/running/falling patterns)

***

### Quick Reference

#### Essential IMU Commands

```bash
# --- View IMU Data ---
ros2 topic echo /imu/data_raw          # Raw sensor
ros2 topic echo /imu/data              # Filtered
ros2 topic hz /imu/data                # Check rate (100 Hz)

# --- Plotting ---
rqt_plot /imu/data/angular_velocity/z  # Gyro
rqt_plot /imu/data/linear_acceleration/x  # Accel

# --- Recording ---
ros2 bag record /imu/data_raw          # Collect data

# --- Run Filter Scripts ---
python3 ~/imu_filter_node.py           # Low-pass filter
python3 ~/orientation_estimator.py     # Complementary filter
python3 ~/gyro_calibration.py          # Calibrate gyro
```

***

#### Key Equations

```python
# Low-pass filter (moving average)
filtered = sum(last_N_samples) / N

# Complementary filter
angle = alpha * (angle + gyro * dt) + (1 - alpha) * accel_angle

# Accelerometer tilt
pitch = atan2(accel_x, accel_z)
roll = atan2(accel_y, accel_z)

# Gyro integration
angle = angle + gyro * dt

# Bias compensation
gyro_corrected = gyro_raw - bias
```

***

**Completed IMU Signal Processing!** 🎉

→ Continue to Teleoperation Control\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 5 of 11 - Intermediate Level*\
*Estimated completion time: 100 minutes*
