# Camera-Based Perception

***

### Tutorial Overview

#### 🎯 Learning Objectives

By the end of this tutorial, you will:

* ✅ Access and view camera streams
* ✅ Understand image topics and formats
* ✅ Perform basic image processing (filters, thresholding, edge detection)
* ✅ Detect colors and shapes
* ✅ Record and process video data
* ✅ Understand camera calibration
* ✅ Explore potential perception applications
* ✅ Integrate vision with robot control

#### ⏱️ Time Required

* **Reading & Setup:** 20 minutes
* **Basic Image Access:** 25 minutes
* **Image Processing:** 40 minutes
* **Color/Shape Detection:** 35 minutes
* **Applications:** 30 minutes
* **Total:** \~150 minutes

#### 📚 Prerequisites

* ✅ Completed Sensor Data Visualization
* ✅ Completed ROS2 Communication & Tools
* ✅ Basic Python knowledge
* ✅ Understanding of image concepts (pixels, RGB)
* ✅ OpenCV basics helpful but not required
* ✅ Can record and play rosbags

#### 🛠️ What You'll Need

* ✅ Beetlebot (powered, camera working)
* ✅ Laptop with ROS2 Jazzy
* ✅ Wireless controller
* ✅ Test objects with distinct colors
* ✅ Good lighting (avoid direct sunlight on camera)
* ✅ Printed patterns for detection tests (optional)

***

### Part 1: Camera System Overview

#### Raspberry Pi Camera V1.3 Specifications

**Your robot's camera:**

**Hardware:**

* Sensor: OmniVision OV5647
* Resolution: 5MP (2592×1944 max)
* Typical streaming: 1080p (1920×1080) or 720p (1280×720)
* Frame rate: 30 fps (1080p), 60 fps (720p)
* FOV: \~54° horizontal, \~41° vertical
* Focus: Fixed (best 30cm - 3m)
* Interface: CSI (Camera Serial Interface) to Pi

**Mounting:**

* Height: 8.8cm from ground
* Position: 15cm forward from center
* Orientation: Horizontal, forward-facing
* Topic: `/pi_camera/image_raw`

***

#### Camera Topics

**Available topics:**

```bash
ros2 topic list | grep camera

# Output:
# /pi_camera/camera_info        ← Calibration data
# /pi_camera/image_raw           ← Uncompressed images
# /pi_camera/image_raw/compressed ← JPEG compressed
```

**Topic details:**

**`/pi_camera/image_raw`** (sensor\_msgs/Image)

* Uncompressed RGB8 or BGR8 format
* \~30 MB/s bandwidth (1080p @ 30fps)
* Best quality
* Use for local processing

**`/pi_camera/image_raw/compressed`** (sensor\_msgs/CompressedImage)

* JPEG compression
* \~3-5 MB/s bandwidth
* Slight quality loss
* Better for remote viewing

**`/pi_camera/camera_info`** (sensor\_msgs/CameraInfo)

* Intrinsic parameters (focal length, principal point)
* Distortion coefficients
* Rectification matrix
* Projection matrix

***

#### Understanding Image Messages

**Image message structure:**

```bash
ros2 interface show sensor_msgs/msg/Image

# Fields:
# std_msgs/Header header
#   builtin_interfaces/Time stamp
#   string frame_id
# uint32 height           # rows
# uint32 width            # columns
# string encoding         # rgb8, bgr8, mono8, etc.
# uint8 is_bigendian
# uint32 step             # bytes per row
# uint8[] data            # actual pixel data
```

**Common encodings:**

* `rgb8`: 8-bit RGB (Red-Green-Blue)
* `bgr8`: 8-bit BGR (OpenCV default)
* `mono8`: 8-bit grayscale
* `rgba8`: 8-bit RGBA (with alpha channel)

***

### Part 2: Accessing Camera Stream

#### Quick View with rqt\_image\_view

**Simplest method:**

