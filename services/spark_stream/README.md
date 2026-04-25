# Spark Stream

This service proves the Kafka -> Spark portion of the NIDSaaS prototype. It reads gateway upload events from Kafka topics matching `raw.tenant.*`, parses each JSON payload, and prints normalized upload records with Kafka metadata.

Run it through Docker after Kafka is running:

```bash
./scripts/run_spark_stream.sh
```

Defaults:

- `KAFKA_BOOTSTRAP_SERVERS=kafka:29092` inside Docker
- `KAFKA_TOPIC_PATTERN=raw.tenant.*`
- `SPARK_MASTER=local[*]`

The gateway still runs locally and publishes to host Kafka at `localhost:9092`. Spark runs in Docker and reads Kafka at the internal Compose address `kafka:29092`.

This milestone does not run IDS inference yet.
