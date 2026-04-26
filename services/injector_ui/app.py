"""Minimal tenant portal for the local NIDSaaS demo."""

from __future__ import annotations

import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
from urllib import error, request

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse


GATEWAY_BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://localhost:8000")
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "dev-secret")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:9001")
KAFKA_UI_URL = os.getenv("KAFKA_UI_URL", "http://localhost:8080")
ATTACK_SAMPLE = Path("data/samples/pcap/cic_attack_sample.pcap")
BENIGN_SAMPLE = Path("data/samples/pcap/cic_benign_sample.pcap")

app = FastAPI(title="NIDSaaS Tenant Portal")


def _page(title: str, body: str) -> str:
    return f"""
    <!doctype html>
    <html>
      <head>
        <title>{escape(title)}</title>
        <style>
          body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #202124; }}
          main {{ max-width: 960px; margin: 0 auto; }}
          .row {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
          .panel {{ border: 1px solid #d8dadd; padding: 20px; margin: 16px 0; border-radius: 6px; }}
          label {{ display: block; font-weight: 600; margin-top: 14px; }}
          input, select {{ padding: 8px; min-width: 260px; border: 1px solid #b9bec5; border-radius: 4px; }}
          button, .button {{ display: inline-block; padding: 9px 14px; border: 1px solid #2f6fed; background: #2f6fed; color: white; border-radius: 4px; text-decoration: none; cursor: pointer; }}
          .link {{ color: #2f6fed; text-decoration: none; }}
          .muted {{ color: #5f6368; }}
          .error {{ color: #b3261e; }}
          pre {{ background: #f6f8fa; padding: 14px; overflow: auto; border: 1px solid #d8dadd; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <main>{body}</main>
      </body>
    </html>
    """


def _default_epoch() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"portal_{stamp}_{uuid.uuid4().hex[:6]}"


def _sample_upload_name(path: Path) -> str:
    if path.is_symlink():
        return Path(os.readlink(path)).name
    return path.name


def _read_sample(mode: str) -> tuple[bytes, str, str]:
    path = ATTACK_SAMPLE if mode == "attack_sample" else BENIGN_SAMPLE
    if not path.exists():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Sample not found: {path}. Create samples with "
                "./scripts/test/create_cic_pcap_samples.sh"
            ),
        )
    return path.read_bytes(), _sample_upload_name(path), str(path)


async def _read_upload(mode: str, custom_file: UploadFile | None) -> tuple[bytes, str, str]:
    if mode in {"attack_sample", "benign_sample"}:
        return _read_sample(mode)
    if mode != "custom_file":
        raise HTTPException(status_code=400, detail=f"Unsupported upload mode: {mode}")
    if custom_file is None or not custom_file.filename:
        raise HTTPException(status_code=400, detail="Custom file upload is required")
    payload = await custom_file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Custom file is empty")
    return payload, Path(custom_file.filename).name, custom_file.filename


