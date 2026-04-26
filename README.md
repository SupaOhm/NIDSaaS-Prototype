# NIDSaaS Prototype

NIDSaaS Prototype is a research-to-prototype repository for network intrusion detection as a service. It currently contains a runnable offline IDS pipeline for CIC-IDS2017 experiments and a clean service-oriented layout for the planned streaming prototype.

## Current Status

The offline IDS pipeline is available under `src/nidsaas/detection/`. Snort replay and alert-mapping utilities are available under `src/nidsaas/snort/`. The local Gateway -> Kafka -> Consumer path is implemented, Docker Spark can read upload events from Kafka, and a demo webhook receiver can display fake tenant alerts. IDS-in-Spark and injector UI services are planned but not implemented yet.

## Repository Structure

```text
.
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── csv/
│   │   └── csv_CIC_IDS2017/
│   ├── pcap/
│   │   └── pcap_CIC_IDS2017/
│   └── samples/
│       └── signature_merged_predictions.csv
├── outputs/
├── src/
│   └── nidsaas/
│       ├── common/
│       ├── config/
│       ├── detection/
│       └── snort/
├── services/
│   ├── gateway/
│   ├── consumer/
│   ├── spark_stream/
│   ├── alert_dispatcher/
│   ├── webhook_receiver/
│   └── injector_ui/
├── scripts/
└── docs/
```

## Existing Offline IDS Pipeline

The current detector is a hybrid IDS pipeline:

1. Load and normalize CIC-IDS2017 flow CSVs.
2. Split data with the locked `temporal_by_file` strategy.
3. Merge cached or regenerated signature/rate-rule predictions.
4. Train or load a self-supervised RF anomaly detector.
5. Calibrate RF anomaly scores with split conformal p-values.
6. Train an escalation gate on suspicious validation rows.
7. Export validation/test prediction tables and metrics.
8. Apply validation-calibrated operating thresholds.

The cached signature table used by the current pipeline is stored at:

```text
data/samples/signature_merged_predictions.csv
```

## Gateway API Prototype

Prototype step 1 is implemented under `services/gateway/`. The gateway accepts tenant PCAP/file uploads, applies mock authentication and safe batch deduplication, saves accepted files under `data/uploads/<tenant_id>/<source_id>/`, and publishes accepted upload metadata to Kafka topic `raw.tenant.<tenant_id>`.

Start Kafka:

```bash
./scripts/start_kafka.sh
```

Kafka is exposed to the host at `localhost:9092`. The optional Kafka UI is available at `http://localhost:8080`.

Run the gateway:

```bash
./scripts/run_gateway.sh
```

Upload a tiny sample file:

```bash
mkdir -p data/samples
echo "demo packet data for NIDSaaS gateway test" > data/samples/demo_upload.pcap

curl -sS --connect-timeout 5 --max-time 20 \
  -X POST http://localhost:8000/upload-pcap \
  -H "x-api-key: dev-secret" \
  -F tenant_id=tenant_A \
  -F source_id=source_1 \
  -F file_epoch=demo_epoch \
  -F start_offset=0 \
  -F end_offset=100 \
  -F file=@data/samples/demo_upload.pcap
```

Manual duplicate test:

```bash
./scripts/test_gateway_upload.sh
```

Expected duplicate behavior:

- First unique batch returns `decision="forward"` and is published to Kafka or written to `outputs/gateway_events.jsonl` if Kafka is unavailable.
- Re-uploading the exact same file for the same tenant/source/epoch returns `decision="drop_duplicate"` and is not published.
- A batch whose `end_offset` is already committed returns `decision="drop_stale"`.
- An overlapping new batch returns `decision="trim_overlap"` and includes `effective_start_offset`.

Consume the raw tenant topic:

```bash
./scripts/consume_kafka_topic.sh raw.tenant.tenant_A
```

List topics:

```bash
./scripts/list_kafka_topics.sh
```

Stop Kafka:

```bash
./scripts/stop_kafka.sh
```

If Kafka is unavailable, the gateway does not crash. It writes accepted upload events to `outputs/gateway_events.jsonl` and returns `published=false`.

## Gateway -> Kafka -> Consumer Local Test

Prototype step 2 adds a simple local Kafka consumer under `services/consumer/`. It subscribes to `raw.tenant.tenant_A` by default, parses gateway upload events as JSON, and prints the tenant, source, uploaded file path, and dedup decision.

Terminal 1:

```bash
./scripts/start_kafka.sh
./scripts/run_gateway.sh
```

Terminal 2:

```bash
./scripts/run_consumer.sh
```

Terminal 3:

```bash
./scripts/test_gateway_upload.sh
```

Expected result:

- The first upload returns `published=true` and the consumer prints one upload event.
- The duplicate upload returns `decision="drop_duplicate"` and should not publish a second Kafka message.
- To consume another topic, run `TOPIC=raw.tenant.some_tenant ./scripts/run_consumer.sh`.

## Kafka -> Spark Local Test

Prototype step 3 adds a PySpark Structured Streaming reader under `services/spark_stream/`. It subscribes to topics matching `raw.tenant.*`, parses upload-event JSON, and prints normalized records with Kafka metadata. This only proves Kafka -> Spark consumption; IDS inference is not integrated yet.

