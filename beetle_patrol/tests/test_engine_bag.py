import math

import numpy as np
import pytest

from patrol.bag import BagRecorder, RecordingConfig, bag_command
from patrol.config import load_settings
from patrol.heatmap import HeatmapConfig
from patrol.engine import Mode, PatrolEngine
from patrol.motion import ScanFrame


@pytest.fixture
def engine():
    """Engine on a fixed 3x4 grid of 1.5 m zones with the original timings (independent of the shipped yaml)."""
    s = load_settings()
    s.zones = {"grid": {"origin": [0, 0], "rows": 3, "cols": 4, "cell_w": 1.5, "cell_h": 1.5},
               "default_risk": 0.3, "risk": {"0,0": 0.9, "2,3": 0.7}}
    s.heatmap = HeatmapConfig(visit_radius_m=1.2, max_age_s=300.0, alert_memory_s=120.0)
    s.priority.failed_goal_cooldown_s = 60.0
    s.priority.min_revisit_s = 30.0
    return PatrolEngine(s, now=0.0)


def test_idle_engine_gives_no_goal_but_entering_a_box_turns_it_green(engine):
    """Manual driving (idle): no goals, but the box the robot is in is marked visited."""
    assert engine.next_goal(10.0) is None
    engine.on_pose(10.0, (0.75, 0.75))                     # inside R0C0 (0..1.5 m)
    assert engine.zonemap.age_s("R0C0", 10.0) == 0.0       # green
    assert engine.zonemap.age_s("R0C1", 10.0) == 10.0      # the next box is untouched


def test_driving_into_the_next_box_turns_that_box_green_even_far_from_its_centre(engine):
    """Entering at the edge, > visit radius (1.2 m) from the centre, still counts."""
    engine.on_pose(10.0, (0.75, 0.75))
    engine.on_pose(20.0, (1.55, 0.2))                      # just inside R0C1 (1.5..3.0), 1.5 m from its centre (2.25, 0.75)
    assert engine.zonemap.age_s("R0C1", 20.0) == 0.0
    assert engine.zonemap.age_s("R0C2", 20.0) == 20.0
    assert engine.zonemap.snapshot(20.0)["R0C1"]["age_norm"] == 0.0


def test_pose_marks_visits_in_every_mode_including_estop(engine):
    from patrol.engine import Mode
    for mode in (Mode.IDLE, Mode.MAPPING, Mode.PATROL, Mode.ESTOP):
        engine.mode = mode
        engine.on_pose(50.0, (2.25, 2.25))                 # R1C1... (1.5..3.0 x 1.5..3.0)
        assert engine.zonemap.age_s("R1C1", 50.0) == 0.0
        engine.zonemap._last_visit["R1C1"] = 0.0           # reset for the next mode


def test_patrol_picks_a_goal_records_decision_and_marks_visits(engine):
    engine.start_patrol()
    engine.on_pose(100.0, (0.75, 0.75))
    assert engine.zonemap.age_s("R0C0", 100.0) == 0.0
    goal = engine.next_goal(100.0)
    assert goal.zone_id != "R0C0" and engine.last_decision.chosen == goal.zone_id
    assert goal.zone_id in engine.last_decision.explanation


def test_failed_goal_is_skipped_for_the_cooldown_then_allowed(engine):
    engine.start_patrol()
    first = engine.next_goal(100.0).zone_id
    engine.goal_finished(100.0, first, success=False)
    assert engine.next_goal(110.0).zone_id != first
    assert engine.next_goal(170.0).zone_id == first


def test_successful_goal_resets_zone_age(engine):
    engine.start_patrol()
    z = engine.next_goal(100.0).zone_id
    engine.goal_finished(100.0, z, success=True)
    assert engine.zonemap.age_s(z, 100.0) == 0.0


def test_estop_blocks_goals_and_start_until_released(engine):
    engine.start_patrol()
    engine.estop()
    assert engine.next_goal(100.0) is None
    engine.start_patrol()
    assert engine.mode is Mode.ESTOP
    engine.release_estop()
    assert engine.mode is Mode.IDLE and engine.next_goal(100.0) is None   # needs a deliberate Start
    engine.start_patrol()
    assert engine.next_goal(100.0) is not None


