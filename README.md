# NIDSaaS Prototype

NIDSaaS Prototype is a research-to-prototype repository for Network Intrusion Detection as a Service. The main objective of this README is to make the prototype reproducible: a new operator should be able to install the required tools, prepare the data/artifacts, run the local demo step by step, verify the expected outputs, and stop or reset the system safely.

The current demo shows a tenant-scoped IDS workflow:

```text
PCAP or Flow CSV Upload
-> Gateway API
-> Kafka raw.tenant.<tenant_id>
-> Spark Structured Streaming
-> IDS artifact inference adapter
-> Kafka alert.tenant.<tenant_id>
-> Alert Delivery Service
-> Webhook Alert UI
```

The demo uses real CIC-IDS2017 PCAP upload inputs and direct CICFlowMeter CSV flow uploads. PCAP uploads resolve to pre-extracted CICFlowMeter CSV evidence when available, and CSV uploads go directly through saved RF inference. Full live CICFlowMeter extraction and full online IDS retraining are not part of the current presentation demo.

## Current Prototype Scope

Implemented:

- Offline hybrid IDS pipeline under `src/nidsaas/detection/`
- Snort replay and alert-mapping utilities under `src/nidsaas/snort/`
- Gateway upload API with mock API-key authentication
- Tenant-scoped Kafka upload topics: `raw.tenant.<tenant_id>`
- Spark Structured Streaming processor for upload events
- IDS artifact inference adapter using saved offline artifacts
- Tenant-scoped Kafka alert topics: `alert.tenant.<tenant_id>`
- Alert delivery service
- Webhook receiver with browser-based tenant alert view
- CLI-based demo upload workflow

Not implemented yet:

- Full production authentication and tenant management
- Full live CICFlowMeter extraction for every uploaded PCAP
- Full online IDS model inference/retraining pipeline
- Production deployment hardening
- Injector UI production workflow

## Prerequisites

Recommended environment:

- macOS or Linux
- Python 3.10 or 3.11
- Docker and Docker Compose
- Git
- `curl`
- At least 8 GB RAM available for Docker and Spark

Optional tools:

- `tshark` for live fallback flow extraction
- CICFlowMeter if testing full PCAP-to-flow extraction outside the saved-artifact demo path

Check basic tools:

```bash
python3 --version
docker --version
docker compose version
git --version
curl --version
```

## Repository Structure

```text
.
├── README.md
├── requirements.txt
├── data/
│   ├── csv/
│   │   └── csv_CIC_IDS2017/
│   ├── pcap/
│   │   └── pcap_CIC_IDS2017/
│   └── samples/
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
│   ├── alert_delivery/
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

## Required Local Data and Artifacts

Large datasets and generated artifacts are intentionally excluded from Git.

Expected local paths:

```text
data/csv/csv_CIC_IDS2017/          # CIC-IDS2017 flow CSV files
data/pcap/pcap_CIC_IDS2017/        # CIC-IDS2017 PCAP files, optional for mining samples
data/samples/pcap/                 # Small demo PCAP samples
outputs/offline_adapter_test/       # Saved IDS artifacts for demo inference
```

Required saved artifact for the current Spark demo:

```text
outputs/offline_adapter_test/rf_anomaly.joblib
```

Required cached signature table for the offline IDS pipeline:

```text
data/samples/signature_merged_predictions.csv
```

Example demo PCAP files:

```text
data/samples/pcap/cic_attack_sample.pcap
data/samples/pcap/cic_ddos_sample.pcap
data/samples/pcap/cic_portscan_sample.pcap
data/samples/pcap/cic_webattack_sample.pcap
data/samples/pcap/cic_benign_sample.pcap
```

If these files are missing, generate sample PCAP windows from local CIC-IDS2017 PCAPs:

```bash
./scripts/test/mine_live_cic_attack_windows.sh
```

The mining script searches local PCAP data and writes small demo files under `data/samples/pcap/`. If a specific attack type is unavailable in the local dataset, the script reports it as unavailable.

## Python Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Verify the Python environment:

```bash
python -c "import pandas, sklearn, joblib; print('python dependencies ok')"
```

## Quick Start: Main Reproducible Demo

Run each long-running component in a separate terminal.

### Terminal 1: Start Kafka and infrastructure

```bash
./scripts/demo/start_infra.sh
```

Expected result:

- Kafka starts successfully
- Kafka is reachable on the host at `localhost:9092`
- Kafka UI is available at `http://localhost:8080`

Check Kafka topics:

```bash
./scripts/debug/kafka_list_topics.sh
```

### Terminal 2: Start Gateway and Webhook Receiver

```bash
./scripts/demo/start_services.sh
```

Expected result:

