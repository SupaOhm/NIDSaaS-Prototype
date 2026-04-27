#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export KAFKA_TOPIC_PATTERN="${KAFKA_TOPIC_PATTERN:-raw.tenant.*}"
export SPARK_MASTER="${SPARK_MASTER:-local[*]}"
export IDS_ARTIFACTS_DIR="${IDS_ARTIFACTS_DIR:-outputs/offline_adapter_test}"
export RF_ARTIFACT_PATH="${RF_ARTIFACT_PATH:-outputs/offline_adapter_test/rf_anomaly.joblib}"
export RF_FILE_ATTACK_RATIO_THRESHOLD="${RF_FILE_ATTACK_RATIO_THRESHOLD:-0.20}"
export CIC_FLOW_CSV_ROOT="${CIC_FLOW_CSV_ROOT:-data/csv/csv_CIC_IDS2017}"
export LIVE_FLOW_OUTPUT_DIR="${LIVE_FLOW_OUTPUT_DIR:-outputs/live_flows}"
export DEMO_FORCE_ATTACK="${DEMO_FORCE_ATTACK:-0}"
DOCKER_SPARK_SUBMIT="${DOCKER_SPARK_SUBMIT:-/opt/spark/bin/spark-submit}"
DOCKER_KAFKA_BOOTSTRAP_SERVERS="${DOCKER_KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}"

echo "[SPARK] main demo processing path"
echo "[SPARK] Gateway -> Kafka -> Spark -> Kafka alert topic"
echo "[SPARK] Kafka bootstrap servers inside Docker: ${DOCKER_KAFKA_BOOTSTRAP_SERVERS}"
echo "[SPARK] topic pattern: ${KAFKA_TOPIC_PATTERN}"
echo "[SPARK] IDS artifacts dir: ${IDS_ARTIFACTS_DIR}"
echo "[SPARK] RF artifact path: ${RF_ARTIFACT_PATH}"
echo "[SPARK] RF file attack ratio threshold: ${RF_FILE_ATTACK_RATIO_THRESHOLD}"
echo "[SPARK] CIC flow CSV root: ${CIC_FLOW_CSV_ROOT}"
echo "[SPARK] live flow output dir: ${LIVE_FLOW_OUTPUT_DIR}"
echo "[SPARK] Kafka connector dependency: baked into Spark Docker image"
echo "[SPARK] DEMO_FORCE_ATTACK: ${DEMO_FORCE_ATTACK}"

exec docker compose run --rm \
  -e HOME=/tmp \
  -e KAFKA_BOOTSTRAP_SERVERS="${DOCKER_KAFKA_BOOTSTRAP_SERVERS}" \
  -e KAFKA_TOPIC_PATTERN="${KAFKA_TOPIC_PATTERN}" \
  -e SPARK_MASTER="${SPARK_MASTER}" \
  -e IDS_ARTIFACTS_DIR="${IDS_ARTIFACTS_DIR}" \
  -e RF_ARTIFACT_PATH="${RF_ARTIFACT_PATH}" \
  -e RF_FILE_ATTACK_RATIO_THRESHOLD="${RF_FILE_ATTACK_RATIO_THRESHOLD}" \
  -e CIC_FLOW_CSV_ROOT="${CIC_FLOW_CSV_ROOT}" \
  -e LIVE_FLOW_OUTPUT_DIR="${LIVE_FLOW_OUTPUT_DIR}" \
  -e DEMO_FORCE_ATTACK="${DEMO_FORCE_ATTACK}" \
  spark \
  "${DOCKER_SPARK_SUBMIT}" \
  --master "${SPARK_MASTER}" \
  services/spark_stream/stream_upload_events.py
