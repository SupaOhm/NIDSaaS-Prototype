#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

status_line() {
  local state="$1"
  local label="$2"
  local detail="${3:-}"
  if [[ -n "$detail" ]]; then
    printf '[%s] %s %s\n' "$state" "$label" "$detail"
  else
    printf '[%s] %s\n' "$state" "$label"
  fi
}

pid_status() {
  local name="$1"
  local pid_file=".pids/${name}.pid"
  if [[ ! -f "$pid_file" ]]; then
    status_line "INFO" "$name" "no PID file"
    return
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    local command
    command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    status_line "OK" "$name" "pid=${pid} ${command}"
  else
    status_line "FAIL" "$name" "pid=${pid:-missing} not running"
  fi
}

process_status() {
  local label="$1"
  local pattern="$2"
  local pids
  pids="$(pgrep -f "$pattern" 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]*$//' || true)"
  if [[ -n "$pids" ]]; then
    status_line "OK" "$label" "pid(s)=${pids}"
  else
    status_line "INFO" "$label" "not running"
  fi
}

port_status() {
  local port="$1"
  local label="$2"
  if ! command -v lsof >/dev/null 2>&1; then
    status_line "INFO" "$label" "port ${port}: lsof not found"
    return
  fi

  local listeners
  listeners="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR > 1 {print $1 "/" $2}' | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//' || true)"
  if [[ -n "$listeners" ]]; then
    status_line "OK" "$label" "port ${port}: ${listeners}"
  else
    status_line "INFO" "$label" "port ${port}: no listener"
  fi
}

endpoint_status() {
  local label="$1"
  local url="$2"
  if curl -fsS --connect-timeout 2 --max-time 5 "$url" >/dev/null 2>&1; then
    status_line "OK" "$label" "$url"
  else
    status_line "FAIL" "$label" "$url"
  fi
}

alert_count() {
  local tenant_id="$1"
  local url="http://localhost:9001/alerts/${tenant_id}"
  local count
  count="$(
    curl -fsS --connect-timeout 2 --max-time 5 "$url" 2>/dev/null |
      python3 -c 'import json, sys; print(len(json.load(sys.stdin).get("alerts", [])))' 2>/dev/null || true
  )"
  if [[ -n "$count" ]]; then
    status_line "OK" "alerts ${tenant_id}" "count=${count}"
  else
    status_line "INFO" "alerts ${tenant_id}" "webhook not reachable"
  fi
}

echo "[INFRA] Docker containers"
if docker compose config --quiet >/dev/null 2>&1; then
  compose_output="$(docker compose ps --all 2>/dev/null || true)"
  for service in zookeeper kafka kafka-ui; do
    line="$(printf '%s\n' "$compose_output" | grep -E "(^|_)${service}([[:space:]]|$)" || true)"
    if [[ -n "$line" ]]; then
      status_line "INFO" "$service" "$line"
    else
      status_line "INFO" "$service" "not created"
    fi
  done
else
  for service in zookeeper kafka kafka-ui; do
    status_line "FAIL" "$service" "docker compose unavailable"
  done
fi

echo
echo "[SERVICE] Local services"
pid_status "gateway"
pid_status "webhook_receiver"
process_status "spark processor" 'spark-submit|services/spark_stream/stream_upload_events.py|run_spark_processor.sh'
process_status "alert delivery" 'services.alert_delivery.delivery|run_alert_delivery.sh'

echo
echo "[SERVICE] Open ports"
port_status 8000 "gateway"
port_status 9001 "webhook"
port_status 8080 "Kafka UI"
port_status 4040 "Spark UI"

echo
echo "[SERVICE] Endpoint checks"
endpoint_status "Gateway health" "http://localhost:8000/health"
endpoint_status "Webhook UI" "http://localhost:9001/"
endpoint_status "Kafka UI" "http://localhost:8080/"
endpoint_status "Spark UI" "http://localhost:4040/"

echo
echo "[KAFKA] Tenant topics"
if docker compose exec -T kafka kafka-topics --bootstrap-server kafka:29092 --list >/dev/null 2>&1; then
  topics="$(docker compose exec -T kafka kafka-topics --bootstrap-server kafka:29092 --list 2>/dev/null || true)"
  raw_topics="$(printf '%s\n' "$topics" | grep '^raw\.tenant\.' || true)"
  alert_topics="$(printf '%s\n' "$topics" | grep '^alert\.tenant\.' || true)"
  if [[ -n "$raw_topics" ]]; then
    printf '%s\n' "$raw_topics" | sed 's/^/[KAFKA] raw    /'
  else
    echo "[KAFKA] raw    none"
  fi
  if [[ -n "$alert_topics" ]]; then
    printf '%s\n' "$alert_topics" | sed 's/^/[KAFKA] alert  /'
  else
    echo "[KAFKA] alert  none"
  fi
else
  echo "[KAFKA] unavailable; start with ./scripts/demo/start_infra.sh"
fi

echo
echo "[WEBHOOK] Alert counts"
alert_count "tenant_A"
alert_count "tenant_B"
