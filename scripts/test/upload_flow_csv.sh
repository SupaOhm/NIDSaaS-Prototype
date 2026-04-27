#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <flow_csv_path> [tenant_id]" >&2
  exit 1
fi

FLOW_CSV_PATH="$1"
TENANT_ID="${2:-tenant_A}"

exec ./scripts/test/pcap_upload.sh --csv -d "$FLOW_CSV_PATH" -t "$TENANT_ID"
