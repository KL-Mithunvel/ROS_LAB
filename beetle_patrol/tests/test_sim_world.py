"""Pure tests for sim/world.py (numpy only; runs under system python too)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim"))
from world import (CameraConfig, DiffDrive, IntruderConfig, LidarConfig, RobotConfig, RoomConfig,  # noqa: E402
                   World, make, raycast)

CLEAN = LidarConfig(noise_sigma_m=0.0, inf_prob=0.0, nan_prob=0.0)
NO_INTRUDER = IntruderConfig(enabled=False)


def world(**kw):
    kw.setdefault("lidar", CLEAN)
    kw.setdefault("intruder", NO_INTRUDER)
    return World(**kw)


def beam_at(w, angle):
    """Index of the beam whose angle (laser frame) is closest to `angle`."""
    return int(round((angle - w.lidar.angle_min) / w.lidar.angle_increment)) % w.lidar.n_beams


# ---------------------------------------------------------------- raycast / scan
def test_walls_at_known_angles_from_centre():
    r = world().scan((0, 0, 0), 0.0)
    assert len(r) == 508
    assert r[beam_at(world(), 0.0)] == pytest.approx(1.5, abs=0.01)
    assert r[beam_at(world(), math.pi / 2)] == pytest.approx(1.5, abs=0.01)
    assert r[beam_at(world(), -math.pi / 2)] == pytest.approx(1.5, abs=0.01)
    # diagonal hits the corner: 1.5*sqrt(2)
    assert r[beam_at(world(), math.pi / 4)] == pytest.approx(1.5 * math.sqrt(2), abs=0.03)


def test_off_centre_pose_and_yaw():
    w = world()
    r = w.scan((1.0, 0.0, 0.0), 0.0)
    assert r[beam_at(w, 0.0)] == pytest.approx(0.5, abs=0.01)
    assert r[beam_at(w, math.pi / 2)] == pytest.approx(1.5, abs=0.01)
    # yawed 90 deg left: laser-frame forward now points at the +y wall
    r = w.scan((0.0, 0.5, math.pi / 2), 0.0)
    assert r[beam_at(w, 0.0)] == pytest.approx(1.0, abs=0.01)


def test_flipped_laser_sees_the_other_wall_on_beam_zero():
    w = world()
    r = w.scan((1.0, 0.0, math.pi), 0.0)   # laser yaw 180: beam 0 looks toward -x
    assert r[beam_at(w, 0.0)] == pytest.approx(2.5, abs=0.01)


def test_box_occludes_wall():
    w = world(room=RoomConfig(boxes=[[0.8, 0.0, 0.2, 0.4]]))
    r = w.scan((0, 0, 0), 0.0)
    assert r[beam_at(w, 0.0)] == pytest.approx(0.7, abs=0.01)             # box front face at x=0.7
    assert r[beam_at(w, math.pi)] == pytest.approx(1.5, abs=0.01)         # behind: still the wall
    assert r[beam_at(w, math.radians(60))] == pytest.approx(1.5 / math.cos(math.radians(30)), abs=0.03)


def test_raycast_box_direct():
    t = raycast(0, 0, np.array([0.0, math.pi / 2]), 1.5, 1.5, np.array([[0.5, 0.7, -0.1, 0.1]]))
    assert t[0] == pytest.approx(0.5)
    assert t[1] == pytest.approx(1.5)


def test_range_limits_give_no_return():
    # room bigger than range_max: far walls must read inf; near-minimum hits also inf
    w = world(room=RoomConfig(half_x=20, half_y=20))
    assert np.all(np.isinf(w.scan((0, 0, 0), 0.0)))
    w = world()
    r = w.scan((1.45, 0.0, 0.0), 0.0)               # wall 0.05 m ahead < range_min 0.15
    assert np.isinf(r[beam_at(w, 0.0)])
    finite = r[np.isfinite(r)]
    assert finite.min() >= 0.15 and finite.max() <= 12.0


def test_noise_and_dropouts_are_present():
    w = World(lidar=LidarConfig(inf_prob=0.05, nan_prob=0.05), intruder=NO_INTRUDER, seed=3)
    r = w.scan((0, 0, 0), 0.0)
    assert np.isinf(r).sum() > 0 and np.isnan(r).sum() > 0
    ok = r[np.isfinite(r)]
    assert ok.std() > 0.05                               # distances vary around the room
    assert not np.allclose(ok, np.round(ok, 3))          # noise present


# ---------------------------------------------------------------- kinematics
def test_straight_line_distance():
    d = DiffDrive(RobotConfig(start=[0, 0, 0]))
    for _ in range(500):                                  # 10 s at 50 Hz
        d.step(0.3, 0.0, 0.02)
    # accelerates 0.3/0.8 = 0.375 s: distance = 0.3*(10 - 0.1875)
    assert d.x == pytest.approx(0.3 * (10 - 0.375 / 2), abs=0.01)
    assert d.y == pytest.approx(0.0, abs=1e-9)


def test_in_place_turn_angle():
    d = DiffDrive(RobotConfig(start=[0, 0, 0]))
    for _ in range(100):                                  # 2 s at 1.0 rad/s
        d.step(0.0, 1.0, 0.02)
    expected = 1.0 * (2.0 - 1.0 / 3.0 / 2)                # ang accel 3 -> ramp 0.333 s
    assert d.yaw == pytest.approx(expected, abs=0.01)
    assert math.hypot(d.x, d.y) == pytest.approx(0.0, abs=1e-9)


def test_accel_limit_and_stop():
    cfg = RobotConfig()
    d = DiffDrive(cfg)
    d.step(0.5, 0.0, 0.1)
    assert d.v == pytest.approx(cfg.lin_accel * 0.1)      # not an instant jump to 0.5
    for _ in range(100):
        d.step(0.5, 0.0, 0.02)
    assert d.v == pytest.approx(0.5)
    for _ in range(100):
        d.step(0.0, 0.0, 0.02)
    assert d.v == 0.0 and d.w == 0.0
    x = d.x
    d.step(0.0, 0.0, 0.02)
    assert d.x == x


def test_speed_clamped():
    d = DiffDrive(RobotConfig(max_lin_speed=0.5))
    for _ in range(200):
        d.step(5.0, 0.0, 0.02)
    assert d.v == pytest.approx(0.5)


def test_clamp_to_room():
    x, y, touched = world().clamp_to_room(2.0, 0.0, 0.2)
    assert (x, y, touched) == (pytest.approx(1.3), 0.0, True)


# ---------------------------------------------------------------- intruder
INTR = IntruderConfig(t_start=10.0, t_end=20.0, path=[[-3.0, 0.0], [0.0, 0.0], [0.0, 1.0]])


def test_intruder_path_timing():
    w = World(lidar=CLEAN, intruder=INTR)
    assert w.intruder_pos(9.9) is None and w.intruder_pos(20.1) is None
    assert w.intruder_pos(10.0) == pytest.approx((-3.0, 0.0))
    assert w.intruder_pos(20.0) == pytest.approx((0.0, 1.0))
    # constant speed = 4 m / 10 s; at t=17.5 it has walked 3.0 m -> reached the corner (0, 0)
    assert w.intruder_pos(17.5) == pytest.approx((0.0, 0.0))
    assert w.intruder_pos(15.0) == pytest.approx((-1.0, 0.0))


def test_intruder_in_scan_only_when_inside_room():
    w = World(lidar=CLEAN, intruder=INTR)
    base = World(lidar=CLEAN, intruder=NO_INTRUDER).scan((0, 0, 0), 0.0)
    # t=12: x=-2.2, outside the west wall (-1.5) -> scan identical to empty room
    assert not w.intruder_in_room(12.0)
    assert np.allclose(w.scan((0, 0, 0), 12.0), base, equal_nan=True)
    # t=15: x=-1.0, inside -> beam toward -x sees the box face at x=-1.15
    assert w.intruder_in_room(15.0)
    r = w.scan((0, 0, 0), 15.0)
    assert r[beam_at(w, math.pi)] == pytest.approx(0.85, abs=0.01)
    # before / after the walk: nothing
    assert np.allclose(w.scan((0, 0, 0), 5.0), base, equal_nan=True)
    assert np.allclose(w.scan((0, 0, 0), 25.0), base, equal_nan=True)


# ---------------------------------------------------------------- camera
def test_camera_changes_only_while_intruder_visible():
    cam = CameraConfig(noise_sigma=0.0)
    w = World(lidar=CLEAN, intruder=IntruderConfig(t_start=10, t_end=20, path=[[-3.0, 0.0], [1.0, 0.0]]),
              camera=cam)
    pose = (0.0, 0.0, math.pi)       # robot looks toward -x, where the intruder arrives
    empty = w.image(pose, 0.0)
    assert empty.shape == (120, 160) and empty.dtype == np.uint8
    assert np.array_equal(w.image(pose, 11.0), empty)                 # outside room: not visible
    assert not w.intruder_visible(pose, 11.0)
    assert w.intruder_visible(pose, 15.0)
    seen = w.image(pose, 15.0)
    assert (np.abs(seen.astype(int) - empty.astype(int)) > 25).mean() > 0.004   # patrol.yaml min_fraction
    assert np.array_equal(w.image(pose, 25.0), empty)                 # walk over
    # looking the other way, intruder not in the field of view: image unchanged
    away = (0.0, 0.0, 0.0)
    assert np.array_equal(w.image(away, 15.0), w.image(away, 0.0))


def test_camera_noise_stays_below_motion_threshold():
    w = World(lidar=CLEAN, intruder=NO_INTRUDER, camera=CameraConfig(noise_sigma=1.0), seed=2)
    a, b = w.image((0, 0, 0), 0.0).astype(int), w.image((0, 0, 0), 0.0).astype(int)
    assert np.abs(a - b).max() < 25


# ---------------------------------------------------------------- determinism / config
def test_same_seed_same_output():
    def run(seed):
        w = World(intruder=INTR, seed=seed)
        return w.scan((0.2, 0.1, 0.3), 15.0), w.image((0, 0, math.pi), 15.0)
    s1, i1 = run(7)
    s2, i2 = run(7)
    s3, _ = run(8)
    assert np.array_equal(s1, s2, equal_nan=True) and np.array_equal(i1, i2)
    assert not np.array_equal(s1, s3, equal_nan=True)


def test_unknown_config_key_rejected():
    with pytest.raises(ValueError):
        make(LidarConfig, {"n_beam": 10})
