#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export KAFKA_TOPIC_PATTERN="${KAFKA_TOPIC_PATTERN:-raw.tenant.*}"
export SPARK_MASTER="${SPARK_MASTER:-local[*]}"
export IDS_ARTIFACTS_DIR="${IDS_ARTIFACTS_DIR:-outputs/offline_adapter_test}"
export CIC_FLOW_CSV_ROOT="${CIC_FLOW_CSV_ROOT:-data/csv/csv_CIC_IDS2017}"
export LIVE_FLOW_OUTPUT_DIR="${LIVE_FLOW_OUTPUT_DIR:-outputs/live_flows}"
export DEMO_FORCE_ATTACK="${DEMO_FORCE_ATTACK:-0}"
SPARK_KAFKA_PACKAGE="${SPARK_KAFKA_PACKAGE:-org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1}"
DOCKER_SPARK_SUBMIT="${DOCKER_SPARK_SUBMIT:-/opt/spark/bin/spark-submit}"
DOCKER_SPARK_IVY_DIR="${DOCKER_SPARK_IVY_DIR:-/tmp/.ivy2}"
DOCKER_KAFKA_BOOTSTRAP_SERVERS="${DOCKER_KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}"
DOCKER_WEBHOOK_BASE_URL="${DOCKER_WEBHOOK_BASE_URL:-http://host.docker.internal:9001}"

echo "[SPARK] main demo processing path"
echo "[SPARK] Gateway -> Kafka -> Spark -> IDS artifact adapter -> Webhook"
echo "[SPARK] Kafka bootstrap servers inside Docker: ${DOCKER_KAFKA_BOOTSTRAP_SERVERS}"
echo "[SPARK] topic pattern: ${KAFKA_TOPIC_PATTERN}"
echo "[SPARK] IDS artifacts dir: ${IDS_ARTIFACTS_DIR}"
echo "[SPARK] CIC flow CSV root: ${CIC_FLOW_CSV_ROOT}"
echo "[SPARK] live flow output dir: ${LIVE_FLOW_OUTPUT_DIR}"
echo "[SPARK] webhook base URL inside Docker: ${DOCKER_WEBHOOK_BASE_URL}"
echo "[SPARK] DEMO_FORCE_ATTACK: ${DEMO_FORCE_ATTACK}"

exec docker compose run --rm \
  -e HOME=/tmp \
  -e KAFKA_BOOTSTRAP_SERVERS="${DOCKER_KAFKA_BOOTSTRAP_SERVERS}" \
  -e KAFKA_TOPIC_PATTERN="${KAFKA_TOPIC_PATTERN}" \
  -e SPARK_MASTER="${SPARK_MASTER}" \
  -e IDS_ARTIFACTS_DIR="${IDS_ARTIFACTS_DIR}" \
  -e CIC_FLOW_CSV_ROOT="${CIC_FLOW_CSV_ROOT}" \
  -e LIVE_FLOW_OUTPUT_DIR="${LIVE_FLOW_OUTPUT_DIR}" \
  -e DEMO_FORCE_ATTACK="${DEMO_FORCE_ATTACK}" \
  -e WEBHOOK_BASE_URL="${DOCKER_WEBHOOK_BASE_URL}" \
  spark \
  "${DOCKER_SPARK_SUBMIT}" \
  --master "${SPARK_MASTER}" \
  --conf "spark.jars.ivy=${DOCKER_SPARK_IVY_DIR}" \
  --packages "${SPARK_KAFKA_PACKAGE}" \
  services/spark_stream/stream_upload_events.py
