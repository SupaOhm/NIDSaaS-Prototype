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
ATTACK_SAMPLE = Path("data/samples/pcap/ddos.pcap")
BENIGN_SAMPLE = Path("data/samples/pcap/benign.pcap")

app = FastAPI(title="NIDSaaS Tenant Portal")


def _page(title: str, body: str) -> str:
    return f"""
    <!doctype html>
    <html>
      <head>
        <title>{escape(title)}</title>
        <style>
          body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #202124; background: #fafafa; }}
          main {{ max-width: 1180px; margin: 0 auto; }}
          .row {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
          .grid {{ display: grid; grid-template-columns: minmax(280px, 360px) 1fr; gap: 18px; align-items: start; }}
          .panel {{ background: white; border: 1px solid #d8dadd; padding: 18px; margin: 14px 0; border-radius: 6px; }}
          .tenant-card {{ min-width: 180px; padding: 20px; text-align: center; }}
          label {{ display: block; font-weight: 600; margin-top: 12px; }}
          input {{ padding: 8px; max-width: 100%; border: 1px solid #b9bec5; border-radius: 4px; }}
          button, .button {{ display: inline-block; padding: 10px 14px; border: 1px solid #2f6fed; background: #2f6fed; color: white; border-radius: 4px; text-decoration: none; cursor: pointer; font-size: 14px; }}
          .secondary {{ border-color: #5f6368; background: #5f6368; }}
          .link {{ color: #2f6fed; text-decoration: none; }}
          .muted {{ color: #5f6368; }}
          .error {{ color: #b3261e; }}
          .result {{ border-left: 4px solid #2f6fed; }}
          iframe {{ width: 100%; height: 620px; border: 1px solid #d8dadd; border-radius: 6px; background: white; }}
          pre {{ background: #f6f8fa; padding: 12px; overflow: auto; border: 1px solid #d8dadd; border-radius: 4px; }}
          details {{ margin-top: 14px; }}
          @media (max-width: 860px) {{ .grid {{ grid-template-columns: 1fr; }} }}
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


def _gateway_fields(tenant_id: str, payload_size: int) -> dict[str, str]:
    return {
        "tenant_id": tenant_id,
        "source_id": "source_1",
        "file_epoch": _default_epoch(),
        "start_offset": "0",
        "end_offset": str(payload_size),
    }


def _read_sample(sample_type: str) -> tuple[bytes, str, str]:
    if sample_type == "attack":
        path = ATTACK_SAMPLE
    elif sample_type == "benign":
        path = BENIGN_SAMPLE
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported sample_type: {sample_type}")

    if not path.exists():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Sample not found: {path}. Create samples with "
                "./scripts/test/create_cic_pcap_samples.sh"
            ),
        )
    payload = path.read_bytes()
    if not payload:
        raise HTTPException(status_code=400, detail=f"Sample is empty: {path}")
    return payload, path.name, str(path)


async def _read_custom(custom_file: UploadFile | None) -> tuple[bytes, str, str]:
    if custom_file is None or not custom_file.filename:
        raise HTTPException(status_code=400, detail="Choose a custom PCAP first")
    payload = await custom_file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Custom PCAP is empty")
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


def _post_gateway(tenant_id: str, filename: str, payload: bytes) -> tuple[int, dict[str, Any] | str]:
    body, content_type = _multipart_body(_gateway_fields(tenant_id, len(payload)), "file", filename, payload)
    gateway_request = request.Request(
        f"{GATEWAY_BASE_URL.rstrip('/')}/upload-pcap",
        data=body,
        headers={"Content-Type": content_type, "x-api-key": GATEWAY_API_KEY},
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


def _response_value(response: dict[str, Any] | str, key: str) -> str:
    if not isinstance(response, dict):
        return ""
    if key in response:
        return str(response.get(key, ""))
    event = response.get("event")
    if isinstance(event, dict):
        return str(event.get(key, ""))
    return ""


def _render_result(
    tenant_id: str,
    status: int,
    gateway_response: dict[str, Any] | str,
    source_path: str,
    filename: str,
) -> str:
    accepted = 200 <= status < 300
    title = "Upload accepted" if accepted else "Upload failed"
    response_text = (
        json.dumps(gateway_response, indent=2, sort_keys=True)
        if isinstance(gateway_response, dict)
        else str(gateway_response)
    )
    return f"""
    <section class="panel result">
      <h2>{escape(title)}</h2>
      <p>Decision: <strong>{escape(_response_value(gateway_response, "decision") or "unknown")}</strong></p>
      <p>Kafka topic: <strong>{escape(_response_value(gateway_response, "topic") or "not published")}</strong></p>
      <p>File path: <code>{escape(_response_value(gateway_response, "file_path") or source_path)}</code></p>
      <p class="muted">Watch live alerts below.</p>
      <details>
        <summary>Gateway response</summary>
        <pre>{escape(response_text)}</pre>
      </details>
      <p class="muted">HTTP status {escape(str(status))}; uploaded as {escape(filename)}</p>
    </section>
    """


def _dashboard(tenant_id: str, result_html: str = "") -> str:
    tenant = escape(tenant_id)
    alerts_url = f"{WEBHOOK_BASE_URL.rstrip('/')}/alerts/{tenant_id}/view"
    body = f"""
    <h1>NIDSaaS Tenant Portal</h1>
    <p class="muted">Tenant: <strong>{tenant}</strong></p>
    <div class="grid">
      <section>
        <div class="panel">
          <h2>Upload demo traffic</h2>
          <div class="row">
            <form method="post" action="/tenant/{tenant}/upload-sample">
              <input type="hidden" name="sample_type" value="attack">
              <button type="submit">Upload Attack Sample</button>
            </form>
            <form method="post" action="/tenant/{tenant}/upload-sample">
              <input type="hidden" name="sample_type" value="benign">
              <button class="secondary" type="submit">Upload Benign Sample</button>
            </form>
          </div>
          <details>
            <summary>Advanced: Upload custom PCAP</summary>
            <form method="post" action="/tenant/{tenant}/upload-custom" enctype="multipart/form-data">
              <label for="custom_file">Custom PCAP</label>
              <input id="custom_file" name="custom_file" type="file" required>
              <p><button type="submit">Upload Custom PCAP</button></p>
            </form>
          </details>
        </div>
        {result_html}
        <div class="panel">
          <h2>Demo links</h2>
          <p><a class="link" href="{KAFKA_UI_URL}" target="_blank">Kafka UI</a></p>
          <p><a class="link" href="{GATEWAY_BASE_URL}/health" target="_blank">Gateway health</a></p>
          <p><a class="link" href="{alerts_url}" target="_blank">Open full alert receiver</a></p>
          <p class="muted">Spark logs: run <code>./scripts/demo/run_spark_processor.sh</code> in its own terminal.</p>
          <p><a class="link" href="/">Switch tenant</a></p>
        </div>
      </section>
      <section class="panel">
        <h2>Live webhook alerts</h2>
        <iframe src="{alerts_url}" title="Live webhook alerts for {tenant}"></iframe>
      </section>
    </div>
    """
    return _page(f"NIDSaaS Tenant Portal - {tenant_id}", body)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    body = """
    <h1>NIDSaaS Tenant Portal</h1>
    <p class="muted">Choose a tenant, upload demo traffic, and watch live webhook alerts.</p>
    <div class="row">
      <a class="button tenant-card" href="/tenant/tenant_A">Tenant A</a>
      <a class="button tenant-card secondary" href="/tenant/tenant_B">Tenant B</a>
    </div>
    """
    return _page("NIDSaaS Tenant Portal", body)


@app.get("/tenant/{tenant_id}", response_class=HTMLResponse)
def tenant_dashboard(tenant_id: str) -> str:
    return _dashboard(tenant_id)


@app.post("/tenant/{tenant_id}/upload-sample", response_class=HTMLResponse)
async def upload_sample(tenant_id: str, sample_type: str = Form(...)) -> str:
    try:
        payload, filename, source_path = _read_sample(sample_type)
        status, gateway_response = _post_gateway(tenant_id, filename, payload)
        result = _render_result(tenant_id, status, gateway_response, source_path, filename)
    except HTTPException as exc:
        result = f'<section class="panel"><p class="error">{escape(str(exc.detail))}</p></section>'
    return _dashboard(tenant_id, result)


@app.post("/tenant/{tenant_id}/upload-custom", response_class=HTMLResponse)
async def upload_custom(tenant_id: str, custom_file: UploadFile | None = File(None)) -> str:
    try:
        payload, filename, source_path = await _read_custom(custom_file)
        status, gateway_response = _post_gateway(tenant_id, filename, payload)
        result = _render_result(tenant_id, status, gateway_response, source_path, filename)
    except HTTPException as exc:
        result = f'<section class="panel"><p class="error">{escape(str(exc.detail))}</p></section>'
    return _dashboard(tenant_id, result)
