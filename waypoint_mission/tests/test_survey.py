"""
pytest suite for survey_spots.py (pure parts: maths + file writer, no ROS).

Run from waypoint_mission/ :   pytest
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import waypoint_config  # noqa: E402
import survey_spots  # noqa: E402
from mission import Pose, yaw_to_quaternion  # noqa: E402


class TestYaw:
    @pytest.mark.parametrize("yaw", [0.0, 0.5, 1.5708, 3.0, -1.0, -3.0])
    def test_round_trips_through_quaternion(self, yaw):
        z, w = yaw_to_quaternion(yaw)
        assert survey_spots.quaternion_to_yaw(0.0, 0.0, z, w) == pytest.approx(yaw, abs=1e-9)

    def test_identity_is_zero(self):
        assert survey_spots.quaternion_to_yaw(0, 0, 0, 1) == 0.0


class TestQuality:
    @staticmethod
    def cov(pos_var=0.01, yaw_var=0.01):
        c = [0.0] * 36
        c[0], c[7], c[35] = pos_var, pos_var, yaw_var
        return c

    def test_converged_is_fine(self):
        assert survey_spots.pose_quality_warning(self.cov()) is None

    def test_wide_position_warns(self):
        assert "position" in survey_spots.pose_quality_warning(self.cov(pos_var=1.0))

    def test_wide_heading_warns(self):
        assert "heading" in survey_spots.pose_quality_warning(self.cov(yaw_var=0.5))

    def test_missing_covariance_warns(self):
        assert survey_spots.pose_quality_warning([]) is not None


class TestSpacing:
    def test_far_apart_is_silent(self):
        poses = [Pose(0, 0, 0, "Home"), Pose(3, 0, 0, "G1")]
        assert survey_spots.spacing_warnings(poses) == []

    def test_close_pair_is_named(self):
        poses = [Pose(0, 0, 0, "G1"), Pose(0.5, 0, 0, "G2"), Pose(5, 5, 0, "G3")]
        out = survey_spots.spacing_warnings(poses)
        assert len(out) == 1 and "G1" in out[0] and "G2" in out[0]


class TestWriter:
    HOME = Pose(0.1234567, -0.5, 3.14159, "Home")
    WAYPOINTS = [Pose(2.0, 1.0, 1.5, "Waypoint 1"), Pose(2.0, 3.0, 1.5, "Waypoint 2")]

    def test_written_file_loads_and_is_surveyed(self, tmp_path):
        path = str(tmp_path / "out.yaml")
        cfg = survey_spots.write_surveyed(path, self.HOME, self.WAYPOINTS)
        assert cfg.surveyed is True
        assert len(cfg.waypoints) == 2
        assert cfg.home.x == pytest.approx(0.123)
        assert cfg.waypoints[1].label == "Waypoint 2"

    def test_settings_carried_over_from_base(self, tmp_path):
        base = waypoint_config.WaypointConfig("map", False, 3, 45.0, self.HOME, tuple(self.WAYPOINTS))
        path = str(tmp_path / "out.yaml")
        cfg = survey_spots.write_surveyed(path, self.HOME, self.WAYPOINTS, base)
        assert cfg.max_auto_retries == 3
        assert cfg.goal_timeout_s == 45.0

    def test_template_file_is_not_touched(self, tmp_path):
        before = open(waypoint_config.DEFAULT_CONFIG_FILE, encoding="utf-8").read()
        survey_spots.write_surveyed(str(tmp_path / "o.yaml"), self.HOME, self.WAYPOINTS)
        assert open(waypoint_config.DEFAULT_CONFIG_FILE, encoding="utf-8").read() == before
