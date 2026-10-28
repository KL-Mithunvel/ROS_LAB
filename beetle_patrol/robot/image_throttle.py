#!/usr/bin/env python3
"""Republish /pi_camera/image_raw/compressed at a capped rate (default 5 Hz).

The camera streams ~56 Hz x 29 KB (~1.6 MB/s), too heavy for Wi-Fi. Frames are
forwarded unchanged (no re-encoding) to /patrol/camera/compressed.
Runs on the robot, pure python.
"""
import os
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from throttle_logic import ThrottleLogic  # noqa: E402


class ImageThrottle(Node):
    def __init__(self):
        super().__init__('image_throttle')
        self.declare_parameter('max_hz', 5.0)
        self.declare_parameter('input_topic', '/pi_camera/image_raw/compressed')
        self.declare_parameter('output_topic', '/patrol/camera/compressed')
        hz = float(self.get_parameter('max_hz').value)
        self.logic = ThrottleLogic(hz)
        # Camera publishes best-effort; subscribe with sensor QoS.
        self.sub = self.create_subscription(
            CompressedImage, self.get_parameter('input_topic').value,
            self.on_image, qos_profile_sensor_data)
        # Reliable output (depth 2) matches both reliable and best-effort subscribers.
        out_qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                             history=HistoryPolicy.KEEP_LAST, depth=2)
        self.pub = self.create_publisher(
            CompressedImage, self.get_parameter('output_topic').value, out_qos)
        self.get_logger().info(f'throttling camera to {hz:.1f} Hz')

    def on_image(self, msg):
        if self.logic.should_publish(time.monotonic()):
            self.pub.publish(msg)


def main():
    rclpy.init()
    node = ImageThrottle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == '__main__':
    main()
