import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from panel_logic import clamp_speed, command_for, direction_for_key  # noqa: E402


@pytest.mark.parametrize(
    "held, expected",
    [
        (set(), "S"),
        ({"up"}, "F"),
        ({"down"}, "B"),
        ({"left"}, "L"),
        ({"right"}, "R"),
        ({"up", "left"}, "G"),
        ({"up", "right"}, "I"),
        ({"down", "left"}, "H"),
        ({"down", "right"}, "J"),
    ],
)
def test_command_for_basic(held, expected):
    assert command_for(held) == expected


def test_opposites_cancel():
    assert command_for({"up", "down"}) == "S"
    assert command_for({"left", "right"}) == "S"


def test_opposite_pair_leaves_other_axis():
    assert command_for({"up", "down", "left"}) == "L"
    assert command_for({"left", "right", "up"}) == "F"


def test_all_four_stops():
    assert command_for({"up", "down", "left", "right"}) == "S"


def test_unknown_directions_ignored():
    assert command_for({"banana"}) == "S"


@pytest.mark.parametrize(
    "keysym, expected",
    [("w", "up"), ("W", "up"), ("Up", "up"), ("s", "down"), ("Down", "down"),
     ("a", "left"), ("Left", "left"), ("d", "right"), ("Right", "right"),
     ("space", None), ("x", None)],
)
def test_direction_for_key(keysym, expected):
    assert direction_for_key(keysym) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(0, 0), (9, 9), (6, 6), (-3, 0), (42, 9), (4.6, 5), ("7", 7), ("x", 0), (None, 0)],
)
def test_clamp_speed(value, expected):
    assert clamp_speed(value) == expected
