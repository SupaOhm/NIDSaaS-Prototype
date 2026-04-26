#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

TOPIC="${1:-raw.tenant.tenant_A}"
TIMEOUT_MS="${KAFKA_CONSUME_TIMEOUT_MS:-10000}"

echo "[KAFKA] consuming topic ${TOPIC}"
echo "[KAFKA] bootstrap server: kafka:29092"
echo "[KAFKA] timeout: ${TIMEOUT_MS} ms"
docker compose exec -T kafka kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic "$TOPIC" \
  --from-beginning \
  --timeout-ms "$TIMEOUT_MS"
