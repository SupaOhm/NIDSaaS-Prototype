"""FastAPI gateway for tenant PCAP uploads."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile

try:
    from .dedupe import BatchDeduper
    from .kafka_producer import GatewayKafkaPublisher
except ImportError:  # Allows `uvicorn app:app` from services/gateway.
    from dedupe import BatchDeduper
    from kafka_producer import GatewayKafkaPublisher


API_KEY = "dev-secret"
UPLOAD_ROOT = Path("data/uploads")

app = FastAPI(title="NIDSaaS Gateway", version="0.1.0")
deduper = BatchDeduper()
publisher = GatewayKafkaPublisher()


def _safe_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    if not cleaned:
        raise HTTPException(status_code=400, detail="tenant_id/source_id cannot be empty")
    return cleaned


def _safe_filename(filename: str | None, batch_hash: str) -> str:
    base = Path(filename or "upload.pcap").name
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", base) or "upload.pcap"
    return f"{batch_hash[:12]}_{cleaned}"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload-pcap")
async def upload_pcap(
    tenant_id: str = Form(...),
    source_id: str = Form(...),
    file_epoch: str = Form(...),
    start_offset: int = Form(...),
    end_offset: int = Form(...),
    file: UploadFile = File(...),
    x_api_key: str = Header(...),
) -> dict:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    if start_offset < 0 or end_offset < 0:
        raise HTTPException(status_code=400, detail="offsets must be non-negative")
    if end_offset <= start_offset:
        raise HTTPException(status_code=400, detail="end_offset must be greater than start_offset")

    tenant_safe = _safe_part(tenant_id)
    source_safe = _safe_part(source_id)

    payload = await file.read()
    batch_hash = hashlib.sha256(payload).hexdigest()

    dedupe_decision = deduper.evaluate(
        tenant_id=tenant_id,
        source_id=source_id,
        file_epoch=file_epoch,
        start_offset=start_offset,
        end_offset=end_offset,
        batch_hash=batch_hash,
    )

    if not dedupe_decision.should_forward:
        if dedupe_decision.decision == "drop_duplicate":
            print("[GATEWAY] dropped duplicate", flush=True)
        else:
            print(f"[GATEWAY] {dedupe_decision.decision}", flush=True)
        return {
            "status": "dropped",
            "decision": dedupe_decision.decision,
            "tenant_id": tenant_id,
            "source_id": source_id,
            "file_epoch": file_epoch,
            "batch_hash": batch_hash,
            "published": False,
        }

    upload_dir = UPLOAD_ROOT / tenant_safe / source_safe
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / _safe_filename(file.filename, batch_hash)
    upload_path.write_bytes(payload)

    topic = f"raw.tenant.{tenant_id}"
    event = {
        "tenant_id": tenant_id,
        "source_id": source_id,
        "file_epoch": file_epoch,
        "start_offset": start_offset,
        "end_offset": end_offset,
        "effective_start_offset": dedupe_decision.effective_start_offset,
        "file_path": str(upload_path),
        "batch_hash": batch_hash,
        "decision": dedupe_decision.decision,
        "upload_time": datetime.now(timezone.utc).isoformat(),
    }

    print("[GATEWAY] forwarded batch", flush=True)
    published = publisher.publish(topic, event)

    return {
        "status": "accepted",
        "decision": dedupe_decision.decision,
        "topic": topic,
        "event": event,
        "published": published,
    }
