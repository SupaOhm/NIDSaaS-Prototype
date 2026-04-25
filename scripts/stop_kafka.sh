#!/usr/bin/env bash
set -euo pipefail

echo "[KAFKA] stopping local Kafka infrastructure"
docker compose down
