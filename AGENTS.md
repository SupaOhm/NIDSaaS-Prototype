# Repository Guidelines

## Project Structure & Module Organization

Core reusable code lives under `src/nidsaas/`. The current offline IDS pipeline is in `src/nidsaas/detection/`; Snort utilities and rules are in `src/nidsaas/snort/`. Prototype service code lives in `services/`, with the implemented FastAPI gateway in `services/gateway/`. Runnable helper scripts belong in `scripts/`. Architecture notes go in `docs/`. Large local datasets are kept under `data/csv/` and `data/pcap/`; generated artifacts and gateway fallbacks go under `outputs/`. Do not commit raw PCAPs, CIC CSVs, uploads, or model artifacts.

## Build, Test, and Development Commands

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the offline IDS pipeline:

```bash
python scripts/run_pipeline.py --data-dir data/csv/csv_CIC_IDS2017
```

Run Kafka infrastructure:

```bash
./scripts/start_kafka.sh
./scripts/list_kafka_topics.sh
./scripts/consume_kafka_topic.sh raw.tenant.tenant_A
./scripts/stop_kafka.sh
```

Run and test the gateway:

```bash
./scripts/run_gateway.sh
./scripts/test_gateway_upload.sh
```

Validate Python syntax before committing:

```bash
python3 -m py_compile services/gateway/*.py scripts/*.py
```

## Coding Style & Naming Conventions

Use Python 3, 4-space indentation, type hints for new public functions, and clear module names using `snake_case.py`. Keep service logic small and explicit. Do not refactor IDS algorithms while working on prototype infrastructure unless the task explicitly requires it.

## Testing Guidelines

There is no formal test suite yet. Use lightweight script-based checks: `bash -n scripts/*.sh`, `python3 -m py_compile ...`, `docker compose config --quiet`, and `scripts/test_gateway_upload.sh` for the gateway path. Add future tests near the code they validate or under a top-level `tests/` directory.

## Commit & Pull Request Guidelines

Recent commits use short imperative messages, for example `Add Kafka infrastructure` and `Add gateway upload API with deduplication`. Keep commits scoped and avoid mixing dataset changes with source changes. PRs should describe behavior changes, list verification commands, note any local services required, and confirm that large data files were not staged.

## Security & Configuration Tips

The gateway uses mock key `dev-secret` and local Kafka at `localhost:9092`; this is for development only. Keep `.env`, uploads, PCAPs, generated outputs, and model binaries out of Git. Preserve fallback behavior to `outputs/gateway_events.jsonl` when Kafka is unavailable.
