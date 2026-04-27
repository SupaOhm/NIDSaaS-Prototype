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
  echo "[DELIVERY] Python not found. Install Python 3 or create .venv." >&2
  exit 1
fi

export PYTHONPATH="${REPO_ROOT}/src:${REPO_ROOT}:${PYTHONPATH:-}"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export KAFKA_TOPIC_PATTERN="${KAFKA_TOPIC_PATTERN:-alert.tenant.*}"
export WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-http://localhost:9001}"
export ALERT_DELIVERY_START_FROM_BEGINNING="${ALERT_DELIVERY_START_FROM_BEGINNING:-0}"

echo "[DELIVERY] starting alert delivery service"
echo "[DELIVERY] Kafka bootstrap servers: ${KAFKA_BOOTSTRAP_SERVERS}"
echo "[DELIVERY] topic pattern: ${KAFKA_TOPIC_PATTERN}"
echo "[DELIVERY] webhook base URL: ${WEBHOOK_BASE_URL}"
echo "[DELIVERY] ALERT_DELIVERY_START_FROM_BEGINNING: ${ALERT_DELIVERY_START_FROM_BEGINNING}"

exec "$PYTHON_BIN" -m services.alert_delivery.delivery
