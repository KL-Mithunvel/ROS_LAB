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


# ---- Wi-Fi link: packets, replies, health ----
from panel_logic import (  # noqa: E402
    HealthTracker, Reply, build_packet, health_level, health_score, parse_reply,
)


def test_build_packet():
    assert build_packet(1042, "F") == b"1042:F"


def test_parse_reply_ok():
    assert parse_reply(b"1042,-61,6,F\n") == Reply(1042, -61, 6, "F")


@pytest.mark.parametrize("data", [b"", b"junk", b"1,2,3", b"a,-60,6,F", b"1,-60,6,FF", b"\xff\xfe", None])
def test_parse_reply_rejects_bad(data):
    assert parse_reply(data) is None


def test_health_score_perfect_and_awful():
    assert health_score(0, 10, -40) == 100
    assert health_score(50, 400, -95) == 0


def test_health_score_weights_loss_most():
    assert health_score(0, 30, -50) > health_score(20, 30, -50)
    assert health_score(0, 30, -50) - health_score(20, 30, -50) == 20   # 0.5 * (2 * 20)


@pytest.mark.parametrize("score, level", [(100, "GOOD"), (70, "GOOD"), (69, "FAIR"), (40, "FAIR"), (39, "POOR"), (0, "POOR")])
def test_health_level(score, level):
    assert health_level(score) == level


def _tracker_with_replies(n, rtt=0.02, rssi=-55, start=0.0, step=0.15):
    t = HealthTracker()
    now = start
    for seq in range(1, n + 1):
        t.sent(seq, now)
        t.on_reply(Reply(seq, rssi, 6, "S"), now + rtt)
        now += step
    return t, now


def test_tracker_healthy_link():
    t, now = _tracker_with_replies(20)
    h = t.snapshot(now)
    assert not h.lost and h.level == "GOOD"
    assert h.loss_pct == 0 and 19 < h.rtt_ms < 21 and h.rssi == -55


def test_tracker_never_replied_is_lost():
    t = HealthTracker()
    t.sent(1, 0.0)
    h = t.snapshot(0.1)
    assert h.lost and h.level == "LOST" and not h.ever_replied and h.score == 0


def test_tracker_goes_lost_after_silence():
    t, now = _tracker_with_replies(5)
    assert not t.snapshot(now).lost
    h = t.snapshot(now + 0.7)                       # > lost_after (0.5 s) since last reply
    assert h.lost and h.ever_replied and h.level == "LOST"


def test_tracker_counts_loss():
    t = HealthTracker()
    now = 0.0
    for seq in range(1, 21):
        t.sent(seq, now)
        if seq % 4 != 1:                             # seq 1,5,9,13,17 get no reply -> 25 % loss
            t.on_reply(Reply(seq, -60, 6, "S"), now + 0.02)
        now += 0.15
    h = t.snapshot(now)
    assert h.loss_pct == pytest.approx(25.0)
    assert not h.lost


def test_tracker_recent_unanswered_not_counted_as_loss_yet():
    t, now = _tracker_with_replies(10)
    t.sent(99, now)                                  # just sent, reply still in flight
    assert t.snapshot(now + 0.05).loss_pct == 0


def test_tracker_reset():
    t, now = _tracker_with_replies(5)
    t.reset()
    assert t.snapshot(now).level == "LOST"


def test_ssh_server_command_start_and_stop():
    from panel_logic import ssh_server_command
    start = ssh_server_command("start", "klm", "192.168.1.11", "tunnel_rig_pi")
    assert start[:5] == ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6"]
    assert start[5] == "klm@192.168.1.11"
    assert "cd ~/tunnel_rig_pi" in start[6] and "rig_server.py" in start[6]
    stop = ssh_server_command("stop", "klm", "192.168.1.11", "tunnel_rig_pi")
    assert "[r]ig_server" in stop[6] and "rig_server" not in stop[6].replace("[r]ig_server", "")


@pytest.mark.parametrize("user, host, d", [("k;m", "h", "d"), ("klm", "h h", "d"), ("klm", "h", "../x")])
def test_ssh_server_command_rejects_unsafe_values(user, host, d):
    from panel_logic import ssh_server_command
    with pytest.raises(ValueError):
        ssh_server_command("start", user, host, d)


def test_ssh_server_command_rejects_unknown_action():
    from panel_logic import ssh_server_command
    with pytest.raises(ValueError):
        ssh_server_command("restart", "klm", "h", "d")


def test_flip_command():
    from panel_logic import flip_command
    assert flip_command("F") == "F"
    assert flip_command("F", flip_fb=True) == "B"
    assert flip_command("G", flip_fb=True) == "H"
    assert flip_command("I", flip_fb=True) == "J"
    assert flip_command("L", flip_lr=True) == "R"
    assert flip_command("G", flip_lr=True) == "I"
    assert flip_command("J", flip_lr=True) == "H"
    assert flip_command("G", True, True) == "J"
    assert flip_command("B", True, True) == "F"
    for passthrough in ("S", "4", "?"):
        assert flip_command(passthrough, True, True) == passthrough
