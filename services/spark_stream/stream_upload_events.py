"""PySpark Structured Streaming reader for gateway upload events."""

from __future__ import annotations

import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import LongType, StringType, StructField, StructType


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


def print_batch(batch_df: DataFrame, batch_id: int) -> None:
    rows = batch_df.count()
    if rows == 0:
        return

    print(f"[SPARK] processing batch_id={batch_id}, rows={rows}", flush=True)
    batch_df.select(
        "tenant_id",
        "source_id",
        "file_path",
        "decision",
        "topic",
        "offset",
    ).show(truncate=False)


def main() -> None:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic_pattern = os.getenv("KAFKA_TOPIC_PATTERN", "raw.tenant.*")
    spark_master = os.getenv("SPARK_MASTER", "local[*]")

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
