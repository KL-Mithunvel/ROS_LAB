#!/usr/bin/env bash
# Start the Gazebo warehouse simulation (everything except the patrol node and GUI).
#   sim_gazebo/run_gazebo_sim.sh            # Gazebo window + robot + Nav2 + arm gate + intruder
#   sim_gazebo/run_gazebo_sim.sh --headless # no Gazebo window (gzserver only)
#   sim_gazebo/run_gazebo_sim.sh --stop     # kill everything started here
# Then:  sim_gazebo/run_patrol_gz.sh        (patrol node + GUI, same environment)
# Always ROS domain 77, localhost only. Refuses real-robot domains 154/155.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS="${BEETLE_SIM_LOGS:-/tmp/beetle_gz_logs}"; mkdir -p "$LOGS"
case "${ROS_DOMAIN_ID:-}" in 154|155) echo "REFUSING: ROS_DOMAIN_ID=${ROS_DOMAIN_ID} is a REAL robot domain." >&2; exit 2;; esac
if [ "${1:-}" = "--stop" ]; then
  pkill -x gzserver; pkill -x gzclient; pkill -x component_container_isolated; pkill -f "$HERE/gate_node.py"; pkill -f "$HERE/scan_restamp.py"; pkill -f "$HERE/intruder.py"
  pkill -f static_transform_publisher; pkill -f "ros2 launch nav2_bringup"; exit 0
fi
HEADLESS=0; [ "${1:-}" = "--headless" ] && HEADLESS=1
export PATH="$(echo "$PATH" | tr ':' '\n' | grep -v '/\.venv' | paste -sd:)"
set +u; source /opt/ros/humble/setup.bash; set -u
export ROS_DOMAIN_ID=77 ROS_LOCALHOST_ONLY=1
[ -f "$HERE/worlds/warehouse.world" ] || /usr/bin/python3 "$HERE/gen_world.py"
bg() { local name=$1; shift; setsid nohup "$@" > "$LOGS/$name.log" 2>&1 & echo "started $name (log $LOGS/$name.log)"; }

GZ_ARGS=(--verbose -s libgazebo_ros_init.so -s libgazebo_ros_factory.so "$HERE/worlds/warehouse.world")
if [ $HEADLESS = 1 ]; then bg gazebo gzserver "${GZ_ARGS[@]}"; else bg gazebo gazebo "${GZ_ARGS[@]}"; fi
sleep 8
bg spawn ros2 run gazebo_ros spawn_entity.py -file "$HERE/beetlebot.sdf" -entity beetlebot -x 1.5 -y 1.5 -z 0.0 -Y 0.0
for t in "laser 0.10 0 0.19" "imu_link 0 0 0.1" "camera_link 0.18 0 0.15"; do
  set -- $t; bg "tf_$1" ros2 run tf2_ros static_transform_publisher --x "$2" --y "$3" --z "$4" --frame-id base_link --child-frame-id "$1" --ros-args -p use_sim_time:=true
done
bg gate /usr/bin/python3 "$HERE/gate_node.py" --ros-args -p use_sim_time:=true
bg restamp /usr/bin/python3 "$HERE/scan_restamp.py" --ros-args -p use_sim_time:=true
bg nav2 ros2 launch nav2_bringup bringup_launch.py map:="$HERE/maps/warehouse.yaml" params_file:="$HERE/nav2_params.yaml" use_sim_time:=true autostart:=true
bg intruder /usr/bin/python3 "$HERE/intruder.py" --delay "${INTRUDER_DELAY:-45}" --repeat "${INTRUDER_REPEAT:-60}" --ros-args -p use_sim_time:=true
echo "sim up (domain 77). Logs: $LOGS"
