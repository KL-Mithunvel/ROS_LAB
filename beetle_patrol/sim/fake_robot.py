#!/usr/bin/python3
"""Fake BeetleBot for laptop-only testing: publishes the same topics as the real robot.

    sim/run_sim.sh --mode fake_nav     # + NavigateToPose server, /map, map->odom tf
    sim/run_sim.sh --mode base         # sensors, odom, tf odom->base_link->laser, arm/disarm only

Like the real cmd_vel_gate the robot moves ONLY from /cmd_vel_nav and ONLY while armed.
Run it via run_sim.sh, which forces ROS_DOMAIN_ID=77 and ROS_LOCALHOST_ONLY=1.
"""
import argparse
import math
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
import yaml
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.duration import Duration
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data)
from sensor_msgs.msg import CompressedImage, Imu, LaserScan
from std_msgs.msg import Bool
from std_srvs.srv import Trigger
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from world import (CameraConfig, DiffDrive, IntruderConfig, LidarConfig, RobotConfig, RoomConfig,  # noqa: E402
                   World, make, wrap_angle)

SCAN_STAMP_LAG_S = 0.05
ALLOWED_TOP = {"seed", "room", "lidar", "robot", "mount", "tf", "rates", "camera", "intruder", "nav", "topics"}


def quat_yaw(yaw):
    return 0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2)


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def load_config(path):
    cfg = yaml.safe_load(Path(path).read_text()) or {}
    unknown = set(cfg) - ALLOWED_TOP
    if unknown:
        raise ValueError(f"sim.yaml: unknown top-level keys {sorted(unknown)}")
    patrol_yaml = yaml.safe_load((HERE.parent / "patrol.yaml").read_text())
    topics = dict(patrol_yaml["topics"])
    topics.update(cfg.get("topics") or {})       # optional override in sim.yaml
    cfg["topics"] = topics
    return cfg


