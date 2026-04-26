#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

mkdir -p logs .pids

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[SERVICE] Python not found. Install Python 3 or create .venv." >&2
  exit 1
fi

export PYTHONPATH="${PYTHONPATH:-}:$REPO_ROOT/src"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"

start_service() {
  local name="$1"
  local pid_file=".pids/${name}.pid"
  local log_file="logs/${name}.log"
  shift

  if [[ -f "$pid_file" ]]; then
    local existing_pid
    existing_pid="$(cat "$pid_file")"
    if kill -0 "$existing_pid" >/dev/null 2>&1; then
      echo "[SERVICE] ${name} already running pid=${existing_pid}"
      return
    fi
    rm -f "$pid_file"
  fi

  echo "[SERVICE] starting ${name}; log=${log_file}"
  nohup "$@" >"$log_file" 2>&1 &
  echo "$!" >"$pid_file"
  echo "[SERVICE] ${name} pid=$(cat "$pid_file")"
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

echo "[SERVICE] waiting for local service endpoints"
sleep 2

if curl -sS --connect-timeout 3 --max-time 5 http://localhost:8000/health >/dev/null; then
  echo "[SERVICE] OK Gateway health: http://localhost:8000/health"
else
  echo "[SERVICE] FAIL Gateway health: http://localhost:8000/health"
fi

if curl -sS --connect-timeout 3 --max-time 5 http://localhost:9001/ >/dev/null; then
  echo "[SERVICE] OK Webhook UI: http://localhost:9001/"
else
  echo "[SERVICE] FAIL Webhook UI: http://localhost:9001/"
fi

echo "[SERVICE] Run Spark processor in another terminal:"
echo "[SERVICE] ./scripts/demo/run_spark_processor.sh"
echo "[SERVICE] Optional tenant portal:"
echo "[SERVICE] ./scripts/demo/run_injector_ui.sh"
echo "[SERVICE] http://localhost:7000"
echo "[SERVICE] Tenant A alerts: http://localhost:9001/alerts/tenant_A/view"
echo "[SERVICE] Tenant B alerts: http://localhost:9001/alerts/tenant_B/view"
