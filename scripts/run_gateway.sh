#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
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
  echo "[GATEWAY] Python not found. Install Python 3 or activate your virtualenv." >&2
  exit 1
fi

echo "[GATEWAY] starting FastAPI gateway"
echo "[GATEWAY] address: http://${HOST}:${PORT}"
echo "[GATEWAY] Kafka bootstrap servers: ${KAFKA_BOOTSTRAP_SERVERS}"
echo "[GATEWAY] Python: ${PYTHON_BIN}"
exec "$PYTHON_BIN" -m uvicorn services.gateway.app:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload \
  --reload-dir services \
  --reload-dir src
