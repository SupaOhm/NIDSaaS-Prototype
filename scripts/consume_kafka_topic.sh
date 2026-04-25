#!/usr/bin/env bash
set -euo pipefail

TOPIC="${1:-raw.tenant.tenant_A}"
TIMEOUT_MS="${KAFKA_CONSUME_TIMEOUT_MS:-10000}"

echo "[KAFKA] consuming topic ${TOPIC}"
docker compose exec -T kafka kafka-console-consumer.sh \
  --bootstrap-server kafka:29092 \
  --topic "$TOPIC" \
  --from-beginning \
  --timeout-ms "$TIMEOUT_MS"
