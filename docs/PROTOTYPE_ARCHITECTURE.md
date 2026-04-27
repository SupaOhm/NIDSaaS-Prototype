# Prototype Architecture

This repository implements a local, tenant-aware IDSaaS demonstration pipeline with explicit service boundaries for ingestion, streaming, inference, alert publication, and webhook delivery.

```text
PCAP or CICFlowMeter CSV upload
-> Gateway API with API-key authentication and deduplication
-> Kafka topic raw.tenant.<tenant_id>
-> Spark Structured Streaming detection processor
-> Kafka topic alert.tenant.<tenant_id>
-> Alert Delivery Service
-> Tenant Webhook Receiver UI
```

## Components

`services/gateway/` validates tenant context, applies local API-key authentication, deduplicates repeated uploads, saves accepted files under `data/uploads/`, and publishes normalized events to tenant-scoped Kafka raw topics.

`services/spark_stream/` consumes `raw.tenant.*` topics, routes CSV uploads to saved RF inference, resolves supported PCAP names to matching CICFlowMeter CSVs when available, and publishes attack alerts to `alert.tenant.<tenant_id>`.

`services/alert_delivery/` consumes `alert.tenant.*` topics and forwards each alert to the tenant webhook URL.

`services/webhook_receiver/` stores received alerts in memory and exposes both JSON endpoints and a browser view for tenant-specific alert inspection.

`services/alert_dispatcher/` contains the webhook POST helper used by Alert Delivery.

`services/injector_ui/` contains an auxiliary browser upload interface. The reproducible evaluation workflow uses CLI upload scripts so commands and responses are visible in the terminal.

`src/nidsaas/detection/` contains the IDS pipeline modules, saved-artifact inference adapter, PCAP resolver, live flow extraction helper, and offline experiment entry points.
