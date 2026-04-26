"""PySpark Structured Streaming reader for gateway upload events."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import LongType, StringType, StructField, StructType


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from nidsaas.detection.demo_inference_adapter import run_demo_ids_inference
from services.alert_dispatcher.dispatcher import dispatch_alert


UPLOAD_EVENT_SCHEMA = StructType(
    [
        StructField("tenant_id", StringType(), True),
        StructField("source_id", StringType(), True),
        StructField("file_epoch", StringType(), True),
        StructField("start_offset", LongType(), True),
        StructField("end_offset", LongType(), True),
        StructField("effective_start_offset", LongType(), True),
        StructField("file_path", StringType(), True),
        StructField("batch_hash", StringType(), True),
        StructField("decision", StringType(), True),
        StructField("upload_time", StringType(), True),
    ]
)


def build_stream(spark: SparkSession, bootstrap_servers: str, topic_pattern: str) -> DataFrame:
    kafka_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribePattern", topic_pattern)
        .option("startingOffsets", "earliest")
        .load()
    )

    parsed_df = kafka_df.select(
        col("topic"),
        col("partition"),
        col("offset"),
        from_json(col("value").cast("string"), UPLOAD_EVENT_SCHEMA).alias("event"),
    )

    return parsed_df.select(
        col("event.tenant_id").alias("tenant_id"),
        col("event.source_id").alias("source_id"),
        col("event.file_epoch").alias("file_epoch"),
        col("event.start_offset").alias("start_offset"),
        col("event.end_offset").alias("end_offset"),
        col("event.effective_start_offset").alias("effective_start_offset"),
        col("event.file_path").alias("file_path"),
        col("event.batch_hash").alias("batch_hash"),
        col("event.decision").alias("decision"),
        col("event.upload_time").alias("upload_time"),
        col("topic"),
        col("partition"),
        col("offset"),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _webhook_url(base_url: str, tenant_id: str) -> str:
    return f"{base_url.rstrip('/')}/webhook/{tenant_id}"


def _build_alert(row, ids_result: dict, webhook_base_url: str) -> tuple[dict, str]:
    tenant_id = row["tenant_id"] or "unknown_tenant"
    file_path = row["file_path"] or ""
    file_name = Path(file_path).name
    evidence = ids_result.get("evidence", {})
    alert = {
        "alert_id": f"spark-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:8]}",
        "tenant_id": tenant_id,
        "source_id": row["source_id"] or "unknown_source",
        "severity": ids_result.get("severity", "high"),
        "prediction": ids_result.get("prediction", "attack"),
        "attack_type": ids_result.get("attack_type", "HybridCascadeDemo"),
        "stage": ids_result.get("stage", "spark_real_ids_artifact_demo"),
        "evidence": {
            "file_path": file_path,
            "file_name": file_name,
            "kafka_topic": row["topic"],
            "kafka_offset": row["offset"],
            "batch_hash": row["batch_hash"],
            "gateway_decision": row["decision"],
            "ids_artifacts_dir": evidence.get("artifacts_dir"),
            "ids_metrics_summary": evidence.get("metrics_used"),
            "ids_sample_row_id": evidence.get("sample_row_id"),
            "note": evidence.get("note", "uses precomputed trained IDS artifacts; no retraining"),
        },
        "timestamp": _utc_now(),
    }
    return alert, _webhook_url(webhook_base_url, tenant_id)


def print_batch(batch_df: DataFrame, batch_id: int) -> None:
    rows = batch_df.count()
    if rows == 0:
        return

    print(f"[SPARK] processing batch_id={batch_id}, rows={rows}", flush=True)
    artifacts_dir = os.getenv("IDS_ARTIFACTS_DIR", "outputs/offline_adapter_test")
    webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "http://host.docker.internal:9001")
    result_rows = []

    selected = batch_df.select(
        "tenant_id",
        "source_id",
        "file_path",
        "batch_hash",
        "decision",
        "topic",
        "offset",
    ).collect()

    for row in selected:
        file_path = row["file_path"] or ""
        file_name = Path(file_path).name
        print("[SPARK] preprocessing upload event", flush=True)
        print(
            f"[SPARK] normalized tenant_id={row['tenant_id']} "
            f"source_id={row['source_id']} file_name={file_name} "
            f"gateway_decision={row['decision']}",
            flush=True,
        )
        print("[SPARK] calling IDS demo inference adapter", flush=True)
        ids_result = run_demo_ids_inference(
            tenant_id=row["tenant_id"] or "unknown_tenant",
            source_id=row["source_id"] or "unknown_source",
            file_path=file_path,
            artifacts_dir=artifacts_dir,
        )
        prediction = ids_result.get("prediction", "benign")
        severity = ids_result.get("severity", "info")
        stage = ids_result.get("stage", "spark_real_ids_artifact_demo")

        if prediction == "attack":
            alert, url = _build_alert(row, ids_result, webhook_base_url)
            if dispatch_alert(alert, url):
                print(f"[ALERT] dispatched to {url}", flush=True)
            else:
                print(f"[ALERT] dispatch failed for {url}", flush=True)
        else:
            print("[SPARK] benign result; no alert dispatched", flush=True)

        result_rows.append(
            {
                "tenant_id": row["tenant_id"],
                "source_id": row["source_id"],
                "file_name": file_name,
                "prediction": prediction,
                "severity": severity,
                "stage": stage,
                "topic": row["topic"],
                "offset": row["offset"],
            }
        )

    if result_rows:
        spark = batch_df.sparkSession
        spark.createDataFrame(result_rows).select(
            "tenant_id",
            "source_id",
            "file_name",
            "prediction",
            "severity",
            "stage",
            "topic",
            "offset",
        ).show(truncate=False)


def main() -> None:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic_pattern = os.getenv("KAFKA_TOPIC_PATTERN", "raw.tenant.*")
    spark_master = os.getenv("SPARK_MASTER", "local[*]")
    artifacts_dir = os.getenv("IDS_ARTIFACTS_DIR", "outputs/offline_adapter_test")
    webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "http://host.docker.internal:9001")

    spark = (
        SparkSession.builder.appName("nidsaas-upload-event-stream")
        .master(spark_master)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    print("[SPARK] starting upload-event stream", flush=True)
    print(f"[SPARK] bootstrap servers: {bootstrap_servers}", flush=True)
    print(f"[SPARK] topic pattern: {topic_pattern}", flush=True)
    print(f"[SPARK] master: {spark_master}", flush=True)
    print(f"[SPARK] IDS artifacts dir: {artifacts_dir}", flush=True)
    print(f"[SPARK] webhook base URL: {webhook_base_url}", flush=True)
    print(f"[SPARK] DEMO_FORCE_ATTACK: {os.getenv('DEMO_FORCE_ATTACK', '0')}", flush=True)

    stream_df = build_stream(spark, bootstrap_servers, topic_pattern)
    query = (
        stream_df.writeStream.foreachBatch(print_batch)
        .outputMode("append")
        .option("checkpointLocation", os.getenv("SPARK_CHECKPOINT_DIR", "/tmp/nidsaas_spark_upload_events"))
        .start()
    )

    try:
        query.awaitTermination()
    except KeyboardInterrupt:
        print("\n[SPARK] stopping", flush=True)
        query.stop()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
