#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "[clean_env] Stopping server on 8080 if running..."
lsof -ti :8080 | xargs kill -9 2>/dev/null || true

echo "[clean_env] Removing virtual environment..."
rm -rf .venv

echo "[clean_env] (Optional) Remove caches (press Ctrl+C to skip in 3s)"
sleep 3 || true
rm -rf __pycache__ **/__pycache__ 2>/dev/null || true

echo "[clean_env] Done. Re-run scripts/setup_web.sh to set up again."

