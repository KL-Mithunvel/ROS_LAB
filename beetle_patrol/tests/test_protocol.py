import copy
import json

import pytest

from patrol import protocol as p
from patrol.config import load_settings
from patrol.engine import PatrolEngine
from patrol.heatmap import HeatmapConfig
from patrol.priority import Weights

W = {"age": 0.5, "risk": 0.2, "distance": 0.2, "alert": 0.1}
RAW = {"age": 0.4, "risk": 0.3, "distance": 0.5, "alert": 0.0}
CONTRIB = {"age": 0.2, "risk": 0.06, "distance": 0.1, "alert": 0.0}


@pytest.fixture
def engine():
    s = load_settings()
    s.zones = {"grid": {"origin": [0, 0], "rows": 3, "cols": 4, "cell_w": 1.5, "cell_h": 1.5},
               "default_risk": 0.3, "risk": {"0,0": 0.9, "2,3": 0.7}}
    s.heatmap = HeatmapConfig(visit_radius_m=1.2, max_age_s=300.0, alert_memory_s=120.0)
    s.priority.failed_goal_cooldown_s = 60.0
    s.priority.min_revisit_s = 30.0
    return PatrolEngine(s, now=0.0)


def decision():
    scores = [{"zone": "R0C1", "total": 0.36, "distance_m": 1.5, "raw": dict(RAW), "contrib": dict(CONTRIB)}]
    return p.build_decision(10.0, "R0C1", "why", W, scores)


def warning():
    return p.build_warning(10.0, 5.0, 1.0, 2.0, "R0C1", 0.8, 0.7, 0.6, "motion")


def status():
    return p.build_status(
        t=10.0, mode="patrol", armed=None, nav_ready=True, explore_active=False,
        robot={"x": 1.0, "y": 2.0, "yaw": 0.1}, goal_zone="R0C1", goal_state="active", weights=W,
        zones=[{"id": "R0C1", "n": 1, "row": 0, "col": 1, "cx": 2.25, "cy": 0.75, "w": 1.5, "h": 1.5, "risk": 0.3}],
        heatmap={"R0C1": {"age_s": 5.0, "age_norm": 0.1, "alert": 0.0}}, skipped={"R0C1": "recent"},
        motion={"lidar": 0.1, "camera": 0.2, "fused": 0.3, "ego_moving": True, "ego_turning": False},
        decision=decision(), last_warning=warning(), recording=False, bag_dir=None)


def test_valid_examples_pass_and_round_trip():
    for msg, validate in ((status(), p.validate_status), (decision(), p.validate_decision),
                          (warning(), p.validate_warning)):
        validate(msg)
        assert json.loads(json.dumps(msg)) == msg
        assert msg["v"] == p.PROTOCOL_VERSION == 1


def test_status_with_nulls_is_valid():
    s = status()
    s.update(robot=None, goal_zone=None, motion=None, decision=None, last_warning=None, armed=True)
    p.validate_status(s)


@pytest.mark.parametrize("make,validate,keys", [
    (status, p.validate_status, p.STATUS_KEYS),
    (decision, p.validate_decision, p.DECISION_KEYS),
    (warning, p.validate_warning, p.WARNING_KEYS)])
def test_every_missing_required_field_is_named(make, validate, keys):
    for key in keys:
        msg = make()
        del msg[key]
        with pytest.raises(ValueError, match=key):
            validate(msg)


def test_missing_nested_fields_are_named():
    s = status()
    del s["robot"]["yaw"]
    with pytest.raises(ValueError, match="robot.yaw"):
        p.validate_status(s)
    s = status()
    del s["heatmap"]["R0C1"]["age_norm"]
    with pytest.raises(ValueError, match="age_norm"):
        p.validate_status(s)
    s = status()
    del s["decision"]["scores"][0]["raw"]["alert"]
    with pytest.raises(ValueError, match="raw.alert"):
        p.validate_status(s)
    s = status()
    del s["zones"][0]["risk"]
    with pytest.raises(ValueError, match="zones.0.risk|zones\\[0\\].risk"):
        p.validate_status(s)


def test_out_of_range_values_are_rejected():
    def bad(msg, path, value, validate, match):
        target = msg
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with pytest.raises(ValueError, match=match):
            validate(msg)
    bad(status(), ["heatmap", "R0C1", "age_norm"], 1.5, p.validate_status, "age_norm")
    bad(status(), ["heatmap", "R0C1", "alert"], -0.1, p.validate_status, "alert")
    bad(status(), ["motion", "fused"], 2, p.validate_status, "fused")
    bad(status(), ["weights", "age"], -1, p.validate_status, "weights.age")
    bad(status(), ["zones", 0, "risk"], 1.2, p.validate_status, "risk")
    bad(warning(), ["camera"], 1.1, p.validate_warning, "camera")
    bad(warning(), ["x"], "1", p.validate_warning, "x")
    bad(warning(), ["x"], float("nan"), p.validate_warning, "x")
    bad(decision(), ["scores", 0, "raw", "age"], 3, p.validate_decision, "raw.age")
    bad(status(), ["v"], 2, p.validate_status, "status.v")


