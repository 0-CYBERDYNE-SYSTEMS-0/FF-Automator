#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root
SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Ensure venv exists; if not, perform one-time setup
if [[ ! -d .venv ]]; then
  echo "[run_web] No venv found. Running one-time setup..."
  bash "$REPO_ROOT/scripts/setup_web.sh"
fi

# Activate venv
source .venv/bin/activate

# Optionally free port 8080 if --restart passed
if [[ "${1:-}" == "--restart" ]]; then
  echo "[run_web] Restart requested; freeing port 8080 if in use..."
  lsof -ti :8080 | xargs kill -9 2>/dev/null || true
fi

# Start server
echo "[run_web] Starting web interface..."
python web_interface_app.py

