"""PatrolEngine with dynamic zones: anchoring, throttled map updates, set_start, tolerance of 0/1 zones."""
import numpy as np
import pytest

from patrol.config import load_settings
from patrol.discovery import OccupancyInfo
from patrol.engine import SET_START, Mode, PatrolEngine
from patrol import protocol as p

RES, SIDE = 0.1, 60


def make_engine(**dynamic):
    s = load_settings()
    s.zones = {"dynamic": {"enabled": True, **dynamic}, "default_risk": 0.4}
    s.priority.min_revisit_s = 0.0
    return PatrolEngine(s, now=0.0)


def free_map(x0=-0.5, x1=0.5, y0=-0.5, y1=0.5):
    g = np.full((SIDE, SIDE), -1, dtype=np.int8)
    g[round((y0 + 3) / RES):round((y1 + 3) / RES), round((x0 + 3) / RES):round((x1 + 3) / RES)] = 0
    return OccupancyInfo(SIDE, SIDE, RES, -3.0, -3.0, g.ravel())


def test_engine_starts_with_no_zones_and_survives_everything_with_zero_zones():
    e = make_engine()
    assert e.zonemap.zones == []
    e.start_patrol()
    assert e.next_goal(1.0) is None
    assert e.should_cancel_active_goal(1.0) is False
    st = p.status_from_engine(e, 1.0, {})
    p.validate_status(st)
    assert st["zones"] == [] and st["heatmap"] == {} and st["skipped"] == {}


def test_first_pose_anchors_zone_one_on_the_robot():
    e = make_engine()
    e.on_pose(5.0, (2.0, -1.0), 0.3)
    (z,) = e.zonemap.zones
    assert (z.id, z.n, z.cx, z.cy, z.risk) == ("R0C0", 1, 2.0, -1.0, 0.4)
    assert e.zonemap.age_s("R0C0", 8.0) == 3.0
    e.on_pose(6.0, (2.2, -1.1), 0.3)                       # still the same cell, anchor unchanged
    assert len(e.zonemap.zones) == 1 and e.zonemap.anchor == (2.0, -1.0)


def test_non_finite_pose_is_ignored():
    e = make_engine()
    e.on_pose(1.0, (float("nan"), 0.0), 0.0)
    assert e.zonemap.zones == []


def test_driving_into_a_new_cell_creates_its_zone_without_a_map():
    e = make_engine()
    e.on_pose(1.0, (0.0, 0.0))
    e.on_pose(2.0, (1.1, 0.0))
    assert [(z.id, z.n) for z in e.zonemap.zones] == [("R0C0", 1), ("R0C1", 2)]


def test_map_before_pose_is_kept_and_used_after_anchoring():
    e = make_engine()
    assert e.on_map(free_map(-0.5, 1.5), 1.0) == []
    e.on_pose(2.0, (0.0, 0.0))
    assert [z.id for z in e.zonemap.zones] == ["R0C0", "R0C1"]


def test_map_updates_are_throttled_by_fake_time():
    e = make_engine(map_update_s=2.0)
    e.on_pose(10.0, (0.0, 0.0))
    wide = free_map(-0.5, 2.5)
    assert [z.id for z in e.on_map(wide, 10.0)] == ["R0C1"]      # first map: processed at once
    assert e.on_map(wide, 11.0) == [] and len(e.zonemap.zones) == 2     # throttled
    e.on_pose(11.9, (0.0, 0.0))
    assert len(e.zonemap.zones) == 2                             # still inside the 2 s window
    e.on_pose(12.0, (0.0, 0.0))                                  # due: the stored map is used again
    assert [z.id for z in e.zonemap.zones] == ["R0C0", "R0C1", "R0C2"]


def test_growth_is_one_ring_per_map_update_then_waits_for_a_new_map():
    e = make_engine(map_update_s=2.0)
    e.on_pose(0.0, (0.0, 0.0))
    e.on_map(free_map(-0.5, 2.5), 2.0)
    assert len(e.zonemap.zones) == 2
    e.on_pose(4.0, (0.0, 0.0))
    assert len(e.zonemap.zones) == 3
    e.on_pose(6.0, (0.0, 0.0))
    e.on_pose(8.0, (0.0, 0.0))
    assert len(e.zonemap.zones) == 3                        # nothing more to reveal: no pointless re-scans
    assert e.on_map(free_map(-0.5, 3.0), 10.0)[0].id == "R0C3"


def test_disabled_dynamic_zones_keep_the_static_grid():
    s = load_settings()
    s.zones = {"dynamic": {"enabled": False},
               "grid": {"origin": [0, 0], "rows": 2, "cols": 2, "cell_w": 1.0, "cell_h": 1.0}}
    e = PatrolEngine(s, now=0.0)
    assert [z.n for z in e.zonemap.zones] == [1, 2, 3, 4]
    e.on_pose(1.0, (5.0, 5.0))
    assert e.on_map(free_map(), 2.0) == [] and len(e.zonemap.zones) == 4
    assert e.handle_command({"cmd": "set_start"}).refused.startswith("set_start refused")


def test_set_start_reanchors_and_clears_state():
    e = make_engine()
    e.on_pose(1.0, (0.0, 0.0))
    e.on_pose(2.0, (1.0, 0.0))
    e._cooldown_until["R0C0"] = 99.0
    result = e.handle_command({"cmd": "set_start"})
    assert result.refused is None and result.actions == [(SET_START, None)]
    e.set_start(1.0, 1.0, 5.0)
    assert [(z.id, z.n, z.cx, z.cy) for z in e.zonemap.zones] == [("R0C0", 1, 1.0, 1.0)]
    assert e._cooldown_until == {} and e.last_decision is None


@pytest.mark.parametrize("mode", [Mode.PATROL, Mode.MAPPING, Mode.ESTOP])
def test_set_start_refused_unless_idle(mode):
    e = make_engine()
    e.on_pose(1.0, (0.0, 0.0))
    e.mode = mode
    r = e.handle_command({"cmd": "set_start"})
    assert r.actions == [] and mode.value in r.refused and "idle" in r.refused


def test_set_start_refused_without_a_pose():
    assert "no robot pose" in make_engine().handle_command({"cmd": "set_start"}).refused


def test_zones_appearing_mid_patrol_are_picked_and_status_shows_them_at_once():
    e = make_engine()
    e.start_patrol()
    e.on_pose(100.0, (0.0, 0.0))
    assert e.next_goal(100.0).zone_id == "R0C0"             # a single zone is a valid goal
    e.on_pose(101.0, (1.0, 0.0))
    st = p.status_from_engine(e, 101.0, {})
    p.validate_status(st)
    assert [z["n"] for z in st["zones"]] == [1, 2] and set(st["heatmap"]) == {"R0C0", "R0C1"}
    e.goal_finished(101.0, "R0C0", False)                   # cooldown dict keyed by id keeps working
    assert e.next_goal(102.0).zone_id == "R0C1"
