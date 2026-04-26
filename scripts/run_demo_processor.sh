#!/usr/bin/env bash
set -euo pipefail

export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export TOPIC="${TOPIC:-raw.tenant.tenant_A}"
export WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-http://localhost:9001}"
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
  echo "[PROCESSOR] Python not found. Install Python 3 or activate your virtualenv." >&2
  exit 1
fi

echo "[PROCESSOR] launching demo processor"
echo "[PROCESSOR] Kafka bootstrap servers: ${KAFKA_BOOTSTRAP_SERVERS}"
if [[ -n "${KAFKA_TOPIC_PATTERN:-}" ]]; then
  echo "[PROCESSOR] topic pattern: ${KAFKA_TOPIC_PATTERN}"
else
  echo "[PROCESSOR] topic: ${TOPIC}"
fi
echo "[PROCESSOR] webhook base URL: ${WEBHOOK_BASE_URL}"
echo "[PROCESSOR] DEMO_FORCE_ATTACK: ${DEMO_FORCE_ATTACK:-0}"
echo "[PROCESSOR] Python: ${PYTHON_BIN}"
exec "$PYTHON_BIN" -m services.demo_processor.processor
