"""Kafka publishing with JSONL fallback for gateway events."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class GatewayKafkaPublisher:
    def __init__(
        self,
        bootstrap_servers: str | None = None,
        fallback_path: str | Path = "outputs/gateway_events.jsonl",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.fallback_path = Path(fallback_path)
        self._producer = None
        self._producer_failed = False

    def _get_producer(self):
        if self._producer_failed:
            return None
        if self._producer is not None:
            return self._producer
        try:
            from kafka import KafkaProducer

            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                acks="all",
                retries=1,
                request_timeout_ms=2000,
                api_version_auto_timeout_ms=2000,
            )
            return self._producer
        except Exception as exc:  # Kafka may be absent or unavailable locally.
            self._producer_failed = True
            print(f"[KAFKA] unavailable, wrote fallback event ({exc})", flush=True)
            return None

    def publish(self, topic: str, event: dict[str, Any]) -> bool:
        producer = self._get_producer()
        if producer is not None:
            try:
                future = producer.send(topic, event)
                future.get(timeout=5)
                producer.flush(timeout=5)
                print(f"[KAFKA] published to {topic}", flush=True)
                return True
            except Exception as exc:
                self._producer_failed = True
                print(f"[KAFKA] unavailable, wrote fallback event ({exc})", flush=True)

        self._write_fallback(event)
        return False

    def _write_fallback(self, event: dict[str, Any]) -> None:
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
        with self.fallback_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
