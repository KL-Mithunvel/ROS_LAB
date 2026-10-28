"""Patrol engine: all patrol decisions, with no ROS imports so it is tested on the laptop.

The ROS node (patrol_node.py) only feeds sensor data in and carries goals out.

Clocks: zone ages and goal cooldowns use `now`, the laptop clock. Sensor fusion uses the robot's
message timestamps, which are only ever compared with each other (dt), so a clock offset between
laptop and robot does not matter.
"""
import math
from dataclasses import dataclass
from enum import Enum

from .fusion import MotionFuser, ego_state
from .discovery import discover_zones
from .heatmap import ZoneMap, build_zones, dynamic_config
from .motion import CameraMotionDetector, LidarMotionDetector
from .priority import (TERMS, alert_outranks_goal, choose_next, explain, score_zones,
                       weights_from_dict)

# --- ROS domain guard ---------------------------------------------------------------------
SHARED_DOMAIN_ID = "155"                      # shared with another robot on the lab Wi-Fi: never use
DOMAIN_ENV, ALLOW_SHARED_ENV = "ROS_DOMAIN_ID", "BEETLE_ALLOW_SHARED_DOMAIN"
GOAL_YAW_MIN_DIST_M = 0.05                    # closer than this the travel direction is meaningless


def shared_domain_error(env):
    """Error text if `env` (os.environ-like) selects the shared domain without the override, else None."""
    if env.get(DOMAIN_ENV) == SHARED_DOMAIN_ID and env.get(ALLOW_SHARED_ENV) != "1":
        return (f"{DOMAIN_ENV}={SHARED_DOMAIN_ID} is shared with another robot; use 154 "
                f"(or set {ALLOW_SHARED_ENV}=1 to override)")
    return None


# --- pure geometry helpers ----------------------------------------------------------------
def wrap_angle(a):
    """Angle in (-pi, pi]."""
    return math.atan2(math.sin(a), math.cos(a))


def pose_jumped(prev, cur, max_m, max_rad):
    """True if pose `cur` (x, y, yaw) is further than max_m or max_rad from `prev` (None -> False)."""
    if prev is None:
        return False
    return (math.hypot(cur[0] - prev[0], cur[1] - prev[1]) > max_m
            or abs(wrap_angle(cur[2] - prev[2])) > max_rad)


def heading_to(from_xy, to_xy, fallback_yaw=0.0):
    """Yaw that faces `to_xy` from `from_xy`; `fallback_yaw` if they are (almost) the same point."""
    dx, dy = to_xy[0] - from_xy[0], to_xy[1] - from_xy[1]
    if math.hypot(dx, dy) < GOAL_YAW_MIN_DIST_M:
        return fallback_yaw
    return math.atan2(dy, dx)


def yaw_to_quaternion(yaw):
    """(z, w) of a rotation about the vertical axis (x = y = 0)."""
    return math.sin(yaw / 2), math.cos(yaw / 2)


# action_msgs/GoalStatus values (identical in Humble and Jazzy)
STATUS_EXECUTING, STATUS_SUCCEEDED, STATUS_CANCELED, STATUS_ABORTED = 2, 4, 5, 6
TERMINAL_NAMES = {STATUS_SUCCEEDED: "succeeded", STATUS_CANCELED: "canceled", STATUS_ABORTED: "aborted"}


def classify_goal_status(entries, goal_uuid):
    """Where is the goal `goal_uuid` according to the action status topic?

    `entries` is an iterable of (uuid, status) with uuid as bytes or a sequence of 16 ints and status an
    int. Returns 'active' (EXECUTING), 'succeeded', 'canceled', 'aborted', or None when the goal is not
    listed or is in a non-decisive state (accepted / canceling / unknown). The status topic is used
    because the NavigateToPose RESULT message differs between ROS distros (Humble laptop, Jazzy robot).
    """
    if goal_uuid is None:
        return None
    want = bytes(goal_uuid)
    for uuid, status in entries:
        if bytes(uuid) != want:
            continue
        if status == STATUS_EXECUTING:
            return "active"
        return TERMINAL_NAMES.get(status)
    return None


def goal_timed_out(now, sent_at, timeout_s):
    """True when a goal sent at `sent_at` has been in flight longer than `timeout_s` (<= 0 disables)."""
    return timeout_s > 0 and sent_at is not None and now - sent_at > timeout_s


class Mode(Enum):
    IDLE = "idle"
    MAPPING = "mapping"     # explore_lite is driving the robot to build the map
    PATROL = "patrol"
    ESTOP = "estop"


