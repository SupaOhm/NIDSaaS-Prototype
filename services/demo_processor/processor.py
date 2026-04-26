"""Fast demo processor: Kafka upload event -> fake detection -> webhook alert."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any

from services.alert_dispatcher.dispatcher import dispatch_alert


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prediction_for_event(event: dict[str, Any]) -> str:
    file_path = str(event.get("file_path", ""))
    if os.getenv("DEMO_FORCE_ATTACK", "0") == "1":
        return "attack"
    if "attack" in file_path.lower():
        return "attack"
    return "benign"


def _build_alert(event: dict[str, Any], topic: str | None = None) -> dict[str, Any]:
    tenant_id = str(event.get("tenant_id", "unknown_tenant"))
    source_id = str(event.get("source_id", "unknown_source"))
    file_path = str(event.get("file_path", ""))
    return {
        "alert_id": f"demo-{int(time.time())}-{uuid.uuid4().hex[:8]}",
        "tenant_id": tenant_id,
        "source_id": source_id,
        "severity": "high",
        "prediction": "attack",
        "attack_type": "demo_synthetic_intrusion",
        "evidence": "Demo processor flagged upload event; no full IDS cascade was run.",
        "timestamp": _utc_now(),
        "original_file_path": file_path,
        "kafka_topic": topic,
    }


def _webhook_url(base_url: str, tenant_id: str) -> str:
    return f"{base_url.rstrip('/')}/webhook/{tenant_id}"


def process_upload_event(event: dict[str, Any], topic: str | None, webhook_base_url: str) -> None:
    print("[PROCESSOR] received upload event", flush=True)
    print(f"tenant_id={event.get('tenant_id', '')}", flush=True)
    print(f"source_id={event.get('source_id', '')}", flush=True)
    print(f"file_path={event.get('file_path', '')}", flush=True)

    prediction = _prediction_for_event(event)
    print(f"[PROCESSOR] prediction={prediction}", flush=True)

    if prediction != "attack":
        print("[PROCESSOR] benign result; no alert dispatched", flush=True)
        return

    tenant_id = str(event.get("tenant_id", "unknown_tenant"))
    alert = _build_alert(event, topic=topic)
    url = _webhook_url(webhook_base_url, tenant_id)
    if dispatch_alert(alert, url):
        print(f"[ALERT] dispatched to {url}", flush=True)
    else:
        print(f"[ALERT] dispatch failed for {url}", flush=True)


def run() -> None:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("TOPIC", "raw.tenant.tenant_A")
    topic_pattern = os.getenv("KAFKA_TOPIC_PATTERN")
    webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:9001")
    group_id = os.getenv("KAFKA_CONSUMER_GROUP", "nidsaas-demo-processor")

    print("[PROCESSOR] starting demo processor", flush=True)
    print(f"[PROCESSOR] bootstrap servers: {bootstrap_servers}", flush=True)
    if topic_pattern:
        print(f"[PROCESSOR] topic pattern: {topic_pattern}", flush=True)
    else:
        print(f"[PROCESSOR] topic: {topic}", flush=True)
    print(f"[PROCESSOR] webhook base URL: {webhook_base_url}", flush=True)
    print(f"[PROCESSOR] force attack: {os.getenv('DEMO_FORCE_ATTACK', '0')}", flush=True)
    print("[PROCESSOR] press Ctrl+C to stop", flush=True)

    try:
        from kafka import KafkaConsumer
    except ImportError as exc:
        raise SystemExit(
            "[PROCESSOR] kafka-python is not installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            consumer_timeout_ms=1000,
            api_version_auto_timeout_ms=3000,
        )
        if topic_pattern:
            consumer.subscribe(pattern=topic_pattern)
        else:
            consumer.subscribe([topic])
    except Exception as exc:
        raise SystemExit(
            f"[PROCESSOR] unable to connect to Kafka at {bootstrap_servers}: {exc}"
        ) from exc

    try:
        while True:
            for message in consumer:
                try:
                    event = json.loads(message.value.decode("utf-8"))
                except (UnicodeDecodeError, JSONDecodeError) as exc:
                    print(f"[PROCESSOR] malformed JSON skipped: {exc}", flush=True)
                    continue

                if not isinstance(event, dict):
                    print("[PROCESSOR] malformed JSON skipped: expected object", flush=True)
                    continue

                process_upload_event(event, topic=getattr(message, "topic", None), webhook_base_url=webhook_base_url)
    except KeyboardInterrupt:
        print("\n[PROCESSOR] stopping", flush=True)
    finally:
        consumer.close()


if __name__ == "__main__":
    run()