class FakeRobot(Node):
    def __init__(self, cfg, mode):
        super().__init__("fake_robot")
        self.mode = mode
        self.cfg = cfg
        self.topics = cfg["topics"]
        self.lock = threading.Lock()
        rb, mount, tfc, rates = cfg.get("robot", {}), cfg.get("mount", {}), cfg.get("tf", {}), cfg.get("rates", {})
        self.cmd_timeout = rb.pop("cmd_timeout_s", 0.5)
        self.physics_hz = rb.pop("physics_hz", 50.0)
        self.robot_cfg = make(RobotConfig, rb)
        self.world = World(make(RoomConfig, cfg.get("room")), make(LidarConfig, cfg.get("lidar")),
                           make(IntruderConfig, cfg.get("intruder")), make(CameraConfig, cfg.get("camera")),
                           seed=cfg.get("seed", 0))
        self.body = DiffDrive(self.robot_cfg)
        self.laser_yaw = math.pi if mount.get("laser_flipped", True) else 0.0
        self.laser_xyz = mount.get("laser_xyz", [0.10, 0.0, 0.15])
        self.map_odom = tfc.get("map_odom_offset", [0.0, 0.0, 0.0]) if mode == "fake_nav" else [0.0, 0.0, 0.0]
        self.armed = False
        self.cmd = (0.0, 0.0)
        self.cmd_time = 0.0
        self.t0 = time.monotonic()
        self.prev_v = 0.0

        top = self.topics
        self.pub_scan = self.create_publisher(LaserScan, top["scan"], qos_profile_sensor_data)
        self.pub_odom = self.create_publisher(Odometry, top["odom"], 10)
        self.pub_imu = self.create_publisher(Imu, top["imu"], qos_profile_sensor_data)
        self.pub_cam = self.create_publisher(CompressedImage, top["camera"], qos_profile_sensor_data)
        self.pub_armed = self.create_publisher(Bool, "/lyra/armed", 10)
        self.create_subscription(Twist, top["nav_cmd_vel"], self._on_cmd, 10)
        self.create_service(Trigger, top["arm_service"], self._arm)
        self.create_service(Trigger, top["disarm_service"], self._disarm)

        self.tf = TransformBroadcaster(self)
        self.static_tf = StaticTransformBroadcaster(self)
        self._publish_static_tf()

        self.create_timer(1.0 / self.physics_hz, self._physics)
        self.create_timer(1.0 / self.world.lidar.rate_hz, self._pub_scan)
        self.create_timer(1.0 / self.world.camera.rate_hz, self._pub_camera)
        self.create_timer(1.0 / rates.get("imu_hz", 50.0), self._pub_imu)
        self.create_timer(1.0 / rates.get("odom_hz", 30.0), self._pub_odom_tf)
        self.create_timer(1.0 / rates.get("armed_hz", 10.0), self._pub_armed)
        self.get_logger().info(f"fake robot up, mode={mode}, laser_yaw={math.degrees(self.laser_yaw):.0f} deg")

    # --- time / frames ---
    def sim_t(self):
        return time.monotonic() - self.t0

    def _map_to_odom(self, x, y, yaw):
        """Ground-truth map pose -> odom-frame pose, so that map->odom composed with odom->base_link
        reproduces the truth exactly. T_map_odom is the configured offset (identity by default)."""
        ox, oy, oyaw = self.map_odom
        dx, dy = x - ox, y - oy
        c, s = math.cos(-oyaw), math.sin(-oyaw)
        return c * dx - s * dy, s * dx + c * dy, wrap_angle(yaw - oyaw)

    def _tf_msg(self, parent, child, xyz, yaw, stamp):
        m = TransformStamped()
        m.header.stamp, m.header.frame_id, m.child_frame_id = stamp, parent, child
        m.transform.translation.x, m.transform.translation.y, m.transform.translation.z = map(float, xyz)
        q = quat_yaw(yaw)
        m.transform.rotation.x, m.transform.rotation.y, m.transform.rotation.z, m.transform.rotation.w = q
        return m

    def _publish_static_tf(self):
        stamp = self.get_clock().now().to_msg()
        self.static_tf.sendTransform(self._tf_msg("base_link", "laser", self.laser_xyz, self.laser_yaw, stamp))

    # --- commands ---
    def _on_cmd(self, msg):
        with self.lock:
            self.cmd = (msg.linear.x, msg.angular.z)
            self.cmd_time = time.monotonic()

    def _arm(self, _req, res):
        self.armed = True
        res.success, res.message = True, "armed (sim)"
        self.get_logger().info("ARMED")
        return res

    def _disarm(self, _req, res):
        self.armed = False
        with self.lock:
            self.cmd = (0.0, 0.0)
        res.success, res.message = True, "disarmed (sim)"
        self.get_logger().info("DISARMED")
        return res

    def effective_cmd(self):
        with self.lock:
            v, w = self.cmd
            fresh = time.monotonic() - self.cmd_time < self.cmd_timeout
        return (v, w) if (self.armed and fresh) else (0.0, 0.0)

    # --- physics ---
    def _physics(self):
        dt = 1.0 / self.physics_hz
        v, w = self.effective_cmd()
        with self.lock:
            self.body.step(v, w, dt)
            x, y, touched = self.world.clamp_to_room(self.body.x, self.body.y, self.robot_cfg.radius)
            if touched:
                self.body.x, self.body.y, self.body.v = x, y, 0.0

    def _pose(self):
        with self.lock:
            return self.body.pose, self.body.v, self.body.w

    # --- publishers ---
    def _pub_armed(self):
        self.pub_armed.publish(Bool(data=self.armed))

    def _laser_pose(self, pose):
        x, y, yaw = pose
        lx, ly, _ = self.laser_xyz
        return (x + lx * math.cos(yaw) - ly * math.sin(yaw), y + lx * math.sin(yaw) + ly * math.cos(yaw),
                yaw + self.laser_yaw)

    def _pub_scan(self):
        pose, _, _ = self._pose()
        lc = self.world.lidar
        msg = LaserScan()
        # a real driver stamps a scan at acquisition time, i.e. slightly in the past; this also keeps the
        # stamp inside the range of tf we have already published (no "extrapolation into the future")
        acquired = self.get_clock().now() - Duration(seconds=SCAN_STAMP_LAG_S)
        msg.header.stamp, msg.header.frame_id = acquired.to_msg(), "laser"
        msg.angle_min, msg.angle_max = lc.angle_min, lc.angle_min + (lc.n_beams - 1) * lc.angle_increment
        msg.angle_increment = lc.angle_increment
        msg.scan_time, msg.time_increment = 1.0 / lc.rate_hz, 1.0 / lc.rate_hz / lc.n_beams
        msg.range_min, msg.range_max = lc.range_min, lc.range_max
        msg.ranges = self.world.scan(self._laser_pose(pose), self.sim_t()).astype(np.float32).tolist()
        self.pub_scan.publish(msg)

    def _pub_camera(self):
        pose, _, _ = self._pose()
        img = self.world.image(pose, self.sim_t())
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.world.camera.jpeg_quality])
        if not ok:
            self.get_logger().error("jpeg encode failed")
            return
        msg = CompressedImage()
        msg.header.stamp, msg.header.frame_id = self.get_clock().now().to_msg(), "camera"
        msg.format, msg.data = "jpeg", buf.tobytes()
        self.pub_cam.publish(msg)

    def _pub_imu(self):
        pose, v, w = self._pose()
        dt = 1.0 / self.cfg.get("rates", {}).get("imu_hz", 50.0)
        accel, self.prev_v = (v - self.prev_v) / dt, v
        msg = Imu()
        msg.header.stamp, msg.header.frame_id = self.get_clock().now().to_msg(), "base_link"
        msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w = quat_yaw(pose[2])
        msg.angular_velocity.z = float(w + self.world.rng.normal(0, 0.002))
        msg.linear_acceleration.x = float(accel)
        msg.linear_acceleration.z = 9.81
        self.pub_imu.publish(msg)

    def _pub_odom_tf(self):
        pose, v, w = self._pose()
        ox, oy, oyaw = self._map_to_odom(*pose)
        stamp = self.get_clock().now().to_msg()
        odom = Odometry()
        odom.header.stamp, odom.header.frame_id, odom.child_frame_id = stamp, "odom", "base_link"
        odom.pose.pose.position.x, odom.pose.pose.position.y = ox, oy
        (odom.pose.pose.orientation.x, odom.pose.pose.orientation.y,
         odom.pose.pose.orientation.z, odom.pose.pose.orientation.w) = quat_yaw(oyaw)
        odom.twist.twist.linear.x, odom.twist.twist.angular.z = v, w
        self.pub_odom.publish(odom)
        transforms = [self._tf_msg("odom", "base_link", (ox, oy, 0.0), oyaw, stamp)]
        if self.mode == "fake_nav":
            mx, my, myaw = self.map_odom
            transforms.append(self._tf_msg("map", "odom", (mx, my, 0.0), myaw, stamp))
        self.tf.sendTransform(transforms)


