import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "robot"))
from watchdog_logic import WatchdogLogic

ALL = ['cancel_goals', 'pause_explore', 'disarm']


def test_fires_once_per_outage():
    w = WatchdogLogic(2.0)
    w.feed(0.0)
    assert w.check(2.5, True) == ALL
    assert w.check(3.0, True) == []
    assert w.check(10.0, True) == []


def test_no_fire_when_disarmed():
    w = WatchdogLogic(2.0)
    w.feed(0.0)
    assert w.check(50.0, False) == []


def test_no_fire_while_heartbeats_arrive():
    w = WatchdogLogic(2.0)
    t = 0.0
    for _ in range(100):
        w.feed(t)
        t += 1.0
        assert w.check(t, True) == []


def test_rearms_after_recovery():
    w = WatchdogLogic(2.0)
    w.feed(0.0)
    assert w.check(3.0, True) == ALL
    w.feed(4.0)
    assert w.check(5.0, True) == []
    assert w.check(6.5, True) == ALL


def test_boundary_exactly_timeout_does_not_fire():
    w = WatchdogLogic(2.0)
    w.feed(0.0)
    assert w.check(2.0, True) == []
    assert w.check(2.001, True) == ALL


def test_disarmed_then_armed_late_fires_if_still_silent():
    w = WatchdogLogic(2.0)
    w.feed(0.0)
    assert w.check(5.0, False) == []
    assert w.check(5.1, True) == ALL


def test_never_heard_uses_first_check_as_baseline():
    w = WatchdogLogic(2.0)
    assert w.check(10.0, True) == []
    assert w.check(11.9, True) == []
    assert w.check(12.1, True) == ALL


def test_clock_backwards_no_fire():
    w = WatchdogLogic(2.0)
    w.feed(100.0)
    assert w.check(50.0, True) == []
