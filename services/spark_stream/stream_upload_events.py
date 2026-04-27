"""PySpark Structured Streaming reader for gateway upload events."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import LongType, StringType, StructField, StructType
from kafka import KafkaProducer
from kafka.errors import KafkaError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from nidsaas.detection.demo_inference_adapter import run_demo_ids_inference
from nidsaas.detection.pcap_flow_resolver import resolve_pcap_to_flow_csv
from nidsaas.detection.live_flow_extractor import extract_flows_from_pcap
from nidsaas.detection.rf_inference_adapter import run_rf_inference_on_flow_csv


UPLOAD_EVENT_SCHEMA = StructType(
    [
        StructField("tenant_id", StringType(), True),
        StructField("source_id", StringType(), True),
        StructField("file_epoch", StringType(), True),
        StructField("start_offset", LongType(), True),
        StructField("end_offset", LongType(), True),
        StructField("effective_start_offset", LongType(), True),
        StructField("file_path", StringType(), True),
        StructField("file_type", StringType(), True),
        StructField("original_filename", StringType(), True),
        StructField("batch_hash", StringType(), True),
        StructField("content_hash", StringType(), True),
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
        col("event.file_type").alias("file_type"),
        col("event.original_filename").alias("original_filename"),
        col("event.batch_hash").alias("batch_hash"),
        col("event.content_hash").alias("content_hash"),
        col("event.decision").alias("decision"),
        col("event.upload_time").alias("upload_time"),
        col("topic"),
        col("partition"),
        col("offset"),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_alert(row, ids_result: dict) -> dict:
    tenant_id = row["tenant_id"] or "unknown_tenant"
    file_path = row["file_path"] or ""
    file_name = Path(file_path).name
    evidence = dict(ids_result.get("evidence", {}))
    evidence.update(
        {
            "file_path": file_path,
            "file_name": file_name,
            "file_type": row["file_type"] or "pcap",
            "original_filename": row["original_filename"],
            "kafka_topic": row["topic"],
            "kafka_offset": row["offset"],
            "batch_hash": row["batch_hash"],
            "content_hash": row["content_hash"],
            "gateway_decision": row["decision"],
        }
    )
    alert = {
        "alert_id": f"spark-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:8]}",
        "tenant_id": tenant_id,
        "source_id": row["source_id"] or "unknown_source",
        "severity": ids_result.get("severity", "high"),
        "prediction": ids_result.get("prediction", "attack"),
        "attack_type": ids_result.get("attack_type", "HybridCascadeDemo"),
        "stage": ids_result.get("stage", "spark_real_ids_artifact_demo"),
        "evidence": {
            **evidence,
        },
        "timestamp": _utc_now(),
    }
    return alert


def _build_kafka_producer(bootstrap_servers: str) -> KafkaProducer | None:
    servers = [server.strip() for server in bootstrap_servers.split(",") if server.strip()]
    if not servers:
        print("[SPARK] no Kafka bootstrap servers configured for alert publication", flush=True)
        return None
    try:
        return KafkaProducer(
            bootstrap_servers=servers,
            value_serializer=lambda payload: json.dumps(payload, default=str).encode("utf-8"),
            linger_ms=10,
            retries=3,
        )
    except Exception as exc:
        print(f"[SPARK] failed to initialize Kafka producer: {exc}", flush=True)
        return None


def _publish_alert_to_kafka(producer: KafkaProducer | None, tenant_id: str, alert: dict) -> bool:
    if producer is None:
        print("[SPARK] no Kafka producer available; alert not published", flush=True)
        return False

    topic = f"alert.tenant.{tenant_id}"
    try:
        producer.send(topic, alert).get(timeout=10)
        producer.flush()
        print(f"[SPARK] published alert to Kafka topic {topic}", flush=True)
        return True
    except KafkaError as exc:
        print(f"[SPARK] failed to publish alert to Kafka topic {topic}: {exc}", flush=True)
        return False


def _log_rf_result(prefix: str, rf_result: dict) -> None:
    print(
        f"{prefix} status={rf_result.get('status', '')} "
        f"input_file_exists={rf_result.get('input_file_exists', '')} "
        f"input_file_size_bytes={rf_result.get('input_file_size_bytes', '')} "
        f"raw_rows_loaded={rf_result.get('raw_rows_loaded', '')} "
        f"rows_after_cleanup={rf_result.get('rows_after_cleanup', '')} "
        f"rows_scored={rf_result.get('rows_scored', '')} "
        f"missing_columns={rf_result.get('missing_columns', [])} "
        f"error={rf_result.get('error', '')}",
        flush=True,
    )


def print_batch(batch_df: DataFrame, batch_id: int) -> None:
    rows = batch_df.count()
    if rows == 0:
        return

    print(f"[SPARK] processing batch_id={batch_id}, rows={rows}", flush=True)
    artifacts_dir = os.getenv("IDS_ARTIFACTS_DIR", "outputs/offline_adapter_test")
    csv_root = os.getenv("CIC_FLOW_CSV_ROOT", "data/csv/csv_CIC_IDS2017")
    live_flow_output_dir = os.getenv("LIVE_FLOW_OUTPUT_DIR", "outputs/live_flows")
    result_rows = []
    rf_artifact_path = os.getenv("RF_ARTIFACT_PATH", "outputs/offline_adapter_test/rf_anomaly.joblib")
    rf_file_attack_ratio_threshold = float(os.getenv("RF_FILE_ATTACK_RATIO_THRESHOLD", "0.20"))
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    alert_producer = _build_kafka_producer(kafka_bootstrap_servers)

    def run_live_fallback(row, file_path: str) -> dict:
        print("[SPARK] extracting live flows from uploaded PCAP", flush=True)
        extraction_metadata = extract_flows_from_pcap(
            file_path,
            output_dir=live_flow_output_dir,
        )
        extracted_flow_csv_path = str(extraction_metadata.get("extracted_flow_csv_path", ""))
        print(f"[SPARK] extracted flow CSV: {extracted_flow_csv_path}", flush=True)
        print(f"[SPARK] number_of_flows={extraction_metadata.get('number_of_flows', 0)}", flush=True)
        print("[SPARK] calling IDS demo inference adapter", flush=True)
        live_result = run_demo_ids_inference(
            tenant_id=row["tenant_id"] or "unknown_tenant",
            source_id=row["source_id"] or "unknown_source",
            file_path=file_path,
            artifacts_dir=artifacts_dir,
            csv_root=csv_root,
            extracted_flow_csv_path=extracted_flow_csv_path,
            extraction_metadata=extraction_metadata,
        )
        live_result["evidence"]["note"] = (
            "live tshark flow-rule fallback; RF requires CICFlowMeter-compatible features"
        )
        return live_result

    selected = batch_df.select(
        "tenant_id",
        "source_id",
        "file_path",
        "file_type",
        "original_filename",
        "batch_hash",
        "content_hash",
        "decision",
        "topic",
        "offset",
    ).collect()

    for row in selected:
        file_path = row["file_path"] or ""
        file_type = row["file_type"] or "pcap"
        file_name = Path(file_path).name
        print("[SPARK] preprocessing upload event", flush=True)
        print(
            f"[SPARK] normalized tenant_id={row['tenant_id']} "
            f"source_id={row['source_id']} file_name={file_name} "
            f"file_type={file_type} gateway_decision={row['decision']}",
            flush=True,
        )

        if file_type == "flow_csv":
            print("[SPARK] using uploaded flow CSV for saved RF inference", flush=True)
            rf_result = run_rf_inference_on_flow_csv(
                flow_csv_path=file_path,
                artifact_path=rf_artifact_path,
                file_attack_ratio_threshold=rf_file_attack_ratio_threshold,
            )
            print(
                f"[SPARK] RF attack_ratio={float(rf_result.get('attack_ratio', 0.0)):.4f}, "
                f"rows_scored={rf_result.get('rows_scored', 0)}, "
                f"prediction={rf_result.get('prediction', 'benign')}",
                flush=True,
            )
            evidence = {
                "original_flow_csv_path": file_path,
                "evidence_source": "saved_rf_artifact_inference",
                "rf_attack_ratio": rf_result.get("attack_ratio", 0.0),
                "rf_file_attack_ratio_threshold": rf_result.get(
                    "file_attack_ratio_threshold",
                    rf_file_attack_ratio_threshold,
                ),
                "rf_row_threshold": rf_result.get("row_threshold", 0.0),
                "rf_row_attack_count": rf_result.get("row_attack_count", 0),
                "rf_row_benign_count": rf_result.get("row_benign_count", 0),
                "rows_scored": rf_result.get("rows_scored", 0),
                "input_file_exists": rf_result.get("input_file_exists", False),
                "input_file_size_bytes": rf_result.get("input_file_size_bytes", 0),
                "raw_rows_loaded": rf_result.get("raw_rows_loaded", 0),
                "rows_after_cleanup": rf_result.get("rows_after_cleanup", 0),
                "missing_columns": rf_result.get("missing_columns", []),
                "rf_artifact_path": rf_artifact_path,
                "note": "saved RF inference on uploaded CICFlowMeter-compatible flow CSV; no retraining",
            }
            if rf_result.get("status") != "success" or int(rf_result.get("rows_scored", 0) or 0) <= 0:
                _log_rf_result("[SPARK] RF inference failed for uploaded flow CSV:", rf_result)
                evidence["rf_error"] = rf_result.get("error", "zero rows scored")
                ids_result = {
                    "status": rf_result.get("status", "error"),
                    "prediction": "error",
                    "severity": "info",
                    "attack_type": "RFInferenceError",
                    "stage": "spark_saved_rf_artifact_demo",
                    "evidence": evidence,
                }
            else:
                ids_result = {
                    "status": rf_result.get("status", "success"),
                    "prediction": rf_result.get("prediction", "benign"),
                    "severity": rf_result.get("severity", "info"),
                    "attack_type": "RFArtifactAttack" if rf_result.get("prediction") == "attack" else "BENIGN",
                    "stage": "spark_saved_rf_artifact_demo",
                    "evidence": evidence,
                }
        else:
            print("[SPARK] resolving PCAP to CICFlowMeter CSV", flush=True)
            resolver_result = resolve_pcap_to_flow_csv(file_path, csv_root=csv_root)
            matched_flow_csv_path = str(resolver_result.get("flow_csv_path", "") or "")

            if matched_flow_csv_path and Path(matched_flow_csv_path).exists():
                print(f"[SPARK] using saved RF inference adapter: {matched_flow_csv_path}", flush=True)
                rf_result = run_rf_inference_on_flow_csv(
                    flow_csv_path=matched_flow_csv_path,
                    artifact_path=rf_artifact_path,
                    file_attack_ratio_threshold=rf_file_attack_ratio_threshold,
                )
                print(
                    f"[SPARK] RF attack_ratio={float(rf_result.get('attack_ratio', 0.0)):.4f}, "
                    f"rows_scored={rf_result.get('rows_scored', 0)}, "
                    f"prediction={rf_result.get('prediction', 'benign')}",
                    flush=True,
                )
                if rf_result.get("status") != "success" or int(rf_result.get("rows_scored", 0) or 0) <= 0:
                    _log_rf_result("[SPARK] RF inference failed for matched CSV:", rf_result)
                    print(
                        "[SPARK] RF inference scored no rows; falling back to live tshark flow rules",
                        flush=True,
                    )
                    ids_result = run_live_fallback(row, file_path)
                else:
                    evidence = {
                        "original_pcap_path": file_path,
                        "matched_flow_csv_path": matched_flow_csv_path,
                        "evidence_source": "saved_rf_artifact_inference",
                        "rf_attack_ratio": rf_result.get("attack_ratio", 0.0),
                        "rf_file_attack_ratio_threshold": rf_result.get(
                            "file_attack_ratio_threshold",
                            rf_file_attack_ratio_threshold,
                        ),
                        "rf_row_threshold": rf_result.get("row_threshold", 0.0),
                        "rf_row_attack_count": rf_result.get("row_attack_count", 0),
                        "rf_row_benign_count": rf_result.get("row_benign_count", 0),
                        "rows_scored": rf_result.get("rows_scored", 0),
                        "input_file_exists": rf_result.get("input_file_exists", False),
                        "input_file_size_bytes": rf_result.get("input_file_size_bytes", 0),
                        "raw_rows_loaded": rf_result.get("raw_rows_loaded", 0),
                        "rows_after_cleanup": rf_result.get("rows_after_cleanup", 0),
                        "missing_columns": rf_result.get("missing_columns", []),
                        "rf_artifact_path": rf_artifact_path,
                        "note": "saved RF inference on CICFlowMeter-compatible CSV; no retraining",
                    }
                    ids_result = {
                        "status": rf_result.get("status", "success"),
                        "prediction": rf_result.get("prediction", "benign"),
                        "severity": rf_result.get("severity", "info"),
                        "attack_type": "RFArtifactAttack" if rf_result.get("prediction") == "attack" else "BENIGN",
                        "stage": "spark_saved_rf_artifact_demo",
                        "evidence": evidence,
                    }
            else:
                print("[SPARK] no matching CICFlowMeter CSV found; falling back to live tshark flow rules", flush=True)
                ids_result = run_live_fallback(row, file_path)
        prediction = ids_result.get("prediction", "benign")
        severity = ids_result.get("severity", "info")
        stage = ids_result.get("stage", "spark_real_ids_artifact_demo")
        evidence = ids_result.get("evidence", {})
        print(f"[SPARK] received file: {evidence.get('original_pcap_path') or evidence.get('original_flow_csv_path') or file_path}", flush=True)
        print(f"[SPARK] extracted flow CSV: {evidence.get('extracted_flow_csv_path', '')}", flush=True)
        print(f"[SPARK] matched flow CSV: {evidence.get('matched_flow_csv_path', '')}", flush=True)
        print(f"[SPARK] detection_reason: {evidence.get('detection_reason', '')}", flush=True)
        print(f"[SPARK] evidence_source: {evidence.get('evidence_source', '')}", flush=True)
        print(f"[SPARK] prediction={prediction}", flush=True)

        if prediction == "attack":
            alert = _build_alert(row, ids_result)
            tenant_id = alert.get("tenant_id", row["tenant_id"] or "unknown_tenant")
            _publish_alert_to_kafka(alert_producer, str(tenant_id), alert)
        elif prediction == "error":
            print("[SPARK] RF inference error, no alert dispatched", flush=True)
        else:
            print("[SPARK] benign result, no alert dispatched", flush=True)

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

    if alert_producer is not None:
        alert_producer.close()


def main() -> None:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic_pattern = os.getenv("KAFKA_TOPIC_PATTERN", "raw.tenant.*")
    spark_master = os.getenv("SPARK_MASTER", "local[*]")
    artifacts_dir = os.getenv("IDS_ARTIFACTS_DIR", "outputs/offline_adapter_test")
    rf_artifact_path = os.getenv("RF_ARTIFACT_PATH", "outputs/offline_adapter_test/rf_anomaly.joblib")
    rf_file_attack_ratio_threshold = float(os.getenv("RF_FILE_ATTACK_RATIO_THRESHOLD", "0.20"))
    csv_root = os.getenv("CIC_FLOW_CSV_ROOT", "data/csv/csv_CIC_IDS2017")

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
    print(f"[SPARK] RF artifact path: {rf_artifact_path}", flush=True)
    print(f"[SPARK] RF file attack ratio threshold: {rf_file_attack_ratio_threshold}", flush=True)
    print(f"[SPARK] CIC flow CSV root: {csv_root}", flush=True)
    print(f"[SPARK] live flow output dir: {os.getenv('LIVE_FLOW_OUTPUT_DIR', 'outputs/live_flows')}", flush=True)
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
