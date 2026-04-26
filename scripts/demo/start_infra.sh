#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "[INFRA] starting Docker infrastructure"
echo "[INFRA] starting Zookeeper, Kafka, and Kafka UI"
docker compose up -d zookeeper kafka kafka-ui

echo "[INFRA] waiting for Kafka broker via kafka:29092"
for _ in $(seq 1 30); do
  if docker compose exec -T kafka kafka-topics --bootstrap-server kafka:29092 --list >/dev/null 2>&1; then
    echo "[INFRA] Kafka ready at localhost:9092"
    echo "[INFRA] Kafka UI: http://localhost:8080"
    exit 0
  fi
  sleep 2
done

echo "[INFRA] Kafka broker did not become ready in time" >&2
docker compose ps
exit 1
