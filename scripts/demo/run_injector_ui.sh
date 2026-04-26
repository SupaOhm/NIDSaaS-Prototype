#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[PORTAL] Python not found. Install Python 3 or create .venv." >&2
  exit 1
fi

export PYTHONPATH="${PYTHONPATH:-}:$REPO_ROOT/src"

HOST="${INJECTOR_UI_HOST:-127.0.0.1}"
PORT="${INJECTOR_UI_PORT:-7000}"

echo "[PORTAL] starting tenant portal"
echo "[PORTAL] URL: http://localhost:${PORT}"
exec "$PYTHON_BIN" -m uvicorn services.injector_ui.app:app \
  --host "$HOST" \
  --port "$PORT"
