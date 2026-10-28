#!/usr/bin/env bash
# Start the fake robot. Usage: sim/run_sim.sh [--mode fake_nav|base] [other fake_robot.py args]
# Always domain 77 + localhost only; refuses if the caller had a REAL robot domain (154/155) set.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${ROS_DOMAIN_ID:-}" in
  154|155)
    echo "REFUSING to start: ROS_DOMAIN_ID=${ROS_DOMAIN_ID} is a REAL robot domain (154/155)." >&2
    echo "Open a clean shell (or 'unset ROS_DOMAIN_ID') and run the simulator again." >&2
    exit 2 ;;
esac

MODE=fake_nav
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
case "$MODE" in
  fake_nav|base) ;;
  *) echo "--mode must be fake_nav or base (got '$MODE')" >&2; exit 2 ;;
esac

# shellcheck disable=SC1091
set +u; source /opt/ros/humble/setup.bash; set -u
export ROS_DOMAIN_ID=77 ROS_LOCALHOST_ONLY=1
echo "sim: mode=$MODE ROS_DOMAIN_ID=$ROS_DOMAIN_ID ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY"
exec /usr/bin/python3 "$HERE/fake_robot.py" --mode "$MODE" --config "$HERE/sim.yaml" ${ARGS[@]+"${ARGS[@]}"}
