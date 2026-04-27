#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

gateway_cleared=false
webhook_cleared=false
transient_outputs_cleared=false
logs_cleared=false
api_key="${GATEWAY_API_KEY:-dev-secret}"

if curl -fsS --connect-timeout 2 --max-time 5 http://localhost:8000/health >/dev/null 2>&1; then
  if curl -fsS -X POST http://localhost:8000/admin/clear-dedupe -H "x-api-key: ${api_key}" >/dev/null; then
    echo "[RESET] cleared gateway dedupe"
    gateway_cleared=true
  else
    echo "[RESET] gateway reachable but clear-dedupe failed" >&2
  fi
else
  echo "[RESET] gateway not running; skipped dedupe clear"
fi

if curl -fsS --connect-timeout 2 --max-time 5 http://localhost:9001/ >/dev/null 2>&1; then
  if curl -fsS -X POST http://localhost:9001/admin/clear-alerts >/dev/null; then
    echo "[RESET] cleared webhook alerts"
    webhook_cleared=true
  else
    echo "[RESET] webhook reachable but clear-alerts failed" >&2
  fi
else
  echo "[RESET] webhook receiver not running; skipped alert clear"
fi

clear_path() {
  local path="$1"
  if [[ -e "$path" ]]; then
    find "$path" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    echo "[RESET] cleared ${path}/*"
    transient_outputs_cleared=true
  else
    mkdir -p "$path"
    echo "[RESET] created empty ${path}/"
    transient_outputs_cleared=true
  fi
}

clear_path "outputs/live_flows"
clear_path "outputs/mining"

if [[ -f "outputs/gateway_events.jsonl" ]]; then
  rm -f "outputs/gateway_events.jsonl"
  echo "[RESET] removed outputs/gateway_events.jsonl"
  transient_outputs_cleared=true
else
  echo "[RESET] skipped outputs/gateway_events.jsonl; file missing"
fi

echo "[RESET] cleared transient outputs"

if [[ "${CLEAR_LOGS:-0}" == "1" ]]; then
  if compgen -G "logs/*.log" >/dev/null; then
    rm -f logs/*.log
    echo "[RESET] removed logs/*.log"
    logs_cleared=true
  else
    echo "[RESET] skipped logs/*.log; no logs present"
  fi
else
  echo "[RESET] kept logs/*.log; set CLEAR_LOGS=1 to clear transient logs"
fi

echo "[RESET] kept trained artifacts"
echo "[RESET] kept outputs/offline_adapter_test/"
echo "[RESET] kept data/csv/ data/pcap/ data/samples/"
printf '[RESET] summary: gateway=%s webhook=%s transient_outputs=%s logs=%s\n' \
  "$gateway_cleared" "$webhook_cleared" "$transient_outputs_cleared" "$logs_cleared"
