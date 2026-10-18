#!/usr/bin/env bash
# One command: SSH into the Acrux, make sure a VNC desktop is running, tunnel it, open a viewer.
#   ./vnc.sh            start (installs server on first run), tunnel and open viewer
#   ./vnc.sh stop       close tunnel and stop the robot's VNC session
#   ./vnc.sh status
# VNC listens on the robot's localhost only; access is via the SSH tunnel (key auth).
set -euo pipefail
cd "$(dirname "$0")"; source ./acrux.env; eval "KEY=$ACRUX_KEY"
DISPLAY_NUM="${VNC_DISPLAY:-1}"; PORT=$((5900 + DISPLAY_NUM)); LOCAL_PORT="${VNC_LOCAL_PORT:-$PORT}"
GEOM="${VNC_GEOMETRY:-1600x900}"
TARGET="$ACRUX_USER@$ACRUX_HOST"
CTL="/tmp/acrux-vnc-tunnel"
SSH=(ssh -i "$KEY" -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)

[ -f "$KEY" ] || { echo "No key yet - run ./setup-key.sh first"; exit 1; }

tunnel_up() { ssh -S "$CTL" -O check "$TARGET" >/dev/null 2>&1; }

case "${1:-start}" in
  stop)
    tunnel_up && ssh -S "$CTL" -O exit "$TARGET" 2>/dev/null && echo "tunnel closed" || true
    "${SSH[@]}" -o BatchMode=yes "$TARGET" "vncserver -kill :$DISPLAY_NUM 2>&1 | tail -1" || true
    exit 0 ;;
  status)
    tunnel_up && echo "tunnel: UP (localhost:$LOCAL_PORT)" || echo "tunnel: down"
    "${SSH[@]}" -o BatchMode=yes "$TARGET" "vncserver -list 2>&1 | tail -4"
    exit 0 ;;
  start) ;;
  *) sed -n 2,7p "$0"; exit 1 ;;
esac

# 1. server installed? (apt needs your sudo password - typed at the prompt, never stored)
if ! "${SSH[@]}" -o BatchMode=yes "$TARGET" 'command -v vncserver >/dev/null && command -v startxfce4 >/dev/null'; then
  echo ">> Installing TigerVNC + XFCE on the robot (one time, ~400 MB). sudo will ask for the robot password."
  "${SSH[@]}" -t "$TARGET" 'sudo apt-get update && sudo apt-get install -y tigervnc-standalone-server tigervnc-common xfce4 xfce4-terminal dbus-x11'
fi

# 2. one-time config: xstartup + VNC password (prompted on the robot, stored hashed in ~/.vnc/passwd)
"${SSH[@]}" -o BatchMode=yes "$TARGET" 'mkdir -p ~/.vnc; [ -f ~/.vnc/xstartup ] || { printf "#!/bin/sh\nunset SESSION_MANAGER DBUS_SESSION_BUS_ADDRESS\nexec dbus-launch --exit-with-session startxfce4\n" > ~/.vnc/xstartup; chmod +x ~/.vnc/xstartup; }'
if ! "${SSH[@]}" -o BatchMode=yes "$TARGET" 'test -s ~/.vnc/passwd'; then
  echo ">> Choose a VNC password (6-8 chars, used by the viewer):"
  "${SSH[@]}" -t "$TARGET" 'vncpasswd'
fi

# 3. start session on localhost only, if not already running
"${SSH[@]}" -o BatchMode=yes "$TARGET" "vncserver -list 2>/dev/null | grep -q ':$DISPLAY_NUM' || vncserver :$DISPLAY_NUM -localhost yes -geometry $GEOM -depth 24 2>&1 | tail -3"

# 4. tunnel
tunnel_up || ssh -i "$KEY" -f -N -M -S "$CTL" -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new \
                 -L "127.0.0.1:$LOCAL_PORT:127.0.0.1:$PORT" "$TARGET"
echo ">> VNC ready:  localhost:$LOCAL_PORT   (display :$DISPLAY_NUM on $ACRUX_HOST)"

# 5. viewer
# VNC_PASSWD_FILE = file made with `vncpasswd -f` (skips the password dialog; used for scripted tests)
VARGS=(); [ -n "${VNC_PASSWD_FILE:-}" ] && VARGS=(-passwd "$VNC_PASSWD_FILE")
for v in vncviewer xtigervncviewer; do
  command -v "$v" >/dev/null && { exec "$v" "${VARGS[@]}" "localhost:$LOCAL_PORT"; }
done
if command -v remmina >/dev/null; then exec remmina -c "vnc://localhost:$LOCAL_PORT"; fi
echo "No VNC viewer found locally. Install one (sudo apt install tigervnc-viewer) or connect any viewer to localhost:$LOCAL_PORT"
