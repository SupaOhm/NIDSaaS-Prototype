#!/usr/bin/env bash
set -euo pipefail

GATEWAY_BASE_URL="${GATEWAY_BASE_URL:-http://localhost:8000}"
WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-http://localhost:9001}"
SAMPLE_FILE="data/samples/demo_upload.pcap"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if [[ ! -f "$SAMPLE_FILE" ]]; then
  mkdir -p data/samples
  echo "demo packet data for NIDSaaS gateway test" > "$SAMPLE_FILE"
fi

if ! curl -sS --connect-timeout 5 --max-time 10 "${GATEWAY_BASE_URL}/health" >/dev/null; then
  echo "Gateway not reachable at ${GATEWAY_BASE_URL}" >&2
  exit 1
fi

if ! curl -sS --connect-timeout 5 --max-time 10 "${WEBHOOK_BASE_URL}/" >/dev/null; then
  echo "Webhook receiver not reachable at ${WEBHOOK_BASE_URL}" >&2
  exit 1
fi

echo "[TEST] uploading sample file to gateway"
curl -sS --connect-timeout 5 --max-time 20 \
  -X POST "${GATEWAY_BASE_URL}/upload-pcap" \
  -H "x-api-key: dev-secret" \
  -F tenant_id=tenant_A \
  -F source_id=source_1 \
  -F file_epoch="demo_epoch_${TIMESTAMP}" \
  -F start_offset=0 \
  -F end_offset=100 \
  -F file=@"$SAMPLE_FILE"

printf '\n[TEST] dispatching fake alert to webhook receiver\n'
curl -sS --connect-timeout 5 --max-time 20 \
  -X POST "${WEBHOOK_BASE_URL}/webhook/tenant_A" \
  -H "Content-Type: application/json" \
  -d "{
    \"alert_id\": \"e2e-demo-alert-${TIMESTAMP}\",
    \"tenant_id\": \"tenant_A\",
    \"source_id\": \"source_1\",
    \"severity\": \"high\",
    \"prediction\": \"malicious\",
    \"attack_type\": \"demo_synthetic_intrusion\",
    \"evidence\": \"Gateway upload accepted; fake detection result emitted for demo\",
    \"timestamp\": \"${TIMESTAMP}\"
  }"

printf '\n[TEST] view alerts at %s/alerts/tenant_A/view\n' "$WEBHOOK_BASE_URL"