def _multipart_body(fields: dict[str, str], file_field: str, filename: str, payload: bytes) -> tuple[bytes, str]:
    boundary = f"----nidsaas-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode(),
                b"\r\n",
            ]
        )

    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{filename}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            payload,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _post_gateway(fields: dict[str, str], filename: str, payload: bytes) -> tuple[int, dict[str, Any] | str]:
    body, content_type = _multipart_body(fields, "file", filename, payload)
    gateway_request = request.Request(
        f"{GATEWAY_BASE_URL.rstrip('/')}/upload-pcap",
        data=body,
        headers={
            "Content-Type": content_type,
            "x-api-key": GATEWAY_API_KEY,
        },
        method="POST",
    )
    try:
        with request.urlopen(gateway_request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, raw
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw
    except error.URLError as exc:
        return 0, f"Gateway request failed: {exc}"


def _json_block(value: dict[str, Any] | str) -> str:
    if isinstance(value, dict):
        text = json.dumps(value, indent=2, sort_keys=True)
    else:
        text = value
    return f"<pre>{escape(text)}</pre>"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    body = """
    <h1>NIDSaaS Tenant Portal</h1>
    <p class="muted">Select a demo tenant. This portal uploads PCAP files through the existing Gateway API.</p>
    <div class="row">
      <a class="button" href="/tenant/tenant_A">tenant_A</a>
      <a class="button" href="/tenant/tenant_B">tenant_B</a>
    </div>
    """
    return _page("NIDSaaS Tenant Portal", body)


@app.get("/tenant/{tenant_id}", response_class=HTMLResponse)
def tenant_dashboard(tenant_id: str) -> str:
    tenant = escape(tenant_id)
    body = f"""
    <h1>Tenant {tenant}</h1>
    <p class="muted">Upload a PCAP to the gateway, then watch tenant-scoped webhook alerts.</p>
    <section class="panel">
      <form method="post" action="/tenant/{tenant}/upload" enctype="multipart/form-data">
        <label for="source_id">source_id</label>
        <input id="source_id" name="source_id" value="source_1" required>

        <label for="file_epoch">file_epoch</label>
        <input id="file_epoch" name="file_epoch" value="{escape(_default_epoch())}" required>

        <label for="upload_mode">upload mode</label>
        <select id="upload_mode" name="upload_mode">
          <option value="attack_sample">attack_sample</option>
          <option value="benign_sample">benign_sample</option>
          <option value="custom_file">custom_file</option>
        </select>

        <label for="custom_file">custom_file</label>
        <input id="custom_file" name="custom_file" type="file">

        <p><button type="submit">Upload to Gateway</button></p>
      </form>
    </section>
    <section class="panel">
      <div class="row">
        <a class="link" href="{WEBHOOK_BASE_URL}/alerts/{tenant}/view" target="_blank">View alerts</a>
        <a class="link" href="{KAFKA_UI_URL}" target="_blank">Kafka UI</a>
        <a class="link" href="{GATEWAY_BASE_URL}/health" target="_blank">Gateway health</a>
        <a class="link" href="/">Switch tenant</a>
      </div>
    </section>
    """
    return _page(f"Tenant {tenant_id}", body)


@app.post("/tenant/{tenant_id}/upload", response_class=HTMLResponse)
async def upload(
    tenant_id: str,
    source_id: str = Form("source_1"),
    file_epoch: str = Form(""),
    upload_mode: str = Form("attack_sample"),
    custom_file: UploadFile | None = File(None),
) -> str:
    try:
        payload, filename, source_path = await _read_upload(upload_mode, custom_file)
    except HTTPException as exc:
        body = f"""
        <h1>Upload error for {escape(tenant_id)}</h1>
        <section class="panel">
          <p class="error">{escape(str(exc.detail))}</p>
        </section>
        <a class="button" href="/tenant/{escape(tenant_id)}">Back to dashboard</a>
        """
        return _page("Upload error", body)

    fields = {
        "tenant_id": tenant_id,
        "source_id": source_id,
        "file_epoch": file_epoch or _default_epoch(),
        "start_offset": "0",
        "end_offset": str(len(payload)),
    }
    status, gateway_response = _post_gateway(fields, filename, payload)
    status_text = "Gateway accepted the request" if 200 <= status < 300 else "Gateway request failed"
    body = f"""
    <h1>Upload result for {escape(tenant_id)}</h1>
    <section class="panel">
      <p><strong>{escape(status_text)}</strong></p>
      <p>HTTP status: {escape(str(status))}</p>
      <p>Upload mode: {escape(upload_mode)}</p>
      <p>Source path: {escape(source_path)}</p>
      <p>Gateway filename: {escape(filename)}</p>
      <p>Bytes uploaded: {len(payload)}</p>
    </section>
    <section class="panel">
      <h2>Gateway response</h2>
      {_json_block(gateway_response)}
    </section>
    <div class="row">
      <a class="button" href="/tenant/{escape(tenant_id)}">Back to dashboard</a>
      <a class="button" href="{WEBHOOK_BASE_URL}/alerts/{escape(tenant_id)}/view" target="_blank">View alerts</a>
    </div>
    """
    return _page("Upload result", body)
