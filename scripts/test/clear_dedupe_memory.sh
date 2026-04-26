#!/usr/bin/env bash
set -euo pipefail

GATEWAY_URL="${GATEWAY_BASE_URL:-http://localhost:8000}"
API_KEY="${GATEWAY_API_KEY:-dev-secret}"

curl -sS --connect-timeout 5 --max-time 30 \
  -X POST "${GATEWAY_URL%/}/admin/clear-dedupe" \
  -H "x-api-key: ${API_KEY}"

printf '\n'
