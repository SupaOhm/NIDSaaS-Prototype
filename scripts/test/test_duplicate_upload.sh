#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

BASE_URL="${GATEWAY_BASE_URL:-http://localhost:8000}"
URL="${BASE_URL}/upload-pcap"
SAMPLE_FILE="data/samples/demo_upload.pcap"

if [[ ! -f "$SAMPLE_FILE" ]]; then
  mkdir -p data/samples
  echo "demo packet data for NIDSaaS gateway duplicate test" >"$SAMPLE_FILE"
fi

if ! curl -sS --connect-timeout 5 --max-time 10 "${BASE_URL}/health" >/dev/null; then
  echo "[TEST] Gateway not reachable at ${BASE_URL}" >&2
  exit 1
fi

echo "[TEST] first upload should be forward/published true"
curl -sS --connect-timeout 5 --max-time 20 -X POST "$URL" \
  -H "x-api-key: dev-secret" \
  -F tenant_id=tenant_A \
  -F source_id=source_1 \
  -F file_epoch=duplicate_demo_epoch \
  -F start_offset=0 \
  -F end_offset=100 \
  -F file=@"$SAMPLE_FILE"

printf '\n[TEST] second upload should be drop_duplicate/published false\n'
curl -sS --connect-timeout 5 --max-time 20 -X POST "$URL" \
  -H "x-api-key: dev-secret" \
  -F tenant_id=tenant_A \
  -F source_id=source_1 \
  -F file_epoch=duplicate_demo_epoch \
  -F start_offset=0 \
  -F end_offset=100 \
  -F file=@"$SAMPLE_FILE"
printf '\n'