Kafka and Spark run in Docker Compose. The gateway still runs locally in the Python virtualenv and publishes to Kafka at `localhost:9092`; Spark reads the same broker from inside Docker at `kafka:29092`.

Terminal 1:

```bash
./scripts/start_kafka.sh
```

Terminal 2:

```bash
./scripts/run_gateway.sh
```

Terminal 3:

```bash
./scripts/run_spark_stream.sh
```

Terminal 4:

```bash
./scripts/test_gateway_upload.sh
```

Expected Spark output:

```text
[SPARK] processing batch_id=..., rows=1
tenant_A source_1 data/uploads/... forward raw.tenant.tenant_A ...
```

The Spark runner uses Docker by default and runs `spark-submit` in the `spark` Compose service. It defaults to Kafka connector package `org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1`. Override with `SPARK_KAFKA_PACKAGE=...` if your Spark image requires a different package. Local Spark is optional with `RUN_SPARK_LOCAL=1 ./scripts/run_spark_stream.sh`.

## Webhook Alert Demo

Prototype step 4 adds a tenant-scoped webhook receiver under `services/webhook_receiver/` and a small dispatch helper under `services/alert_dispatcher/`. This milestone uses fake detection alerts so the demo can show alert delivery without running full IDS training.

Terminal 1:

```bash
./scripts/run_webhook_receiver.sh
```

Send a fake alert:

```bash
./scripts/test_webhook_alert.sh
```

Open the tenant alert view:

```text
http://localhost:9001/alerts/tenant_A/view
```

End-to-end demo with gateway upload plus fake alert:

```bash
./scripts/start_kafka.sh
./scripts/run_gateway.sh
./scripts/run_webhook_receiver.sh
./scripts/test_end_to_end_fake_alert.sh
```

Expected result:

- Gateway accepts the sample upload and publishes metadata to Kafka.
- The test script posts a fake alert to `tenant_A`.
- The webhook receiver stores the alert in memory and shows it at `http://localhost:9001/alerts/tenant_A/view`.

## Full Demo Processor Flow

Prototype step 5 adds `services/demo_processor/`, a fast Kafka consumer that turns upload events into demo detection results and dispatches attack alerts to the webhook receiver. This path does not require Spark and does not run the offline IDS cascade.

Terminal 1:

```bash
./scripts/start_kafka.sh
```

Terminal 2:

```bash
./scripts/run_gateway.sh
```

Terminal 3:

```bash
./scripts/run_webhook_receiver.sh
```

Terminal 4:

```bash
DEMO_FORCE_ATTACK=1 ./scripts/run_demo_processor.sh
```

Terminal 5:

```bash
./scripts/test_full_demo_alert.sh
```

Expected result:

- Gateway publishes the upload event to `raw.tenant.tenant_A`.
- The demo processor logs `[PROCESSOR] received upload event` and `[PROCESSOR] prediction=attack`.
- The dispatcher logs `[ALERT] dispatched to http://localhost:9001/webhook/tenant_A`.
- The alert appears at `http://localhost:9001/alerts/tenant_A/view`.

## Planned Streaming Prototype

The planned NIDSaaS streaming flow is:

```text
PCAP Injector UI
-> Gateway API with mock auth and dedup
-> Kafka topic raw.tenant.<tenant_id>
-> PySpark Structured Streaming preprocessing and IDS inference
-> Alert Dispatcher
-> Tenant Webhook Receiver UI
```

See `docs/PROTOTYPE_ARCHITECTURE.md` for the service plan. These services are scaffolded under `services/` but do not contain runtime logic yet.

## Setup

Use Python 3.10 or 3.11 where possible.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Expected local data placement:

- CIC-IDS2017 flow CSVs: `data/csv/csv_CIC_IDS2017/`
- CIC-IDS2017 PCAPs for optional Snort runs: `data/pcap/pcap_CIC_IDS2017/`
- Generated outputs: `outputs/`

Large raw data and generated model artifacts should remain untracked.

## Run the Current Offline IDS Pipeline

From the repository root:

```bash
python scripts/run_pipeline.py \
  --data-dir data/csv/csv_CIC_IDS2017 \
  --snort-predictions data/samples/signature_merged_predictions.csv \
  --output-dir outputs/proposed_locked_a20_g50 \
  --alpha-escalate 0.20 \
  --calibration-fraction 0.50 \
  --split-strategy temporal_by_file \
  --seed 42
```

The direct package module is also available if `src/` is on `PYTHONPATH`, but `scripts/run_pipeline.py` is the preferred entry point.

## Baselines and Snort Utilities

Baseline wrapper:

```bash
python scripts/run_baseline.py rf --help
python scripts/run_baseline.py rate --help
python scripts/run_baseline.py anomaly --help
```

Snort utility wrapper:

```bash
python scripts/run_snort.py runner --help
python scripts/run_snort.py parser --help
python scripts/run_snort.py policy-filter --help
python scripts/run_snort.py evaluator --help
```

The Snort community rules and SID policy files are kept intact under:

```text
src/nidsaas/snort/rules/
```

## Notes

- This refactor preserves the existing IDS algorithms and moves them into a package layout.
- Kafka, Spark, gateway, webhook, and UI services are intentionally placeholders.
- Keep reusable source under `src/nidsaas/`, service code under `services/`, runnable entry points under `scripts/`, and generated experiment artifacts under `outputs/`.
