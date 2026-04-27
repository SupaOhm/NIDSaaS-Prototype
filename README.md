# NIDSaaS Prototype

## Overview

This repository contains the submitted prototype implementation for a tenant-aware Network Intrusion Detection as a Service (NIDSaaS) pipeline. It demonstrates local reproducibility of ingestion, tenant-scoped Kafka buffering, Spark-based detection orchestration, saved Random Forest (RF) inference, Kafka alert topics, alert delivery, and a browser-based webhook alert view.

Main runtime flow:

```text
PCAP or CICFlowMeter CSV upload
-> Gateway API
-> Kafka raw.tenant.<tenant_id>
-> Spark Structured Streaming
-> saved RF / IDS inference
-> Kafka alert.tenant.<tenant_id>
-> Alert Delivery Service
-> Webhook Alert UI
```

The recommended evaluator path is the RF Flow CSV demo mode. It uploads real CICFlowMeter-compatible CIC-IDS2017 flow CSV files through the Gateway and runs the saved RF inference adapter inside Spark.

## Repository Structure

```text
.
├── README.md
├── requirements.txt
├── docker-compose.yml
├── docker/spark/Dockerfile
├── data/
│   ├── csv/                  # local CIC-IDS2017 CSV data
│   ├── pcap/                 # local CIC-IDS2017 PCAP data
│   ├── samples/csv/          # small demo flow CSV samples
│   └── samples/pcap/         # small demo PCAP samples
├── outputs/
│   └── offline_adapter_test/ # saved RF/IDS artifacts
├── services/
│   ├── gateway/              # FastAPI upload gateway
│   ├── spark_stream/         # Spark upload-event processor
│   ├── alert_delivery/       # Kafka alert topic consumer
│   ├── webhook_receiver/     # tenant alert receiver and UI
│   └── alert_dispatcher/     # webhook POST helper
├── src/nidsaas/
│   ├── detection/            # IDS pipeline and inference adapters
│   └── snort/                # Snort utilities and rules
├── scripts/
│   ├── demo/                 # start, stop, reset, status scripts
│   ├── test/                 # upload and validation scripts
│   ├── debug/                # Kafka inspection scripts
│   └── offline/              # offline IDS entry points
└── docs/
    └── DEMO_RUNBOOK.md       # detailed operator runbook
```

## Prerequisites

Recommended environment:

- macOS or Linux terminal
- Python 3.10 or 3.11
- Docker Desktop or Docker Engine with Docker Compose
- Git
- `curl`
- At least 8 GB RAM available for Docker and Spark

Verify tools:

```bash
python3 --version
docker --version
docker compose version
git --version
curl --version
```

## Required Local Data and Artifacts

Large CIC datasets and generated model artifacts are kept outside normal source control. For evaluation, place the provided data/artifact files at these paths before running the full demo:

```text
outputs/offline_adapter_test/rf_anomaly.joblib
data/samples/csv/benign.csv
data/samples/csv/ddos.csv
```

Recommended additional files:

```text
outputs/offline_adapter_test/
data/csv/csv_CIC_IDS2017/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv
data/samples/pcap/benign.pcap
data/samples/pcap/ddos.pcap
data/samples/signature_merged_predictions.csv
```

The small CSV samples are enough for the main RF Flow CSV demo. The full CIC CSV path is used for larger validation.

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Verify Python dependencies:

```bash
python -c "import pandas, sklearn, joblib, fastapi, kafka; print('python dependencies ok')"
```

Build or refresh the Spark image:

```bash
docker compose build spark
```

Validate Compose configuration:

```bash
docker compose config --quiet
```

## Running the System

Run long-running components in separate terminals so their logs remain visible.

### Terminal 1: Infrastructure

```bash
./scripts/demo/start_infra.sh
```

Expected output includes:

```text
[INFRA] Kafka ready at localhost:9092
[INFRA] Kafka UI: http://localhost:8080
```

### Terminal 2: Gateway and Webhook Receiver

```bash
./scripts/demo/start_services.sh
```

Expected endpoints:

