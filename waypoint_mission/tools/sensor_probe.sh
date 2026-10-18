#!/usr/bin/env bash
# Runs ON the robot (pushed by sensor-test.sh). Prints PASS/LOW/FAIL per topic. Usage: sensor_probe.sh lidar|camera|all
source /opt/ros/humble/setup.bash
export FASTRTPS_DEFAULT_PROFILES_FILE=$HOME/fastdds_udp.xml
WHAT="${1:-all}"

rate() { timeout 10 ros2 topic hz "$1" --qos-reliability best_effort --window 10 2>&1 | grep -m1 'average rate' | awk '{print $3}'; }
verdict() {  # topic min_hz
  local r; r="$(rate "$1")"
  if [ -z "$r" ]; then printf '%-5s %-36s NO DATA\n' FAIL "$1"
  elif awk -v r="$r" -v m="$2" 'BEGIN{exit !(r>=m)}'; then printf '%-5s %-36s %.1f Hz (min %s)\n' PASS "$1" "$r" "$2"
  else printf '%-5s %-36s %.1f Hz (min %s)\n' LOW "$1" "$r" "$2"; fi
}

if [ "$WHAT" = lidar ] || [ "$WHAT" = all ]; then
  echo "== lidar (YDLidar X2)"
  verdict /scan 5
  python3 - <<'PY'
import math, rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rclpy.qos import qos_profile_sensor_data
rclpy.init(); n = Node('scan_probe'); got = []
n.create_subscription(LaserScan, '/scan', got.append, qos_profile_sensor_data)
for _ in range(40):
    rclpy.spin_once(n, timeout_sec=0.25)
    if got: break
if not got: print('FAIL  /scan content: NO DATA')
else:
    m = got[0]; r = [x for x in m.ranges if math.isfinite(x) and m.range_min < x < m.range_max]
    pct = 100.0 * len(r) / max(1, len(m.ranges))
    print(f"{'PASS' if pct > 30 else 'LOW '}  /scan content: {len(r)}/{len(m.ranges)} valid beams ({pct:.0f}%), "
          f"nearest {min(r):.2f} m, farthest {max(r):.2f} m, frame {m.header.frame_id}" if r else "FAIL  /scan content: no valid ranges")
PY
fi

if [ "$WHAT" = camera ] || [ "$WHAT" = all ]; then
  # realsense2_camera >= 4.56 publishes under /camera/camera/*, older under /camera/*
  CAM="$(ros2 topic list 2>/dev/null | grep -m1 -E '/color/image_raw$' | sed 's#/color/image_raw$##')"
  CAM="${CAM:-/camera}"; export CAM
  echo "== camera (RealSense D435i)  prefix: $CAM"
  python3 - <<'PY'
import os, time, rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data as Q
from sensor_msgs.msg import Image, PointCloud2
CAM = os.environ.get('CAM', '/camera')
rclpy.init(); n = Node('rate_probe')
topics = [(CAM + '/color/image_raw', Image, 10), (CAM + '/depth/image_rect_raw', Image, 10),
          (CAM + '/depth/color/points', PointCloud2, 5)]
cnt = {t: 0 for t, _, _ in topics}
for t, ty, _ in topics:
    n.create_subscription(ty, t, (lambda m, t=t: cnt.__setitem__(t, cnt[t] + 1)), Q)
t0 = time.time()
while time.time() - t0 < 6: rclpy.spin_once(n, timeout_sec=0.1)
dt = time.time() - t0
for t, _, mn in topics:
    r = cnt[t] / dt
    tag = 'FAIL' if cnt[t] == 0 else ('PASS' if r >= mn else 'LOW ')
    print(f'{tag}  {t:<36} ' + ('NO DATA' if cnt[t] == 0 else f'{r:.1f} Hz (min {mn})'))
PY
  ros2 topic list 2>/dev/null | grep -q "^$CAM/imu$" && verdict $CAM/imu 50 || echo 'SKIP  imu (IMU stream not enabled)'
  python3 - <<'PY'
import os, struct, rclpy
CAM = os.environ.get('CAM', '/camera')
from rclpy.node import Node
from sensor_msgs.msg import Image, Imu
from rclpy.qos import qos_profile_sensor_data as Q
rclpy.init(); n = Node('cam_probe'); d = []; c = []; i = []
n.create_subscription(Image, CAM + '/depth/image_rect_raw', d.append, Q)
n.create_subscription(Image, CAM + '/color/image_raw', c.append, Q)
n.create_subscription(Imu, CAM + '/imu', i.append, Q)
for _ in range(60):
    rclpy.spin_once(n, timeout_sec=0.2)
    if d and c and i: break
if d:
    m = d[0]; cx, cy = m.width // 2, m.height // 2
    vals = []
    for dy in range(-5, 6):
        for dx in range(-5, 6):
            o = (cy + dy) * m.step + (cx + dx) * 2
            v = struct.unpack_from('<H', bytes(m.data), o)[0]
            if v: vals.append(v)
    print(f"{'PASS' if vals else 'LOW '}  depth centre 11x11: {len(vals)}/121 valid, median "
          f"{sorted(vals)[len(vals)//2] if vals else 0} mm  ({m.width}x{m.height}, {m.encoding})")
else: print('FAIL  depth image: NO DATA')
if c:
    m = c[0]; px = bytes(m.data); mean = sum(px[::97]) / len(px[::97])
    print(f"{'PASS' if 5 < mean < 250 else 'LOW '}  colour mean brightness {mean:.0f}/255 ({m.width}x{m.height}, {m.encoding})")
else: print('FAIL  colour image: NO DATA')
if i:
    a = i[0].linear_acceleration
    g = (a.x**2 + a.y**2 + a.z**2) ** 0.5
    print(f"{'PASS' if 8.5 < g < 11 else 'LOW '}  IMU |accel| {g:.2f} m/s^2 (expect ~9.8 at rest)")
else: print('SKIP  IMU (not enabled or no data)')
PY
fi
