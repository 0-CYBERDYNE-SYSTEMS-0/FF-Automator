#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -d .venv ]]; then
  echo "[update_deps] venv not found. Run scripts/setup_web.sh first." >&2
  exit 1
fi

source .venv/bin/activate

echo "[update_deps] Updating project and web interface dependencies..."
uv pip install --upgrade --editable .
uv pip install --upgrade -r web_interface/requirements.txt

echo "[update_deps] Done."

