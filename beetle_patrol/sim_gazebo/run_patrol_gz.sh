#!/usr/bin/env bash
# Patrol node + GUI against the Gazebo warehouse (start run_gazebo_sim.sh first).  --no-gui = node only.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(dirname "$HERE")"
LOGS="${BEETLE_SIM_LOGS:-/tmp/beetle_gz_logs}"; mkdir -p "$LOGS"
case "${ROS_DOMAIN_ID:-}" in 154|155) echo "REFUSING: real-robot domain." >&2; exit 2;; esac
export PATH="$(echo "$PATH" | tr ':' '\n' | grep -v '/\.venv' | paste -sd:)"
set +u; source /opt/ros/humble/setup.bash; set -u
export ROS_DOMAIN_ID=77 ROS_LOCALHOST_ONLY=1
export BEETLE_PATROL_YAML="$HERE/patrol_gz.yaml" BEETLE_ZONES_YAML="$HERE/zones_gz.yaml"
cd "$ROOT"
setsid nohup /usr/bin/python3 patrol_node.py --ros-args -p use_sim_time:=true > "$LOGS/patrol_node.log" 2>&1 &
echo "patrol node started (log $LOGS/patrol_node.log)"
[ "${1:-}" = "--no-gui" ] || { setsid nohup /usr/bin/python3 beetle_gui.py > "$LOGS/gui.log" 2>&1 & echo "GUI started (log $LOGS/gui.log)"; }
