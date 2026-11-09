"""Load patrol.yaml + zones.yaml into ready-to-use settings objects."""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .bag import RecordingConfig
from .fusion import FusionConfig
from .heatmap import HeatmapConfig, dynamic_config
from .motion import CameraMotionConfig, LidarMotionConfig
from .priority import PriorityConfig
from .schema import from_mapping

HERE = Path(__file__).resolve().parent.parent
SECTIONS = {"heatmap", "priority", "lidar_motion", "camera_motion", "fusion", "topics", "recording"}


@dataclass
class TopicsConfig:
    """Topic and action names; the sim or another robot can override them in patrol.yaml."""
    scan: str = "/scan"
    map: str = "/map"                 # SLAM occupancy grid, drives dynamic zones
    odom: str = "/odometry/filtered"
    imu: str = "/imu/data"
    camera: str = "/pi_camera/image_raw/compressed"
    nav_action: str = "/navigate_to_pose"
    nav_cmd_vel: str = "/cmd_vel_nav"
    arm_service: str = "/lyra/arm"
    disarm_service: str = "/lyra/disarm"
    map_frame: str = "map"
    base_frame: str = "base_link"


@dataclass
class PatrolSettings:
    heatmap: HeatmapConfig
    priority: PriorityConfig
    lidar_motion: LidarMotionConfig
    camera_motion: CameraMotionConfig
    fusion: FusionConfig
    topics: TopicsConfig
    recording: RecordingConfig
    zones: dict   # parsed zones.yaml, fed to heatmap.build_zones


def _read_yaml(path):
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text())
    except FileNotFoundError:
        raise FileNotFoundError(f"settings file not found: {path}") from None
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name} is not valid YAML: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a mapping at the top level")
    return data


def load_settings(patrol_yaml=None, zones_yaml=None):
    """Env BEETLE_PATROL_YAML / BEETLE_ZONES_YAML point at other files (used by sim_gazebo/); default is the lab pair."""
    patrol_yaml = Path(patrol_yaml or os.environ.get("BEETLE_PATROL_YAML") or HERE / "patrol.yaml")
    zones_yaml = Path(zones_yaml or os.environ.get("BEETLE_ZONES_YAML") or HERE / "zones.yaml")
    cfg = _read_yaml(patrol_yaml)
    unknown = set(cfg) - SECTIONS
    if unknown:
        raise ValueError(f"patrol.yaml: unknown section(s) {sorted(unknown)}; allowed: {sorted(SECTIONS)}")
    zones = _read_yaml(zones_yaml)
    dynamic_config(zones)       # fail at start-up, not at the first map, on a bad dynamic: section
    return PatrolSettings(
        heatmap=from_mapping(HeatmapConfig, cfg.get("heatmap"), "heatmap"),
        priority=from_mapping(PriorityConfig, cfg.get("priority"), "priority"),
        lidar_motion=from_mapping(LidarMotionConfig, cfg.get("lidar_motion"), "lidar_motion"),
        camera_motion=from_mapping(CameraMotionConfig, cfg.get("camera_motion"), "camera_motion"),
        fusion=from_mapping(FusionConfig, cfg.get("fusion"), "fusion"),
        topics=from_mapping(TopicsConfig, cfg.get("topics"), "topics"),
        recording=from_mapping(RecordingConfig, cfg.get("recording"), "recording"),
        zones=zones)
