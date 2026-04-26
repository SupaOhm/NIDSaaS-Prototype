#!/usr/bin/env bash
set -euo pipefail

stop_service() {
  local name="$1"
  local pid_file=".pids/${name}.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "[DEMO] ${name}: no PID file"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "[DEMO] stopping ${name} pid=${pid}"
    kill "$pid" >/dev/null 2>&1 || true
  else
    echo "[DEMO] ${name}: pid=${pid} is not running"
  fi
  rm -f "$pid_file"
}

stop_service gateway
stop_service webhook_receiver
stop_service demo_processor

echo "[DEMO] local demo services stopped"
echo "[DEMO] Docker infrastructure is still running."
echo "[DEMO] Run ./scripts/stop_kafka.sh if you want to stop Kafka/Zookeeper/Kafka UI."
