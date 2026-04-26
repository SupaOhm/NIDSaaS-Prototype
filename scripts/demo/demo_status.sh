#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "[INFRA] Docker containers"
if docker ps --filter name=nidsaas; then
  :
else
  echo "[FAIL] Could not query Docker containers"
fi

echo
echo "[SERVICE] Local service PIDs"
for name in gateway webhook_receiver; do
  pid_file=".pids/${name}.pid"
  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "[OK]   ${name} pid=${pid}"
    else
      echo "[FAIL] ${name} pid=${pid} not running"
    fi
  else
    echo "[FAIL] ${name} no PID file"
  fi
done

for name in demo_processor injector_ui; do
  pid_file=".pids/${name}.pid"
  label="${name}"
  [[ "$name" == "injector_ui" ]] && label="injector_ui optional/future"
  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "[OK]   ${label} pid=${pid}"
    else
      echo "[FAIL] ${label} pid=${pid} not running"
    fi
  else
    echo "[INFO] ${label} not running"
  fi
done

echo
echo "[SERVICE] Local port listeners"
if command -v lsof >/dev/null 2>&1; then
  for port in 7000 8000 9001; do
    echo "[PORT] ${port}"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || echo "[PORT] ${port} no listener"
  done
else
  echo "[INFO] lsof not found"
fi

echo
echo "[SERVICE] Endpoint checks"
if curl -sS --connect-timeout 3 --max-time 5 http://localhost:8000/health >/dev/null; then
  echo "[OK]   Gateway health: http://localhost:8000/health"
else
  echo "[FAIL] Gateway health: http://localhost:8000/health"
fi

if curl -sS --connect-timeout 3 --max-time 5 http://localhost:9001/ >/dev/null; then
  echo "[OK]   Webhook UI: http://localhost:9001/"
else
  echo "[FAIL] Webhook UI: http://localhost:9001/"
fi

echo
echo "[SPARK] Main processor runs in the foreground:"
echo "[SPARK] ./scripts/demo/run_spark_processor.sh"
echo "[SPARK] Spark is not tracked by .pids because it should stay visible in its own terminal."
