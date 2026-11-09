#!/usr/bin/env python3
"""Walks the red 'intruder' box through the warehouse so the patrol's motion warning has something to find.
Teleports the Gazebo model along a path at constant speed (gazebo_msgs/SetEntityState). Starts after --delay s
of sim time, enters through the east door, loops the north half of the floor, then leaves and parks outside."""
import argparse
import math

import rclpy
from gazebo_msgs.srv import SetEntityState
from rclpy.node import Node

PATH = [(13.8, 4.5), (10.8, 4.5), (10.8, 7.8), (7.9, 7.8), (7.9, 4.5), (10.8, 4.5), (13.8, 4.5)]


class Intruder(Node):
    def __init__(self, delay, speed, repeat):
        super().__init__("intruder")
        self.delay, self.speed, self.repeat = delay, speed, repeat
        self.cli = self.create_client(SetEntityState, "/set_entity_state")
        self.t0 = self.get_clock().now()
        self.seg, self.pos, self.pause_until = 0, list(PATH[0]), None
        self.create_timer(0.05, self.tick)

    def tick(self):
        now = self.get_clock().now()
        t = (now - self.t0).nanoseconds * 1e-9
        if t < self.delay or not self.cli.service_is_ready():
            return
        if self.seg >= len(PATH) - 1:
            if self.repeat and t > self.delay + self.repeat:       # go again after `repeat` s
                self.seg, self.delay = 0, t
            return
        tx, ty = PATH[self.seg + 1]
        dx, dy = tx - self.pos[0], ty - self.pos[1]
        d = math.hypot(dx, dy)
        step = self.speed * 0.05
        if d <= step:
            self.pos = [tx, ty]; self.seg += 1
        else:
            self.pos = [self.pos[0] + dx / d * step, self.pos[1] + dy / d * step]
        req = SetEntityState.Request()
        req.state.name = "intruder"
        req.state.pose.position.x, req.state.pose.position.y, req.state.pose.position.z = self.pos[0], self.pos[1], 0.85
        req.state.pose.orientation.w = 1.0
        req.state.reference_frame = "world"
        self.cli.call_async(req)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=60.0)
    ap.add_argument("--speed", type=float, default=0.6)
    ap.add_argument("--repeat", type=float, default=0.0, help="start another walk this many s after the last one ends (0 = once)")
    a, _ = ap.parse_known_args()
    rclpy.init()
    rclpy.spin(Intruder(a.delay, a.speed, a.repeat))


if __name__ == "__main__":
    main()
