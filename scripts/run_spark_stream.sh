#!/usr/bin/env bash
set -euo pipefail

export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export KAFKA_TOPIC_PATTERN="${KAFKA_TOPIC_PATTERN:-raw.tenant.*}"
export SPARK_MASTER="${SPARK_MASTER:-local[*]}"
SPARK_KAFKA_PACKAGE="${SPARK_KAFKA_PACKAGE:-org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1}"
DOCKER_SPARK_SUBMIT="${DOCKER_SPARK_SUBMIT:-/opt/spark/bin/spark-submit}"
DOCKER_SPARK_IVY_DIR="${DOCKER_SPARK_IVY_DIR:-/tmp/.ivy2}"

if [[ "${RUN_SPARK_LOCAL:-0}" == "1" ]]; then
  if [[ -n "${SPARK_HOME:-}" && -x "${SPARK_HOME}/bin/spark-submit" ]]; then
    SPARK_SUBMIT="${SPARK_HOME}/bin/spark-submit"
  elif command -v spark-submit >/dev/null 2>&1; then
    SPARK_SUBMIT="spark-submit"
  else
    echo "[SPARK] spark-submit not found. Install Apache Spark or set SPARK_HOME." >&2
    exit 1
  fi

  echo "[SPARK] launching local upload-event stream"
  echo "[SPARK] Kafka bootstrap servers: ${KAFKA_BOOTSTRAP_SERVERS}"
  echo "[SPARK] topic pattern: ${KAFKA_TOPIC_PATTERN}"
  echo "[SPARK] master: ${SPARK_MASTER}"
  echo "[SPARK] Kafka package: ${SPARK_KAFKA_PACKAGE}"
  echo "[SPARK] spark-submit: ${SPARK_SUBMIT}"

  exec "$SPARK_SUBMIT" \
    --master "$SPARK_MASTER" \
    --packages "$SPARK_KAFKA_PACKAGE" \
    services/spark_stream/stream_upload_events.py
fi

DOCKER_KAFKA_BOOTSTRAP_SERVERS="${DOCKER_KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}"

echo "[SPARK] launching Docker Spark upload-event stream"
echo "[SPARK] Kafka bootstrap servers inside Docker: ${DOCKER_KAFKA_BOOTSTRAP_SERVERS}"
echo "[SPARK] topic pattern: ${KAFKA_TOPIC_PATTERN}"
echo "[SPARK] master: ${SPARK_MASTER}"
echo "[SPARK] Kafka package: ${SPARK_KAFKA_PACKAGE}"
echo "[SPARK] Docker spark-submit: ${DOCKER_SPARK_SUBMIT}"
echo "[SPARK] Docker Ivy cache: ${DOCKER_SPARK_IVY_DIR}"

exec docker compose run --rm \
  -e HOME=/tmp \
  -e KAFKA_BOOTSTRAP_SERVERS="${DOCKER_KAFKA_BOOTSTRAP_SERVERS}" \
  -e KAFKA_TOPIC_PATTERN="${KAFKA_TOPIC_PATTERN}" \
  -e SPARK_MASTER="${SPARK_MASTER}" \
  spark \
  "${DOCKER_SPARK_SUBMIT}" \
  --master "${SPARK_MASTER}" \
  --conf "spark.jars.ivy=${DOCKER_SPARK_IVY_DIR}" \
  --packages "${SPARK_KAFKA_PACKAGE}" \
  services/spark_stream/stream_upload_events.py
