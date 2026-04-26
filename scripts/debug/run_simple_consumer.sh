#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export TOPIC="${TOPIC:-raw.tenant.tenant_A}"
export PYTHONPATH="${PYTHONPATH:-}:$REPO_ROOT/src"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[KAFKA] Python not found. Install Python 3 or create .venv." >&2
  exit 1
fi

echo "[KAFKA] launching simple debug consumer"
echo "[KAFKA] bootstrap servers: ${KAFKA_BOOTSTRAP_SERVERS}"
echo "[KAFKA] topic: ${TOPIC}"
exec "$PYTHON_BIN" -m services.consumer.consumer
