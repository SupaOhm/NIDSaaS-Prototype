#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "[KAFKA] listing topics from inside the Kafka container"
echo "[KAFKA] bootstrap server: kafka:29092"
echo "[KAFKA] expected tenant topics: raw.tenant.<tenant_id>, alert.tenant.<tenant_id>"
docker compose exec -T kafka kafka-topics --bootstrap-server kafka:29092 --list
