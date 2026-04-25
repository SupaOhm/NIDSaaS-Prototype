#!/usr/bin/env bash
set -euo pipefail

export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export TOPIC="${TOPIC:-raw.tenant.tenant_A}"
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
  echo "[CONSUMER] Python not found. Install Python 3 or activate your virtualenv." >&2
  exit 1
fi

echo "[CONSUMER] launching local Kafka consumer"
echo "[CONSUMER] Kafka bootstrap servers: ${KAFKA_BOOTSTRAP_SERVERS}"
echo "[CONSUMER] topic: ${TOPIC}"
echo "[CONSUMER] Python: ${PYTHON_BIN}"
exec "$PYTHON_BIN" -m services.consumer.consumer
