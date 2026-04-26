#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

mkdir -p .pids

is_demo_process() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null | grep -E \
    'services\.(gateway\.app|webhook_receiver\.app|injector_ui\.app)|services/demo_processor|services\.demo_processor\.processor' \
    >/dev/null
}

kill_pid() {
  local pid="$1"
  local reason="$2"
  echo "[SERVICE] stopping pid=${pid} (${reason})"
  kill "$pid" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "[SERVICE] force stopping pid=${pid} (${reason})"
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
}

stop_pid_file() {
  local name="$1"
  local pid_file=".pids/${name}.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "[SERVICE] ${name}: no PID file"
    return
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    echo "[SERVICE] ${name}: empty PID file"
    rm -f "$pid_file"
    return
  fi

  kill_pid "$pid" "${name} PID file"
  rm -f "$pid_file"
}

kill_known_processes() {
  local pattern='services\.(gateway\.app|webhook_receiver\.app|injector_ui\.app)|services\.demo_processor\.processor'
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    kill_pid "$pid" "known demo uvicorn/app process"
  done < <(pgrep -f "$pattern" 2>/dev/null || true)
}

free_demo_port() {
  local port="$1"
  if ! command -v lsof >/dev/null 2>&1; then
    echo "[SERVICE] lsof not found; cannot inspect port ${port}"
    return
  fi

  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    local command="${entry%%:*}"
    local pid="${entry#*:}"
    if is_demo_process "$pid" || [[ "$command" =~ ^(Python|python|uvicorn)$ ]]; then
      kill_pid "$pid" "demo Python/uvicorn listener on port ${port}"
    else
      local cmd
      cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
      echo "[SERVICE] leaving non-demo listener on port ${port}: pid=${pid} command=${command} ${cmd}"
    fi
  done < <(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR > 1 {print $1 ":" $2}' | sort -u || true)
}

for name in gateway webhook_receiver demo_processor injector_ui; do
  stop_pid_file "$name"
done

kill_known_processes

for port in 7000 8000 9001; do
  free_demo_port "$port"
done

echo "[SERVICE] local demo services stopped"
echo "[SERVICE] Docker infrastructure is still running."
echo "[SERVICE] Run ./scripts/demo/stop_infra.sh to stop Kafka/Zookeeper/Kafka UI."
