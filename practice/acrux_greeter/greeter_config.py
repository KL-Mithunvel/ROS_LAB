"""
greeter_config.py — load and validate guests.yaml.

guests.yaml holds the surveyed map coordinates of the home pose and the guest
stand positions, plus a few mission settings. Everything is validated up front
so a typo is caught at your desk, not when the robot is already driving.
"""

import math
import os
from dataclasses import dataclass

import yaml

from mission import Pose

DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guests.yaml")
MAX_GUESTS = 4   # hard upper limit agreed for this event


class ConfigError(ValueError):
    """guests.yaml is missing something or contains an invalid value."""


@dataclass(frozen=True)
class GreeterConfig:
    frame_id: str
    surveyed: bool            # False = placeholder coordinates, do not drive hardware
    max_auto_retries: int
    goal_timeout_s: float
    home: Pose
    slots: tuple


def _number(value, where):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{where} must be a number, got {value!r}")
    if not math.isfinite(value):
        raise ConfigError(f"{where} must be a finite number, got {value!r}")
    return float(value)


def _pose(spec, where, default_label):
    if not isinstance(spec, dict):
        raise ConfigError(f"{where} must be a mapping with x, y, yaw")
    missing = [k for k in ("x", "y", "yaw") if k not in spec]
    if missing:
        raise ConfigError(f"{where} is missing: {', '.join(missing)}")
    return Pose(
        x=_number(spec["x"], f"{where}.x"),
        y=_number(spec["y"], f"{where}.y"),
        yaw=_number(spec["yaw"], f"{where}.yaw"),
        label=str(spec.get("label", default_label)),
    )


def load_config(path=DEFAULT_CONFIG_FILE):
    """Read and validate the YAML file. Raises FileNotFoundError or ConfigError."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a mapping at the top level")
    if "home" not in raw:
        raise ConfigError("'home' is required")
    slots_raw = raw.get("slots")
    if not isinstance(slots_raw, list) or not slots_raw:
        raise ConfigError("'slots' must be a non-empty list")
    if len(slots_raw) > MAX_GUESTS:
        raise ConfigError(f"'slots' has {len(slots_raw)} entries, the maximum is {MAX_GUESTS}")

    retries = raw.get("max_auto_retries", 1)
    if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
        raise ConfigError(f"max_auto_retries must be a whole number >= 0, got {retries!r}")
    timeout = _number(raw.get("goal_timeout_s", 120), "goal_timeout_s")
    if timeout <= 0:
        raise ConfigError("goal_timeout_s must be positive")

    return GreeterConfig(
        frame_id=str(raw.get("frame_id", "map")),
        surveyed=bool(raw.get("surveyed", False)),
        max_auto_retries=retries,
        goal_timeout_s=timeout,
        home=_pose(raw["home"], "home", "Home"),
        slots=tuple(_pose(s, f"slots[{i}]", f"Guest {i + 1}")
                    for i, s in enumerate(slots_raw)),
    )
