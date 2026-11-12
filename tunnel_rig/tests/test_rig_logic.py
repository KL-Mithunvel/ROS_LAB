import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pi"))

from rig_logic import RigState, level_to_duty, parse_packet  # noqa: E402


@pytest.mark.parametrize("data, expected", [
    (b"1042:F", (1042, "F")), (b"F", (0, "F")), (b"7:s\n", (7, "s")),
    (b"", (0, "")), (b"x:F", (0, "F")),
])
def test_parse_packet(data, expected):
    assert parse_packet(data) == expected


def test_level_to_duty():
    assert level_to_duty(0) == 0
    assert level_to_duty(9) == 255


def run(state, until, t0=0.0, dt=0.01):
    t, out = t0, (state.cur_l, state.cur_r)
    while t < until:
        t += dt
        out = state.tick(t)
    return out


def test_forward_ramps_to_target():
    s = RigState(default_level=9)
    assert s.handle("F", 0.0)
    assert s.tick(0.011) == (12, 12)            # ramp-limited first step
    assert run(s, 0.45, t0=0.011) == (255, 255)


def test_spin_left_is_opposite_sides():
    s = RigState(default_level=9)
    s.handle("L", 0.0)
    assert (s.tgt_l, s.tgt_r) == (-255, 255)


def test_stop_is_immediate():
    s = RigState(default_level=9)
    s.handle("F", 0.0)
    run(s, 0.3)
    s.handle("S", 0.3)
    assert s.tick(0.31) == (0, 0)
    assert s.last_char == "S"


def test_failsafe_stops_without_commands():
    s = RigState(default_level=9, cmd_timeout_s=0.5)
    s.handle("F", 0.0)
    assert run(s, 0.4)[0] > 0
    assert s.tick(0.6) == (0, 0)


def test_ping_does_not_move_or_feed_failsafe():
    s = RigState()
    assert not s.handle("?", 0.0)
    assert (s.tgt_l, s.tgt_r) == (0, 0)


def test_speed_change_rescales_move_in_progress():
    s = RigState(default_level=9)
    s.handle("G", 0.0)                          # 40 % / 100 %
    s.handle("3", 0.1)
    assert s.tgt_r == level_to_duty(3)
    assert s.tgt_l < s.tgt_r


def test_reply_format():
    s = RigState()
    s.handle("F", 0.0)
    assert s.reply(42, -50) == "42,-50,6,F"
