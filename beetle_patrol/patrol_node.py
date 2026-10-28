#!/usr/bin/python3
"""Beetle patrol node - runs on the LAPTOP, talks to the robot over ROS 2 (same ROS_DOMAIN_ID).

    source /opt/ros/humble/setup.bash && export ROS_DOMAIN_ID=154     # NOT 155 (shared with another robot)
    /usr/bin/python3 patrol_node.py

All decisions live in patrol/engine.py and messages in patrol/protocol.py; this file only moves data
in and out of ROS:
  in : /map (SLAM grid, grows the dynamic zones), /scan, /odometry/filtered, /imu/data, camera (compressed), /lyra/armed, tf (map <- laser, base_link)
  out: Nav2 NavigateToPose goals, /patrol/status (2 Hz), /patrol/warning, /patrol/decision (JSON, protocol v1),
       /explore/resume (std_msgs/Bool, starts/stops explore_lite)
  cmd: /patrol/command (std_msgs/String, parsed by protocol.parse_command): start | pause | estop |
       release | arm | disarm | explore_start | explore_stop | save_map | set_weights | record | stop_record |
       set_start (idle only: re-anchor the dynamic zones at the robot, that cell becomes zone 1)

E-STOP cancels ALL Nav2 goals (cancel-all service), stops explore_lite, calls the disarm service and
keeps streaming zero velocity until released. Arming is refused while the E-STOP is latched.
If the laptop link drops, Nav2 (which runs on the robot) finishes or aborts its current goal and
no new one is sent; this node cannot stop the robot over a dead link.

Startup refuses ROS_DOMAIN_ID=155 unless BEETLE_ALLOW_SHARED_DOMAIN=1.
"""
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import cv2
import json
import numpy as np
import rclpy
from action_msgs.msg import GoalStatus, GoalStatusArray
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import SaveMap
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from sensor_msgs.msg import CompressedImage, Imu, LaserScan
from std_srvs.srv import Trigger
from std_msgs.msg import Bool, String
from nav_msgs.msg import OccupancyGrid, Odometry
from tf2_ros import Buffer, TransformException, TransformListener

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from patrol import engine as eng  # noqa: E402
from patrol import protocol  # noqa: E402
from patrol.bag import BagRecorder  # noqa: E402
from patrol.config import load_settings  # noqa: E402
from patrol.discovery import OccupancyInfo  # noqa: E402
from patrol.engine import Mode, PatrolEngine, shared_domain_error  # noqa: E402
from patrol.motion import ScanFrame  # noqa: E402

