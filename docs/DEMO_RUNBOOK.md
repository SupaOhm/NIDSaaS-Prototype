# Demo Runbook

Stable demo flow:

```text
Gateway -> Kafka raw.tenant.<tenant_id> -> Spark -> Kafka alert.tenant.<tenant_id> -> Alert Delivery -> Webhook UI
```

Keep Spark and Alert Delivery in their own terminals. Their logs are part of the demo.

## Clean Start

Terminal 1:

```bash
./scripts/demo/start_infra.sh
./scripts/demo/start_services.sh
./scripts/demo/demo_status.sh
```

Terminal 2:

```bash
./scripts/demo/run_spark_processor.sh
```

Terminal 3:

```bash
./scripts/demo/run_alert_delivery.sh
```

Terminal 4:

```bash
./scripts/demo/reset_demo_state.sh
```

Open:

```text
http://localhost:9001/alerts/tenant_A/view
http://localhost:8080
```

## Normal Demo Run

Upload benign traffic:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/benign.pcap -t tenant_A
```

Expected result:

- Gateway returns `decision="forward"`.
- Spark logs a benign result.
- Alert Delivery does not forward a webhook alert for benign traffic.

Upload attack traffic:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_A
```

Expected result:

- Gateway publishes to `raw.tenant.tenant_A`.
- Spark publishes to `alert.tenant.tenant_A`.
- Alert Delivery forwards to `http://localhost:9001/webhook/tenant_A`.
- The alert appears at `http://localhost:9001/alerts/tenant_A/view`.

## RF Flow CSV Demo Mode

The saved RF model requires CICFlowMeter-compatible flow features. Full PCAP files are large, and live CICFlowMeter extraction is outside the short presentation window. For that reason, the demo supports direct upload of real CICFlowMeter CSV flows from CIC-IDS2017.

This still exercises the real demo pipeline:

```text
CSV upload -> Gateway -> Kafka raw.tenant.<tenant_id> -> Spark -> saved RF inference -> Kafka alert.tenant.<tenant_id> -> Alert Delivery -> Webhook UI
```

Upload a benign sample CSV:

```bash
./scripts/test/pcap_upload.sh --csv -d data/samples/csv/benign.csv -t tenant_A
```

Expected result:

- Spark runs saved RF inference on the uploaded CSV.
- The result is benign.
- No alert is published.

Upload an attack sample CSV:

```bash
./scripts/test/pcap_upload.sh --csv -d data/samples/csv/ddos.csv -t tenant_A
```

Expected result:

- Spark runs saved RF inference on the uploaded CSV.
- Spark publishes to `alert.tenant.tenant_A`.
- Alert Delivery forwards to the webhook UI.

Upload a full local CIC-IDS2017 CSV:

```bash
./scripts/test/pcap_upload.sh --csv -d data/csv/csv_CIC_IDS2017/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv -t tenant_A
```

Short wrapper:

```bash
./scripts/test/upload_flow_csv.sh data/samples/csv/ddos.csv tenant_A
```

## Reset Between Demos

Use reset when you want a clean visual demo without restarting Kafka or Spark:

```bash
./scripts/demo/reset_demo_state.sh
```

This clears gateway dedupe memory, webhook alerts, `outputs/live_flows/`, `outputs/mining/`, and `outputs/gateway_events.jsonl`.

Clear logs only when you want fresh log files:

```bash
CLEAR_LOGS=1 ./scripts/demo/reset_demo_state.sh
```

The reset script keeps model artifacts and datasets:

- `outputs/offline_adapter_test/`
- Trained artifacts
- `data/csv/`
- `data/pcap/`
- `data/samples/`

## Duplicate Test

Run:

```bash
./scripts/test/test_duplicate_upload.sh
```

Expected result:

- First upload returns `decision="forward"`.
- Second upload of the same bytes for the same tenant/source returns `decision="drop_duplicate"` with `reason="content_hash_match"`.