```bash
# On laptop
ros2 run rqt_image_view rqt_image_view

# Window opens
# Dropdown: Select "/pi_camera/image_raw/compressed"
# Image appears!
```

**Controls:**

* Zoom: Mouse wheel
* Pan: Right-click + drag
* Refresh: Click dropdown again
* Rotate: Image → Transform menu

\[PLACEHOLDER: Screenshot of rqt\_image\_view showing camera feed]

***

#### Exercise 9.1: Camera Field of View Test

**Task:** Measure camera's actual field of view

**Materials needed:**

* Measuring tape
* Flat wall
* Markers or tape

**Procedure:**

```
1. Place robot 1 meter from wall (measure precisely)
2. Robot facing wall directly (perpendicular)
3. View camera in rqt_image_view
4. Mark left edge of camera view on wall (left_edge)
5. Mark right edge of camera view on wall (right_edge)
6. Measure distance between marks (width)

Calculation:
  FOV = 2 × atan(width / (2 × distance))
  FOV = 2 × atan(width / 2.0)

Example:
  width = 1.1 meters
  FOV = 2 × atan(1.1 / 2.0) = 2 × atan(0.55)
      = 2 × 28.8° = 57.6°

Expected: ~54° (spec says 54°, you should get close!)
```

***

#### Viewing in RViz

**Integrated visualization:**

```bash
# Launch RViz
rviz2

# Add Camera display:
Add → Camera
  Image Topic: /pi_camera/image_raw
  Transport Hint: compressed (for better performance)

# New window shows camera feed with RViz overlays
```

**Benefits of RViz camera view:**

* See camera + LiDAR + map simultaneously
* Overlay detection results
* 3D context for camera view
* Can add measurement tools

***

### Part 3: Basic Image Processing with OpenCV

#### Installing Dependencies

```bash
# Install OpenCV for Python
sudo apt install python3-opencv python3-numpy --break-system-packages

# Or pip (if needed)
pip3 install opencv-python numpy --break-system-packages

# Verify installation
python3 -c "import cv2; print(cv2.__version__)"
# Should show: 4.x.x
```

***

#### Creating Image Processing Node

> \[!WARNING] **TODO: Exercise Script Not Included in Core Repository** The `camera_processor.py` script below is an exercise for the user to practice processing camera frames with OpenCV. It does *not* come pre-installed.

**Basic template for image processing:**

```bash
nano ~/camera_processor.py
```

**Script:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np

class CameraProcessor(Node):
    def __init__(self):
        super().__init__('camera_processor')

        # Bridge converts ROS Image ↔ OpenCV image
        self.bridge = CvBridge()

        # Subscribe to camera
        self.subscription = self.create_subscription(
            Image,
            '/pi_camera/image_raw',
            self.image_callback,
            10)

        # Publisher for processed images (optional)
        self.publisher = self.create_publisher(
            Image,
            '/camera/processed',
            10)

        self.get_logger().info('Camera Processor started!')

    def image_callback(self, msg):
        try:
            # Convert ROS Image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            # **PROCESSING HAPPENS HERE**
            # Example: Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            # Display (local window)
            cv2.imshow('Original', cv_image)
            cv2.imshow('Grayscale', gray)
            cv2.waitKey(1)

            # Publish processed image (optional)
            processed_msg = self.bridge.cv2_to_imgmsg(gray, encoding='mono8')
            self.publisher.publish(processed_msg)

        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = CameraProcessor()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Run:**

```bash
chmod +x ~/camera_processor.py
python3 ~/camera_processor.py
```

**Two windows appear:**

* Original: Color camera feed
* Grayscale: Converted to grayscale

**Press Ctrl+C to stop**

***

#### Image Filtering

**Add filters to processing node:**

