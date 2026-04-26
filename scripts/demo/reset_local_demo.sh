#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

./scripts/demo/stop_services.sh

rm -rf .pids
echo "[RESET] removed .pids/"

if [[ "${CLEAR_LOGS:-0}" == "1" ]]; then
  rm -rf logs
  echo "[RESET] removed logs/"
fi

if [[ "${STOP_INFRA:-0}" == "1" ]]; then
  ./scripts/demo/stop_infra.sh
else
  echo "[RESET] Docker infrastructure left running. Set STOP_INFRA=1 to stop it."
fi

echo "[RESET] remaining listeners on local demo ports"
if command -v lsof >/dev/null 2>&1; then
  lsof -nP -iTCP:7000 -iTCP:8000 -iTCP:9001 -sTCP:LISTEN || true
else
  echo "[RESET] lsof not found"
fi
