#!/usr/bin/env bash
# Sync this repo to a server (code + configs + docs; not local venvs or run artifacts).
#
#   scripts/sync_to_server.sh [port] [remote_dir]
#
# Default: port 224, /data/dzy/heura_repr/heurbridge (next to the HA-PR eda/ harness).
set -euo pipefail
PORT="${1:-224}"
REMOTE_DIR="${2:-/data/dzy/heura_repr/heurbridge}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$HOME/.config/heurbridge/servers.sh" ] && . "$HOME/.config/heurbridge/servers.sh"
: "${HB_SSH_HOST:?}"; : "${HB_SSH_USER:?}"
KEY="${HB_SSH_KEY:-$HOME/.ssh/id_ed25519_heurbridge}"
SSH="ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes -o ControlMaster=auto -o ControlPath=$HOME/.ssh/cm-hb-%C -o ControlPersist=10m -p $PORT"
"$ROOT/scripts/ssh_run.sh" "$PORT" "mkdir -p '$REMOTE_DIR'"
rsync -az -e "$SSH" \
  --exclude '.git/' --exclude '.venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' \
  --exclude '.hypothesis/' --exclude 'papers/' --exclude '*.pdf' --exclude 'v1.2_audit_response/' \
  --exclude 'logs/' --exclude 'archive/db/' --exclude 'archive/blobs/' --exclude 'archive/programs/' \
  --exclude 'data/' --exclude 'benchmarks/' --exclude 'runs/' --exclude 'checkpoints/' --exclude '.DS_Store' \
  "$ROOT/" "$HB_SSH_USER@$HB_SSH_HOST:$REMOTE_DIR/"
echo "SYNC_OK port=$PORT dir=$REMOTE_DIR git=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo none)"