```python
# In image_callback, replace processing section:

# 1. Gaussian Blur (smoothing, noise reduction)
blurred = cv2.GaussianBlur(cv_image, (15, 15), 0)

# 2. Edge Detection (Canny)
edges = cv2.Canny(cv_image, 50, 150)

# 3. Median Blur (removes salt-and-pepper noise)
median = cv2.medianBlur(cv_image, 5)

# 4. Sharpening
kernel = np.array([[-1,-1,-1],
                   [-1, 9,-1],
                   [-1,-1,-1]])
sharpened = cv2.filter2D(cv_image, -1, kernel)

# Display all
cv2.imshow('Original', cv_image)
cv2.imshow('Blurred', blurred)
cv2.imshow('Edges', edges)
cv2.imshow('Median', median)
cv2.imshow('Sharpened', sharpened)
```

\[PLACEHOLDER: Screenshot showing original vs filtered images]

***

#### Exercise 9.2: Edge Detection for Obstacle Boundaries

**Task:** Detect obstacles using edge detection

**Modify processing node:**

```python
def image_callback(self, msg):
    cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    # Convert to grayscale
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    # Blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)

    # Find contours (boundaries)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                     cv2.CHAIN_APPROX_SIMPLE)

    # Draw contours on original image
    output = cv_image.copy()
    cv2.drawContours(output, contours, -1, (0, 255, 0), 2)

    # Display
    cv2.imshow('Edges', edges)
    cv2.imshow('Contours', output)
    cv2.waitKey(1)
```

**Test:**

* Place various objects in front of robot
* Observe edge detection outlining objects
* Try different Canny thresholds (50, 150) to tune sensitivity

***

### Part 4: Color Detection

#### HSV Color Space

**Why HSV instead of RGB?**

**RGB (Red-Green-Blue):**

* How cameras capture
* Lighting affects all channels
* Hard to isolate specific colors

**HSV (Hue-Saturation-Value):**

* Hue = Color (0-180° in OpenCV)
* Saturation = Color intensity (0-255)
* Value = Brightness (0-255)
* Lighting mainly affects Value
* Easier to detect specific colors

**Color ranges in HSV (OpenCV):**

```
Red:    Hue 0-10, 170-180 (wraps around)
Orange: Hue 10-25
Yellow: Hue 25-35
Green:  Hue 35-85
Blue:   Hue 85-125
Purple: Hue 125-155
```

***

#### Color Detection Node

> \[!WARNING] **TODO: Exercise Script Not Included in Core Repository** The `color_detector.py` script below is an exercise for color tracking. It is *not* pre-installed. You are encouraged to create it yourself!

**Create color detector:**

```bash
nano ~/color_detector.py
```

**Script:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np

