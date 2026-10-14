#!/usr/bin/env bash
# Bring up and sanity-test the Acrux sensors without the full autostart stack.
#   ./sensor-test.sh preflight          read-only: USB, device nodes, firmware, free ports/processes
#   ./sensor-test.sh start [lidar|camera|all]   launch drivers (default: all)
#   ./sensor-test.sh check [lidar|camera|all]   rates + content sanity, PASS/FAIL per topic
#   ./sensor-test.sh stop               stop the drivers started here
#   ./sensor-test.sh run                start -> warm-up -> check -> stop
#   SENSOR_IMU=true ./sensor-test.sh start camera   also enable the D435i IMU (needs udev rules, see README)
# Drivers run as rigbetel-labs (owns the serial/camera permissions and the built workspace), so `start`
# and `stop` use the robot's sudo: run from a real terminal and type the robot password when asked.
set -euo pipefail
cd "$(dirname "$0")"; source ./acrux.env; eval "KEY=$ACRUX_KEY"
CMD="${1:-preflight}"; WHAT="${2:-all}"
OWNER=rigbetel-labs; OWS=/home/$OWNER/ros2_ws
ACRUX=./acrux
[ "$(id -u)" -ne 0 ] || { echo "Run as your normal user, not root."; exit 1; }

root_sh() {   # run a bash snippet as root on the robot (TTY prompt, or ACRUX_SUDO_PW env for automation)
  if [ -n "${ACRUX_SUDO_PW:-}" ]; then
    printf '%s\n' "$ACRUX_SUDO_PW" | $ACRUX run "sudo -S -p '' bash -c $(printf %q "$1")"
  else
    ssh -t -i "$KEY" "$ACRUX_USER@$ACRUX_HOST" "sudo bash -c $(printf %q "$1")"
  fi
}

preflight() {
  $ACRUX run '
    echo "== devices";  ls -l /dev/lidar /dev/esp 2>&1; ls /dev/video* 2>/dev/null | wc -l | sed "s/^/video nodes: /"
    echo "== usb";      lsusb | grep -i -E "realsense|cp210" ; lsusb -t | grep -E "uvcvideo" | head -1
    echo "== power";    (cat /sys/class/power_supply/*/status 2>/dev/null | head -1); uptime
    echo "== busy ports"; for d in /dev/lidar /dev/ttyUSB1; do fuser -v $d 2>&1 | tail -2; done; true
    echo "== running drivers"; pgrep -af "ydlidar_ros2_driver_node|realsense2_camera_node|micro_ros_agent" | cut -c1-110 || echo none
    echo "== temps"; for z in /sys/class/thermal/thermal_zone*/temp; do echo -n "$(cat ${z%temp}type): "; echo $(( $(cat $z)/1000 ))C; done 2>/dev/null | sort -u | head -5
  '
}

start() {
  local script="set -e; sudo_user() { runuser -u $OWNER -- bash -lc \"\$1\"; }"
  script+="; mkdir -p /tmp/sensor_test; chmod 777 /tmp/sensor_test"
  if [ "$WHAT" = lidar ] || [ "$WHAT" = all ]; then
    script+="; pgrep -f '[y]dlidar_ros2_driver_node' >/dev/null && echo 'lidar already running' || { setsid -f runuser -u $OWNER -- bash -lc 'source $OWS/install/setup.bash; exec ros2 launch ydlidar_ros2_driver ydlidar_launch.py params_file:=$OWS/src/acrux/acrux_firmware/config/x2_params.yaml' > /tmp/sensor_test/lidar.log 2>&1; echo 'lidar started'; }"
  fi
  if [ "$WHAT" = base ]; then   # micro-ROS agent = motor/encoder bridge (development mode only; not part of "all")
    script+="; pgrep -f '[l]ib/micro_ros_agent/micro_ros_agent' >/dev/null && echo 'base already running' || { setsid -f runuser -u $OWNER -- bash -lc 'source $OWS/install/setup.bash; exec ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/esp -b 921600' > /tmp/sensor_test/base.log 2>&1; echo 'base started'; }"
  fi
  if [ "$WHAT" = camera ] || [ "$WHAT" = all ]; then
    script+="; pgrep -f '[r]ealsense2_camera_node' >/dev/null && echo 'camera already running' || { setsid -f runuser -u $OWNER -- bash -lc 'source $OWS/install/setup.bash; exec ros2 launch realsense2_camera rs_launch.py pointcloud.enable:=true initial_reset:=${SENSOR_RESET:-false} enable_gyro:=${SENSOR_IMU:-false} enable_accel:=${SENSOR_IMU:-false} unite_imu_method:=2 depth_module.depth_profile:=640x480x15 rgb_camera.color_profile:=640x480x15' > /tmp/sensor_test/camera.log 2>&1; echo 'camera started'; }"
  fi
  root_sh "$script"
}

stop() {
  if [ "$WHAT" = base ]; then root_sh "pkill -f '[l]ib/micro_ros_agent/micro_ros_agent|[r]os2 run micro_ros_agent' || true; sleep 1; pgrep -af '[l]ib/micro_ros_agent/micro_ros_agent' || echo 'base stopped'"; return; fi
  root_sh "pkill -f '[y]dlidar_launch.py|[y]dlidar_ros2_driver_node|[r]s_launch.py|[r]ealsense2_camera_node|[s]tatic_tf_pub_laser' || true; sleep 1; pgrep -af '[y]dlidar_ros2_driver_node|[r]ealsense2_camera_node' || echo 'drivers stopped'"
}

check() {
  $ACRUX push "$(dirname "$0")/sensor_probe.sh" /tmp/sensor_probe.sh >/dev/null
  $ACRUX run "bash /tmp/sensor_probe.sh $WHAT"
}

case "$CMD" in
  preflight) preflight ;;
  start) start ;;
  check) check ;;
  stop) stop ;;
  run) start; echo "warming up 12 s..."; sleep 12; check; stop ;;
  *) sed -n 2,10p "$0"; exit 1 ;;
esac
