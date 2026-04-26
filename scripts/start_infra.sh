#!/usr/bin/env bash
set -euo pipefail

echo "[DEMO] starting Docker infrastructure"
./scripts/start_kafka.sh
echo "[DEMO] Kafka UI: http://localhost:8080"
