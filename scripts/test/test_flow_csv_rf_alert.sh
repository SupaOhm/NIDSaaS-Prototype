#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

TENANT_ID="${TENANT_ID:-tenant_A}"
FLOW_CSV_PATH="${1:-data/samples/csv/ddos.csv}"

if [[ ! -f "$FLOW_CSV_PATH" ]]; then
  echo "[TEST] missing flow CSV: ${FLOW_CSV_PATH}" >&2
  exit 1
fi

./scripts/demo/reset_demo_state.sh
./scripts/test/pcap_upload.sh --csv -d "$FLOW_CSV_PATH" -t "$TENANT_ID"

printf '[TEST] alert page URL: http://localhost:9001/alerts/%s/view\n' "$TENANT_ID"
