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
./scripts/test/create_cic_demo_dataset.sh
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_ddos_sample.pcap -t tenant_A
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_portscan_sample.pcap -t tenant_B
```

`create_cic_demo_dataset.sh` extracts small demo samples from the original
CIC-IDS2017 PCAP files and creates matching CICFlowMeter CSV samples under
`data/samples/pcap/` and `data/samples/csv/`. The full CIC datasets stay under
`data/pcap/` and `data/csv/`, which are excluded from Git.

The category PCAP files are broad-day demo triggers rather than
category-isolated captures. The matching CSV samples provide category-specific
label evidence for inference.

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