THUMB_SIZE = (32, 24)       # camera frames are shrunk to this before differencing (cheap)
STATUS_HZ, LOOP_HZ, ESTOP_STREAM_HZ = 2.0, 5.0, 20.0
TF_TIMEOUT_S = 0.1          # how long a scan waits for its map <- laser transform
LOG_THROTTLE_S = 5.0        # repeated warnings / validation errors are logged at most this often
SERVICE_TIMEOUT_S = 5.0     # cancel-all / disarm / arm / save_map calls are given this long
EXPLORE_RESUME_TOPIC, ARMED_TOPIC = "/explore/resume", "/lyra/armed"
COMMAND_TOPIC = "/patrol/command"
# Nav2's cancel-all service is "<action name>/_action/cancel_goal"; an empty request cancels every goal.
CANCEL_ALL_SUFFIX = "/_action/cancel_goal"
# nav2_msgs/srv/SaveMap lives in Nav2's map_saver on the ROBOT; paths are robot-side.
SAVE_MAP_SERVICE = "/map_saver/save_map"
SAVE_MAP_DIR = "/home/veerobot/patrol_logs/maps"
SAVE_MAP_FORMAT, SAVE_MAP_MODE = "pgm", "trinary"
SAVE_MAP_FREE_THRESH, SAVE_MAP_OCCUPIED_THRESH = 0.25, 0.65   # map_saver_cli defaults
SAVE_MAP_HINT = "run on the robot: ros2 run nav2_map_server map_saver_cli -f ~/patrol_logs/maps/<name>"
# Testing only (default off): ignore get_result_async so completion must come from the status topic.
IGNORE_NAV_RESULT = os.environ.get("BEETLE_IGNORE_NAV_RESULT", "") not in ("", "0")
STATUS_SUFFIX = "/_action/status"
GOAL_NONE, GOAL_SENT, GOAL_ACTIVE, GOAL_CANCELLING = protocol.GOAL_STATES


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def stamp_s(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


class PatrolNode(Node):
    def __init__(self, settings):
        super().__init__("beetle_patrol")
        self.cfg = settings
        top = settings.topics
        self.engine = PatrolEngine(settings, self._now())
        self.recorder = BagRecorder(settings.recording, HERE)
        self._goal_handle = None
        self._goal_state = GOAL_NONE
        self._goal_seq = 0                  # bumps per goal so late callbacks of an old goal are ignored
        self._goal_sent_at = None
        self._last_status_entries = []      # [(uuid bytes, status)] from the action status topic
        self._armed = None                  # None until the first /lyra/armed message
        self._last_warning = None           # protocol warning dict
        self._pending_calls = []            # (future, deadline, what) of service calls being timed

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.nav = ActionClient(self, NavigateToPose, top.nav_action)

        # rclpy's action server publishes status RELIABLE + TRANSIENT_LOCAL (depth 1); depth 10 is compatible.
        # Goal completion is read from here, not from the result message (differs Humble vs Jazzy).
        status_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        latched_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                 durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(GoalStatusArray, top.nav_action + STATUS_SUFFIX, self._on_nav_status, status_qos)
        self.create_subscription(LaserScan, top.scan, self._on_scan, qos_profile_sensor_data)
        self.create_subscription(Odometry, top.odom, self._on_odom, 10)
        self.create_subscription(Imu, top.imu, lambda m: self.engine.on_imu(m.angular_velocity.z),
                                 qos_profile_sensor_data)
        self.create_subscription(CompressedImage, top.camera, self._on_camera, qos_profile_sensor_data)
        # slam_toolbox latches /map (reliable + transient local, depth 1)
        self.create_subscription(OccupancyGrid, top.map, self._on_map, latched_qos)
        self.create_subscription(Bool, ARMED_TOPIC, self._on_armed, 10)
        self.create_subscription(String, COMMAND_TOPIC, self._on_command, 10)

        self.pub_status = self.create_publisher(String, "/patrol/status", 10)
        self.pub_warning = self.create_publisher(String, "/patrol/warning", 10)
        self.pub_decision = self.create_publisher(String, "/patrol/decision", 10)
        self.pub_stop = self.create_publisher(Twist, top.nav_cmd_vel, 10)
        # latched, so explore_lite sees the last value even if it starts later
        self.pub_explore = self.create_publisher(Bool, EXPLORE_RESUME_TOPIC, latched_qos)
        self.disarm = self.create_client(Trigger, top.disarm_service)
        self.arm = self.create_client(Trigger, top.arm_service)
        self.cancel_all = self.create_client(CancelGoal, top.nav_action + CANCEL_ALL_SUFFIX)
        self.save_map_client = self.create_client(SaveMap, SAVE_MAP_SERVICE)

        self.create_timer(1.0 / LOOP_HZ, self._loop)
        self.create_timer(1.0 / STATUS_HZ, self._publish_status)
        self.create_timer(1.0 / ESTOP_STREAM_HZ, self._stream_stop)
        self.get_logger().info(f"patrol node up; zones: {len(self.engine.zonemap.zones)}")

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _lookup(self, target, source, stamp):
        """(x, y, yaw) of frame `source` in `target` at `stamp`, or None if tf is not available."""
        try:
            t = self.tf_buffer.lookup_transform(target, source, stamp, Duration(seconds=TF_TIMEOUT_S))
        except TransformException:
            return None
        p = t.transform
        return p.translation.x, p.translation.y, yaw_of(p.rotation)

    def _map_pose(self):
        """(x, y, yaw) of base_link in the map frame (latest), or None until SLAM/AMCL provides the tf."""
        top = self.cfg.topics
        try:
            t = self.tf_buffer.lookup_transform(top.map_frame, top.base_frame, rclpy.time.Time())
        except TransformException:
            return None
        p = t.transform
        return p.translation.x, p.translation.y, yaw_of(p.rotation)

    def _publish_json(self, publisher, message, validate, what):
        """Publish a protocol dict; a message that fails validation is logged (throttled), never fatal."""
        try:
            validate(message)
        except ValueError as exc:
            self.get_logger().error(f"outgoing {what} violates the protocol: {exc}",
                                    throttle_duration_sec=LOG_THROTTLE_S)
        publisher.publish(String(data=json.dumps(message)))

    # --- sensor callbacks -------------------------------------------------------------
    def _on_odom(self, msg):
        self.engine.on_odom(msg.twist.twist.linear.x, msg.twist.twist.angular.z)

    def _on_map(self, msg):
        """SLAM map -> engine (zone discovery). A map in another frame would put zones in the wrong place."""
        if msg.header.frame_id != self.cfg.topics.map_frame:
            self.get_logger().warning(f"map frame {msg.header.frame_id!r} != {self.cfg.topics.map_frame!r}; "
                                      "map ignored", throttle_duration_sec=LOG_THROTTLE_S)
            return
        info = msg.info
        try:
            occupancy = OccupancyInfo(info.width, info.height, info.resolution, info.origin.position.x,
                                      info.origin.position.y, np.array(msg.data, dtype=np.int8))
        except ValueError as exc:
            self.get_logger().warning(f"bad /map: {exc}", throttle_duration_sec=LOG_THROTTLE_S)
            return
        for zone in self.engine.on_map(occupancy, self._now()):
            self.get_logger().info(f"new zone {zone.n}: {zone.id}")

    def _on_armed(self, msg):
        self._armed = bool(msg.data)

    def _on_scan(self, msg):
        # The scan is placed at the LASER pose in the map frame, at the scan's own timestamp. Using
        # base_link would ignore the laser mounting (e.g. rotated 180 deg), and the odom frame
        # under-reads, so both would invent motion.
        laser_pose = self._lookup(self.cfg.topics.map_frame, msg.header.frame_id,
                                  rclpy.time.Time.from_msg(msg.header.stamp))
        if laser_pose is None:
            self.get_logger().warning(f"no transform {self.cfg.topics.map_frame} <- {msg.header.frame_id}; "
                                      "scan skipped", throttle_duration_sec=LOG_THROTTLE_S)
            return
        frame = ScanFrame(stamp_s(msg.header.stamp), laser_pose, np.asarray(msg.ranges, dtype=float),
                          msg.angle_min, msg.angle_increment, msg.range_min, msg.range_max)
        result = self.engine.on_scan(self._now(), frame)
        if result is None:
            self.get_logger().warning("scan dropped: pose jumped between frames (localisation jump?)",
                                      throttle_duration_sec=LOG_THROTTLE_S)
        elif result.warning:
            self._publish_warning(result.warning)

    def _publish_warning(self, w):
        zone = self.engine.zonemap.zone_at(w.x, w.y)
        warning = protocol.build_warning(self._now(), w.t, w.x, w.y, None if zone is None else zone.id,
                                         w.fused, w.lidar, w.camera, w.message)
        self._last_warning = warning
        self.get_logger().warning(w.message)
        self._publish_json(self.pub_warning, warning, protocol.validate_warning, "warning")

    def _on_camera(self, msg):
        gray = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            self.get_logger().warning("camera frame could not be decoded", throttle_duration_sec=10)
            return
        self.engine.on_camera(cv2.resize(gray, THUMB_SIZE, interpolation=cv2.INTER_AREA),
                              stamp_s(msg.header.stamp))

    # --- commands ---------------------------------------------------------------------
    def _on_command(self, msg):
        try:
            command = protocol.parse_command(msg.data)
        except ValueError as exc:
            self.get_logger().warning(f"bad command {msg.data!r}: {exc}")
            return
        result = self.engine.handle_command(command)
        if result.refused:
            self.get_logger().warning(result.refused)
            return
        for action, argument in result.actions:
            self._do_action(action, argument)

    def _do_action(self, action, argument):
        if action == eng.CANCEL_GOALS:
            self._cancel_all_goals()
        elif action == eng.EXPLORE_ON:
            self.pub_explore.publish(Bool(data=True))
        elif action == eng.EXPLORE_OFF:
            self.pub_explore.publish(Bool(data=False))
        elif action == eng.ARM:
            self._call_trigger(self.arm, "arm")
        elif action == eng.DISARM:
            self._call_trigger(self.disarm, "disarm")
        elif action == eng.SAVE_MAP:
            self._save_map(argument)
        elif action == eng.SET_START:
            self._set_start()
        elif action == eng.START_RECORD:
            self._start_recording()
        elif action == eng.STOP_RECORD:
            self.recorder.stop()

    def _set_start(self):
        pose = self._map_pose()
        if pose is None:
            self.get_logger().error("set_start: no map-frame robot pose")
            return
        self.engine.set_start(pose[0], pose[1], self._now())
        self.get_logger().info(f"zones re-anchored: zone 1 is centred on ({pose[0]:.2f}, {pose[1]:.2f})")

    def _start_recording(self):
        try:
            self.get_logger().info(f"recording bag to {self.recorder.start()}")
        except (RuntimeError, OSError) as exc:
            self.get_logger().error(f"cannot record: {exc}")

    def _call_trigger(self, client, what):
        """Fire a std_srvs/Trigger call; an unavailable service is an error, not a silent no-op."""
        if not client.service_is_ready():
            self.get_logger().error(f"{what} service {client.srv_name} not available")
            return
        self._watch(client.call_async(Trigger.Request()), what)

    def _watch(self, future, what):
        """Log the outcome of a service call, or an error if it takes longer than SERVICE_TIMEOUT_S."""
        self._pending_calls.append((future, self._now() + SERVICE_TIMEOUT_S, what))

    def _check_calls(self):
        still_pending = []
        for future, deadline, what in self._pending_calls:
            if future.done():
                self._report_call(what, future.result())
            elif self._now() > deadline:
                self.get_logger().error(f"{what}: no reply within {SERVICE_TIMEOUT_S:.0f} s")
            else:
                still_pending.append((future, deadline, what))
        self._pending_calls = still_pending

    def _report_call(self, what, reply):
        ok = getattr(reply, "success", getattr(reply, "result", True))
        text = f"{what}: {'ok' if ok else 'FAILED'}" + (f" ({reply.message})" if getattr(reply, "message", "") else "")
        (self.get_logger().info if ok else self.get_logger().error)(text)

    def _save_map(self, name):
        name = name or f"map_{datetime.now():%Y%m%d_%H%M%S}"
        if not self.save_map_client.service_is_ready():
            self.get_logger().error(f"save_map: service {SAVE_MAP_SERVICE} not available; {SAVE_MAP_HINT}")
            return
        req = SaveMap.Request()
        req.map_topic, req.map_url = "map", f"{SAVE_MAP_DIR}/{name}"
        req.image_format, req.map_mode = SAVE_MAP_FORMAT, SAVE_MAP_MODE
        req.free_thresh, req.occupied_thresh = SAVE_MAP_FREE_THRESH, SAVE_MAP_OCCUPIED_THRESH
        self._watch(self.save_map_client.call_async(req), f"save_map {req.map_url}")

    def _cancel_all_goals(self):
        """Cancel EVERY Nav2 goal (also ones this node does not know yet or that explore_lite sent)."""
        if self._goal_handle is not None:
            self._goal_state = GOAL_CANCELLING
        if self.cancel_all.service_is_ready():
            self.cancel_all.call_async(CancelGoal.Request())
        else:
            self.get_logger().error(f"{self.cancel_all.srv_name} not available - cancelling own goal only")
            self._cancel_goal()

    def _stream_stop(self):
        if self.engine.mode is Mode.ESTOP:
            self.pub_stop.publish(Twist())

    # --- patrol loop ------------------------------------------------------------------
    def _loop(self):
        self._check_calls()
        failure = self.recorder.failure()
        if failure:
            self.get_logger().error(failure)
        pose = self._map_pose()
        if pose is None:
            return
        now = self._now()
        self.engine.on_pose(now, pose[:2], pose[2])
        if self._goal_state == GOAL_ACTIVE and self.engine.should_cancel_active_goal(now):
            self._cancel_goal()     # paused / E-STOP / an alert elsewhere now outranks this goal
        if self._goal_state != GOAL_NONE and eng.goal_timed_out(
                now, self._goal_sent_at, self.cfg.priority.goal_timeout_s):
            self._timeout_goal()
        if self.engine.mode is Mode.PATROL and self._goal_state == GOAL_NONE:
            goal = self.engine.next_goal(now)
            if goal is not None:
                self._send_goal(goal)

    def _send_goal(self, goal):
        if not self.nav.server_is_ready():
            self.get_logger().warning("Nav2 action server not ready", throttle_duration_sec=LOG_THROTTLE_S)
            return
        msg = NavigateToPose.Goal()
        msg.pose = PoseStamped()
        msg.pose.header.frame_id = self.cfg.topics.map_frame
        msg.pose.header.stamp = self.get_clock().now().to_msg()
        msg.pose.pose.position.x, msg.pose.pose.position.y = goal.x, goal.y
        msg.pose.pose.orientation.z, msg.pose.pose.orientation.w = eng.yaw_to_quaternion(goal.yaw)
        self._goal_state = GOAL_SENT
        self._goal_seq += 1
        seq = self._goal_seq
        self._goal_sent_at = self._now()
        self.engine.goal_sent(goal)
        self.nav.send_goal_async(msg).add_done_callback(lambda f: self._on_goal_accepted(f, seq))
        decision = self.engine.sent_decision     # published only now that a goal really went out
        if decision is not None:
            self.get_logger().info(decision.explanation)
            message = protocol.build_decision(decision.t, decision.chosen, decision.explanation,
                                              decision.weights, eng.decision_dict(decision)["scores"])
            self._publish_json(self.pub_decision, message, protocol.validate_decision, "decision")

    def _on_goal_accepted(self, future, seq):
        handle = future.result()
        if seq != self._goal_seq or self._goal_state == GOAL_NONE:
            if handle.accepted:             # goal timed out / finished before the accept arrived: don't orphan it
                handle.cancel_goal_async()
            return
        if not handle.accepted:
            self._finish_goal(GoalStatus.STATUS_ABORTED)
            return
        self._goal_handle = handle
        if self._goal_state == GOAL_SENT:
            self._goal_state = GOAL_ACTIVE
        if not IGNORE_NAV_RESULT:           # bonus signal; may never arrive across distros
            handle.get_result_async().add_done_callback(lambda f: self._on_result(f, seq))
        self._check_status()                # the terminal status may already have been published
        if self._goal_handle is not None and self.engine.should_cancel_active_goal(self._now()):
            # Pause / E-STOP may have happened while Nav2 was still accepting the goal.
            self._cancel_goal()

    def _on_result(self, future, seq):
        if seq == self._goal_seq and self._goal_state != GOAL_NONE:
            self._finish_goal(future.result().status)

    def _on_nav_status(self, msg):
        self._last_status_entries = [(bytes(s.goal_info.goal_id.uuid), s.status) for s in msg.status_list]
        self._check_status()

    def _check_status(self):
        if self._goal_handle is None or self._goal_state == GOAL_NONE:
            return
        uuid = bytes(self._goal_handle.goal_id.uuid)
        state = eng.classify_goal_status(self._last_status_entries, uuid)
        if state == "active":
            if self._goal_state == GOAL_SENT:
                self._goal_state = GOAL_ACTIVE
        elif state is not None:
            code = {"succeeded": GoalStatus.STATUS_SUCCEEDED, "canceled": GoalStatus.STATUS_CANCELED,
                    "aborted": GoalStatus.STATUS_ABORTED}[state]
            self._finish_goal(code)

    def _cancel_goal(self):
        if self._goal_handle is not None:
            if self._goal_state != GOAL_CANCELLING:
                self._goal_sent_at = self._now()    # the timeout now bounds the cancel itself
            self._goal_state = GOAL_CANCELLING
            self._goal_handle.cancel_goal_async()

    def _timeout_goal(self):
        """Safety net: no terminal status in time. Cancel and count it as a failure (zone cooldown)."""
        cancelling = self._goal_state == GOAL_CANCELLING
        self.get_logger().warning(f"goal to {self.engine.active_zone} timed out "
                                  f"({self.cfg.priority.goal_timeout_s:.0f} s); cancelling")
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
        self._finish_goal(GoalStatus.STATUS_CANCELED if cancelling else GoalStatus.STATUS_ABORTED)

    def _finish_goal(self, status):
        """Idempotent: the first of status topic / result / timeout wins, later signals are ignored."""
        if self._goal_state == GOAL_NONE:
            return
        zone = self.engine.active_zone
        self._goal_handle, self._goal_state, self._goal_sent_at = None, GOAL_NONE, None
        self._goal_seq += 1
        if zone is None:
            return
        if status == GoalStatus.STATUS_CANCELED:
            self.engine.goal_cancelled()
            return
        success = status == GoalStatus.STATUS_SUCCEEDED
        self.engine.goal_finished(self._now(), zone, success)
        if not success:
            self.get_logger().warning(f"goal to {zone} failed; skipping it for a while")

    def _publish_status(self):
        pose = self._map_pose()
        extras = {
            "armed": self._armed,
            "nav_ready": self.nav.server_is_ready(),
            "explore_active": self.engine.mode is Mode.MAPPING,
            "robot": None if pose is None else {"x": pose[0], "y": pose[1], "yaw": pose[2]},
            "goal_zone": self.engine.active_zone,
            "goal_state": self._goal_state,
            "last_warning": self._last_warning,
            "recording": self.recorder.recording,
            "bag_dir": str(self.recorder.out_dir) if self.recorder.out_dir else None,
        }
        status = protocol.status_from_engine(self.engine, self._now(), extras)
        self._publish_json(self.pub_status, status, protocol.validate_status, "status")

    def shutdown(self):
        self._cancel_goal()
        self.recorder.stop()


def main():
    error = shared_domain_error(os.environ)
    if error:
        print(f"patrol_node: {error}", file=sys.stderr)
        sys.exit(1)
    rclpy.init()
    node = PatrolNode(load_settings())
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
