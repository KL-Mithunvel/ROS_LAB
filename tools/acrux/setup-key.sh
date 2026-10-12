#!/usr/bin/env bash
# One-time: create an SSH key and install it on the robot. You type the robot
# password once at the ssh-copy-id prompt; it is never stored anywhere.
set -euo pipefail
cd "$(dirname "$0")"; source ./acrux.env
eval "KEY=$ACRUX_KEY"
[ -f "$KEY" ] || ssh-keygen -t ed25519 -N "" -C "acrux-lab@$(hostname)" -f "$KEY"
ssh-copy-id -i "$KEY.pub" -o StrictHostKeyChecking=accept-new "$ACRUX_USER@$ACRUX_HOST"
echo "Key installed. Test with: ./acrux status"