def test_enum_violations_are_rejected():
    for key, value in (("mode", "flying"), ("goal_state", "done")):
        s = status()
        s[key] = value
        with pytest.raises(ValueError, match=key):
            p.validate_status(s)
    s = status()
    s["skipped"]["R0C1"] = "bored"
    with pytest.raises(ValueError, match="skipped"):
        p.validate_status(s)
    s = status()
    s["recording"] = "yes"
    with pytest.raises(ValueError, match="recording"):
        p.validate_status(s)


@pytest.mark.parametrize("word", p.SIMPLE_COMMANDS)
def test_plain_word_and_json_commands_agree(word):
    assert p.parse_command(word) == {"cmd": word}
    assert p.parse_command(f"  {word.upper()}\n") == {"cmd": word}
    assert p.parse_command(json.dumps({"cmd": word})) == {"cmd": word}


def test_save_map_and_set_weights_commands():
    assert p.parse_command('{"cmd": "save_map", "name": "lab"}') == {"cmd": "save_map", "name": "lab"}
    assert p.parse_command('{"cmd": "save_map"}') == {"cmd": "save_map"}
    cmd = p.build_command("set_weights", weights=W)
    assert p.parse_command(json.dumps(cmd)) == cmd
    assert p.build_command("save_map", name="x") == {"cmd": "save_map", "name": "x"}


@pytest.mark.parametrize("text,match", [
    ("dance", "cmd"),
    ("", "cmd"),
    ("{not json", "JSON"),
    ('{"name": "x"}', "cmd"),
    ('{"cmd": "start", "name": "x"}', "name"),
    ('{"cmd": "arm", "weights": {}}', "weights"),
    ('{"cmd": "save_map", "name": ""}', "name"),
    ('{"cmd": "save_map", "name": 3}', "name"),
    ("save_map", "name"),
    ("set_weights", "weights"),
    ('{"cmd": "set_weights"}', "weights"),
    ('{"cmd": "set_weights", "weights": {"age": 1}}', "risk"),
    ('{"cmd": "set_weights", "weights": {"age": -1, "risk": 1, "distance": 1, "alert": 1}}', "weights.age"),
    ('{"cmd": "set_weights", "weights": {"age": 0, "risk": 0, "distance": 0, "alert": 0}}', "all zero"),
    ("[1]", "object")])
def test_bad_commands_are_rejected(text, match):
    with pytest.raises(ValueError, match=match):
        p.parse_command(text)


def test_parse_command_rejects_non_text():
    with pytest.raises(ValueError, match="text"):
        p.parse_command(None)


def test_weights_from_priority_is_normalised():
    w = p.weights_from_priority(Weights(2, 1, 1, 0))
    assert w == {"age": 0.5, "risk": 0.25, "distance": 0.25, "alert": 0.0}


def test_status_from_engine_validates_before_and_after_a_decision(engine):
    s = p.status_from_engine(engine, 5.0, {})
    p.validate_status(s)
    assert s["decision"] is None and s["mode"] == "idle" and len(s["zones"]) == 12
    assert s["skipped"]["R0C0"] == "recent"

    engine.start_patrol()
    goal = engine.next_goal(100.0)
    engine.goal_sent(goal)
    engine.goal_finished(100.0, goal.zone_id, success=False)
    extras = {"mode": "patrol", "armed": True, "nav_ready": True, "robot": {"x": 0.0, "y": 0.0, "yaw": 0.0},
              "goal_zone": goal.zone_id, "goal_state": "sent", "recording": True, "bag_dir": "/tmp/bag",
              "last_warning": warning()}
    s = p.status_from_engine(engine, 110.0, extras)
    p.validate_status(s)
    assert s["decision"]["chosen"] == goal.zone_id
    assert s["skipped"][goal.zone_id] == "cooldown"
    assert sum(s["weights"].values()) == pytest.approx(1.0)
    assert json.loads(json.dumps(s)) == s
    original = copy.deepcopy(s)
    p.validate_status(s)
    assert s == original


def test_zone_number_is_required_integer_and_cells_may_be_negative():
    s = status()
    s["zones"][0].update(row=-2, col=-1, n=7)
    p.validate_status(s)
    for field, value in (("n", 0), ("n", 1.5), ("n", True), ("row", 0.5)):
        s = status()
        s["zones"][0][field] = value
        with pytest.raises(ValueError, match=field):
            p.validate_status(s)
    s = status()
    del s["zones"][0]["n"]
    with pytest.raises(ValueError, match="zones.*n"):
        p.validate_status(s)


def test_set_start_command_round_trips_and_takes_no_fields():
    assert p.parse_command("set_start") == {"cmd": "set_start"}
    assert p.parse_command(json.dumps(p.build_command("set_start"))) == {"cmd": "set_start"}
    with pytest.raises(ValueError):
        p.validate_command({"cmd": "set_start", "name": "x"})
