#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-9001}"

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"

if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
  PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[WEBHOOK] Python not found. Install Python 3 or activate your virtualenv." >&2
  exit 1
fi

echo "[WEBHOOK] starting receiver"
echo "[WEBHOOK] address: http://${HOST}:${PORT}"
echo "[WEBHOOK] tenant_A view: http://${HOST}:${PORT}/alerts/tenant_A/view"
echo "[WEBHOOK] Python: ${PYTHON_BIN}"
exec "$PYTHON_BIN" -m uvicorn services.webhook_receiver.app:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload \
  --reload-dir services