- Gateway starts at `http://localhost:8000`
- Webhook receiver starts at `http://localhost:9001`
- Logs are written under `logs/`
- PID files are written under `.pids/`

### Terminal 3: Start Spark Processor

```bash
./scripts/demo/run_spark_processor.sh
```

Expected result:

- Spark starts through Docker Compose
- Spark subscribes to `raw.tenant.*` topics
- The terminal stays open and prints processing logs when uploads arrive

### Terminal 4: Start Alert Delivery

```bash
./scripts/demo/run_alert_delivery.sh
```

Expected result:

- Alert delivery subscribes to `alert.tenant.*` topics
- The terminal stays open and forwards alerts to the webhook receiver

### Terminal 5: Upload a Demo PCAP

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_attack_sample.pcap -t tenant_A
```

Category-specific samples can also be uploaded:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_ddos_sample.pcap -t tenant_A
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_portscan_sample.pcap -t tenant_A
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_webattack_sample.pcap -t tenant_A
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_benign_sample.pcap -t tenant_A
```

View tenant alerts in the browser:

```text
http://localhost:9001/alerts/tenant_A/view
```

## RF Flow CSV Demo Mode

The saved RF model requires CICFlowMeter-compatible flow features. Full PCAP files are large, and live CICFlowMeter extraction is outside the short presentation path, so the demo supports direct upload of real CICFlowMeter CSV flows from CIC-IDS2017.

This still exercises the real pipeline:

```text
CSV upload -> Gateway -> Kafka raw.tenant.<tenant_id> -> Spark -> saved RF inference -> Kafka alert.tenant.<tenant_id> -> Alert Delivery -> Webhook UI
```

Upload sample flow CSVs:

```bash
./scripts/test/pcap_upload.sh --csv -d data/samples/csv/benign.csv -t tenant_A
./scripts/test/pcap_upload.sh --csv -d data/samples/csv/ddos.csv -t tenant_A
```

Upload a full local CIC-IDS2017 flow CSV:

```bash
./scripts/test/pcap_upload.sh --csv -d data/csv/csv_CIC_IDS2017/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv -t tenant_A
```

## Expected End-to-End Result

A successful run should show this behavior:

1. The upload script sends a PCAP to the Gateway.
2. The Gateway saves the accepted upload under `data/uploads/<tenant_id>/<source_id>/`.
3. The Gateway publishes upload metadata to `raw.tenant.tenant_A`.
4. Spark consumes the upload event.
5. Spark resolves the uploaded PCAP to CICFlowMeter-compatible CSV evidence when available.
6. Spark uses the saved IDS artifact from `outputs/offline_adapter_test`.
7. Spark publishes an alert to `alert.tenant.tenant_A`.
8. Alert Delivery forwards the alert to the Webhook Receiver.
9. The alert appears in the tenant alert UI.

Expected Spark log pattern:

```text
[SPARK] processing batch_id=..., rows=1
[SPARK] preprocessing upload event
[SPARK] calling IDS demo inference adapter
[SPARK] received PCAP: data/uploads/tenant_A/source_1/...
[SPARK] matched flow CSV: data/csv/csv_CIC_IDS2017/...
[SPARK] evidence_source: ids_prediction_artifact_source_file
[SPARK] prediction=attack
tenant_A source_1 ... attack high spark_real_ids_artifact_demo raw.tenant.tenant_A ...
```

Expected alert page:

```text
http://localhost:9001/alerts/tenant_A/view
```

The page should show a new tenant-scoped IDS alert after the upload is processed.

## Print Demo Command Layout

To print the standard terminal layout:

```bash
./scripts/demo/print_demo_commands.sh
```

## Stop and Reset

Stop local services:

```bash
./scripts/demo/stop_services.sh
```

Stop Docker infrastructure:

```bash
./scripts/demo/stop_infra.sh
```

Clear webhook alerts:

```bash
curl -sS -X POST http://localhost:9001/admin/clear-alerts
```

Clear gateway in-memory dedupe state between repeated demos:

```bash
./scripts/test/clear_dedupe_memory.sh
```

If a port is already in use, stop old demo processes first:

```bash
./scripts/demo/stop_services.sh
./scripts/demo/stop_infra.sh
```

Then check remaining processes manually if needed:

```bash
lsof -i :8000
lsof -i :9001
lsof -i :9092
```

## Duplicate Upload Test

Run the duplicate upload test:

```bash
./scripts/test/test_duplicate_upload.sh
```

Expected behavior:

- First unique batch returns `decision="forward"` and is published to Kafka.
- Re-uploading the exact same file for the same tenant/source/epoch returns `decision="drop_duplicate"` and is not published.
- A stale batch returns `decision="drop_stale"`.
- An overlapping new batch returns `decision="trim_overlap"` with `effective_start_offset`.

