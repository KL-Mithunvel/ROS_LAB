"""Pure logic added for the patrol node: commands, modes, cancel/replan rules, goal yaw, scan filter,
bag failures, domain guard. Uses a fixed grid, not the shipped zones.yaml."""
import math
import sys

import pytest

from patrol import engine as eng
from patrol import protocol
from patrol.bag import BagRecorder, RecordingConfig
from patrol.config import load_settings
from patrol.engine import Mode, PatrolEngine
from patrol.heatmap import HeatmapConfig
from patrol.motion import ScanFrame
from patrol.priority import alert_outranks_goal, score_zones, weights_from_dict
from test_engine_bag import room_scan


@pytest.fixture
def engine():
    s = load_settings()
    s.zones = {"grid": {"origin": [0, 0], "rows": 3, "cols": 4, "cell_w": 1.5, "cell_h": 1.5},
               "default_risk": 0.3, "risk": {}}
    s.heatmap = HeatmapConfig(visit_radius_m=1.2, max_age_s=300.0, alert_memory_s=120.0)
    s.priority.min_revisit_s = 30.0
    s.priority.replan_min_interval_s = 5.0
    s.recording.auto_start = False
    return PatrolEngine(s, now=0.0)


def run(engine, text):
    return engine.handle_command(protocol.parse_command(text))


def actions(result):
    return [a for a, _ in result.actions]


# --- domain guard -------------------------------------------------------------------------------
def test_shared_domain_is_refused_unless_overridden():
    assert "154" in eng.shared_domain_error({"ROS_DOMAIN_ID": "155"})
    assert eng.shared_domain_error({"ROS_DOMAIN_ID": "155", "BEETLE_ALLOW_SHARED_DOMAIN": "1"}) is None
    assert eng.shared_domain_error({"ROS_DOMAIN_ID": "154"}) is None
    assert eng.shared_domain_error({}) is None


# --- commands and modes -------------------------------------------------------------------------
def test_estop_cancels_everything_stops_explore_and_disarms(engine):
    r = run(engine, "estop")
    assert actions(r) == [eng.CANCEL_GOALS, eng.EXPLORE_OFF, eng.DISARM]
    assert engine.mode is Mode.ESTOP


def test_arm_is_refused_in_estop_and_allowed_otherwise(engine):
    assert actions(run(engine, "arm")) == [eng.ARM]
    run(engine, "estop")
    refused = run(engine, "arm")
    assert refused.refused and refused.actions == []
    run(engine, "release")
    assert actions(run(engine, "arm")) == [eng.ARM]


def test_disarm_stops_patrol_and_disarms(engine):
    run(engine, "start")
    assert eng.DISARM in actions(run(engine, "disarm")) and engine.mode is Mode.IDLE


def test_explore_start_enters_mapping_and_explore_stop_or_pause_leave_it(engine):
    r = run(engine, "explore_start")
    assert engine.mode is Mode.MAPPING and eng.EXPLORE_ON in actions(r)
    run(engine, "explore_stop")
    assert engine.mode is Mode.IDLE
    run(engine, "explore_start")
    r = run(engine, "pause")
    assert engine.mode is Mode.IDLE and eng.EXPLORE_OFF in actions(r)


def test_start_from_mapping_stops_explore_and_patrol_blocks_no_goal_while_mapping(engine):
    run(engine, "explore_start")
    assert engine.next_goal(100.0) is None
    r = run(engine, "start")
    assert engine.mode is Mode.PATROL and eng.EXPLORE_OFF in actions(r)


def test_explore_and_start_refused_in_estop(engine):
    run(engine, "estop")
    assert run(engine, "explore_start").refused and engine.mode is Mode.ESTOP
    assert run(engine, "start").refused and engine.mode is Mode.ESTOP


def test_start_records_only_when_auto_start(engine):
    assert eng.START_RECORD not in actions(run(engine, "start"))
    engine.settings.recording.auto_start = True
    assert eng.START_RECORD in actions(run(engine, "start"))


