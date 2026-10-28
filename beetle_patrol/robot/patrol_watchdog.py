#!/usr/bin/env python3
"""Robot-side dead-man watchdog. NEVER arms anything.

Heartbeat: std_msgs/String on /patrol/status (from the laptop patrol node).
When /lyra/armed is True and the heartbeat is silent > timeout, once per outage:
  cancel_goals  -> /navigate_to_pose/_action/cancel_goal (CancelGoal, empty request = all goals)
  pause_explore -> Bool False on /explore/resume
  disarm        -> Trigger /lyra/disarm
"""
import os
import sys
import time

import rclpy
from rclpy.node import Node
from action_msgs.srv import CancelGoal
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from watchdog_logic import WatchdogLogic, CANCEL, PAUSE, DISARM  # noqa: E402


class PatrolWatchdog(Node):
    def __init__(self):
        super().__init__('patrol_watchdog')
        self.declare_parameter('timeout_s', 2.0)
        self.declare_parameter('check_hz', 4.0)
        self.logic = WatchdogLogic(float(self.get_parameter('timeout_s').value))
        self.armed = False
        self.create_subscription(String, '/patrol/status', self.on_beat, 10)
        self.create_subscription(Bool, '/lyra/armed', self.on_armed, 10)
        self.resume_pub = self.create_publisher(Bool, '/explore/resume', 10)
        self.cancel_cli = self.create_client(CancelGoal, '/navigate_to_pose/_action/cancel_goal')
        self.disarm_cli = self.create_client(Trigger, '/lyra/disarm')
        self.create_timer(1.0 / float(self.get_parameter('check_hz').value), self.tick)
        self.get_logger().info('watchdog up (never arms)')

    def on_beat(self, _msg):
        self.logic.feed(time.monotonic())

    def on_armed(self, msg):
        self.armed = bool(msg.data)

    def tick(self):
        actions = self.logic.check(time.monotonic(), self.armed)
        if not actions:
            return
        self.get_logger().warn(f'heartbeat lost while armed -> {actions}')
        if CANCEL in actions:
            # empty request (zero goal id, zero stamp) = cancel ALL goals
            self.cancel_cli.call_async(CancelGoal.Request())
        if PAUSE in actions:
            self.resume_pub.publish(Bool(data=False))
        if DISARM in actions:
            self.disarm_cli.call_async(Trigger.Request())


def main():
    rclpy.init()
    node = PatrolWatchdog()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == '__main__':
    main()