def room_scan(t, pose, box=None):
    n, inc = 360, math.radians(1)
    r = np.full(n, 4.0)
    if box:
        r[170:190] = 1.5
    return ScanFrame(t, pose, r, -math.pi, inc, 0.1, 12.0)


def test_scan_warning_raises_alert_in_map_zone_and_requests_replan(engine):
    engine.start_patrol()
    pose = (2.0, 2.0, 0.0)      # laser pose in the MAP frame: robot stands in zone R1C1 (cell 1.5 m)
    for i in range(5):
        engine.on_scan(100 + i * 0.1, room_scan(i * 0.1, pose))
    warned = None
    for i in range(5, 12):
        res = engine.on_scan(100 + i * 0.1, room_scan(i * 0.1, pose, box=True))
        warned = warned or res.warning
    assert warned is not None
    assert engine.replan_requested
    zone = engine.zonemap.zone_at(warned.x, warned.y)
    assert zone is not None and engine.zonemap.alert_level(zone.id, 101.0) > 0.9


def test_status_is_json_serialisable(engine):
    import json
    engine.start_patrol()
    goal = engine.next_goal(100.0)
    assert engine.status(100.0)["decision"] is None      # picked but not sent: nothing to show yet
    engine.goal_sent(goal)
    assert json.loads(json.dumps(engine.status(100.0)))["decision"]["chosen"] == goal.zone_id


def test_bag_command_contains_topics_storage_and_compression(tmp_path):
    cfg = RecordingConfig(storage="sqlite3", compression="zstd", topics=["/scan", "/tf"])
    cmd = bag_command(cfg, tmp_path / "x")
    assert cmd[:3] == ["ros2", "bag", "record"] and cmd[-2:] == ["/scan", "/tf"]
    assert "zstd" in cmd and "sqlite3" in cmd
    assert "--compression-mode" not in bag_command(RecordingConfig(compression=""), tmp_path)


def test_recorder_without_ros2_on_path_raises_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="ros2 not found"):
        BagRecorder(RecordingConfig(), tmp_path).start()


def test_recently_visited_zone_is_not_picked_even_if_risky(engine):
    engine.start_patrol()
    engine.on_pose(100.0, (0.75, 0.75))                 # R0C0 (risk 0.9) just visited
    assert engine.next_goal(100.0).zone_id != "R0C0"
    assert engine.next_goal(140.0).zone_id == "R0C0"    # eligible again after min_revisit_s


# --- goal completion from the action status topic (no ROS) ---------------------------------------
U1, U2 = bytes(range(16)), bytes(range(16, 32))


def test_classify_goal_status_terminal_and_active():
    from patrol.engine import classify_goal_status as c
    assert c([(U1, 2)], U1) == "active"
    assert c([(U1, 4)], U1) == "succeeded"
    assert c([(U1, 5)], U1) == "canceled"
    assert c([(U1, 6)], U1) == "aborted"


def test_classify_goal_status_ignores_other_goals_and_nondecisive_states():
    from patrol.engine import classify_goal_status as c
    assert c([(U2, 4), (U1, 2)], U1) == "active"
    assert c([(U2, 4)], U1) is None
    assert c([], U1) is None and c([(U1, 4)], None) is None
    for st in (0, 1, 3):
        assert c([(U1, st)], U1) is None


def test_classify_goal_status_accepts_int_lists():
    from patrol.engine import classify_goal_status as c
    assert c([(list(U1), 4)], U1) == "succeeded"
    assert c([(U1, 6)], list(U1)) == "aborted"


def test_goal_timed_out():
    from patrol.engine import goal_timed_out as t
    assert not t(100.0, 50.0, 90.0)
    assert t(141.0, 50.0, 90.0)
    assert not t(140.0, 50.0, 90.0)
    assert not t(1e9, 0.0, 0.0) and not t(1e9, None, 90.0)


def test_goal_timeout_default_is_configured():
    assert load_settings().priority.goal_timeout_s == 90.0
