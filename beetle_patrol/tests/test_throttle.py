import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "robot"))
import pytest
from throttle_logic import ThrottleLogic


def test_first_passes():
    assert ThrottleLogic(5).should_publish(100.0)


def test_below_period_dropped_boundary_passes():
    t = ThrottleLogic(5)  # 0.2 s
    assert t.should_publish(0.0)
    assert not t.should_publish(0.19)
    assert t.should_publish(0.2)
    assert not t.should_publish(0.399)
    assert t.should_publish(0.4)


def test_float_rounding_on_period():
    t = ThrottleLogic(5)
    now = 1000.1
    assert t.should_publish(now)
    assert t.should_publish(now + 0.2)


def test_56hz_input_yields_about_5hz():
    t = ThrottleLogic(5)
    n = sum(t.should_publish(i / 56.0) for i in range(56 * 10))
    assert 45 <= n <= 52


def test_clock_backwards_resets():
    t = ThrottleLogic(5)
    assert t.should_publish(100.0)
    assert t.should_publish(50.0)      # jump back: passes, resets
    assert not t.should_publish(50.1)
    assert t.should_publish(50.2)


def test_bad_rate():
    with pytest.raises(ValueError):
        ThrottleLogic(0)
