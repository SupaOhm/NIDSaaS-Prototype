"""Consume tenant alert topics from Kafka and forward them to webhooks."""

from __future__ import annotations

import json
import os
import re
import signal
import sys
from pathlib import Path

from kafka import KafkaConsumer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from services.alert_dispatcher.dispatcher import dispatch_alert


def _build_webhook_url(base_url: str, tenant_id: str) -> str:
    return f"{base_url.rstrip('/')}/webhook/{tenant_id}"


def _parse_bootstrap_servers(value: str) -> list[str]:
    return [server.strip() for server in value.split(",") if server.strip()]


def _compile_topic_pattern(topic_pattern: str) -> re.Pattern[str]:
    escaped = re.escape(topic_pattern).replace(r"\*", ".*")
    return re.compile(f"^{escaped}$")


def run_delivery(bootstrap_servers: str, topic_pattern: str, webhook_base_url: str) -> None:
    servers = _parse_bootstrap_servers(bootstrap_servers)
    if not servers:
        raise SystemExit("[DELIVERY] no Kafka bootstrap servers configured")

    start_from_beginning = os.getenv("ALERT_DELIVERY_START_FROM_BEGINNING", "0") == "1"
    auto_offset_reset = "earliest" if start_from_beginning else "latest"
    group_id = os.getenv("ALERT_DELIVERY_GROUP_ID") or f"nidsaas-alert-delivery-{os.getpid()}"

    consumer = KafkaConsumer(
        bootstrap_servers=servers,
        auto_offset_reset=auto_offset_reset,
        enable_auto_commit=True,
        group_id=group_id,
        value_deserializer=lambda data: data.decode("utf-8", errors="replace"),
        consumer_timeout_ms=100,
        max_poll_records=5,
        fetch_max_wait_ms=500,
        request_timeout_ms=15000,
        session_timeout_ms=10000,
    )
    consumer.subscribe(pattern=_compile_topic_pattern(topic_pattern).pattern)
    print(
        f"[DELIVERY] polling Kafka topics matching {topic_pattern} "
        f"(auto_offset_reset={auto_offset_reset}, group_id={group_id})",
        flush=True,
    )
    print(f"[DELIVERY] bootstrap servers: {', '.join(servers)}", flush=True)
    print(f"[DELIVERY] webhook base URL: {webhook_base_url}", flush=True)
    print("[DELIVERY] polling loop started", flush=True)

    stop_requested = False

    def _handle_signal(signum, frame):  # noqa: ANN001
        nonlocal stop_requested
        stop_requested = True
        print(f"[DELIVERY] stopping on signal {signum}", flush=True)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        while not stop_requested:
            try:
                print("[DELIVERY] polling for new alerts", flush=True)
                records = consumer.poll(timeout_ms=250, max_records=5)
            except Exception as exc:
                print(f"[DELIVERY] Kafka poll failed: {exc}", flush=True)
                continue

            if not records:
                continue

            for tp, messages in records.items():
                for message in messages:
                    print(
                        f"[DELIVERY] received alert from Kafka topic={message.topic} "
                        f"partition={message.partition} offset={message.offset}",
                        flush=True,
                    )
                    try:
                        alert = json.loads(message.value)
                    except json.JSONDecodeError as exc:
                        print(f"[DELIVERY] malformed alert JSON skipped: {exc}", flush=True)
                        continue
                    if not isinstance(alert, dict):
                        print("[DELIVERY] alert payload is not a JSON object; skipped", flush=True)
                        continue

                    tenant_id = str(alert.get("tenant_id") or "")
                    if not tenant_id:
                        topic_tenant = message.topic.split(".", 2)[-1] if "." in message.topic else ""
                        tenant_id = topic_tenant or "unknown_tenant"
                        alert["tenant_id"] = tenant_id

                    webhook_url = _build_webhook_url(webhook_base_url, tenant_id)
                    if dispatch_alert(alert, webhook_url):
                        print(f"[DELIVERY] forwarded to webhook {webhook_url}", flush=True)
                    else:
                        print(f"[DELIVERY] failed to forward to webhook {webhook_url}", flush=True)
    finally:
        consumer.close()
        print("[DELIVERY] stopped", flush=True)


def main() -> int:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic_pattern = os.getenv("KAFKA_TOPIC_PATTERN", "alert.tenant.*")
    webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:9001")
    run_delivery(bootstrap_servers, topic_pattern, webhook_base_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
