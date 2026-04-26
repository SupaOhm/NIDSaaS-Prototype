#!/usr/bin/env bash
set -euo pipefail

mkdir -p logs .pids

if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
  PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[DEMO] Python not found. Install Python 3 or activate your virtualenv." >&2
  exit 1
fi

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export TOPIC="${TOPIC:-raw.tenant.tenant_A}"
export WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-http://localhost:9001}"

start_service() {
  local name="$1"
  local pid_file=".pids/${name}.pid"
  local log_file="logs/${name}.log"
  shift

  if [[ -f "$pid_file" ]]; then
    local existing_pid
    existing_pid="$(cat "$pid_file")"
    if kill -0 "$existing_pid" >/dev/null 2>&1; then
      echo "[DEMO] ${name} already running pid=${existing_pid}"
      return
    fi
    rm -f "$pid_file"
  fi

  echo "[DEMO] starting ${name}; log=${log_file}"
  nohup "$@" >"$log_file" 2>&1 &
  echo "$!" > "$pid_file"
  echo "[DEMO] ${name} pid=$(cat "$pid_file")"
}

start_service gateway \
  "$PYTHON_BIN" -m uvicorn services.gateway.app:app \
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --reload-dir services \
    --reload-dir src

start_service webhook_receiver \
  "$PYTHON_BIN" -m uvicorn services.webhook_receiver.app:app \
    --host 127.0.0.1 \
    --port 9001 \
    --reload \
    --reload-dir services

DEMO_FORCE_ATTACK=1 start_service demo_processor \
  "$PYTHON_BIN" -m services.demo_processor.processor

echo "[DEMO] services started"
echo "[DEMO] Gateway health: http://localhost:8000/health"
echo "[DEMO] Webhook UI: http://localhost:9001/"
echo "[DEMO] Tenant A alerts: http://localhost:9001/alerts/tenant_A/view"
echo "[DEMO] Tenant B alerts: http://localhost:9001/alerts/tenant_B/view"
echo "[DEMO] Run status check: ./scripts/demo_status.sh"