# Actions handle_command() asks the node to carry out (the node has the ROS handles, the engine does not).
CANCEL_GOALS, EXPLORE_ON, EXPLORE_OFF = "cancel_goals", "explore_on", "explore_off"
ARM, DISARM, SAVE_MAP = "arm", "disarm", "save_map"
START_RECORD, STOP_RECORD = "start_record", "stop_record"
SET_START = "set_start"       # node: re-anchor the zones at the current map-frame pose (engine.set_start)


@dataclass
class CommandResult:
    actions: list           # [(action, argument)] for the node, in order
    refused: str = None     # reason text if the command was refused (actions is then empty)


@dataclass
class GoTo:
    zone_id: str
    x: float
    y: float
    yaw: float = 0.0        # faces the direction of travel so the robot does not spin on arrival


@dataclass
class Decision:
    t: float
    chosen: str
    explanation: str
    scores: list    # list[ZoneScore], best first - the data behind the decision panel
    weights: dict = None   # normalised weights used for this decision


def decision_dict(d):
    """Plain-data form of a Decision (shared by status() and the /patrol/decision message)."""
    return {"t": d.t, "chosen": d.chosen, "explanation": d.explanation,
            "scores": [{"zone": s.zone_id, "total": s.total, "distance_m": s.distance_m,
                        "raw": s.raw, "contrib": s.contrib} for s in d.scores]}


