# NIDSaaS Prototype

NIDSaaS Prototype is a research-to-prototype repository for network intrusion detection as a service. It currently contains a runnable offline IDS pipeline for CIC-IDS2017 experiments and a clean service-oriented layout for the planned streaming prototype.

## Current Status

The offline IDS pipeline is available under `src/nidsaas/detection/`. Snort replay and alert-mapping utilities are available under `src/nidsaas/snort/`. The Kafka, Spark, gateway, alert dispatcher, webhook receiver, and injector UI services are planned but not implemented yet.

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

Run the gateway:

```bash
./scripts/run_gateway.sh
```

Upload a file:

```bash
curl -s -X POST http://127.0.0.1:8000/upload-pcap \
  -H "x-api-key: dev-secret" \
  -F tenant_id=acme \
  -F source_id=edge-1 \
  -F file_epoch=demo-001 \
  -F start_offset=0 \
  -F end_offset=1024 \
  -F file=@data/pcap/pcap_CIC_IDS2017/Monday-WorkingHours.pcap
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