class FakeNav(FakeRobot):
    """fake_nav mode: adds /map, the NavigateToPose action (drives straight at the goal) and its cancel."""

    def __init__(self, cfg):
        super().__init__(cfg, "fake_nav")
        from nav2_msgs.action import NavigateToPose
        from rclpy.action import ActionServer, CancelResponse
        self.nav_cfg = cfg.get("nav", {})
        self.pub_cmd = self.create_publisher(Twist, self.topics["nav_cmd_vel"], 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.pub_map = self.create_publisher(OccupancyGrid, "/map", latched)
        self.pub_map.publish(self._make_map())
        self.nav_group = ReentrantCallbackGroup()
        self.server = ActionServer(self, NavigateToPose, self.topics["nav_action"], self._execute,
                                   cancel_callback=lambda _g: CancelResponse.ACCEPT,
                                   callback_group=self.nav_group)

    def _make_map(self):
        n = self.nav_cfg
        res, margin = n.get("map_resolution", 0.05), n.get("map_margin_m", 0.5)
        hx, hy = self.world.room.half_x, self.world.room.half_y
        w, h = int(round((2 * hx + 2 * margin) / res)), int(round((2 * hy + 2 * margin) / res))
        ox, oy = -hx - margin, -hy - margin
        grid = np.full((h, w), -1, dtype=np.int8)
        xs = ox + (np.arange(w) + 0.5) * res
        ys = oy + (np.arange(h) + 0.5) * res
        gx, gy = np.meshgrid(xs, ys)
        grid[(np.abs(gx) < hx) & (np.abs(gy) < hy)] = 0
        wall = (np.abs(gx) >= hx - res) & (np.abs(gx) < hx + res) & (np.abs(gy) < hy + res)
        wall |= (np.abs(gy) >= hy - res) & (np.abs(gy) < hy + res) & (np.abs(gx) < hx + res)
        grid[wall] = 100
        for xmin, xmax, ymin, ymax in self.world._static_boxes:
            grid[(gx >= xmin) & (gx <= xmax) & (gy >= ymin) & (gy <= ymax)] = 100
        msg = OccupancyGrid()
        msg.header.stamp, msg.header.frame_id = self.get_clock().now().to_msg(), "map"
        msg.info.resolution, msg.info.width, msg.info.height = res, w, h
        msg.info.origin.position.x, msg.info.origin.position.y, msg.info.origin.orientation.w = ox, oy, 1.0
        msg.data = grid.ravel().tolist()
        return msg

    def _execute(self, goal_handle):
        from nav2_msgs.action import NavigateToPose
        n = self.nav_cfg
        p = goal_handle.request.pose.pose.position
        gx, gy = p.x, p.y
        result = NavigateToPose.Result()
        margin = n.get("margin_m", 0.2)
        hx, hy = self.world.room.half_x, self.world.room.half_y
        if abs(gx) > hx - margin or abs(gy) > hy - margin:
            self.get_logger().warning(f"goal ({gx:.2f},{gy:.2f}) outside the room - aborting")
            goal_handle.abort()
            return result
        self.get_logger().info(f"goal accepted: ({gx:.2f}, {gy:.2f})")
        t_start = time.monotonic()
        disarmed_since = None
        feedback = NavigateToPose.Feedback()
        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                self.pub_cmd.publish(Twist())
                goal_handle.canceled()
                self.get_logger().info("goal cancelled")
                return result
            (x, y, yaw), _, _ = self._pose()
            dist = math.hypot(gx - x, gy - y)
            if dist <= n.get("xy_tolerance", 0.15):
                self.pub_cmd.publish(Twist())
                goal_handle.succeed()
                self.get_logger().info("goal reached")
                return result
            if time.monotonic() - t_start > n.get("goal_timeout_s", 90.0):
                goal_handle.abort()
                return result
            if self.armed:
                disarmed_since = None
            else:
                disarmed_since = disarmed_since or time.monotonic()
                if time.monotonic() - disarmed_since > n.get("disarmed_abort_s", 3.0):
                    self.get_logger().warning("robot disarmed during goal - aborting")
                    goal_handle.abort()
                    return result
            err = wrap_angle(math.atan2(gy - y, gx - x) - yaw)
            tw = Twist()
            tw.angular.z = float(np.clip(2.0 * err, -n.get("max_ang_speed", 1.0), n.get("max_ang_speed", 1.0)))
            tw.linear.x = 0.0 if abs(err) > 0.5 else float(min(n.get("max_lin_speed", 0.3), dist))
            self.pub_cmd.publish(tw)
            feedback.distance_remaining = float(dist)
            feedback.current_pose.header.frame_id = "map"
            feedback.current_pose.pose.position.x, feedback.current_pose.pose.position.y = x, y
            goal_handle.publish_feedback(feedback)
            time.sleep(0.05)
        goal_handle.abort()
        return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fake_nav", "base"], default="fake_nav")
    ap.add_argument("--config", default=str(HERE / "sim.yaml"))
    args = ap.parse_args()
    cfg = load_config(args.config)
    rclpy.init()
    node = FakeNav(cfg) if args.mode == "fake_nav" else FakeRobot(cfg, "base")
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
