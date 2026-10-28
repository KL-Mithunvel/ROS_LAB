"""Moving-object detectors. Each returns a confidence in 0..1; fusion.py combines them.

LiDAR: every scan is placed in the odom frame using the robot pose, so the robot's own movement
cancels out. A scan point is "new" when, seen from the pose of an older scan, it is clearly nearer
than anything that older scan saw in that direction. Clusters of new points (not wall-sized) are
moving-object candidates. Only objects that *appear* are looked for - a mover keeps appearing at
new places, so this is enough and stays cheap.

Camera: frame differencing on small greyscale images (the node does the resize). The camera only
says "something changed", never where, and is ignored while the robot itself moves.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass
class ScanFrame:
    t: float
    pose: tuple          # (x, y, yaw) of the robot in the odom frame when the scan was taken
    ranges: np.ndarray   # metres; inf / nan / out-of-range entries are handled
    angle_min: float
    angle_inc: float
    range_min: float
    range_max: float


@dataclass
class Detection:
    x: float             # odom frame
    y: float
    n_points: int
    size_m: float
    confidence: float    # 0..1


@dataclass
class LidarMotionConfig:
    compare_dt_s: float = 0.4
    history_s: float = 2.0
    appear_tol_m: float = 0.25
    neighbour_beams: int = 2
    cluster_gap_m: float = 0.30
    min_points: int = 3
    max_cluster_size_m: float = 1.5
    saturate_points: int = 8


@dataclass
class CameraMotionConfig:
    pixel_thresh: int = 25
    min_fraction: float = 0.004
    saturate_fraction: float = 0.05
    global_change_fraction: float = 0.6


def _valid_mask(frame):
    r = frame.ranges
    return np.isfinite(r) & (r >= frame.range_min) & (r <= frame.range_max)


class LidarMotionDetector:
    def __init__(self, config=None):
        self.config = config or LidarMotionConfig()
        self._history = deque()

    def update(self, frame):
        """Add a scan; return the Detections found by comparing it with an older one."""
        cfg = self.config
        self._history.append(frame)
        while self._history and frame.t - self._history[0].t > cfg.history_s:
            self._history.popleft()

        ref = self._reference(frame.t - cfg.compare_dt_s)
        if ref is None or len(ref.ranges) != len(frame.ranges):
            return []
        return self._cluster(frame, self._new_points(frame, ref))

    def _reference(self, t_wanted):
        """Newest stored scan that is at least compare_dt_s old."""
        older = [f for f in self._history if f.t <= t_wanted]
        return older[-1] if older else None

    def _new_points(self, frame, ref):
        """World-frame (N, 2) array of points in `frame` that are nearer than `ref` saw, in beam order."""
        cfg = self.config
        valid = _valid_mask(frame)
        beam = np.arange(len(frame.ranges))
        x, y, yaw = frame.pose
        ang = frame.angle_min + beam * frame.angle_inc + yaw
        wx = x + frame.ranges * np.cos(ang)
        wy = y + frame.ranges * np.sin(ang)

        # Same points as seen from the older scan's pose: bearing -> which old beam, range -> compare.
        rx, ry, ryaw = ref.pose
        dx, dy = wx - rx, wy - ry
        r_from_ref = np.hypot(dx, dy)
        bearing = np.arctan2(dy, dx) - ryaw
        bearing = (bearing + np.pi) % (2 * np.pi) - np.pi
        idx = np.rint((bearing - ref.angle_min) / ref.angle_inc).astype(int)
        in_fov = valid & (idx >= 0) & (idx < len(ref.ranges))

        # Old ranges: "no return" (inf) means free out to range_max; nan / too-close is unknown.
        ref_r = ref.ranges
        unknown = np.isnan(ref_r) | (ref_r < ref.range_min)
        ref_eff = np.where(np.isposinf(ref_r) | (ref_r > ref.range_max), ref.range_max, ref_r)

        old_min = np.full(len(beam), np.inf)
        old_known = np.ones(len(beam), dtype=bool)
        safe_idx = np.clip(idx, 0, len(ref.ranges) - 1)
        for off in range(-cfg.neighbour_beams, cfg.neighbour_beams + 1):
            j = np.clip(safe_idx + off, 0, len(ref.ranges) - 1)
            old_min = np.minimum(old_min, np.where(unknown[j], np.inf, ref_eff[j]))
            old_known &= ~unknown[j]

        appeared = in_fov & old_known & (r_from_ref < old_min - cfg.appear_tol_m)
        return np.column_stack([wx[appeared], wy[appeared]])

    def _cluster(self, frame, pts):
        """Group consecutive new points into clusters and keep object-sized ones."""
        cfg = self.config
        if len(pts) == 0:
            return []
        gaps = np.hypot(*np.diff(pts, axis=0).T) > cfg.cluster_gap_m
        detections = []
        for group in np.split(pts, np.flatnonzero(gaps) + 1):
            size = float(np.hypot(*(group.max(axis=0) - group.min(axis=0))))
            if len(group) < cfg.min_points or size > cfg.max_cluster_size_m:
                continue
            cx, cy = group.mean(axis=0)
            conf = min(1.0, len(group) / cfg.saturate_points)
            detections.append(Detection(float(cx), float(cy), len(group), size, conf))
        return detections


class CameraMotionDetector:
    def __init__(self, config=None):
        self.config = config or CameraMotionConfig()
        self._prev = None

    def update(self, gray, ego_moving):
        """Confidence 0..1 that something in view moved. `gray` is a small 2-D uint8 image."""
        cfg = self.config
        gray = np.asarray(gray, dtype=np.int16)
        prev, self._prev = self._prev, gray
        if ego_moving or prev is None or prev.shape != gray.shape:
            return 0.0   # robot's own motion shifts the whole image; start fresh once it stops
        changed = float(np.mean(np.abs(gray - prev) > cfg.pixel_thresh))
        if changed > cfg.global_change_fraction:
            return 0.0   # auto-exposure / lights switching, not an object
        span = cfg.saturate_fraction - cfg.min_fraction
        return float(np.clip((changed - cfg.min_fraction) / span, 0.0, 1.0))
