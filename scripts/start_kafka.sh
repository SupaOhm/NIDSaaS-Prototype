#!/usr/bin/env bash
set -euo pipefail

echo "[KAFKA] starting local Kafka infrastructure"
echo "[KAFKA] starting Zookeeper, Kafka, and Kafka UI with Docker Compose"
docker compose up -d zookeeper kafka kafka-ui

echo "[KAFKA] waiting for broker health via kafka:29092 inside the Kafka container"
for _ in $(seq 1 30); do
  if docker compose exec -T kafka kafka-topics --bootstrap-server kafka:29092 --list >/dev/null 2>&1; then
    echo "[KAFKA] ready at localhost:9092"
    echo "[KAFKA] UI available at http://localhost:8080"
    exit 0
  fi
  sleep 2
done

echo "[KAFKA] broker did not become ready in time" >&2
docker compose ps
exit 1
