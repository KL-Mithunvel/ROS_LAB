#!/usr/bin/env bash
# Switch the Acrux between autostart (demo) and development mode.
#   ./dev-mode.sh on      development: disable + stop rigbetel-labs' robot_bringup.service, linger off
#   ./dev-mode.sh off     demo: linger on, enable + start the service (stack comes back up)
#   ./dev-mode.sh status
# Run as your normal user from a real terminal (NOT with local sudo): the robot's sudo asks for
# the robot password. It is never stored.
set -euo pipefail
[ "$(id -u)" -ne 0 ] || { echo "Don't run this with sudo/as root on your PC; run it as your normal user."; exit 1; }
cd "$(dirname "$0")"; source ./acrux.env; eval "KEY=$ACRUX_KEY"
MODE="${1:-status}"
case "$MODE" in on|off|status) ;; *) sed -n 2,8p "$0"; exit 1 ;; esac

# Everything runs inside ONE root shell on the robot (sudoers forbids `sudo -u X VAR=...`).
read -r -d '' REMOTE <<'RS' || true
U=rigbetel-labs; UID_=$(id -u $U); UNIT=robot_bringup.service; R=/run/user/$UID_
usr() { runuser -u $U -- env XDG_RUNTIME_DIR=$R systemctl --user "$@"; }
have_bus() { [ -S $R/bus ]; }
case "$MODE" in
  on)
    if have_bus; then usr disable $UNIT; usr stop $UNIT; else echo "(user manager already down)"; fi
    loginctl disable-linger $U
    # no bus => cannot disable via systemctl; drop the enable symlink directly as a fallback
    rm -f /home/$U/.config/systemd/user/default.target.wants/$UNIT
    sleep 3 ;;
  off)
    loginctl enable-linger $U
    for i in $(seq 1 15); do have_bus && break; sleep 1; done
    have_bus || { echo "user manager did not start"; exit 1; }
    usr enable $UNIT; usr start $UNIT; sleep 2 ;;
esac
echo "--- state"
echo "linger: $(loginctl show-user $U -p Linger --value 2>/dev/null || echo no-user-session)"
if have_bus; then echo "service: enabled=$(usr is-enabled $UNIT 2>&1) active=$(usr is-active $UNIT 2>&1)"
else echo "service: user manager down (development mode: nothing autostarts)"; fi
echo "robot procs: $(pgrep -fc 'micro_ros_agent|nav2_|cartographer|ydlidar_ros2' || true)"
RS
if [ -n "${ACRUX_SUDO_PW:-}" ]; then   # automation (acrux_gui.py): password on stdin, no TTY
  printf '%s\n' "$ACRUX_SUDO_PW" | ssh -i "$KEY" -o BatchMode=yes "$ACRUX_USER@$ACRUX_HOST" \
    "sudo -S -p '' MODE=$MODE bash -c $(printf %q "$REMOTE")"
else
  ssh -t -i "$KEY" "$ACRUX_USER@$ACRUX_HOST" "sudo MODE=$MODE bash -c $(printf %q "$REMOTE")"
fi
