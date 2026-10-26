"""
pytest suite for lab_preflight.py parsers (no ROS needed).

Run from waypoint_mission/ :   pytest
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab_preflight as pf  # noqa: E402

TOPIC_INFO = """Type: geometry_msgs/msg/Twist

Publisher count: 2

Node name: controller_server
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Endpoint type: PUBLISHER
GID: 01.0f

Node name: teleop_twist_keyboard
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Endpoint type: PUBLISHER

Subscription count: 1

Node name: micro_ros_agent
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Endpoint type: SUBSCRIPTION
"""


def test_topic_info_split():
    pubs, subs = pf.parse_topic_info_verbose(TOPIC_INFO)
    assert pubs == ["controller_server", "teleop_twist_keyboard"]
    assert subs == ["micro_ros_agent"]


def test_hz_takes_latest_average():
    text = "average rate: 9.5\n\tmin: 0.1\naverage rate: 10.02\n"
    assert pf.parse_hz(text) == pytest.approx(10.02)


def test_hz_none_when_silent():
    assert pf.parse_hz("") is None


@pytest.mark.parametrize("text,expected", [
    ("At time 12.3\n- Translation: [0, 0, 0]", True),
    ("Waiting for transform map -> odom: Invalid frame ID", False),
])
def test_has_transform(text, expected):
    assert pf.has_transform(text) is expected


def test_find_matches_is_case_insensitive():
    nodes = ["/amcl", "/AS21_Cartographer_Node", "/map_server"]
    assert pf.find_matches(nodes, "cartographer") == ["/AS21_Cartographer_Node"]


class TestCmdVel:
    def test_no_publisher_warns(self):
        assert pf.classify_cmd_vel([], ["base"])[0] == pf.WARN

    def test_two_publishers_warn(self):
        assert pf.classify_cmd_vel(["a", "b"], ["base"])[0] == pf.WARN

    def test_single_direct_publisher_is_info(self):
        assert pf.classify_cmd_vel(["controller_server"], ["base"])[0] == pf.INFO

    def test_collision_monitor_is_pass(self):
        assert pf.classify_cmd_vel(["collision_monitor"], ["base"])[0] == pf.PASS


def test_run_missing_command_reports_not_found():
    ok, out = pf.run(["definitely-not-a-real-command-xyz"])
    assert ok is False and "not found" in out