class ColorDetector(Node):
    def __init__(self):
        super().__init__('color_detector')
        self.bridge = CvBridge()

        self.subscription = self.create_subscription(
            Image, '/pi_camera/image_raw', self.image_callback, 10)

        # Define color ranges (HSV)
        # Red (example: red ball, red tape)
        self.lower_red1 = np.array([0, 100, 100])
        self.upper_red1 = np.array([10, 255, 255])
        self.lower_red2 = np.array([170, 100, 100])
        self.upper_red2 = np.array([180, 255, 255])

        # Green (example: green marker)
        self.lower_green = np.array([35, 50, 50])
        self.upper_green = np.array([85, 255, 255])

        # Blue (example: blue object)
        self.lower_blue = np.array([85, 50, 50])
        self.upper_blue = np.array([125, 255, 255])

        self.get_logger().info('Color Detector started!')

    def image_callback(self, msg):
        # Convert to OpenCV
        cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        # Convert to HSV
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

        # Create masks for each color
        # Red (two ranges because it wraps around)
        mask_red1 = cv2.inRange(hsv, self.lower_red1, self.upper_red1)
        mask_red2 = cv2.inRange(hsv, self.lower_red2, self.upper_red2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)

        mask_green = cv2.inRange(hsv, self.lower_green, self.upper_green)
        mask_blue = cv2.inRange(hsv, self.lower_blue, self.upper_blue)

        # Find contours for each color
        contours_red, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL,
                                            cv2.CHAIN_APPROX_SIMPLE)
        contours_green, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL,
                                              cv2.CHAIN_APPROX_SIMPLE)
        contours_blue, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL,
                                             cv2.CHAIN_APPROX_SIMPLE)

        # Draw on original image
        output = cv_image.copy()

        # Red objects
        for contour in contours_red:
            if cv2.contourArea(contour) > 500:  # Filter small noise
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(output, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(output, 'RED', (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Green objects
        for contour in contours_green:
            if cv2.contourArea(contour) > 500:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(output, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(output, 'GREEN', (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Blue objects
        for contour in contours_blue:
            if cv2.contourArea(contour) > 500:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(output, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(output, 'BLUE', (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        # Display
        cv2.imshow('Original', cv_image)
        cv2.imshow('Detected Colors', output)
        cv2.imshow('Red Mask', mask_red)
        cv2.imshow('Green Mask', mask_green)
        cv2.imshow('Blue Mask', mask_blue)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = ColorDetector()
    rclpy.spin(node)
    cv2.destroyAllWindows()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Run:**

```bash
chmod +x ~/color_detector.py
python3 ~/color_detector.py
```

***

#### Exercise 9.3: Color-Based Object Tracking

**Task:** Track colored object and display centroid

**Modification to color\_detector.py:**

```python
# After finding contours for red objects:
for contour in contours_red:
    if cv2.contourArea(contour) > 500:
        # Calculate centroid
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            # Draw centroid
            cv2.circle(output, (cx, cy), 5, (255, 255, 255), -1)

            # Draw bounding box
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(output, (x, y), (x+w, y+h), (0, 0, 255), 2)

            # Display position info
            cv2.putText(output, f'RED ({cx}, {cy})', (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # Log position
            self.get_logger().info(f'Red object at pixel ({cx}, {cy})')
```

**Test:**

* Hold red object in front of camera
* Move it around
* Observe centroid tracking
* Check console for position logs

***

### Part 5: Shape Detection

#### Detecting Simple Shapes

**Add shape detection:**

```python
def detect_shape(self, contour):
    """Identify shape based on contour properties"""

    # Approximate contour to polygon
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

    # Number of vertices determines shape
    vertices = len(approx)

    if vertices == 3:
        return "Triangle"
    elif vertices == 4:
        # Check if square or rectangle
        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h
        if 0.95 <= aspect_ratio <= 1.05:
            return "Square"
        else:
            return "Rectangle"
    elif vertices == 5:
        return "Pentagon"
    elif vertices > 5:
        # Check circularity
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        circularity = 4 * np.pi * area / (perimeter * perimeter)

        if circularity > 0.8:
            return "Circle"
        else:
            return "Polygon"
    else:
        return "Unknown"

# In image_callback, after finding contours:
for contour in contours_red:
    if cv2.contourArea(contour) > 500:
        shape = self.detect_shape(contour)
        x, y, w, h = cv2.boundingRect(contour)
        cv2.putText(output, shape, (x, y-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
```

***

#### Exercise 9.4: Shape and Color Recognition

**Task:** Create multi-property detector

**Test scenario:**

```
Objects to detect:
- Red circle (ball)
- Blue rectangle (book)
- Green triangle (folded paper)

Output should show:
- "RED CIRCLE at (320, 240)"
- "BLUE RECTANGLE at (150, 300)"
- "GREEN TRIANGLE at (500, 180)"
```

***

### Part 6: Camera Calibration

#### Why Calibrate?

**Camera distortion:**

* Lens distortion (barrel, pincushion)
* Affects measurements and 3D perception
* Need calibration to correct

**What calibration provides:**

* Intrinsic matrix (focal length, principal point)
* Distortion coefficients
* Allows undistortion of images
* Enables accurate 3D measurements

***

#### Viewing Current Calibration

```bash
# Check camera_info topic
ros2 topic echo /pi_camera/camera_info --once

# Output shows:
# K: [fx, 0, cx, 0, fy, cy, 0, 0, 1]  ← Intrinsic matrix
#   fx, fy = focal length (pixels)
#   cx, cy = principal point (image center)
#
# D: [k1, k2, t1, t2, k3]  ← Distortion coefficients
#   k1, k2, k3 = radial distortion
#   t1, t2 = tangential distortion
```

***

#### Using Calibration Data

**Undistort image:**

```python
import cv2
import numpy as np

# Get calibration from camera_info (run once)
# camera_matrix = np.array([[fx, 0, cx],
#                           [0, fy, cy],
#                           [0,  0,  1]])
# dist_coeffs = np.array([k1, k2, t1, t2, k3])

# Example values (yours may differ):
camera_matrix = np.array([[640, 0, 640],
                          [0, 640, 360],
                          [0, 0, 1]], dtype=float)
dist_coeffs = np.array([0.1, -0.05, 0, 0, 0], dtype=float)

# In image_callback:
def image_callback(self, msg):
    cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    # Undistort
    h, w = cv_image.shape[:2]
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeffs, (w, h), 1, (w, h))

    undistorted = cv2.undistort(cv_image, camera_matrix,
                                 dist_coeffs, None, new_camera_matrix)

    # Display both
    cv2.imshow('Original (Distorted)', cv_image)
    cv2.imshow('Undistorted', undistorted)
    cv2.waitKey(1)
```

***

### Part 7: Practical Applications

#### Application 1: Line Following

**Detect line on floor, steer toward it:**

```python
def detect_line(self, cv_image):
    """Detect line in lower portion of image"""

    # Region of interest (bottom half of image)
    height, width = cv_image.shape[:2]
    roi = cv_image[int(height/2):height, 0:width]

    # Convert to grayscale
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Threshold (assuming dark line on light floor)
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                     cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Find largest contour (assumed to be line)
        largest = max(contours, key=cv2.contourArea)

        # Calculate centroid
        M = cv2.moments(largest)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])

            # Error from center
            center_x = width // 2
            error = cx - center_x

            return error  # Positive = line to right, negative = line to left

    return None
```

**Use error for steering:**

```python
# In control loop:
error = self.detect_line(cv_image)
if error is not None:
    # Simple proportional control
    angular_vel = -0.005 * error  # Scale factor

    cmd = Twist()
    cmd.linear.x = 0.3  # Constant forward speed
    cmd.angular.z = angular_vel
    self.cmd_vel_pub.publish(cmd)
```

***

#### Application 2: Obstacle Color Classification

**Classify obstacles by color, react differently:**

```python
def classify_obstacle(self, cv_image):
    """Determine obstacle type by color"""

    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

    # Red = STOP
    mask_red = cv2.inRange(hsv, self.lower_red, self.upper_red)
    if cv2.countNonZero(mask_red) > 1000:  # Significant red detected
        return "STOP"

    # Green = GO
    mask_green = cv2.inRange(hsv, self.lower_green, self.upper_green)
    if cv2.countNonZero(mask_green) > 1000:
        return "GO"

    # Yellow = SLOW
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([30, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    if cv2.countNonZero(mask_yellow) > 1000:
        return "SLOW"

    return "UNKNOWN"

# In control loop:
obstacle_type = self.classify_obstacle(cv_image)
if obstacle_type == "STOP":
    # Stop robot
    cmd.linear.x = 0.0
elif obstacle_type == "SLOW":
    # Reduce speed
    cmd.linear.x = 0.2
elif obstacle_type == "GO":
    # Full speed
    cmd.linear.x = 0.8
```

***

#### Application 3: AprilTag Detection

**AprilTags = Fiducial markers (like QR codes for robots)**

**Install apriltag library:**

```bash
sudo apt install ros-jazzy-apriltag-ros
```

**Launch apriltag detector:**

```bash
ros2 launch apriltag_ros tag_realsense.launch.py
```

**Use cases:**

* Precise localization (know exact position from tag)
* Object identification (each tag has unique ID)
* Docking stations (navigate to specific tag)
* AR applications (overlay virtual objects)

***

### Part 8: Recording and Processing Video

#### Recording Camera Data

```bash
# Record camera feed
ros2 bag record -o camera_test /pi_camera/image_raw/compressed

# Drive around, collect data
# Ctrl+C to stop

# Play back
ros2 bag play camera_test
```

***

#### Offline Processing

> \[!WARNING] **TODO: Exercise Script Not Included in Core Repository** The `offline_processor.py` script below is an exercise to demonstrate processing rosbags programmatically. It is *not* pre-installed.

**Python script: `offline_processor.py`**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class OfflineProcessor(Node):
    def __init__(self):
        super().__init__('offline_processor')
        self.bridge = CvBridge()

        # Output video writer
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.out = cv2.VideoWriter('processed_output.avi', fourcc,
                                    30.0, (1280, 720))

        self.subscription = self.create_subscription(
            Image, '/pi_camera/image_raw', self.process, 10)

        self.frame_count = 0

    def process(self, msg):
        cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        # **YOUR PROCESSING HERE**
        # Example: Add timestamp overlay
        timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
        cv2.putText(cv_image, f'Time: {timestamp:.2f}s', (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Write to output video
        self.out.write(cv_image)

        self.frame_count += 1
        if self.frame_count % 30 == 0:
            self.get_logger().info(f'Processed {self.frame_count} frames')

def main():
    rclpy.init()
    node = OfflineProcessor()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.out.release()
        node.get_logger().info('Video saved as processed_output.avi')
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Run:**

```bash
# Terminal 1: Play bag
ros2 bag play camera_test

# Terminal 2: Process
python3 offline_processor.py
```

***

### Part 9: Limitations and Considerations

#### What Camera Perception Can't Do (Without ML)

**⚠️ Important:** Basic image processing has limitations

**Without machine learning:**

❌ **Cannot do:**

* Object recognition (identify specific objects like "person", "chair", "dog")
* Face recognition
* Text reading (OCR - though basic, possible with libraries)
* Complex scene understanding
* Semantic segmentation

✅ **Can do:**

* Color detection
* Shape detection (simple geometries)
* Edge/contour detection
* Motion detection
* Line following
* Marker detection (AprilTags, QR codes)
* Brightness/contrast analysis

***

#### When to Use Machine Learning

**For advanced perception, need ML models:**

**Options:**

* **Pre-trained models** (YOLO, MobileNet, etc.)
  * Object detection
  * Instance segmentation
  * Pose estimation
* **Custom training** (TensorFlow, PyTorch)
  * Train on specific objects
  * Requires dataset collection
  * Computationally intensive

**Note:** ML perception is beyond this tutorial but worth exploring!

***

#### Lighting Considerations

**Camera performance varies with lighting:**

**Good lighting:**

* Indirect, even illumination
* No harsh shadows
* Consistent throughout environment

**Poor lighting:**

* Direct sunlight (overexposes)
* Backlit scenes (subject too dark)
* Rapid changes (drives in/out of shadows)
* Very low light (noisy images)

**Tip:** Test perception algorithms in actual target lighting conditions!

***

### Part 10: Knowledge Check

#### Concept Quiz

1. **Why use HSV instead of RGB for color detection?**
2. **What does camera calibration provide?**
3. **What's the difference between /image\_raw and /image\_raw/compressed?**
4. **Can basic OpenCV detect "what" an object is (e.g., identify as "cup")?**
5. **Why is the camera mounted forward-facing at 8.8cm height?**

***

#### Hands-On Challenge

**Task:** Color-based navigation system

**Requirements:**

1. Robot follows green markers on floor
2. Stops at red markers
3. Ignores other colors
4. Publishes cmd\_vel based on vision
5. Displays annotated video showing detections
6. Records demo video

**Deliverable:**

* Python script with vision processing
* Video recording of robot navigating course
* Documentation of color thresholds used
* Discussion of challenges encountered

**Bonus:**

* Add shape detection (only respond to green circles, not rectangles)
* Implement smooth steering (PID control based on centroid error)
* Handle cases where no marker visible

***

### Part 11: What You've Learned

#### ✅ Congratulations!

You now understand:

**Camera Fundamentals:**

* ✅ Camera specifications and mounting
* ✅ Image topics and message formats
* ✅ Viewing camera streams (rqt, RViz)
* ✅ Recording and playing back video

**Image Processing:**

* ✅ OpenCV basics (CvBridge, cv2 functions)
* ✅ Image filtering (blur, edge detection)
* ✅ Color detection (HSV color space)
* ✅ Shape detection (contours, polygons)

**Practical Applications:**

* ✅ Line following
* ✅ Obstacle classification by color
* ✅ Object tracking (centroids)
* ✅ Marker detection (AprilTags)

**Advanced Topics:**

* ✅ Camera calibration concepts
* ✅ Undistorting images
* ✅ Offline video processing
* ✅ Limitations of basic vision

***

### Next Steps

#### 🎯 You're Now Ready For:

**Immediate Next:** → Localization Techniques - Combine vision with other sensors

**Autonomous Navigation:** → Autonomous Navigation - Vision-aided obstacle avoidance

**Advanced Vision:**

* Machine learning object detection (YOLO, MobileNet)
* Visual odometry (estimate motion from camera)
* SLAM with visual features (ORB-SLAM)
* Depth estimation (if adding depth camera)

***

### Quick Reference

#### Essential Camera Commands

```bash
# --- View Camera ---
ros2 run rqt_image_view rqt_image_view
# Select: /pi_camera/image_raw/compressed

# --- Check Camera Status ---
ros2 topic hz /pi_camera/image_raw    # Should be ~30 Hz
ros2 topic echo /pi_camera/camera_info --once

# --- Record Video ---
ros2 bag record /pi_camera/image_raw/compressed

# --- Launch Processing Node ---
python3 camera_processor.py

# --- View Processed Output ---
ros2 run rqt_image_view rqt_image_view
# Select: /camera/processed
```

***

#### OpenCV Quick Reference

```python
# Convert ROS → OpenCV
cv_image = bridge.imgmsg_to_cv2(msg, 'bgr8')

# Convert OpenCV → ROS
ros_image = bridge.cv2_to_imgmsg(cv_image, 'bgr8')

# Color space conversion
hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

# Filtering
blurred = cv2.GaussianBlur(cv_image, (5, 5), 0)
edges = cv2.Canny(gray, 50, 150)

# Color detection
mask = cv2.inRange(hsv, lower_color, upper_color)

# Contours
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_SIMPLE)

# Drawing
cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
cv2.circle(image, (cx, cy), 5, (255, 0, 0), -1)
cv2.putText(image, 'Text', (x, y), cv2.FONT_HERSHEY_SIMPLEX,
           0.6, (0, 0, 255), 2)

# Display
cv2.imshow('Window', image)
cv2.waitKey(1)
```

***

#### HSV Color Ranges (OpenCV)

| Color  | Hue Range     | Typical Sat | Typical Val |
| ------ | ------------- | ----------- | ----------- |
| Red    | 0-10, 170-180 | 100-255     | 100-255     |
| Orange | 10-25         | 100-255     | 100-255     |
| Yellow | 25-35         | 100-255     | 100-255     |
| Green  | 35-85         | 50-255      | 50-255      |
| Blue   | 85-125        | 50-255      | 50-255      |
| Purple | 125-155       | 50-255      | 50-255      |

***

**Completed Camera-Based Perception!** 🎉

→ Continue to Localization Techniques\
→ Or return to Tutorial Index

***

*Last Updated: January 2026*\
*Tutorial 9 of 11 - Advanced Level*\
*Estimated completion time: 150 minutes*
