#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "[setup_web] Ensuring uv is installed..."
if ! command -v uv >/dev/null 2>&1; then
  brew install uv
fi

echo "[setup_web] Creating virtual environment..."
uv venv
source .venv/bin/activate

echo "[setup_web] Installing project (editable)..."
uv pip install --editable .

echo "[setup_web] Installing web interface requirements..."
uv pip install -r web_interface/requirements.txt

if [[ ! -f .env ]]; then
  echo "[setup_web] Creating .env (edit with your API keys)"
  cat > .env <<EOF
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
DEFAULT_LLM_PROVIDER=OpenAI
DEFAULT_LLM_MODEL=gpt-4.1
WEB_HOST=127.0.0.1
WEB_PORT=8080
EOF
fi

echo "[setup_web] Done. Use scripts/run_web.sh to start the server."