def test_save_map_record_and_stop_record_map_to_actions(engine):
    r = engine.handle_command(protocol.parse_command('{"cmd": "save_map", "name": "lab"}'))
    assert r.actions == [(eng.SAVE_MAP, "lab")]
    assert actions(run(engine, "record")) == [eng.START_RECORD]
    assert actions(run(engine, "stop_record")) == [eng.STOP_RECORD]


# --- weights ------------------------------------------------------------------------------------
def test_set_weights_normalises_and_applies_to_next_goal(engine):
    engine.handle_command(protocol.parse_command(
        '{"cmd": "set_weights", "weights": {"age": 2, "risk": 2, "distance": 4, "alert": 0}}'))
    assert (engine.weights.age, engine.weights.distance, engine.weights.alert) == (0.25, 0.5, 0.0)
    engine.start_patrol()
    engine.next_goal(100.0)
    assert engine.last_decision.weights["distance"] == 0.5


def test_invalid_weights_are_rejected_and_old_weights_kept(engine):
    before = engine.weights
    with pytest.raises(ValueError):
        engine.set_weights({"age": 0, "risk": 0, "distance": 0, "alert": 0})
    with pytest.raises(ValueError):
        weights_from_dict({"age": 1})
    with pytest.raises(ValueError):
        weights_from_dict({"age": -1, "risk": 1, "distance": 1, "alert": 1})
    assert engine.weights is before


# --- cancel rule --------------------------------------------------------------------------------
def test_goal_is_cancelled_when_not_patrolling(engine):
    engine.start_patrol()
    engine.goal_sent(engine.next_goal(100.0))
    assert not engine.should_cancel_active_goal(100.0)
    engine.pause()
    assert engine.should_cancel_active_goal(100.0)
    engine.estop()
    assert engine.should_cancel_active_goal(100.0)


def test_sent_decision_only_after_goal_sent(engine):
    engine.start_patrol()
    goal = engine.next_goal(100.0)
    assert engine.last_decision is not None and engine.sent_decision is None
    engine.goal_sent(goal)
    assert engine.sent_decision.chosen == goal.zone_id and engine.active_zone == goal.zone_id
    engine.goal_cancelled()
    assert engine.active_zone is None


# --- replan rule --------------------------------------------------------------------------------
def alert_in(engine, zone_id, now):
    z = engine.zonemap.zone(zone_id)
    engine._alerted_zone = engine.zonemap.record_alert(z.cx, z.cy, now)
    engine.replan_requested = True


def patrolling_towards(engine, now):
    engine.start_patrol()
    engine.on_pose(now, (0.75, 0.75))       # in R0C0
    goal = engine.next_goal(now)
    engine.goal_sent(goal)
    return goal


def test_alert_in_goal_zone_does_not_cancel(engine):
    goal = patrolling_towards(engine, 100.0)
    alert_in(engine, goal.zone_id, 100.0)
    assert not engine.should_cancel_active_goal(100.0)
    assert not engine.replan_requested


def test_alert_in_a_zone_that_outranks_goal_cancels_once_per_interval(engine):
    patrolling_towards(engine, 100.0)
    scores = score_zones(engine.zonemap, (0.75, 0.75), 100.0, engine.weights)
    engine.active_zone = scores[-1].zone_id                  # driving to the weakest zone ...
    target = next(z for z in scores if z.zone_id not in engine._skip_ids(100.0)).zone_id   # ... alert in a strong one
    alert_in(engine, target, 100.0)
    assert engine.should_cancel_active_goal(100.0)
    alert_in(engine, target, 101.0)
    assert not engine.should_cancel_active_goal(101.0) and engine.replan_requested   # too soon, keep request
    assert engine.should_cancel_active_goal(106.0)                                    # interval passed


