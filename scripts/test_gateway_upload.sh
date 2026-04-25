#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${GATEWAY_BASE_URL:-http://localhost:8000}"
URL="${BASE_URL}/upload-pcap"
SAMPLE_FILE="data/samples/demo_upload.pcap"

if [[ ! -f "$SAMPLE_FILE" ]]; then
  mkdir -p data/samples
  echo "demo packet data for NIDSaaS gateway test" > "$SAMPLE_FILE"
fi

if ! curl -sS --connect-timeout 5 --max-time 10 "${BASE_URL}/health" >/dev/null; then
  echo "Gateway not reachable at ${BASE_URL}" >&2
  exit 1
fi

echo "[TEST] first upload should be accepted"
curl -sS --connect-timeout 5 --max-time 20 -X POST "$URL" \
  -H "x-api-key: dev-secret" \
  -F tenant_id=tenant_A \
  -F source_id=source_1 \
  -F file_epoch=demo_epoch \
  -F start_offset=0 \
  -F end_offset=100 \
  -F file=@"$SAMPLE_FILE"

printf '\n[TEST] second upload should be dropped as duplicate\n'
curl -sS --connect-timeout 5 --max-time 20 -X POST "$URL" \
  -H "x-api-key: dev-secret" \
  -F tenant_id=tenant_A \
  -F source_id=source_1 \
  -F file_epoch=demo_epoch \
  -F start_offset=0 \
  -F end_offset=100 \
  -F file=@"$SAMPLE_FILE"
printf '\n'