Consume the raw tenant topic for debugging:

```bash
./scripts/debug/kafka_consume_topic.sh raw.tenant.tenant_A
```

## Manual Gateway Upload Test

Start infrastructure and services first:

```bash
./scripts/demo/start_infra.sh
./scripts/demo/start_services.sh
```

Create a tiny sample file:

```bash
mkdir -p data/samples
echo "demo packet data for NIDSaaS gateway test" > data/samples/demo_upload.pcap
```

Upload it manually:

```bash
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

If Kafka is unavailable, the Gateway should not crash. It writes accepted upload events to:

```text
outputs/gateway_events.jsonl
```

and returns `published=false`.

## Run the Offline IDS Pipeline

The offline IDS pipeline is separate from the live demo and can be used to regenerate experiment outputs.

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

The current detector pipeline:

1. Loads and normalizes CIC-IDS2017 flow CSVs.
2. Splits data with the locked `temporal_by_file` strategy.
3. Merges cached or regenerated signature/rate-rule predictions.
4. Trains or loads a self-supervised RF anomaly detector.
5. Calibrates RF anomaly scores with split conformal p-values.
6. Trains an escalation gate on suspicious validation rows.
7. Exports validation/test prediction tables and metrics.
8. Applies validation-calibrated operating thresholds.

## Baseline and Snort Utilities

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

Snort community rules and SID policy files are kept under:

```text
src/nidsaas/snort/rules/
```

## Important Environment Variables

The Spark runner has these useful defaults:

```text
SPARK_KAFKA_PACKAGE=org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1
IDS_ARTIFACTS_DIR=outputs/offline_adapter_test
CIC_FLOW_CSV_ROOT=data/csv/csv_CIC_IDS2017
DEMO_FORCE_ATTACK=0
LIVE_FLOW_OUTPUT_DIR=outputs/live_flows
```

Use `DEMO_FORCE_ATTACK=1` only as a debug override, not for the main reproducible demo.

Example override:

```bash
IDS_ARTIFACTS_DIR=outputs/offline_adapter_test ./scripts/demo/run_spark_processor.sh
```

## Troubleshooting

### Port already in use

```bash
./scripts/demo/stop_services.sh
lsof -i :8000
lsof -i :9001
```

Kill only the stale process if needed.

### Kafka topic not found

Start infrastructure first:

```bash
./scripts/demo/start_infra.sh
```

Then list topics:

```bash
./scripts/debug/kafka_list_topics.sh
```

### Spark does not receive uploads

Check that the Gateway published the upload:

```bash
./scripts/debug/kafka_consume_topic.sh raw.tenant.tenant_A
```

Check that Spark is running in its own terminal:

```bash
./scripts/demo/run_spark_processor.sh
```

### Alert page is empty

Check that Alert Delivery is running:

```bash
./scripts/demo/run_alert_delivery.sh
```

Check the tenant page:

```text
http://localhost:9001/alerts/tenant_A/view
```

### Missing demo PCAP samples

Generate samples from local CIC-IDS2017 PCAPs:

```bash
./scripts/test/mine_live_cic_attack_windows.sh
```

### Missing saved IDS artifacts

The main demo expects saved artifacts under:

```text
outputs/offline_adapter_test/
```

If this directory is missing, run the offline pipeline or copy the prepared artifacts before starting the Spark demo.

## Reproducibility Checklist

Before presenting or testing, verify:

- Python virtual environment is active
- Dependencies are installed from `requirements.txt`
- Docker is running
- Kafka infrastructure starts successfully
- `outputs/offline_adapter_test/rf_anomaly.joblib` exists
- `data/samples/signature_merged_predictions.csv` exists
- Demo PCAP files exist under `data/samples/pcap/`
- Gateway starts on port `8000`
- Webhook receiver starts on port `9001`
- Spark processor is running visibly in its own terminal
- Alert Delivery is running visibly in its own terminal
- Tenant alert page opens in the browser

## Additional Documentation

Main operator docs:

- `docs/DEMO_RUNBOOK.md`
- `scripts/README.md`
- `docs/PROTOTYPE_ARCHITECTURE.md`

## Notes for Contributors

- Keep reusable source code under `src/nidsaas/`.
- Keep service code under `services/`.
- Keep runnable entry points under `scripts/`.
- Keep generated outputs under `outputs/`.
- Keep large raw datasets and generated model artifacts untracked.
- The old flat script wrappers were removed. Use the organized scripts under `scripts/demo/`, `scripts/test/`, `scripts/debug/`, and `scripts/offline/`.
