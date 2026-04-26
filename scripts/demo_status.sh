#!/usr/bin/env bash
set -euo pipefail

echo "[DEMO] Docker containers"
if docker ps --filter name=nidsaas; then
  :
else
  echo "[FAIL] Could not query Docker containers"
fi

echo
echo "[DEMO] Local service PIDs"
for name in gateway webhook_receiver demo_processor; do
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

echo
echo "[DEMO] Endpoint checks"
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