If you need to replay the same upload in a demo, run:

```bash
./scripts/demo/reset_demo_state.sh
```

## Tenant Isolation Test

Upload the same attack sample to two tenants:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_A
./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_B
```

Open:

```text
http://localhost:9001/alerts/tenant_A/view
http://localhost:9001/alerts/tenant_B/view
```

Expected result:

- Tenant A alert appears only on the Tenant A page.
- Tenant B alert appears only on the Tenant B page.
- Kafka topics are tenant-scoped: `raw.tenant.tenant_A`, `raw.tenant.tenant_B`, `alert.tenant.tenant_A`, and `alert.tenant.tenant_B`.

## Kafka Alert Topic Proof

List topics:

```bash
./scripts/debug/kafka_list_topics.sh
```

Consume alert topic:

```bash
./scripts/debug/kafka_consume_topic.sh alert.tenant.tenant_A
```

Expected Spark log:

```text
[SPARK] published alert to Kafka topic alert.tenant.tenant_A
```

Expected Alert Delivery log:

```text
[DELIVERY] received alert from Kafka topic=alert.tenant.tenant_A
[DELIVERY] forwarded to webhook http://localhost:9001/webhook/tenant_A
```

## Troubleshooting

### Gateway Not Reachable

Check:

```bash
./scripts/demo/demo_status.sh
curl http://localhost:8000/health
tail -n 80 logs/gateway.log
```

Fix:

```bash
./scripts/demo/stop_services.sh
./scripts/demo/start_services.sh
```

### Spark Running But No Alert

Check Spark logs for:

```text
[SPARK] processing batch_id=...
[SPARK] prediction=attack
[SPARK] benign result, no alert dispatched
```

If the upload was benign, no webhook alert is expected. If the upload was attack traffic, verify the raw topic exists:

```bash
./scripts/debug/kafka_list_topics.sh
./scripts/debug/kafka_consume_topic.sh raw.tenant.tenant_A
```

### Alert In Kafka But Not UI

Check that Alert Delivery is running before uploading:

```bash
./scripts/demo/run_alert_delivery.sh
```

It should log:

```text
[DELIVERY] polling Kafka topics matching alert.tenant.*
[DELIVERY] received alert from Kafka topic=alert.tenant.tenant_A
[DELIVERY] forwarded to webhook
```

For debug replay of older alert-topic messages:

```bash
ALERT_DELIVERY_START_FROM_BEGINNING=1 ./scripts/demo/run_alert_delivery.sh
```

Default demo behavior consumes new alerts quickly and does not replay old backlog.

### Duplicate Upload Dropped

This is expected when the same PCAP bytes are uploaded twice for the same tenant/source. The gateway response will include:

```json
{"decision": "drop_duplicate", "reason": "content_hash_match"}
```

Reset dedupe memory:

```bash
./scripts/demo/reset_demo_state.sh
```

### Webhook UI Empty

Check:

```bash
curl http://localhost:9001/alerts/tenant_A
./scripts/demo/demo_status.sh
```

If JSON has alerts but `/view` is empty, refresh the page. If JSON is empty, verify Alert Delivery forwarded the alert.

### Port 7000 Occupied By macOS ControlCenter

Port `7000` is only for the optional injector UI. It is not used in the main CLI demo. If you run the optional UI and the port is occupied, set another port:

```bash
INJECTOR_UI_PORT=7001 ./scripts/demo/run_injector_ui.sh
```

### Reset vs Stop Services vs Stop Infra

Use reset when you want to keep Kafka, Spark, gateway, and webhook running:

```bash
./scripts/demo/reset_demo_state.sh
```

Use stop services when gateway or webhook processes need a clean restart:

```bash
./scripts/demo/stop_services.sh
./scripts/demo/start_services.sh
```

Use stop infra when you want to stop Kafka, Zookeeper, Kafka UI, and Docker Spark containers:

```bash
./scripts/demo/stop_infra.sh
```