class PatrolEngine:
    def __init__(self, settings, now):
        self.settings = settings
        self.weights = settings.priority.weight_obj()
        self.dynamic = dynamic_config(settings.zones)
        if self.dynamic.enabled:    # starts EMPTY: zone 1 is made at the first robot pose
            self.zonemap = ZoneMap([], now, settings.heatmap, self.dynamic,
                                   float(settings.zones.get("default_risk", 0.3)))
        else:
            self.zonemap = ZoneMap(build_zones(settings.zones), now, settings.heatmap)
        self.lidar = LidarMotionDetector(settings.lidar_motion)
        self.camera = CameraMotionDetector(settings.camera_motion)
        self.fuser = MotionFuser(settings.fusion)
        self.mode = Mode.IDLE
        self.replan_requested = False
        self.last_result = None
        self.last_decision = None          # the latest pick, even if no goal was sent for it
        self.sent_decision = None          # the pick for the goal actually sent to Nav2 (shown in status)
        self.active_zone = None            # zone of the goal in flight, set by goal_sent()
        self.scans_dropped = 0             # scans rejected by the pose-jump filter
        self._odom = (0.0, 0.0)            # linear, angular speed
        self._gyro_z = 0.0
        self._camera = (0.0, None)         # confidence, robot-clock timestamp
        self._cooldown_until = {}          # zone id -> laptop time until which it is skipped
        self._robot_xy = (0.0, 0.0)
        self._robot_yaw = 0.0
        self._last_scan_pose = None
        self._alerted_zone = None
        self._last_replan = -math.inf
        self._have_pose = False
        self._map = None                   # latest OccupancyInfo
        self._map_pending = False          # the zones may still grow from self._map
        self._last_map_processed = -math.inf

    # --- mode control -------------------------------------------------------------------
    def start_patrol(self):
        if self.mode is not Mode.ESTOP:
            self.mode = Mode.PATROL

    def pause(self):
        if self.mode in (Mode.PATROL, Mode.MAPPING):
            self.mode = Mode.IDLE

    def estop(self):
        self.mode = Mode.ESTOP

    def release_estop(self):
        if self.mode is Mode.ESTOP:
            self.mode = Mode.IDLE   # deliberate: the operator must press Start again

    def start_mapping(self):
        """Enter MAPPING (explore_lite drives). Refused in E-STOP. Returns True if entered."""
        if self.mode is Mode.ESTOP:
            return False
        self.mode = Mode.MAPPING
        return True

    def stop_mapping(self):
        if self.mode is Mode.MAPPING:
            self.mode = Mode.IDLE

    def arm_allowed(self):
        """Arming is refused while the E-STOP is latched."""
        return self.mode is not Mode.ESTOP

    def set_weights(self, values):
        """Validate, normalise and adopt new priority weights; they apply from the next goal.

        Raises ValueError (weights unchanged) if `values` is invalid.
        """
        self.weights = weights_from_dict(values)

    def handle_command(self, command):
        """Apply a parsed command (protocol.parse_command) to the mode; return what the node must do."""
        cmd = command["cmd"]
        was_mapping = self.mode is Mode.MAPPING
        if cmd == "start":
            if self.mode is Mode.ESTOP:
                return CommandResult([], "start refused: E-STOP is latched, release it first")
            self.start_patrol()
            actions = [(EXPLORE_OFF, None)] if was_mapping else []
            if self.settings.recording.auto_start:
                actions.append((START_RECORD, None))
            return CommandResult(actions)
        if cmd == "pause":
            self.pause()
            return CommandResult([(CANCEL_GOALS, None)] + ([(EXPLORE_OFF, None)] if was_mapping else []))
        if cmd == "estop":
            self.estop()
            return CommandResult([(CANCEL_GOALS, None), (EXPLORE_OFF, None), (DISARM, None)])
        if cmd == "release":
            self.release_estop()
            return CommandResult([])
        if cmd == "arm":
            if not self.arm_allowed():
                return CommandResult([], "arm refused: E-STOP is latched, release it first")
            return CommandResult([(ARM, None)])
        if cmd == "disarm":
            self.pause()
            return CommandResult([(CANCEL_GOALS, None), (EXPLORE_OFF, None), (DISARM, None)])
        if cmd == "explore_start":
            if not self.start_mapping():
                return CommandResult([], "explore refused: E-STOP is latched, release it first")
            return CommandResult([(CANCEL_GOALS, None), (EXPLORE_ON, None)])
        if cmd == "explore_stop":
            self.stop_mapping()
            return CommandResult([(EXPLORE_OFF, None), (CANCEL_GOALS, None)])
        if cmd == "save_map":
            return CommandResult([(SAVE_MAP, command.get("name"))])
        if cmd == "set_weights":
            try:
                self.set_weights(command["weights"])
            except ValueError as exc:
                return CommandResult([], str(exc))
            return CommandResult([])
        if cmd == "set_start":
            if not self.dynamic.enabled:
                return CommandResult([], "set_start refused: dynamic zones are disabled (zones.yaml)")
            if self.mode is not Mode.IDLE:
                return CommandResult([], f"set_start refused: mode is {self.mode.value}, must be idle")
            if not self._have_pose:
                return CommandResult([], "set_start refused: no robot pose in the map frame yet")
            return CommandResult([(SET_START, None)])
        if cmd == "record":
            return CommandResult([(START_RECORD, None)])
        if cmd == "stop_record":
            return CommandResult([(STOP_RECORD, None)])
        return CommandResult([], f"unknown command {cmd!r}")

    # --- sensor inputs ------------------------------------------------------------------
    def on_pose(self, now, map_xy, yaw=0.0):
        """Robot pose in the map frame. Marks the zone(s) the robot is in as visited (any mode).

        Dynamic zones: the first valid pose becomes the anchor (zone 1); afterwards the robot's own
        cell becomes a zone if it is new (the robot drove into a cell the map has not confirmed yet).
        """
        if not all(math.isfinite(v) for v in (map_xy[0], map_xy[1], yaw)):
            return
        self._robot_xy = map_xy
        self._robot_yaw = yaw
        self._have_pose = True
        if self.dynamic.enabled:
            if self.zonemap.anchor is None:
                self.zonemap.reset(map_xy, now)
                self._map_pending = True
            else:
                self.zonemap.ensure_zone_at(map_xy[0], map_xy[1], now)
            self._process_map(now)
        # Entering a box turns it green in EVERY mode (manual driving, mapping, patrol, even E-STOP when
        # the robot is pushed by hand): the heatmap records where the robot has been, not who drove it.
        self.zonemap.mark_visited(map_xy[0], map_xy[1], now)

    def set_start(self, x, y, now):
        """Re-anchor the dynamic zones: forget all zones; the cell centred on (x, y) becomes zone 1.
        The caller (handle_command) has already checked the mode; the goal state is reset here."""
        if not self.dynamic.enabled:
            raise RuntimeError("set_start: dynamic zones are disabled")
        self.zonemap.reset((x, y), now)
        self._cooldown_until.clear()
        self.last_decision = self.sent_decision = self.active_zone = self._alerted_zone = None
        self.replan_requested = False
        self._map_pending = True
        self._last_map_processed = -math.inf
        self._process_map(now)

    def on_map(self, info, now):
        """A new SLAM map (patrol.discovery.OccupancyInfo). Remembered always, processed at most every
        dynamic.map_update_s. Returns the zones created now (usually [])."""
        self._map = info
        self._map_pending = True
        return self._process_map(now)

    def _process_map(self, now):
        """Run zone discovery on the stored map if it is due and the zones may still grow."""
        if (not self.dynamic.enabled or self._map is None or not self._map_pending
                or self.zonemap.anchor is None
                or now - self._last_map_processed < self.dynamic.map_update_s):
            return []
        self._last_map_processed = now
        created = discover_zones(self._map, self.zonemap, self.dynamic, now,
                                 self._robot_xy if self._have_pose else None)
        self._map_pending = bool(created)      # a new ring may reveal the next one; else wait for a new map
        return created

    def on_odom(self, linear, angular):
        self._odom = (linear, angular)

    def on_imu(self, gyro_z):
        self._gyro_z = gyro_z

    def _ego(self):
        return ego_state(self.settings.fusion, self._odom[0], self._odom[1], self._gyro_z)

    def on_camera(self, gray, stamp):
        """Greyscale thumbnail from the camera; `stamp` is the robot-clock message time."""
        self._camera = (self.camera.update(gray, self._ego().moving), stamp)

    def on_scan(self, now, frame):
        """Run LiDAR + fusion on one scan whose `frame.pose` is the LASER pose in the MAP frame.

        Returns the FusedResult, or None if the scan was dropped because its pose jumped from the
        previous scan (localisation jump). After a drop the detector history is cleared, so the
        jump cannot show up as phantom "appeared" points. A warning raises an alert in its zone.
        """
        limits = self.settings.priority
        jumped = pose_jumped(self._last_scan_pose, frame.pose, limits.max_scan_jump_m, limits.max_scan_jump_rad)
        self._last_scan_pose = frame.pose
        if jumped:
            self.scans_dropped += 1
            self.lidar = LidarMotionDetector(self.settings.lidar_motion)
            return None
        detections = self.lidar.update(frame)
        result = self.fuser.update(frame.t, detections, self._camera[0], self._camera[1], self._ego())
        self.last_result = result
        if result.warning:
            self._alerted_zone = self.zonemap.record_alert(result.warning.x, result.warning.y, now)
            self.replan_requested = True   # should_cancel_active_goal() decides if it matters
        return result

    # --- goals --------------------------------------------------------------------------
    def _skip_ids(self, now):
        """Zones next_goal() must not pick: cooling down after a failure, or visited too recently."""
        skip = {z for z, until in self._cooldown_until.items() if until > now}
        skip |= {z.id for z in self.zonemap.zones
                 if self.zonemap.age_s(z.id, now) < self.settings.priority.min_revisit_s}
        return skip

    def next_goal(self, now):
        """Pick the next zone to patrol; None unless patrolling or if every zone is cooling down."""
        if self.mode is not Mode.PATROL:
            return None
        scores = score_zones(self.zonemap, self._robot_xy, now, self.weights)
        best = choose_next(scores, self._skip_ids(now))
        self.replan_requested = False
        if best is None:
            return None
        weights = {t: getattr(self.weights.normalised(), t) for t in TERMS}
        self.last_decision = Decision(now, best.zone_id, explain(best, scores), scores, weights)
        zone = self.zonemap.zone(best.zone_id)
        yaw = heading_to(self._robot_xy, (zone.cx, zone.cy), self._robot_yaw)
        return GoTo(zone.id, zone.cx, zone.cy, yaw)

    def goal_sent(self, goal):
        """The node really sent `goal` to Nav2: only now does it become the decision shown in status."""
        self.active_zone = goal.zone_id
        if self.last_decision is not None and self.last_decision.chosen == goal.zone_id:
            self.sent_decision = self.last_decision

    def should_cancel_active_goal(self, now):
        """Should the goal in flight (or one just accepted by Nav2) be cancelled right now?

        Yes when the mode is no longer PATROL (pause / E-STOP / explore), or when a motion alert
        in ANOTHER zone now outranks the goal's zone and the last re-plan was at least
        replan_min_interval_s ago. An alert that does not outrank the goal just clears the request,
        so the robot is not stopped and restarted for nothing.
        """
        if self.mode is not Mode.PATROL:
            return True
        if not self.replan_requested or self.active_zone is None:
            return False
        scores = score_zones(self.zonemap, self._robot_xy, now, self.weights)
        if not alert_outranks_goal(scores, self._alerted_zone, self.active_zone, self._skip_ids(now)):
            self.replan_requested = False
            return False
        if now - self._last_replan < self.settings.priority.replan_min_interval_s:
            return False        # keep the request; try again once the interval has passed
        self._last_replan = now
        return True

    def goal_cancelled(self):
        """The goal in flight was cancelled (pause / E-STOP / re-plan): neither a visit nor a failure."""
        self.active_zone = None

    def goal_finished(self, now, zone_id, success):
        """Nav2 reported back. Success counts as a visit; failure skips the zone for a while."""
        self.active_zone = None
        if success:
            zone = self.zonemap.zone(zone_id)
            self.zonemap.mark_visited(zone.cx, zone.cy, now)
        else:
            self._cooldown_until[zone_id] = now + self.settings.priority.failed_goal_cooldown_s

    def status(self, now):
        """Everything the GUI needs, as plain JSON-able data."""
        r = self.last_result
        d = self.sent_decision
        return {
            "mode": self.mode.value,
            "heatmap": self.zonemap.snapshot(now),
            "motion": None if r is None else {
                "lidar": r.lidar, "camera": r.camera, "fused": r.fused,
                "ego_moving": r.ego.moving, "ego_turning": r.ego.turning},
            "decision": None if d is None else decision_dict(d),
        }
