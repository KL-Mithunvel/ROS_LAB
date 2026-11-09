#!/usr/bin/env python3
"""Arm/disarm gate, like the real robot's: /cmd_vel (Nav2 + teleop after the velocity smoother) -> /cmd_vel_gated
(what Gazebo drives on) ONLY while armed. Starts DISARMED. A command older than 0.5 s counts as zero.
Provides /lyra/arm, /lyra/disarm (std_srvs/Trigger) and publishes /lyra/armed (Bool, 10 Hz)."""
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool
from std_srvs.srv import Trigger

TIMEOUT_S = 0.5


class Gate(Node):
    def __init__(self):
        super().__init__("lyra_gate")
        self.use_sim = self.get_parameter("use_sim_time").value
        self.armed, self.cmd, self.t_cmd = False, Twist(), None
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd, 10)
        self.out = self.create_publisher(Twist, "/cmd_vel_gated", 10)
        self.pub_armed = self.create_publisher(Bool, "/lyra/armed", 10)
        self.create_service(Trigger, "/lyra/arm", lambda q, r: self.set_armed(True, r))
        self.create_service(Trigger, "/lyra/disarm", lambda q, r: self.set_armed(False, r))
        self.create_timer(0.05, self.tick)
        self.create_timer(0.1, lambda: self.pub_armed.publish(Bool(data=self.armed)))

    def set_armed(self, value, resp):
        self.armed = value
        if not value:
            self.out.publish(Twist())
        resp.success, resp.message = True, "armed" if value else "disarmed"
        self.get_logger().info(resp.message)
        return resp

    def on_cmd(self, msg):
        self.cmd, self.t_cmd = msg, self.get_clock().now()

    def tick(self):
        fresh = self.t_cmd is not None and (self.get_clock().now() - self.t_cmd).nanoseconds * 1e-9 < TIMEOUT_S
        self.out.publish(self.cmd if (self.armed and fresh) else Twist())


def main():
    rclpy.init()
    rclpy.spin(Gate())


if __name__ == "__main__":
    main()
