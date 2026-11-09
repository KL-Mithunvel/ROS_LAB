#!/usr/bin/env python3
"""/scan_raw (Gazebo, stamped 'now') -> /scan stamped 50 ms in the past, like the real RPLiDAR driver stamping at
acquisition. Without it a scan can be newer than the latest odom tf and the patrol node skips it."""
import rclpy
from builtin_interfaces.msg import Time
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

DELAY_NS = 50_000_000


class Restamp(Node):
    def __init__(self):
        super().__init__("scan_restamp")
        self.pub = self.create_publisher(LaserScan, "/scan", qos_profile_sensor_data)
        self.create_subscription(LaserScan, "/scan_raw", self.cb, qos_profile_sensor_data)

    def cb(self, m):
        ns = max(0, m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec - DELAY_NS)
        m.header.stamp = Time(sec=ns // 1_000_000_000, nanosec=ns % 1_000_000_000)
        self.pub.publish(m)


def main():
    rclpy.init()
    rclpy.spin(Restamp())


if __name__ == "__main__":
    main()
