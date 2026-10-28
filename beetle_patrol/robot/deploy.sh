#!/usr/bin/env bash
# Sync beetle_patrol/robot/ to the robot. ONLY rsync; starts/kills nothing.
# Default is a dry run. Use --go to really transfer.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HERE/../secrets.env"
MODE="dry"
case "${1:-}" in
  ""|--dry-run) MODE="dry" ;;
  --go) MODE="go" ;;
  *) echo "usage: $0 [--dry-run|--go]" >&2; exit 2 ;;
esac

# read only the non-secret keys; the password is never read or printed
getv() { grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -n1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//' || true; }
HOST="$(getv BEETLE_HOST)"; USER_="$(getv BEETLE_USER)"; KEY="$(getv BEETLE_KEY)"
HOST="${HOST:-192.168.0.154}"; USER_="${USER_:-veerobot}"; KEY="${KEY:-~/.ssh/beetlebot_ed25519}"
KEY="${KEY/#\~/$HOME}"; KEY="${KEY/#\$HOME/$HOME}"   # secrets.env may hold ~ or a literal $HOME
[ -f "$KEY" ] || { echo "ssh key not found: $KEY" >&2; exit 1; }

DEST="$USER_@$HOST:~/patrol_ws/beetle_patrol_robot/"
FLAGS=(-av --delete --exclude '__pycache__' --exclude '*.pyc')
[ "$MODE" = "dry" ] && FLAGS+=(-n)
echo "mode=$MODE  src=$HERE/  dest=$DEST"
rsync "${FLAGS[@]}" -e "ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes" "$HERE/" "$DEST"
[ "$MODE" = "dry" ] && echo "(dry run: nothing transferred; re-run with --go)"