```text
Gateway health: http://localhost:8000/health
Webhook UI:     http://localhost:9001/
```

### Terminal 3: Spark Processor

```bash
./scripts/demo/run_spark_processor.sh
```

Spark subscribes to:

```text
raw.tenant.*
```

### Terminal 4: Alert Delivery

```bash
./scripts/demo/run_alert_delivery.sh
```

Alert Delivery subscribes to:

```text
alert.tenant.*
```

### Terminal 5: Upload Test Data

Recommended RF Flow CSV attack upload:

```bash
./scripts/test/pcap_upload.sh --csv -d data/samples/csv/ddos.csv -t tenant_A
```

Recommended benign upload:

```bash
./scripts/test/pcap_upload.sh --csv -d data/samples/csv/benign.csv -t tenant_A
```

Full CIC-IDS2017 CSV upload:

```bash
./scripts/test/pcap_upload.sh --csv -d data/csv/csv_CIC_IDS2017/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv -t tenant_A
```

PCAP upload mode is also available:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_A
./scripts/test/pcap_upload.sh -d data/samples/pcap/benign.pcap -t tenant_A
```

Open the tenant alert page:

```text
http://localhost:9001/alerts/tenant_A/view
```

Open Kafka UI:

```text
http://localhost:8080
```

Print the standard command layout:

```bash
./scripts/demo/print_demo_commands.sh
```

## Testing and Verification

### 1. Status Check

```bash
./scripts/demo/demo_status.sh
```

This reports Docker containers, local services, ports, Kafka topics, Spark/Alert Delivery processes, and alert counts for `tenant_A` and `tenant_B`.

### 2. RF Inference Smoke Test

Host Python:

```bash
.venv/bin/python scripts/test/test_rf_inference_csv.py data/samples/csv/ddos.csv
```

Spark container:

```bash
docker compose run --rm spark python3 scripts/test/test_rf_inference_csv.py data/samples/csv/ddos.csv
```

Expected fields for the DDoS CSV:

```text
status="success"
rows_scored > 0
prediction="attack"
attack_ratio >= 0.20
```

### 3. End-to-End Alert Test

With infrastructure, services, Spark, and Alert Delivery running:

```bash
./scripts/test/test_flow_csv_rf_alert.sh data/samples/csv/ddos.csv
```

Expected Spark log pattern:

```text
[SPARK] using uploaded flow CSV for saved RF inference
[SPARK] RF attack_ratio=...
[SPARK] prediction=attack
[SPARK] published alert to Kafka topic alert.tenant.tenant_A
```

Expected Alert Delivery log pattern:

```text
[DELIVERY] received alert from Kafka topic=alert.tenant.tenant_A
[DELIVERY] forwarded to webhook http://localhost:9001/webhook/tenant_A
```

Expected UI result:

```text
http://localhost:9001/alerts/tenant_A/view
```

The page shows a tenant-scoped alert row with severity, prediction, attack type, timestamp, and evidence fields.

### 4. Duplicate Upload Test

```bash
./scripts/test/test_duplicate_upload.sh
```

Expected behavior:

- First upload returns `decision="forward"`.
- Second upload of the same bytes for the same tenant/source returns `decision="drop_duplicate"`.
- Duplicate reason is `content_hash_match`.

### 5. Kafka Topic Inspection

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

## Expected Output Summary

For an attack CSV upload, the system should produce:

1. Gateway response with `status="accepted"` and `decision="forward"`.
2. Kafka raw event on `raw.tenant.tenant_A`.
3. Spark RF inference result with `prediction="attack"`.
4. Kafka alert event on `alert.tenant.tenant_A`.
5. Alert Delivery webhook forward log.
6. Browser-visible alert at `http://localhost:9001/alerts/tenant_A/view`.

For a benign CSV upload, Spark logs `prediction=benign` and no high-severity alert is forwarded.

## Resetting Between Runs

Reset in-memory and transient demo state without stopping Kafka/Spark:

```bash
./scripts/demo/reset_demo_state.sh
```

This clears:

