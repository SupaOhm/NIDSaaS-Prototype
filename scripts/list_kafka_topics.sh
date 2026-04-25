#!/usr/bin/env bash
set -euo pipefail

echo "[KAFKA] topics"
docker compose exec -T kafka kafka-topics --bootstrap-server kafka:29092 --list
