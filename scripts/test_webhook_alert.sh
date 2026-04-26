#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${WEBHOOK_BASE_URL:-http://localhost:9001}"
URL="${BASE_URL}/webhook/tenant_A"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if ! curl -sS --connect-timeout 5 --max-time 10 "${BASE_URL}/" >/dev/null; then
  echo "Webhook receiver not reachable at ${BASE_URL}" >&2
  exit 1
fi

echo "[TEST] posting fake alert to ${URL}"
curl -sS --connect-timeout 5 --max-time 20 \
  -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"alert_id\": \"demo-alert-${TIMESTAMP}\",
    \"tenant_id\": \"tenant_A\",
    \"source_id\": \"source_1\",
    \"severity\": \"high\",
    \"prediction\": \"malicious\",
    \"attack_type\": \"demo_synthetic_intrusion\",
    \"evidence\": \"Fake detection result for webhook milestone demo\",
    \"timestamp\": \"${TIMESTAMP}\"
  }"

printf '\n[TEST] view alerts at %s/alerts/tenant_A/view\n' "$BASE_URL"
