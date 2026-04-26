# NIDSaaS Prototype

NIDSaaS Prototype is a research-to-prototype repository for network intrusion detection as a service. It currently contains a runnable offline IDS pipeline for CIC-IDS2017 experiments and a clean service-oriented layout for the planned streaming prototype.

## Current Status

The offline IDS pipeline is available under `src/nidsaas/detection/`. Snort replay and alert-mapping utilities are available under `src/nidsaas/snort/`. The local Gateway -> Kafka -> Spark -> Webhook demo path is implemented using saved IDS artifacts from `outputs/offline_adapter_test`. Real CIC-IDS2017 PCAP upload is supported for the demo by resolving the uploaded PCAP name to an existing pre-extracted CICFlowMeter CSV and using saved IDS prediction/label evidence. The injector UI is kept for future development. The current presentation demo uses CLI upload for reliability. Full live CICFlowMeter extraction and full online IDS inference are planned but not implemented yet.

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
│   ├── demo/
│   ├── test/
│   ├── debug/
│   ├── offline/
│   └── README.md
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
./scripts/demo/start_infra.sh
```

Kafka is exposed to the host at `localhost:9092`. The optional Kafka UI is available at `http://localhost:8080`.

Run the gateway:

```bash
./scripts/demo/start_services.sh
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
./scripts/test/test_duplicate_upload.sh
```

Expected duplicate behavior:

- First unique batch returns `decision="forward"` and is published to Kafka or written to `outputs/gateway_events.jsonl` if Kafka is unavailable.
- Re-uploading the exact same file for the same tenant/source/epoch returns `decision="drop_duplicate"` and is not published.
- A batch whose `end_offset` is already committed returns `decision="drop_stale"`.
- An overlapping new batch returns `decision="trim_overlap"` and includes `effective_start_offset`.

Consume the raw tenant topic:

```bash
./scripts/debug/kafka_consume_topic.sh raw.tenant.tenant_A
```

List topics:

```bash
./scripts/debug/kafka_list_topics.sh
```

Stop Kafka:

```bash
./scripts/demo/stop_infra.sh
```

If Kafka is unavailable, the gateway does not crash. It writes accepted upload events to `outputs/gateway_events.jsonl` and returns `published=false`.

## Gateway -> Kafka -> Consumer Local Test

Prototype step 2 adds a simple local Kafka consumer under `services/consumer/`. It subscribes to `raw.tenant.tenant_A` by default, parses gateway upload events as JSON, and prints the tenant, source, uploaded file path, and dedup decision.

Terminal 1:

```bash
./scripts/demo/start_infra.sh
./scripts/demo/start_services.sh
```

Terminal 2:

```bash
./scripts/debug/run_simple_consumer.sh
```

Terminal 3:

```bash
./scripts/test/test_duplicate_upload.sh
```

Expected result:

- The first upload returns `published=true` and the consumer prints one upload event.
- The duplicate upload returns `decision="drop_duplicate"` and should not publish a second Kafka message.
- To consume another topic, run `TOPIC=raw.tenant.some_tenant ./scripts/debug/run_simple_consumer.sh`.

## Kafka -> Spark IDS Artifact Demo

Prototype step 3 adds a PySpark Structured Streaming reader under `services/spark_stream/`. It subscribes to topics matching `raw.tenant.*`, parses upload-event JSON, prints normalized records with Kafka metadata, calls the IDS demo inference adapter, and dispatches attack alerts to the webhook receiver.

Kafka and Spark run in Docker Compose. The gateway still runs locally in the Python virtualenv and publishes to Kafka at `localhost:9092`; Spark reads the same broker from inside Docker at `kafka:29092`.

The Spark job uses `src/nidsaas/detection/demo_inference_adapter.py`, which loads saved offline IDS outputs from `outputs/offline_adapter_test`. It does not retrain RF, conformal calibration, or the escalation gate during the live demo. For real CIC-IDS2017 PCAP uploads, the adapter uses `src/nidsaas/detection/pcap_flow_resolver.py` to map the uploaded PCAP to the corresponding pre-extracted CICFlowMeter CSV under `data/csv/csv_CIC_IDS2017`. If saved cascade predictions contain rows for that CSV via `source_file`, those prediction rows are preferred as IDS evidence; otherwise the adapter falls back to the matched CSV `Label` column and marks the evidence source as `matched_cic_flow_csv_label`.

Live PCAP-to-flow extraction is not implemented in the runtime path yet. The current demo uses real PCAP upload as the trigger, existing CICFlowMeter CSVs as flow evidence, and existing IDS artifacts/outputs as model evidence.

Terminal 1:

```bash
./scripts/demo/start_infra.sh
```

Terminal 2:

```bash
./scripts/demo/start_services.sh
```

Terminal 3:

```bash
./scripts/demo/run_spark_processor.sh
```

Create the two small PCAP samples once:

```bash
./scripts/test/create_cic_pcap_samples.sh
```

Terminal 1:

```bash
./scripts/demo/start_infra.sh
```

Terminal 2:

```bash
./scripts/demo/start_services.sh
```

Terminal 3:

```bash
./scripts/demo/run_spark_processor.sh
```

Terminal 4:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_attack_sample.pcap -t tenant_A
```

View webhook UI:

```text
http://localhost:9001/alerts/tenant_A/view
```

Tenant B:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_attack_sample.pcap -t tenant_B
```

```text
http://localhost:9001/alerts/tenant_B/view
```

Duplicate upload check:

```bash
./scripts/test/test_duplicate_upload.sh
```

Expected Spark output:

