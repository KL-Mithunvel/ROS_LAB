"""
pytest suite for guests.yaml loading/validation (greeter_config.py).

Run from practice/acrux_greeter/ :   pytest
"""

import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import greeter_config  # noqa: E402
from greeter_config import ConfigError, load_config  # noqa: E402

GOOD = {
    "surveyed": True,
    "home": {"x": 0.0, "y": 0.0, "yaw": 0.0},
    "slots": [
        {"label": "A", "x": 1.0, "y": 2.0, "yaw": 1.5},
        {"x": 2.0, "y": 2.0, "yaw": 1.5},
    ],
}


def write(tmp_path, data):
    path = tmp_path / "guests.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return str(path)


def mutated(**changes):
    data = {k: (v.copy() if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
            for k, v in GOOD.items()}
    data.update(changes)
    return data


def test_good_file_loads_with_defaults(tmp_path):
    cfg = load_config(write(tmp_path, GOOD))
    assert cfg.surveyed is True
    assert cfg.frame_id == "map"
    assert cfg.max_auto_retries == 1
    assert cfg.goal_timeout_s == 120.0
    assert [p.label for p in cfg.slots] == ["A", "Guest 2"]   # default label by position
    assert cfg.home.label == "Home"


def test_shipped_guests_yaml_is_valid_but_marked_unsurveyed():
    cfg = load_config()
    assert len(cfg.slots) == greeter_config.MAX_GUESTS
    assert cfg.surveyed is False, "placeholders must stay marked unsurveyed"


def test_surveyed_defaults_to_false_when_missing(tmp_path):
    data = mutated()
    del data["surveyed"]
    assert load_config(write(tmp_path, data)).surveyed is False


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "nope.yaml"))


def test_invalid_yaml_raises_config_error(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("home: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(str(path))


@pytest.mark.parametrize("data, fragment", [
    (mutated(home=None), "home"),
    (mutated(slots=[]), "non-empty"),
    (mutated(slots="x"), "non-empty"),
    (mutated(slots=[GOOD["slots"][0]] * 5), "maximum"),
    (mutated(home={"x": 0.0, "y": 0.0}), "yaw"),
    (mutated(home={"x": "left", "y": 0.0, "yaw": 0.0}), "number"),
    (mutated(home={"x": float("nan"), "y": 0.0, "yaw": 0.0}), "finite"),
    (mutated(max_auto_retries=-1), "max_auto_retries"),
    (mutated(goal_timeout_s=0), "positive"),
])
def test_bad_values_are_rejected_with_a_useful_message(tmp_path, data, fragment):
    if data["home"] is None:
        del data["home"]
    with pytest.raises(ConfigError, match=fragment):
        load_config(write(tmp_path, data))
