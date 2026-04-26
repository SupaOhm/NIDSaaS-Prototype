#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

BASE_URL="${WEBHOOK_BASE_URL:-http://localhost:9001}"
URL="${BASE_URL}/webhook/tenant_A"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if ! curl -sS --connect-timeout 5 --max-time 10 "${BASE_URL}/" >/dev/null; then
  echo "[TEST] Webhook receiver not reachable at ${BASE_URL}" >&2
  exit 1
fi

echo "[TEST] posting fake alert directly to ${URL}"
curl -sS --connect-timeout 5 --max-time 20 \
  -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"alert_id\": \"direct-debug-${TIMESTAMP}\",
    \"tenant_id\": \"tenant_A\",
    \"source_id\": \"debug_source\",
    \"severity\": \"high\",
    \"prediction\": \"attack\",
    \"attack_type\": \"debug_direct_webhook\",
    \"evidence\": \"Direct webhook debug test\",
    \"timestamp\": \"${TIMESTAMP}\"
  }"

printf '\n[TEST] view alerts at %s/alerts/tenant_A/view\n' "$BASE_URL"