```text
[SPARK] processing batch_id=..., rows=1
[SPARK] preprocessing upload event
[SPARK] calling IDS demo inference adapter
[SPARK] received PCAP: data/uploads/tenant_A/source_1/...
[SPARK] matched flow CSV: data/csv/csv_CIC_IDS2017/...
[SPARK] evidence_source: ids_prediction_artifact_source_file
[SPARK] prediction=attack
tenant_A source_1 demo_attack_upload.pcap attack high spark_real_ids_artifact_demo raw.tenant.tenant_A ...
```

The Spark runner uses Docker by default and runs `spark-submit` in the `spark` Compose service. It defaults to Kafka connector package `org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1`, `IDS_ARTIFACTS_DIR=outputs/offline_adapter_test`, `CIC_FLOW_CSV_ROOT=data/csv/csv_CIC_IDS2017`, `DEMO_FORCE_ATTACK=0`, and `WEBHOOK_BASE_URL=http://host.docker.internal:9001`. Set `DEMO_FORCE_ATTACK=1` only as a debug override. Override with `SPARK_KAFKA_PACKAGE=...` if your Spark image requires a different package.

## Webhook Alert Demo

Prototype step 4 adds a tenant-scoped webhook receiver under `services/webhook_receiver/` and a small dispatch helper under `services/alert_dispatcher/`. The tenant alert page updates live with Server-Sent Events when new alerts arrive, while the JSON endpoint remains available for debugging.

Terminal 1:

```bash
./scripts/demo/start_services.sh
```

Send a fake alert:

```bash
./scripts/test/test_webhook_direct.sh
```

Open the tenant alert view:

```text
http://localhost:9001/alerts/tenant_A/view
```

Direct webhook debug test:

```bash
./scripts/demo/start_services.sh
./scripts/test/test_webhook_direct.sh
```

Expected result:

- The test script posts a fake alert directly to `tenant_A`.
- The webhook receiver stores the alert in memory and pushes it live to `http://localhost:9001/alerts/tenant_A/view`.

## Main Demo Workflow

The main presentation flow uses Apache Spark as the visible processing job:

```text
Gateway -> Kafka -> Spark Structured Streaming -> IDS artifact demo adapter -> Webhook alert
```

The older `services/demo_processor/` path remains available as a fallback/debug consumer, but it is not started by default.

Terminal 1:

```bash
./scripts/demo/start_infra.sh
```

Terminal 2:

```bash
./scripts/demo/start_services.sh
```

Terminal 3:

```bash
./scripts/demo/run_spark_processor.sh
```

Terminal 4:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_attack_sample.pcap -t tenant_A
```

Open:

```text
http://localhost:9001/alerts/tenant_A/view
```

Standardized commands:

```bash
./scripts/demo/start_infra.sh
./scripts/demo/start_services.sh
./scripts/demo/run_spark_processor.sh
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_attack_sample.pcap -t tenant_A
```

Shutdown:

```bash
./scripts/demo/stop_services.sh
./scripts/demo/stop_infra.sh
```

Debug:

```bash
./scripts/debug/kafka_list_topics.sh
./scripts/debug/kafka_consume_topic.sh raw.tenant.tenant_A
./scripts/debug/run_simple_consumer.sh
./scripts/debug/run_demo_processor.sh
```

The old flat script wrappers were removed. `scripts/demo/start_infra.sh` starts Docker infrastructure. `scripts/demo/start_services.sh` starts the local gateway and webhook receiver in the background and writes logs to `logs/` and PID files to `.pids/`. Run Spark separately so it is visible during the presentation.

Detailed terminal layout:

Terminal 1:

```bash
./scripts/demo/start_infra.sh
```

Terminal 2:

```bash
./scripts/demo/start_services.sh
```

Terminal 3:

```bash
./scripts/demo/run_spark_processor.sh
```

Terminal 4:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_attack_sample.pcap -t tenant_A
```

Expected result:

- Gateway publishes the upload event to `raw.tenant.tenant_A`.
- Spark logs `[SPARK] processing batch_id=...`, `[SPARK] preprocessing upload event`, and `[SPARK] calling IDS demo inference adapter`.
- Spark dispatches an attack alert to `http://host.docker.internal:9001/webhook/tenant_A`.
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

See `docs/PROTOTYPE_ARCHITECTURE.md` for the service plan. `services/injector_ui/` is kept as a future/optional UI, but the current demo uses CLI upload and the webhook receiver UI.

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
python scripts/offline/run_pipeline.py \
  --data-dir data/csv/csv_CIC_IDS2017 \
  --snort-predictions data/samples/signature_merged_predictions.csv \
  --output-dir outputs/proposed_locked_a20_g50 \
  --alpha-escalate 0.20 \
  --calibration-fraction 0.50 \
  --split-strategy temporal_by_file \
  --seed 42
```

The direct package module is also available if `src/` is on `PYTHONPATH`, but `scripts/offline/run_pipeline.py` is the preferred entry point.

## Baselines and Snort Utilities

Baseline wrapper:

```bash
python scripts/offline/run_baseline.py rf --help
python scripts/offline/run_baseline.py rate --help
python scripts/offline/run_baseline.py anomaly --help
```

Snort utility wrapper:

```bash
python scripts/offline/run_snort.py runner --help
python scripts/offline/run_snort.py parser --help
python scripts/offline/run_snort.py policy-filter --help
python scripts/offline/run_snort.py evaluator --help
```

The Snort community rules and SID policy files are kept intact under:

```text
src/nidsaas/snort/rules/
```

## Notes

- This refactor preserves the existing IDS algorithms and moves them into a package layout.
- Kafka, Spark, gateway, webhook, and UI services are intentionally placeholders.
- Keep reusable source under `src/nidsaas/`, service code under `services/`, runnable entry points under `scripts/`, and generated experiment artifacts under `outputs/`.
