# Local Kafka Consumer

This service is a minimal consumer-side prototype for the local Gateway -> Kafka -> Consumer flow. It subscribes to a tenant raw upload topic, parses gateway upload events as JSON, and prints the key fields needed to verify that Kafka delivery works before adding Spark or downstream alerting services.
