#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
exec python -m uvicorn services.gateway.app:app --host "$HOST" --port "$PORT" --reload
