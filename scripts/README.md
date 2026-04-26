# Scripts

The scripts are grouped by purpose so the demo workflow stays transparent.

## Main Demo

```bash
./scripts/demo/start_infra.sh
./scripts/demo/start_services.sh
./scripts/demo/run_spark_processor.sh
./scripts/test/test_inject_attack.sh
```

Real CIC PCAP upload:

```bash
./scripts/test/test_inject_real_cic_pcap.sh
```

Open:

```text
http://localhost:9001/alerts/tenant_A/view
```

Optional tenant portal:

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
