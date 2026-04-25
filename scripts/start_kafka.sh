#!/usr/bin/env bash
set -euo pipefail

echo "[KAFKA] starting local Kafka infrastructure"
docker compose up -d kafka kafka-ui
echo "[KAFKA] waiting for broker health"
for _ in $(seq 1 30); do
  if docker compose exec -T kafka kafka-topics.sh --bootstrap-server kafka:29092 --list >/dev/null 2>&1; then
    echo "[KAFKA] ready at localhost:9092"
    echo "[KAFKA] UI available at http://localhost:8080"
    exit 0
  fi
  sleep 2
done

echo "[KAFKA] broker did not become ready in time" >&2
docker compose ps
exit 1
