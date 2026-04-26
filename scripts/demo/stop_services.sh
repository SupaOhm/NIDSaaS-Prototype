#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

stop_service() {
  local name="$1"
  local pid_file=".pids/${name}.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "[SERVICE] ${name}: no PID file"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "[SERVICE] stopping ${name} pid=${pid}"
    kill "$pid" >/dev/null 2>&1 || true
  else
    echo "[SERVICE] ${name}: pid=${pid} is not running"
  fi
  rm -f "$pid_file"
}

stop_service gateway
stop_service webhook_receiver
stop_service demo_processor

echo "[SERVICE] local services stopped"
echo "[SERVICE] Docker infrastructure is still running."
echo "[SERVICE] Run ./scripts/demo/stop_infra.sh to stop Kafka/Zookeeper/Kafka UI."
