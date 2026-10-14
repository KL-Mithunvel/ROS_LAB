#!/usr/bin/env python3
"""Republish a CompressedImage topic at a lower rate. Runs ON THE ROBOT, next to the camera driver.

    python3 image_throttle.py [src] [dst] [hz]

Why: the full-rate camera stream (30 fps x ~43 KB) over Wi-Fi/UDP overflows the laptop's default
socket buffer and starves /scan on the same DDS socket. A 5 Hz copy is plenty for the GUI.
"""
import sys
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage

SRC = sys.argv[1] if len(sys.argv) > 1 else "/camera/camera/color/image_raw/compressed"
DST = sys.argv[2] if len(sys.argv) > 2 else "/gui/camera/compressed"
HZ = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0


def main():
    rclpy.init()
    node = rclpy.create_node("image_throttle")
    pub = node.create_publisher(CompressedImage, DST, qos_profile_sensor_data)
    last = [0.0]

    def cb(msg):
        now = time.monotonic()
        if now - last[0] >= 1.0 / HZ:
            last[0] = now
            pub.publish(msg)

    node.create_subscription(CompressedImage, SRC, cb, qos_profile_sensor_data)
    node.get_logger().info(f"{SRC} -> {DST} at <= {HZ} Hz")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
