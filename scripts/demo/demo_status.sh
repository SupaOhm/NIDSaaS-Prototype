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

if [[ -f ".pids/demo_processor.pid" ]]; then
  pid="$(cat .pids/demo_processor.pid)"
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "[OK]   demo_processor fallback pid=${pid}"
  else
    echo "[FAIL] demo_processor fallback pid=${pid} not running"
  fi
else
  echo "[INFO] demo_processor fallback not running"
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
