# Scripts

The scripts are grouped by purpose so the demo workflow stays transparent.

## Main Demo

```bash
./scripts/demo/start_infra.sh
./scripts/demo/start_services.sh
./scripts/demo/run_spark_processor.sh
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_attack_sample.pcap -t tenant_A
```

Real CIC PCAP upload:

```bash
./scripts/test/mine_live_cic_attack_windows.sh
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_highrate_sample.pcap -t tenant_A
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_benign_sample.pcap -t tenant_B
```

`mine_live_cic_attack_windows.sh` searches real CIC-IDS2017 PCAP files by
packet window and saves only windows whose live extracted flows classify as
attack. CSV labels are not used as the primary selector. If a category cannot
be found from locally available PCAPs, the script reports it as unavailable.
The full CIC datasets stay under `data/pcap/` and `data/csv/`, which are
excluded from Git.

For live PCAP classification in Spark, the priority is:
1. Resolve to a matching CICFlowMeter CSV and run the saved RF artifact.
2. Fall back to live `tshark` flow extraction and live flow rules when no
   matching CSV exists.

Set `CICFLOWMETER_CMD` or `CICFLOWMETER_JAR` to use CICFlowMeter; otherwise
install `tshark` for the fallback extractor. Flow CSVs are written under
`LIVE_FLOW_OUTPUT_DIR`, default `outputs/live_flows`.

Open:

```text
http://localhost:9001/alerts/tenant_A/view
```

Future/optional tenant portal, not used in the main demo:

```bash
./scripts/demo/run_injector_ui.sh
```

Open:

```text
http://localhost:7000
```

Shutdown:

```bash
./scripts/demo/stop_services.sh
./scripts/demo/stop_infra.sh
```

## Folders

- `demo/`: startup, shutdown, status, and visible Spark processor scripts.
- `test/`: lightweight demo and debugging tests.
- `debug/`: Kafka and fallback consumer tools.
- `offline/`: offline IDS, Snort, and baseline entry points.

## Debug

```bash
./scripts/debug/kafka_list_topics.sh
./scripts/debug/kafka_consume_topic.sh raw.tenant.tenant_A
./scripts/debug/run_simple_consumer.sh
./scripts/debug/run_demo_processor.sh
```

## Offline IDS

```bash
python scripts/offline/run_offline_adapter.py
python scripts/offline/run_pipeline.py --help
python scripts/offline/run_baseline.py --help
python scripts/offline/run_snort.py --help
```

## RF Artifact CSV Inference (Inference-Only)

Use the saved RF artifact (`outputs/offline_adapter_test/rf_anomaly.joblib`) directly on
CICFlowMeter-compatible flow CSV files without retraining:

```bash
python3 scripts/test/test_rf_inference_csv.py data/samples/csv/cic_benign_sample.csv
python3 scripts/test/test_rf_inference_csv.py data/samples/csv/cic_ddos_sample.csv
```

Notes:
- This path is inference-only and does not call `fit()`.
- Input must be CICFlowMeter-compatible schema (80 required RF features).
- tshark fallback flow CSV output is not compatible with this RF artifact.