def test_alert_outranks_goal_pure_rule():
    class S:
        def __init__(self, zone_id, total):
            self.zone_id, self.total = zone_id, total
    scores = [S("A", 0.9), S("B", 0.5), S("C", 0.1)]
    assert alert_outranks_goal(scores, "A", "B")
    assert not alert_outranks_goal(scores, "C", "B")
    assert not alert_outranks_goal(scores, "B", "B")
    assert not alert_outranks_goal(scores, None, "B")
    assert not alert_outranks_goal(scores, "A", "B", exclude={"A"})
    assert not alert_outranks_goal(scores, "X", "B")


# --- goal yaw -----------------------------------------------------------------------------------
def test_goal_faces_direction_of_travel(engine):
    engine.start_patrol()
    engine.on_pose(100.0, (0.75, 0.75), 2.0)
    goal = engine.next_goal(100.0)
    assert goal.yaw == pytest.approx(math.atan2(goal.y - 0.75, goal.x - 0.75))


def test_heading_to_and_quaternion():
    assert eng.heading_to((0, 0), (0, 2)) == pytest.approx(math.pi / 2)
    assert eng.heading_to((1, 1), (1.01, 1.0), fallback_yaw=0.7) == 0.7
    z, w = eng.yaw_to_quaternion(math.pi)
    assert (z, w) == pytest.approx((1.0, 0.0), abs=1e-9)
    z, w = eng.yaw_to_quaternion(0.0)
    assert (z, w) == (0.0, 1.0)


# --- scan pose-jump filter ------------------------------------------------------------------------
def test_pose_jumped_thresholds_and_angle_wrap():
    assert not eng.pose_jumped(None, (0, 0, 0), 0.3, 0.5)
    assert not eng.pose_jumped((0, 0, 0), (0.2, 0.0, 0.4), 0.3, 0.5)
    assert eng.pose_jumped((0, 0, 0), (0.4, 0.0, 0.0), 0.3, 0.5)
    assert eng.pose_jumped((0, 0, 0), (0.0, 0.0, 0.6), 0.3, 0.5)
    assert not eng.pose_jumped((0, 0, math.pi - 0.1), (0, 0, -math.pi + 0.1), 0.3, 0.5)   # 0.2 rad across +-pi


def test_engine_drops_jumping_scan_and_clears_history(engine):
    assert engine.on_scan(100.0, room_scan(0.0, (1.0, 1.0, 0.0))) is not None
    assert engine.on_scan(100.1, room_scan(0.1, (3.0, 1.0, 0.0))) is None       # 2 m jump
    assert engine.scans_dropped == 1
    assert engine.on_scan(100.2, room_scan(0.2, (3.0, 1.0, 0.0))) is not None   # new pose is accepted


# --- bag ----------------------------------------------------------------------------------------
def test_default_bag_topics():
    topics = RecordingConfig().topics
    assert "/patrol/camera/compressed" in topics and "/pi_camera/image_raw/compressed" not in topics
    for needed in ("/patrol/command", "/explore/status", "/cmd_vel", "/cmd_vel_nav", "/lyra/armed", "/tf",
                   "/tf_static", "/map", "/scan", "/odometry/filtered", "/imu/data", "/patrol/status",
                   "/patrol/warning", "/patrol/decision"):
        assert needed in topics


def test_shipped_yaml_uses_throttled_camera():
    assert load_settings().topics.camera == "/patrol/camera/compressed"


def test_failed_recorder_is_reported_once_with_log_tail(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/bin/true")
    cmd = lambda cfg, out: [sys.executable, "-c", "import sys; sys.stderr.write('no such topic'); sys.exit(3)"]
    rec = BagRecorder(RecordingConfig(), tmp_path, command_fn=cmd)
    rec.start()
    rec._proc.wait(10)
    assert not rec.recording
    msg = rec.failure()
    assert "code 3" in msg and "no such topic" in msg and str(rec.log_path) in msg
    assert rec.failure() is None


def test_deliberate_stop_is_not_a_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/bin/true")
    cmd = lambda cfg, out: [sys.executable, "-c", "import time; time.sleep(30)"]
    rec = BagRecorder(RecordingConfig(), tmp_path, command_fn=cmd)
    rec.start()
    assert rec.recording and rec.failure() is None
    rec.stop()
    assert rec.failure() is None
