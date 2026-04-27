#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SAMPLE_FILE="data/samples/pcap/benign.pcap"
TENANT_ID="${TENANT_ID:-tenant_A}"
SOURCE_ID="${SOURCE_ID:-source_duplicate_$$_$(date -u +"%Y%m%dT%H%M%SZ")}"
GATEWAY_URL="${GATEWAY_BASE_URL:-http://localhost:8000}"
API_KEY="${GATEWAY_API_KEY:-dev-secret}"
if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "[TEST] Missing demo PCAP sample: ${SAMPLE_FILE}" >&2
  echo "[TEST] Place demo samples under data/samples/pcap/ or run the sample-generation scripts." >&2
  exit 1
fi

FILE_SIZE="$(wc -c <"$SAMPLE_FILE" | tr -d ' ')"

json_field() {
  python3 -c 'import json, sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

upload_with_auto_epoch() {
  local epoch
  epoch="cli_$(date -u +"%Y%m%dT%H%M%SZ")"
  echo "[TEST] uploading epoch=${epoch}" >&2
  curl -sS --connect-timeout 5 --max-time 60 \
    -X POST "${GATEWAY_URL%/}/upload-pcap" \
    -H "x-api-key: ${API_KEY}" \
    -F tenant_id="${TENANT_ID}" \
    -F source_id="${SOURCE_ID}" \
    -F file_epoch="${epoch}" \
    -F start_offset="0" \
    -F end_offset="${FILE_SIZE}" \
    -F file=@"${SAMPLE_FILE}"
}

echo "[TEST] first upload should be forward"
FIRST_RESPONSE="$(upload_with_auto_epoch)"
echo "$FIRST_RESPONSE"

FIRST_DECISION="$(json_field decision <<<"$FIRST_RESPONSE")"
if [[ "$FIRST_DECISION" != "forward" ]]; then
  echo "[TEST] expected first upload decision forward, got ${FIRST_DECISION}" >&2
  exit 1
fi

sleep 1

printf '\n[TEST] second upload should be drop_duplicate/published false\n'
SECOND_RESPONSE="$(upload_with_auto_epoch)"
echo "$SECOND_RESPONSE"

SECOND_DECISION="$(json_field decision <<<"$SECOND_RESPONSE")"
SECOND_REASON="$(json_field reason <<<"$SECOND_RESPONSE")"
SECOND_PUBLISHED="$(json_field published <<<"$SECOND_RESPONSE")"

if [[ "$SECOND_DECISION" != "drop_duplicate" ]]; then
  echo "[TEST] expected second upload decision drop_duplicate, got ${SECOND_DECISION}" >&2
  exit 1
fi

if [[ "$SECOND_REASON" != "content_hash_match" ]]; then
  echo "[TEST] expected duplicate reason content_hash_match, got ${SECOND_REASON}" >&2
  exit 1
fi

if [[ "$SECOND_PUBLISHED" != "False" ]]; then
  echo "[TEST] expected second upload published false, got ${SECOND_PUBLISHED}" >&2
  exit 1
fi

printf '\n'
