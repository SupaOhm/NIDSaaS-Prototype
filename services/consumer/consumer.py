"""Simple Kafka consumer for gateway upload events."""

from __future__ import annotations

import json
import os
from json import JSONDecodeError
from typing import Any


def _print_event(event: dict[str, Any]) -> None:
    print("[CONSUMER] received upload event", flush=True)
    print(f"tenant_id={event.get('tenant_id', '')}", flush=True)
    print(f"source_id={event.get('source_id', '')}", flush=True)
    print(f"file_path={event.get('file_path', '')}", flush=True)
    print(f"decision={event.get('decision', '')}", flush=True)


def consume() -> None:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("TOPIC", "raw.tenant.tenant_A")
    group_id = os.getenv("KAFKA_CONSUMER_GROUP", "nidsaas-local-consumer")

    print("[CONSUMER] starting Kafka upload-event consumer", flush=True)
    print(f"[CONSUMER] bootstrap servers: {bootstrap_servers}", flush=True)
    print(f"[CONSUMER] topic: {topic}", flush=True)
    print("[CONSUMER] press Ctrl+C to stop", flush=True)

    try:
        from kafka import KafkaConsumer
    except ImportError as exc:
        raise SystemExit(
            "[CONSUMER] kafka-python is not installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            consumer_timeout_ms=1000,
            api_version_auto_timeout_ms=3000,
        )
    except Exception as exc:
        raise SystemExit(
            f"[CONSUMER] unable to connect to Kafka at {bootstrap_servers}: {exc}"
        ) from exc

    try:
        while True:
            for message in consumer:
                try:
                    event = json.loads(message.value.decode("utf-8"))
                except (UnicodeDecodeError, JSONDecodeError) as exc:
                    print(f"[CONSUMER] malformed JSON message skipped: {exc}", flush=True)
                    continue

                if not isinstance(event, dict):
                    print("[CONSUMER] malformed JSON message skipped: expected object", flush=True)
                    continue

                _print_event(event)
    except KeyboardInterrupt:
        print("\n[CONSUMER] stopping", flush=True)
    finally:
        consumer.close()


if __name__ == "__main__":
    consume()
