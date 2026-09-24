#!/usr/bin/env bash
# Run a command on a lab server with key-only SSH auth.
#
#   scripts/ssh_run.sh <port> '<remote command>'
#
# BatchMode=yes: never prompts for, stores, or sends a password.  Host/user/key
# come from the environment or from ~/.config/heurbridge/servers.sh (outside the
# repo).  Ports 223-234 map to different nodes; 224 is the EDA node.
set -euo pipefail
PORT="${1:?usage: ssh_run.sh <port> '<cmd>'}"; shift
[ -f "$HOME/.config/heurbridge/servers.sh" ] && . "$HOME/.config/heurbridge/servers.sh"
: "${HB_SSH_HOST:?set HB_SSH_HOST (or ~/.config/heurbridge/servers.sh)}"
: "${HB_SSH_USER:?set HB_SSH_USER}"
KEY="${HB_SSH_KEY:-$HOME/.ssh/id_ed25519_heurbridge}"
exec ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=15 \
  -o ServerAliveInterval=30 -o StrictHostKeyChecking=accept-new \
  -o ControlMaster=auto -o "ControlPath=$HOME/.ssh/cm-hb-%C" -o ControlPersist=10m \
  -p "$PORT" "$HB_SSH_USER@$HB_SSH_HOST" "$@"
