#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "[INFRA] stopping Docker infrastructure"
docker compose down
echo "[INFRA] stopped Kafka, Zookeeper, and Kafka UI"
