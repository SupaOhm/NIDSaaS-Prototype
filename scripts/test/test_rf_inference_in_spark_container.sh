#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 1 ]]; then
  echo "Usage: $0 <flow_csv_path>" >&2
  exit 1
fi

FLOW_CSV_PATH="$1"

exec docker compose run --rm spark \
  python3 scripts/test/test_rf_inference_csv.py "$FLOW_CSV_PATH"
