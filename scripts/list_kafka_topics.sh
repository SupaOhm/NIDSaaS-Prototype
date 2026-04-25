#!/usr/bin/env bash
set -euo pipefail

echo "[KAFKA] listing topics from inside the Kafka container"
echo "[KAFKA] bootstrap server: kafka:29092"
docker compose exec -T kafka kafka-topics --bootstrap-server kafka:29092 --list
