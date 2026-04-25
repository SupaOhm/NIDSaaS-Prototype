# Prototype Architecture

The planned NIDSaaS prototype will turn the current offline IDS pipeline into a tenant-aware streaming workflow. The first implementation should preserve the existing detector contract while adding service boundaries around ingestion, streaming, inference, and alert delivery.

```text
PCAP Injector UI
-> Gateway API with mock auth and dedup
-> Kafka topic raw.tenant.<tenant_id>
-> PySpark Structured Streaming preprocessing and IDS inference
-> Alert Dispatcher
-> Tenant Webhook Receiver UI
```

## Components

`services/injector_ui/` will provide a simple interface for choosing PCAP inputs and submitting ingestion jobs.

`services/gateway/` will validate tenant context, perform mock authentication, deduplicate repeated chunks or events, and publish normalized raw events to Kafka topics named by tenant.

`services/spark_stream/` will consume tenant raw topics, preprocess records into the feature schema expected by the IDS modules under `src/nidsaas/detection/`, run detection inference, and publish alert events.

`services/alert_dispatcher/` will consume alert events and deliver tenant-specific payloads to configured webhook destinations.

`services/webhook_receiver/` will provide a local receiver and UI for validating alert delivery during demos.

Kafka, Spark, gateway logic, and webhook delivery are planned but not implemented yet.
