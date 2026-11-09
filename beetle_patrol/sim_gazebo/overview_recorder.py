#!/usr/bin/env python3
"""Records the virtual overview camera (/overview/image_raw) to PNG stills and an mp4, independent of any window.
   overview_recorder.py --out DIR [--still-every 30] [--fps 8]"""
import argparse
import os
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class Rec(Node):
    def __init__(self, out, every, fps):
        super().__init__("overview_recorder")
        os.makedirs(out, exist_ok=True)
        self.out, self.every, self.fps = out, every, fps
        self.writer, self.t0, self.last_still, self.last_frame, self.n = None, time.time(), -1e9, 0.0, 0
        self.create_subscription(Image, "/overview/image_raw", self.cb, qos_profile_sensor_data)

    def cb(self, m):
        now = time.time()
        img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.width, 3)[:, :, ::-1].copy()
        if self.writer is None:
            self.writer = cv2.VideoWriter(os.path.join(self.out, "overview.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), self.fps, (m.width, m.height))
        if now - self.last_frame >= 1.0 / self.fps:
            self.writer.write(img); self.last_frame = now
        if now - self.last_still >= self.every:
            cv2.imwrite(os.path.join(self.out, "still_%04d.png" % self.n), img); self.n += 1; self.last_still = now
            self.get_logger().info(f"still {self.n}")

    def close(self):
        if self.writer: self.writer.release()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True)
    ap.add_argument("--still-every", type=float, default=30.0); ap.add_argument("--fps", type=float, default=8.0)
    a, _ = ap.parse_known_args()
    rclpy.init(); n = Rec(a.out, a.still_every, a.fps)
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    n.close()


if __name__ == "__main__":
    main()