- Gateway dedupe memory
- Webhook alert memory
- `outputs/live_flows/`
- `outputs/mining/`
- `outputs/gateway_events.jsonl`

Clear transient logs as well:

```bash
CLEAR_LOGS=1 ./scripts/demo/reset_demo_state.sh
```

The reset script preserves:

- `outputs/offline_adapter_test/`
- trained model artifacts
- `data/csv/`
- `data/pcap/`
- `data/samples/`

## Stopping the System

Stop local Python services:

```bash
./scripts/demo/stop_services.sh
```

Stop Docker infrastructure:

```bash
./scripts/demo/stop_infra.sh
```

Confirm status:

```bash
./scripts/demo/demo_status.sh
```

## Offline IDS Pipeline

The repository also includes the offline IDS experiment pipeline. Run it when regenerating offline experiment outputs:

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

Related utilities:

```bash
python scripts/offline/run_baseline.py rf --help
python scripts/offline/run_baseline.py rate --help
python scripts/offline/run_baseline.py anomaly --help
python scripts/offline/run_snort.py runner --help
python scripts/offline/run_snort.py parser --help
```

## Troubleshooting

### Docker is not running

Symptom:

```text
Cannot connect to the Docker daemon
```

Action:

Start Docker Desktop or Docker Engine, then run:

```bash
docker compose config --quiet
./scripts/demo/start_infra.sh
```

### Kafka is not ready

Action:

```bash
./scripts/demo/start_infra.sh
./scripts/debug/kafka_list_topics.sh
```

If topics are still unavailable, inspect container status:

```bash
docker compose ps
```

### Python virtual environment is not active

Symptom:

```text
ModuleNotFoundError
```

Action:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Port already in use

Check common ports:

```bash
lsof -i :8000
lsof -i :9001
lsof -i :8080
lsof -i :4040
```

Stop local services managed by this repository:

```bash
./scripts/demo/stop_services.sh
```

Port `7000` can be used by macOS ControlCenter. It is only relevant for the auxiliary injector UI. The main demo uses CLI upload.

### Spark runs but no alert appears

Check the Spark terminal for:

```text
[SPARK] prediction=attack
[SPARK] published alert to Kafka topic alert.tenant.tenant_A
```

Then check Alert Delivery:

```text
[DELIVERY] received alert from Kafka topic=alert.tenant.tenant_A
[DELIVERY] forwarded to webhook
```

Check the alert topic directly:

```bash
./scripts/debug/kafka_consume_topic.sh alert.tenant.tenant_A
```

### Alert page is empty

Confirm the webhook receiver is running:

```bash
curl http://localhost:9001/
curl http://localhost:9001/alerts/tenant_A
```

Then open:

```text
http://localhost:9001/alerts/tenant_A/view
```

### Duplicate upload is dropped

This is expected replay-protection behavior. Reset demo state when repeating the same upload during demonstrations:

```bash
./scripts/demo/reset_demo_state.sh
```

### Spark container RF inference returns an error

Run the same RF check inside the Spark container:

```bash
docker compose run --rm spark python3 scripts/test/test_rf_inference_csv.py data/samples/csv/ddos.csv
```

The JSON output includes diagnostic fields:

```text
input_file_exists
input_file_size_bytes
raw_rows_loaded
rows_after_cleanup
rows_scored
missing_columns
error
```

Use these fields to distinguish file path, CSV schema, and artifact-loading issues.

## Notes for Evaluation

- Run commands from the repository root.
- Use separate terminals for infrastructure/services, Spark, Alert Delivery, and uploads.
- The default API key for local evaluation is `dev-secret`.
- Tenant isolation is visible through topic names such as `raw.tenant.tenant_A` and `alert.tenant.tenant_A`.
- Generated uploads and runtime outputs are written under `data/uploads/`, `outputs/`, and `logs/`.
- Large CIC datasets and model artifacts should remain outside source control unless they are explicitly included in the evaluation package.

Additional documentation:

- `docs/DEMO_RUNBOOK.md`
- `scripts/README.md`
- `docs/PROTOTYPE_ARCHITECTURE.md`
