# Demo Processor

Fast local processor for the presentation path `Gateway -> Kafka -> demo detection -> webhook alert`. It consumes upload events from Kafka, applies a fake detection rule, and dispatches alerts to the tenant webhook receiver. It does not run Spark or the offline IDS cascade.

Run:

```bash
DEMO_FORCE_ATTACK=1 ./scripts/debug/run_demo_processor.sh
```

Defaults:

- `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`
- `TOPIC=raw.tenant.tenant_A`
- `WEBHOOK_BASE_URL=http://localhost:9001`

Set `KAFKA_TOPIC_PATTERN=raw.tenant.*` to subscribe by pattern instead of a single explicit topic.
