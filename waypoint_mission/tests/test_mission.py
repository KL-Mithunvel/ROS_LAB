"""
pytest suite for the waypoint state machine (mission.py). No ROS needed.

Run from waypoint_mission/ :   pytest
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mission  # noqa: E402
from mission import (  # noqa: E402
    CancelNavigation, Message, Mission, NavigateTo, NavResult, Pose, Shutdown, State,
)

HOME = Pose(0.0, 0.0, 0.0, "Home")
WAYPOINTS = [Pose(3.0, float(i), 1.5, f"Waypoint {i + 1}") for i in range(4)]


def make(count=3, retries=1):
    return Mission(HOME, WAYPOINTS, count, max_auto_retries=retries)


def navigates(actions):
    return [a.pose for a in actions if isinstance(a, NavigateTo)]


def has(actions, cls):
    return any(isinstance(a, cls) for a in actions)


def arrive(m):
    """Simulate Nav2 reporting success for the goal in flight."""
    return m.on_nav_result(NavResult.SUCCEEDED)


# --- construction ------------------------------------------------------------
@pytest.mark.parametrize("bad", [0, -1, 5, 3.0, "3", None, True])
def test_waypoint_count_must_be_whole_number_in_range(bad):
    with pytest.raises(ValueError):
        Mission(HOME, WAYPOINTS, bad)


def test_negative_retries_rejected():
    with pytest.raises(ValueError):
        Mission(HOME, WAYPOINTS, 3, max_auto_retries=-1)


# --- happy path --------------------------------------------------------------
@pytest.mark.parametrize("count", [1, 3, 4])
def test_full_run_visits_exactly_count_waypoints_then_home(count):
    m = make(count)
    assert m.state is State.IDLE
    goals = []
    goals += navigates(m.on_command(mission.CMD_NEXT))      # start -> waypoint 1
    for _ in range(count):
        assert m.state is State.NAVIGATING
        arrive(m)
        assert m.state is State.AT_WAYPOINT
        goals += navigates(m.on_command(mission.CMD_NEXT))  # task done -> next/home
    assert m.state is State.RETURNING_HOME
    arrive(m)
    assert m.state is State.DONE and m.is_finished
    assert goals == WAYPOINTS[:count] + [HOME]
    assert m.visited == WAYPOINTS[:count]
    assert m.skipped == []


def test_robot_does_not_move_until_first_yes():
    m = make(3)
    assert m.state is State.IDLE
    assert m.on_nav_result(NavResult.SUCCEEDED) == []   # stale/unexpected: ignored
    assert m.state is State.IDLE


def test_next_while_driving_does_not_send_another_goal():
    m = make(3)
    m.on_command(mission.CMD_NEXT)
    actions = m.on_command(mission.CMD_NEXT)
    assert navigates(actions) == []
    assert m.state is State.NAVIGATING


def test_robot_waits_at_waypoint_until_told():
    m = make(3)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    assert m.state is State.AT_WAYPOINT
    assert m.on_nav_result(NavResult.SUCCEEDED) == []   # nothing new happens by itself
    assert m.state is State.AT_WAYPOINT


# --- failures and obstacles --------------------------------------------------
def test_failure_auto_retries_once_then_blocks():
    m = make(3, retries=1)
    m.on_command(mission.CMD_NEXT)
    first = m.on_nav_result(NavResult.FAILED)
    assert navigates(first) == [WAYPOINTS[0]] and m.state is State.NAVIGATING
    second = m.on_nav_result(NavResult.FAILED)
    assert navigates(second) == [] and m.state is State.BLOCKED


def test_unexpected_cancel_is_treated_as_failure():
    m = make(3, retries=0)
    m.on_command(mission.CMD_NEXT)
    m.on_nav_result(NavResult.CANCELED)
    assert m.state is State.BLOCKED


def test_blocked_retry_resends_same_goal_and_resets_retries():
    m = make(3, retries=1)
    m.on_command(mission.CMD_NEXT)
    m.on_nav_result(NavResult.FAILED)
    m.on_nav_result(NavResult.FAILED)
    assert m.state is State.BLOCKED
    actions = m.on_command(mission.CMD_RETRY)
    assert navigates(actions) == [WAYPOINTS[0]] and m.state is State.NAVIGATING
    # the auto-retry budget is fresh again
    assert navigates(m.on_nav_result(NavResult.FAILED)) == [WAYPOINTS[0]]


def test_blocked_skip_moves_to_next_waypoint():
    m = make(3, retries=0)
    m.on_command(mission.CMD_NEXT)
    m.on_nav_result(NavResult.FAILED)
    actions = m.on_command(mission.CMD_SKIP)
    assert navigates(actions) == [WAYPOINTS[1]]
    assert not has(actions, CancelNavigation)   # goal already ended
    assert m.skipped == [WAYPOINTS[0]]


def test_blocked_going_home_cannot_be_skipped():
    m = make(1, retries=0)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    m.on_command(mission.CMD_NEXT)               # -> home
    m.on_nav_result(NavResult.FAILED)
    assert m.state is State.BLOCKED
    actions = m.on_command(mission.CMD_SKIP)
    assert navigates(actions) == [] and m.state is State.BLOCKED
    assert navigates(m.on_command(mission.CMD_RETRY)) == [HOME]


def test_stale_result_after_finish_is_ignored():
    m = make(1)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    assert m.state is State.DONE
    assert m.on_nav_result(NavResult.FAILED) == []
    assert m.state is State.DONE


# --- operator commands -------------------------------------------------------
def test_skip_while_navigating_cancels_and_goes_to_next():
    m = make(3)
    m.on_command(mission.CMD_NEXT)
    actions = m.on_command(mission.CMD_SKIP)
    assert isinstance(actions[0], CancelNavigation)
    assert navigates(actions) == [WAYPOINTS[1]]
    assert m.skipped == [WAYPOINTS[0]]


def test_skip_at_waypoint_drops_the_next_waypoint_without_moving():
    m = make(3)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    actions = m.on_command(mission.CMD_SKIP)
    assert navigates(actions) == [] and m.state is State.AT_WAYPOINT
    assert m.skipped == [WAYPOINTS[1]]
    assert navigates(m.on_command(mission.CMD_NEXT)) == [WAYPOINTS[2]]


def test_skip_with_nobody_left_just_explains():
    m = make(1)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    actions = m.on_command(mission.CMD_SKIP)
    assert navigates(actions) == [] and m.skipped == []


def test_home_cancels_drops_remaining_and_returns():
    m = make(4)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    m.on_command(mission.CMD_NEXT)                # driving to waypoint 2
    actions = m.on_command(mission.CMD_HOME)
    assert isinstance(actions[0], CancelNavigation)
    assert navigates(actions) == [HOME]
    assert m.state is State.RETURNING_HOME
    assert m.skipped == WAYPOINTS[1:]                 # 2 (in flight) + 3, 4 (queued)


def test_home_from_at_waypoint_needs_no_cancel():
    m = make(3)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    actions = m.on_command(mission.CMD_HOME)
    assert not has(actions, CancelNavigation)
    assert navigates(actions) == [HOME]


def test_pause_cancels_and_resume_goes_to_same_target():
    m = make(3)
    m.on_command(mission.CMD_NEXT)
    paused = m.on_command(mission.CMD_PAUSE)
    assert has(paused, CancelNavigation) and m.state is State.PAUSED
    assert m.on_command(mission.CMD_NEXT)[0].text.startswith("Paused")
    resumed = m.on_command(mission.CMD_PAUSE)
    assert navigates(resumed) == [WAYPOINTS[0]] and m.state is State.NAVIGATING


def test_pause_when_not_driving_does_nothing():
    m = make(3)
    assert navigates(m.on_command(mission.CMD_PAUSE)) == []
    assert m.state is State.IDLE


def test_quit_while_driving_cancels_then_shuts_down():
    m = make(3)
    m.on_command(mission.CMD_NEXT)
    actions = m.on_command(mission.CMD_QUIT)
    assert has(actions, CancelNavigation) and has(actions, Shutdown)
    assert m.state is State.ABORTED and m.is_finished


def test_quit_while_waiting_needs_no_cancel():
    m = make(3)
    actions = m.on_command(mission.CMD_QUIT)
    assert not has(actions, CancelNavigation) and has(actions, Shutdown)


def test_commands_after_finish_do_nothing_but_explain():
    m = make(3)
    m.on_command(mission.CMD_QUIT)
    actions = m.on_command(mission.CMD_NEXT)
    assert navigates(actions) == [] and has(actions, Message)


def test_status_reports_progress():
    m = make(3)
    m.on_command(mission.CMD_NEXT)
    arrive(m)
    text = m.on_command(mission.CMD_STATUS)[0].text
    assert "AT_WAYPOINT" in text and "Waypoint 1" in text and "Waypoint 2" in text


# --- parsing and geometry ----------------------------------------------------
@pytest.mark.parametrize("typed, expected", [
    ("", mission.CMD_NEXT), ("y", mission.CMD_NEXT), (" YES \n", mission.CMD_NEXT),
    ("s", mission.CMD_SKIP), ("r", mission.CMD_RETRY), ("h", mission.CMD_HOME),
    ("p", mission.CMD_PAUSE), ("resume", mission.CMD_PAUSE),
    ("q", mission.CMD_QUIT), ("?", mission.CMD_STATUS),
])
def test_parse_command_aliases(typed, expected):
    assert mission.parse_command(typed) == expected


@pytest.mark.parametrize("typed", ["n", "no", "banana", "stop"])
def test_parse_command_unknown_is_none(typed):
    # "n"/"no" are deliberately NOT aliases: they must not be mistaken for yes.
    assert mission.parse_command(typed) is None


def test_yaw_to_quaternion():
    z, w = mission.yaw_to_quaternion(0.0)
    assert (z, w) == (0.0, 1.0)
    z, w = mission.yaw_to_quaternion(math.pi)
    assert z == pytest.approx(1.0) and w == pytest.approx(0.0, abs=1e-12)
    z, w = mission.yaw_to_quaternion(math.pi / 2)
    assert z == pytest.approx(math.sqrt(0.5)) and w == pytest.approx(math.sqrt(0.5))
