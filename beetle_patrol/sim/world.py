"""Pure simulated world for beetle_patrol (numpy only, NO ROS).

Everything a real robot would give us, with the same data shape:
  * ray-cast LaserScan-like ranges (RPLiDAR C1 style: ~508 beams, 0.15-12 m, noise, inf/nan returns)
  * a diff-drive / skid-steer kinematic model with an acceleration limit
  * a scripted intruder: a small square box that walks a path between t_start and t_end
  * a synthetic grey camera image that changes only while the intruder is in view

World frame == map frame (metres, x forward, y left, yaw counter-clockwise). The room is centred on
the origin. Time is always passed in explicitly, so tests are deterministic (same seed -> same output).
"""
import math
from dataclasses import dataclass, field, fields

import numpy as np


def make(cls, data):
    """Build dataclass `cls` from a dict; unknown keys are an error (a typo must not pass silently)."""
    data = dict(data or {})
    known = {f.name for f in fields(cls)}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"{cls.__name__}: unknown settings {sorted(unknown)}")
    return cls(**data)


def wrap_angle(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# --------------------------------------------------------------------------- settings
@dataclass
class RoomConfig:
    half_x: float = 1.5           # walls at x = +/- half_x
    half_y: float = 1.5           # walls at y = +/- half_y
    boxes: list = field(default_factory=list)   # static obstacles: [cx, cy, width, height]


@dataclass
class LidarConfig:
    n_beams: int = 508
    angle_min: float = -math.pi
    range_min: float = 0.15
    range_max: float = 12.0
    rate_hz: float = 9.0
    noise_sigma_m: float = 0.01
    inf_prob: float = 0.01        # fraction of beams with no return (reported as inf)
    nan_prob: float = 0.003       # fraction of beams with an invalid reading (reported as nan)

    @property
    def angle_increment(self):
        return 2 * math.pi / self.n_beams


@dataclass
class RobotConfig:
    start: list = field(default_factory=lambda: [0.0, 0.0, 0.0])   # x, y, yaw in the map frame
    max_lin_speed: float = 0.5
    max_ang_speed: float = 1.5
    lin_accel: float = 0.8        # m/s^2
    ang_accel: float = 3.0        # rad/s^2
    radius: float = 0.2           # keeps the robot centre this far from walls / boxes (clamped)


@dataclass
class IntruderConfig:
    enabled: bool = True
    size: float = 0.3             # side of the square box (m)
    t_start: float = 30.0         # sim seconds since start
    t_end: float = 60.0
    path: list = field(default_factory=lambda: [[-1.2, 1.2], [1.0, 1.2], [1.0, -1.0]])


@dataclass
class CameraConfig:
    width: int = 160
    height: int = 120
    fov_deg: float = 62.0
    noise_sigma: float = 1.0      # grey levels; far below patrol.yaml camera pixel_thresh (25)
    rate_hz: float = 5.0
    jpeg_quality: int = 80


# --------------------------------------------------------------------------- geometry
def raycast(ox, oy, angles, half_x, half_y, boxes):
    """Distance from (ox, oy) along each world-frame angle to the nearest wall or box.

    The origin must be inside the room. `boxes` is an (K, 4) array of xmin, xmax, ymin, ymax.
    """
    dx, dy = np.cos(angles), np.sin(angles)
    with np.errstate(divide="ignore", invalid="ignore"):
        tx = np.where(dx > 0, (half_x - ox) / dx, np.where(dx < 0, (-half_x - ox) / dx, np.inf))
        ty = np.where(dy > 0, (half_y - oy) / dy, np.where(dy < 0, (-half_y - oy) / dy, np.inf))
        t = np.minimum(tx, ty)
        inv_x = 1.0 / np.where(dx == 0, 1e-12, dx)
        inv_y = 1.0 / np.where(dy == 0, 1e-12, dy)
        for xmin, xmax, ymin, ymax in boxes:
            t1, t2 = (xmin - ox) * inv_x, (xmax - ox) * inv_x
            t3, t4 = (ymin - oy) * inv_y, (ymax - oy) * inv_y
            t_near = np.maximum(np.minimum(t1, t2), np.minimum(t3, t4))
            t_far = np.minimum(np.maximum(t1, t2), np.maximum(t3, t4))
            hit = (t_far >= t_near) & (t_near > 0)
            t = np.where(hit & (t_near < t), t_near, t)
    return t


def box_corners(cx, cy, w, h):
    return [cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2]


# --------------------------------------------------------------------------- kinematics
class DiffDrive:
    """Unicycle model: commanded (v, w) are reached through an acceleration limit, then integrated."""

    def __init__(self, cfg, x=None, y=None, yaw=None):
        self.cfg = cfg
        sx, sy, syaw = cfg.start
        self.x = sx if x is None else x
        self.y = sy if y is None else y
        self.yaw = syaw if yaw is None else yaw
        self.v = 0.0
        self.w = 0.0

    @staticmethod
    def _approach(current, target, max_step):
        return current + float(np.clip(target - current, -max_step, max_step))

    def step(self, cmd_v, cmd_w, dt):
        cfg = self.cfg
        cmd_v = float(np.clip(cmd_v, -cfg.max_lin_speed, cfg.max_lin_speed))
        cmd_w = float(np.clip(cmd_w, -cfg.max_ang_speed, cfg.max_ang_speed))
        self.v = self._approach(self.v, cmd_v, cfg.lin_accel * dt)
        self.w = self._approach(self.w, cmd_w, cfg.ang_accel * dt)
        # midpoint integration: exact enough at 50 Hz and exact for straight lines / in-place turns
        mid_yaw = self.yaw + 0.5 * self.w * dt
        self.x += self.v * math.cos(mid_yaw) * dt
        self.y += self.v * math.sin(mid_yaw) * dt
        self.yaw = wrap_angle(self.yaw + self.w * dt)

    @property
    def pose(self):
        return self.x, self.y, self.yaw


# --------------------------------------------------------------------------- the world
class World:
    def __init__(self, room=None, lidar=None, intruder=None, camera=None, seed=0):
        self.room = room or RoomConfig()
        self.lidar = lidar or LidarConfig()
        self.intruder_cfg = intruder or IntruderConfig()
        self.camera = camera or CameraConfig()
        self.rng = np.random.default_rng(seed)
        self._static_boxes = np.array([box_corners(*b) for b in self.room.boxes], dtype=float).reshape(-1, 4)
        path = np.asarray(self.intruder_cfg.path, dtype=float).reshape(-1, 2)
        self._path = path
        seg = np.hypot(*np.diff(path, axis=0).T) if len(path) > 1 else np.zeros(0)
        self._cum = np.concatenate([[0.0], np.cumsum(seg)])

    # --- intruder ---
    def intruder_pos(self, t):
        """(x, y) of the intruder at sim time t, or None when it is not walking."""
        cfg = self.intruder_cfg
        if not cfg.enabled or len(self._path) == 0 or not (cfg.t_start <= t <= cfg.t_end):
            return None
        total = self._cum[-1]
        frac = (t - cfg.t_start) / max(cfg.t_end - cfg.t_start, 1e-9)
        s = frac * total
        return (float(np.interp(s, self._cum, self._path[:, 0])),
                float(np.interp(s, self._cum, self._path[:, 1])))

    def intruder_in_room(self, t):
        p = self.intruder_pos(t)
        return p is not None and abs(p[0]) < self.room.half_x and abs(p[1]) < self.room.half_y

    def _boxes_at(self, t):
        """Static boxes plus the intruder box (only while it is inside the room)."""
        if not self.intruder_in_room(t):
            return self._static_boxes
        cx, cy = self.intruder_pos(t)
        extra = np.array([box_corners(cx, cy, self.intruder_cfg.size, self.intruder_cfg.size)])
        return np.vstack([self._static_boxes, extra])

    # --- lidar ---
    def scan(self, laser_pose, t):
        """Ranges (n_beams,) as a LaserScan would carry them. laser_pose = (x, y, yaw) in the world frame."""
        cfg = self.lidar
        ox, oy, yaw = laser_pose
        angles = cfg.angle_min + np.arange(cfg.n_beams) * cfg.angle_increment
        r = raycast(ox, oy, angles + yaw, self.room.half_x, self.room.half_y, self._boxes_at(t))
        r = r + self.rng.normal(0.0, cfg.noise_sigma_m, r.shape)
        r[(r < cfg.range_min) | (r > cfg.range_max)] = np.inf     # outside the sensor's span: no return
        u = self.rng.random(r.shape)
        r[u < cfg.inf_prob] = np.inf
        r[(u >= cfg.inf_prob) & (u < cfg.inf_prob + cfg.nan_prob)] = np.nan
        return r

    # --- camera ---
    def intruder_visible(self, cam_pose, t):
        """True when the intruder centre is inside the field of view, in the room and not hidden by a box."""
        if not self.intruder_in_room(t):
            return False
        px, py = self.intruder_pos(t)
        x, y, yaw = cam_pose
        bearing = wrap_angle(math.atan2(py - y, px - x) - yaw)
        if abs(bearing) >= math.radians(self.camera.fov_deg) / 2:
            return False
        dist = math.hypot(px - x, py - y)
        wall = raycast(x, y, np.array([yaw + bearing]), self.room.half_x, self.room.half_y, self._static_boxes)[0]
        return dist < wall

    def image(self, cam_pose, t):
        """Grey uint8 (height, width) image. A fixed textured background (depends on heading only) plus
        a dark rectangle for the intruder while it is visible. Noise is small and always present."""
        cfg = self.camera
        x, y, yaw = cam_pose
        fov = math.radians(cfg.fov_deg)
        cols = np.arange(cfg.width)
        rel = fov / 2 - (cols + 0.5) / cfg.width * fov           # left of centre is positive
        absolute = yaw + rel
        column = 110 + 30 * np.sin(4 * absolute) + 15 * np.sin(11 * absolute)
        rows = np.linspace(-1, 1, cfg.height)[:, None]
        img = column[None, :] + 20 * rows
        if self.intruder_visible(cam_pose, t):
            px, py = self.intruder_pos(t)
            dist = math.hypot(px - x, py - y)
            bearing = wrap_angle(math.atan2(py - y, px - x) - yaw)
            focal = (cfg.width / 2) / math.tan(fov / 2)
            half_w = focal * (self.intruder_cfg.size / 2) / dist
            centre_col = cfg.width / 2 - focal * math.tan(bearing)
            half_h = focal * 0.3 / dist                              # intruder is ~0.6 m tall
            mid_row = cfg.height / 2 + focal * 0.1 / dist            # camera is ~0.1 m above the box centre
            in_c = np.abs(cols + 0.5 - centre_col) <= half_w
            in_r = np.abs(np.arange(cfg.height) + 0.5 - mid_row) <= half_h
            img[np.ix_(in_r, in_c)] = 25.0
        img = img + self.rng.normal(0.0, cfg.noise_sigma, img.shape)
        return np.clip(img, 0, 255).astype(np.uint8)

    # --- helpers for the node ---
    def clamp_to_room(self, x, y, radius):
        """Keep the robot centre `radius` inside the walls. Returns (x, y, touched)."""
        nx = float(np.clip(x, -self.room.half_x + radius, self.room.half_x - radius))
        ny = float(np.clip(y, -self.room.half_y + radius, self.room.half_y - radius))
        return nx, ny, (nx != x or ny != y)
