#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PCAP_PATH=""
UPLOAD_MODE="pcap"
TENANT_ID="tenant_A"
SOURCE_ID="source_1"
FILE_EPOCH=""
START_OFFSET="0"
END_OFFSET=""
GATEWAY_URL="${GATEWAY_BASE_URL:-http://localhost:8000}"
WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-http://localhost:9001}"
API_KEY="${GATEWAY_API_KEY:-dev-secret}"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/test/pcap_upload.sh --csv -d data/samples/csv/ddos.csv -t tenant_A
  ./scripts/test/pcap_upload.sh --csv -d data/samples/csv/benign.csv -t tenant_A
  ./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_A
  ./scripts/test/pcap_upload.sh -d data/samples/pcap/benign.pcap -t tenant_A
  ./scripts/test/pcap_upload.sh --path data/samples/pcap/benign.pcap --tenant tenant_B

Options:
  --csv               upload CICFlowMeter-compatible CSV to /upload-flow-csv
  -d, --path          file path to upload
  -t, --tenant        tenant_id, default tenant_A
  -s, --source        source_id, default source_1
  -e, --epoch         file_epoch, default auto timestamp
  --start-offset      default 0
  --end-offset        default file size
  --gateway-url       default http://localhost:8000
  --api-key           default dev-secret
  -h, --help          show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --csv)
      UPLOAD_MODE="flow_csv"
      shift
      ;;
    -d|--path)
      PCAP_PATH="${2:-}"
      shift 2
      ;;
    -t|--tenant)
      TENANT_ID="${2:-}"
      shift 2
      ;;
    -s|--source)
      SOURCE_ID="${2:-}"
      shift 2
      ;;
    -e|--epoch)
      FILE_EPOCH="${2:-}"
      shift 2
      ;;
    --start-offset)
      START_OFFSET="${2:-}"
      shift 2
      ;;
    --end-offset)
      END_OFFSET="${2:-}"
      shift 2
      ;;
    --gateway-url)
      GATEWAY_URL="${2:-}"
      shift 2
      ;;
    --api-key)
      API_KEY="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[UPLOAD] unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PCAP_PATH" ]]; then
  echo "[UPLOAD] --path is required" >&2
  usage >&2
  exit 1
fi

if [[ ! -f "$PCAP_PATH" ]]; then
  echo "[UPLOAD] file not found: ${PCAP_PATH}" >&2
  exit 1
fi

FILE_SIZE="$(wc -c <"$PCAP_PATH" | tr -d ' ')"
if [[ "$FILE_SIZE" -le 0 ]]; then
  echo "[UPLOAD] file is empty: ${PCAP_PATH}" >&2
  exit 1
fi

if [[ -z "$END_OFFSET" ]]; then
  END_OFFSET="$FILE_SIZE"
fi

if [[ -z "$FILE_EPOCH" ]]; then
  FILE_EPOCH="cli_$(date -u +"%Y%m%dT%H%M%SZ")"
fi

if [[ "$UPLOAD_MODE" == "flow_csv" ]]; then
  ENDPOINT="/upload-flow-csv"
else
  ENDPOINT="/upload-pcap"
fi

echo "[UPLOAD] mode: ${UPLOAD_MODE}"
echo "[UPLOAD] file: ${PCAP_PATH}"
echo "[UPLOAD] tenant_id: ${TENANT_ID}"
echo "[UPLOAD] source_id: ${SOURCE_ID}"
echo "[UPLOAD] file_epoch: ${FILE_EPOCH}"
echo "[UPLOAD] expected Kafka topic: raw.tenant.${TENANT_ID}"
echo "[UPLOAD] gateway JSON response:"

if [[ "$UPLOAD_MODE" == "flow_csv" ]]; then
  curl -sS --connect-timeout 5 --max-time 60 \
    -X POST "${GATEWAY_URL%/}${ENDPOINT}" \
    -H "x-api-key: ${API_KEY}" \
    -F tenant_id="${TENANT_ID}" \
    -F source_id="${SOURCE_ID}" \
    -F file_epoch="${FILE_EPOCH}" \
    -F file=@"${PCAP_PATH}"
else
  curl -sS --connect-timeout 5 --max-time 60 \
    -X POST "${GATEWAY_URL%/}${ENDPOINT}" \
    -H "x-api-key: ${API_KEY}" \
    -F tenant_id="${TENANT_ID}" \
    -F source_id="${SOURCE_ID}" \
    -F file_epoch="${FILE_EPOCH}" \
    -F start_offset="${START_OFFSET}" \
    -F end_offset="${END_OFFSET}" \
    -F file=@"${PCAP_PATH}"
fi

printf '\n[UPLOAD] alert page URL: %s/alerts/%s/view\n' "$WEBHOOK_BASE_URL" "$TENANT_ID"
