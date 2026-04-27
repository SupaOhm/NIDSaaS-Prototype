# Scripts Operator Guide

The stable demo architecture is:

```text
Gateway -> Kafka raw.tenant.<tenant_id> -> Spark -> Kafka alert.tenant.<tenant_id> -> Alert Delivery -> Webhook UI
```

Run Spark and Alert Delivery in separate terminals so the processing and delivery logs stay visible during the demo.

## Main Demo Commands

Start infrastructure:

```bash
./scripts/demo/start_infra.sh
```

Start local services:

```bash
./scripts/demo/start_services.sh
```

Start Spark processor:

```bash
./scripts/demo/run_spark_processor.sh
```

Start alert delivery:

```bash
./scripts/demo/run_alert_delivery.sh
```

Upload benign:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/benign.pcap -t tenant_A
```

Upload attack:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_A
```

View alerts:

```text
http://localhost:9001/alerts/tenant_A/view
```

Kafka UI:

```text
http://localhost:8080
```

Shutdown:

```bash
./scripts/demo/stop_services.sh
./scripts/demo/stop_infra.sh
```

## Terminal Layout

Print the commands for each terminal:

```bash
./scripts/demo/print_demo_commands.sh
```

Expected layout:

```text
Terminal 1 - Infra/services:
  ./scripts/demo/start_infra.sh
  ./scripts/demo/start_services.sh

Terminal 2 - Spark:
  ./scripts/demo/run_spark_processor.sh

Terminal 3 - Alert delivery:
  ./scripts/demo/run_alert_delivery.sh

Terminal 4 - Upload/test:
  ./scripts/demo/reset_demo_state.sh
  ./scripts/test/pcap_upload.sh -d data/samples/pcap/benign.pcap -t tenant_A
  ./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_A
```

## Reset Commands

Reset in-memory and transient demo state without stopping Kafka or Spark:

```bash
./scripts/demo/reset_demo_state.sh
```

This clears:

- Gateway dedupe memory through `POST /admin/clear-dedupe`
- Webhook alert memory through `POST /admin/clear-alerts`
- `outputs/live_flows/`
- `outputs/mining/`
- `outputs/gateway_events.jsonl`

Logs are kept by default. Clear transient logs explicitly:

```bash
CLEAR_LOGS=1 ./scripts/demo/reset_demo_state.sh
```

The reset script does not delete:

- `outputs/offline_adapter_test/`
- Trained model artifacts
- `data/csv/`
- `data/pcap/`
- `data/samples/`

Stop only local Python services:

```bash
./scripts/demo/stop_services.sh
```

Stop Docker infrastructure:

```bash
./scripts/demo/stop_infra.sh
```

## Status Checks

Show container, process, port, Kafka topic, and alert-count status:

```bash
./scripts/demo/demo_status.sh
```

Manual endpoint checks:

```bash
curl http://localhost:8000/health
curl http://localhost:9001/alerts/tenant_A
```

Expected ports:

- `8000`: Gateway
- `9001`: Webhook receiver
- `8080`: Kafka UI
- `4040`: Spark UI when Spark is running

## Kafka Debugging

List topics:

```bash
./scripts/debug/kafka_list_topics.sh
```

Consume raw upload events:

```bash
./scripts/debug/kafka_consume_topic.sh raw.tenant.tenant_A
```

Consume alert events:

```bash
./scripts/debug/kafka_consume_topic.sh alert.tenant.tenant_A
```

Expected tenant topic families:

- `raw.tenant.<tenant_id>`
- `alert.tenant.<tenant_id>`

## Demo Tests

Duplicate upload protection:

```bash
./scripts/test/test_duplicate_upload.sh
```

Direct webhook receiver check:

```bash
./scripts/test/test_webhook_direct.sh
```

RF inference smoke checks:

```bash
python3 scripts/test/test_rf_inference_csv.py data/samples/csv/benign.csv
python3 scripts/test/test_rf_inference_csv.py data/samples/csv/ddos.csv
```

## Detection Priority

Spark uses this order:

1. Resolve uploaded PCAP to a CICFlowMeter-compatible CSV and run the saved RF artifact.
2. If no matching CSV exists or RF scores zero rows, extract live flow-like features from the PCAP and use live flow rules.

The saved RF artifact path defaults to:

```text
outputs/offline_adapter_test/rf_anomaly.joblib
```

The live extraction output defaults to:

```text
outputs/live_flows/
```

## Script Groups

- `scripts/demo/`: startup, shutdown, reset, status, and foreground demo runners.
- `scripts/test/`: upload and lightweight validation scripts.
- `scripts/debug/`: Kafka and consumer inspection tools.
- `scripts/offline/`: offline IDS, Snort, and baseline entry points.
