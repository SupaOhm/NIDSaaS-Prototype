# Alert Dispatcher

Helper module for posting alert JSON payloads to tenant webhook URLs. The Kafka-backed alert delivery service uses the same dispatch function when forwarding alerts from `alert.tenant.<tenant_id>` topics to the webhook receiver.
