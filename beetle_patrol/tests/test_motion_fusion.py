import math

import numpy as np
import pytest

from patrol.config import _read_yaml, load_settings
from patrol.fusion import EgoState, FusionConfig, MotionFuser, ego_state
from patrol.motion import (CameraMotionConfig, CameraMotionDetector, Detection, LidarMotionConfig,
                           LidarMotionDetector, ScanFrame)

N, INC = 360, math.radians(1.0)
ROOM = 4.0   # square room, walls at +/-4 m


def scan(t, pose=(0.0, 0.0, 0.0), box=None):
    """Synthetic scan in a square room; `box` = (cx, cy, half) adds a square object."""
    x, y, yaw = pose
    ranges = np.full(N, np.inf)
    for i in range(N):
        a = -math.pi + i * INC + yaw
        dx, dy = math.cos(a), math.sin(a)
        r = min((ROOM - (x if dx > 0 else -x)) / abs(dx) if abs(dx) > 1e-9 else np.inf,
                (ROOM - (y if dy > 0 else -y)) / abs(dy) if abs(dy) > 1e-9 else np.inf)
        if box:
            for s in np.arange(0.1, r, 0.02):
                px, py = x + s * dx, y + s * dy
                if abs(px - box[0]) < box[2] and abs(py - box[1]) < box[2]:
                    r = s
                    break
        ranges[i] = r
    return ScanFrame(t, pose, ranges, -math.pi, INC, 0.1, 12.0)


def test_static_room_gives_no_detection():
    d = LidarMotionDetector()
    out = [d.update(scan(t / 10)) for t in range(10)]
    assert all(o == [] for o in out)


def test_object_appearing_is_detected_near_its_position():
    d = LidarMotionDetector()
    for t in range(5):
        d.update(scan(t / 10))
    found = d.update(scan(0.6, box=(2.0, 0.0, 0.2)))
    assert len(found) == 1
    assert found[0].x == pytest.approx(1.8, abs=0.3) and abs(found[0].y) < 0.4
    assert found[0].confidence > 0.3


def test_robot_driving_alone_does_not_trigger_when_pose_is_right():
    d = LidarMotionDetector()
    out = [d.update(scan(t / 10, pose=(t * 0.05, 0.0, 0.0))) for t in range(12)]
    assert all(o == [] for o in out)


def test_wall_sized_change_is_rejected():
    d = LidarMotionDetector(LidarMotionConfig(max_cluster_size_m=0.3))
    for t in range(5):
        d.update(scan(t / 10))
    assert d.update(scan(0.6, box=(2.0, 0.0, 0.5))) == []


def test_no_reference_scan_yet_returns_nothing():
    assert LidarMotionDetector().update(scan(0.0)) == []


def img(v=100):
    return np.full((24, 32), v, dtype=np.uint8)


def test_camera_static_scene_zero_and_moving_block_positive():
    c = CameraMotionDetector(CameraMotionConfig())
    assert c.update(img(), False) == 0.0
    assert c.update(img(), False) == 0.0
    moved = img()
    moved[5:15, 5:15] = 220
    assert c.update(moved, False) > 0.9


def test_camera_ignored_while_robot_moves_and_for_lighting_change():
    c = CameraMotionDetector()
    c.update(img(), False)
    assert c.update(img(200), True) == 0.0      # ego motion
    assert c.update(img(40), False) == 0.0      # whole frame changed = exposure, not an object


def det(conf, x=1.0, y=1.0):
    return Detection(x, y, 8, 0.4, conf)


STILL, MOVING, TURNING = EgoState(False, False), EgoState(True, False), EgoState(False, True)


def run(fuser, frames, ego=STILL, cam=0.0):
    results = []
    for i, dets in enumerate(frames):
        results.append(fuser.update(i * 0.1, dets, cam, i * 0.1, ego))
    return results


def test_strong_lidar_alone_warns_after_confirmation_frames():
    r = run(MotionFuser(), [[det(1.0)]] * 4)
    assert [x.warning is not None for x in r] == [False, False, True, False]   # 3rd frame, then cooldown


def test_camera_alone_never_warns():
    assert all(x.warning is None for x in run(MotionFuser(), [[]] * 10, cam=1.0))


def test_weak_lidar_plus_camera_confirms():
    weak = [[det(0.5)]] * 6
    assert all(x.warning is None for x in run(MotionFuser(), weak, cam=0.0))
    assert any(x.warning for x in run(MotionFuser(), weak, cam=1.0))


def test_camera_dropped_while_driving_and_lidar_cut_while_turning():
    assert run(MotionFuser(), [[det(0.5)]], ego=MOVING, cam=1.0)[0].camera == 0.0
    assert run(MotionFuser(), [[det(1.0)]], ego=TURNING)[0].lidar == pytest.approx(0.5)


def test_stale_camera_value_ignored():
    f = MotionFuser()
    assert f.update(5.0, [det(0.5)], 1.0, camera_t=1.0, ego=STILL).camera == 0.0


def test_cooldown_suppresses_repeat_but_not_a_new_place():
    f = MotionFuser(FusionConfig(confirm_frames=1, window_frames=1, cooldown_s=5.0))
    assert f.update(0.0, [det(1.0, 1, 1)], 0, 0, STILL).warning
    assert f.update(1.0, [det(1.0, 1.2, 1)], 0, 0, STILL).warning is None
    assert f.update(2.0, [det(1.0, 9, 9)], 0, 0, STILL).warning
    assert f.update(9.0, [det(1.0, 1, 1)], 0, 0, STILL).warning


def test_ego_state_uses_larger_of_odom_and_gyro():
    cfg = FusionConfig()
    assert ego_state(cfg, 0.0, 0.0, 0.5).turning and not ego_state(cfg, 0.0, 0.0, 0.1).turning
    assert ego_state(cfg, 0.3, 0.0, 0.0).moving


@pytest.mark.parametrize("kw", [{"confirm_frames": 9}, {"camera_weight": 0.6}])
def test_bad_fusion_config_rejected(kw):
    with pytest.raises(ValueError):
        FusionConfig(**kw)


def test_unknown_yaml_key_is_reported(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("fusion:\n  lidar_wieght: 0.5\n")
    with pytest.raises(ValueError, match="lidar_wieght"):
        load_settings(p)
    assert _read_yaml(p)["fusion"]
