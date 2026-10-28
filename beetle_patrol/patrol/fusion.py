"""Fuse LiDAR, camera, IMU and wheel-odometry evidence into one motion warning.

  fused = lidar_weight * lidar_conf + camera_weight * camera_conf        (all 0..1)

  * Wheel odometry (already EKF-fused with the IMU on the robot) and the raw IMU gyro tell us how
    the robot itself is moving. While it drives, the camera is ignored (the whole image shifts);
    while it turns, LiDAR confidence is cut (a small yaw error smears every wall).
  * camera_weight is below warn_threshold, so the camera can confirm a weak LiDAR sighting but can
    never raise a warning alone.
  * A warning needs the threshold passed in `confirm_frames` of the last `window_frames` updates,
    and repeats near the same spot are suppressed for `cooldown_s`.
"""
import math
from collections import deque
from dataclasses import dataclass



@dataclass
class FusionConfig:
    lidar_weight: float = 0.7
    camera_weight: float = 0.3
    warn_threshold: float = 0.5
    confirm_frames: int = 3
    window_frames: int = 5
    cooldown_s: float = 5.0
    cooldown_radius_m: float = 1.5
    camera_max_age_s: float = 1.0
    moving_mps: float = 0.05
    turning_rps: float = 0.25
    turn_penalty: float = 0.5

    def __post_init__(self):
        if self.confirm_frames > self.window_frames or self.confirm_frames < 1:
            raise ValueError("fusion: need 1 <= confirm_frames <= window_frames")
        if self.camera_weight >= self.warn_threshold:
            raise ValueError("fusion: camera_weight must stay below warn_threshold, "
                             "otherwise the camera alone could raise a warning")


@dataclass
class EgoState:
    moving: bool    # translating faster than moving_mps
    turning: bool   # yawing faster than turning_rps


def ego_state(config, odom_linear, odom_angular, imu_gyro_z):
    """Classify the robot's own motion. Turning uses the larger of odometry and raw gyro."""
    return EgoState(
        moving=abs(odom_linear) > config.moving_mps,
        turning=max(abs(odom_angular), abs(imu_gyro_z)) > config.turning_rps)


@dataclass
class Warning:
    t: float
    x: float
    y: float
    fused: float
    lidar: float
    camera: float
    message: str


@dataclass
class FusedResult:
    """Everything the GUI shows for one update; `warning` is set only when one is raised."""
    t: float
    lidar: float
    camera: float
    fused: float
    ego: EgoState
    detection: object = None
    warning: Warning = None


class MotionFuser:
    def __init__(self, config=None):
        self.config = config or FusionConfig()
        self._over = deque(maxlen=self.config.window_frames)
        self._last_warning = None

    def update(self, t, detections, camera_conf, camera_t, ego):
        cfg = self.config
        best = max(detections, key=lambda d: d.confidence, default=None)

        lidar = best.confidence if best else 0.0
        if ego.turning:
            lidar *= cfg.turn_penalty
        camera_fresh = camera_t is not None and t - camera_t <= cfg.camera_max_age_s
        camera = camera_conf if camera_fresh and not ego.moving else 0.0

        fused = cfg.lidar_weight * lidar + cfg.camera_weight * camera
        self._over.append(fused >= cfg.warn_threshold)
        result = FusedResult(t, lidar, camera, fused, ego, best)

        confirmed = sum(self._over) >= cfg.confirm_frames
        if confirmed and best is not None and not self._in_cooldown(t, best):
            result.warning = Warning(
                t, best.x, best.y, fused, lidar, camera,
                f"Moving object near ({best.x:.1f}, {best.y:.1f}): fused {fused:.2f} "
                f"(lidar {lidar:.2f}, camera {camera:.2f})")
            self._last_warning = (t, best.x, best.y)
        return result

    def _in_cooldown(self, t, det):
        if self._last_warning is None:
            return False
        lt, lx, ly = self._last_warning
        return (t - lt < self.config.cooldown_s
                and math.hypot(det.x - lx, det.y - ly) < self.config.cooldown_radius_m)
