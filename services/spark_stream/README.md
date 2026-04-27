# Spark Stream

This service runs the Spark Structured Streaming stage of the NIDSaaS prototype. It reads gateway upload events from Kafka topics matching `raw.tenant.*`, parses each JSON payload, runs the configured detection path, and publishes attack alerts to tenant-scoped Kafka alert topics.

Run it through Docker after Kafka is running:

```bash
./scripts/demo/run_spark_processor.sh
```

Defaults:

- `KAFKA_BOOTSTRAP_SERVERS=kafka:29092` inside Docker
- `KAFKA_TOPIC_PATTERN=raw.tenant.*`
- `SPARK_MASTER=local[*]`

The gateway still runs locally and publishes to host Kafka at `localhost:9092`. Spark runs in Docker and reads Kafka at the internal Compose address `kafka:29092`.

The demo path uses saved IDS/RF artifacts from `outputs/offline_adapter_test`.
For uploaded CICFlowMeter CSV files, Spark runs saved RF inference directly.
For PCAP uploads, Spark resolves matching CICFlowMeter CSV evidence when
available and uses live flow extraction as the runtime fallback path.

Attack results are published to `alert.tenant.<tenant_id>` for delivery by
`services/alert_delivery/`.
