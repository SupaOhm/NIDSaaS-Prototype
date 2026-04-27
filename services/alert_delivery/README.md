# Alert Delivery Service

This service consumes Kafka topics matching `alert.tenant.*` and forwards each
alert payload to the tenant webhook receiver at `/webhook/<tenant_id>`.

Run it with:

```bash
./scripts/demo/run_alert_delivery.sh
```

Defaults:

- `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`
- `KAFKA_TOPIC_PATTERN=alert.tenant.*`
- `WEBHOOK_BASE_URL=http://localhost:9001`

The service is separate from Spark so the demo alert phase stays visible:

`Spark -> Kafka alert.tenant.<tenant_id> -> Alert Delivery Service -> Webhook Receiver`

