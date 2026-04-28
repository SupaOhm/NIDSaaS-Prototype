"""Tenant-scoped webhook receiver for local alert demos."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from html import escape
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse


app = FastAPI(title="NIDSaaS Webhook Receiver")
_ALERTS: dict[str, list[dict[str, Any]]] = defaultdict(list)
_ALERT_STREAMS: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)


def _evidence_summary(alert: dict[str, Any]) -> str:
    evidence = alert.get("evidence", {})
    if isinstance(evidence, dict):
        def _sanitize(value: Any) -> Any:
            if isinstance(value, dict):
                return {
                    key: _sanitize(child)
                    for key, child in value.items()
                    if child not in (None, "")
                }
            if isinstance(value, list):
                return [_sanitize(child) for child in value if child not in (None, "")]
            return value

        return json.dumps(_sanitize(evidence), sort_keys=True, default=str)
    return str(evidence)


def _alert_row(alert: dict[str, Any], tenant_id: str) -> str:
    return (
        "<tr>"
        f"<td>{escape(str(alert.get('alert_id', '')))}</td>"
        f"<td>{escape(str(alert.get('tenant_id', tenant_id)))}</td>"
        f"<td>{escape(str(alert.get('severity', '')))}</td>"
        f"<td>{escape(str(alert.get('prediction', '')))}</td>"
        f"<td>{escape(str(alert.get('stage', '')))}</td>"
        f"<td>{escape(str(alert.get('timestamp', '')))}</td>"
        f"<td><code>{escape(_evidence_summary(alert))}</code></td>"
        "</tr>"
    )


@app.post("/webhook/{tenant_id}")
async def receive_webhook(tenant_id: str, request: Request) -> dict[str, Any]:
    alert = await request.json()
    if not isinstance(alert, dict):
        return {"status": "rejected", "tenant_id": tenant_id, "error": "JSON object required"}

    stored_alert = dict(alert)
    stored_alert.setdefault("tenant_id", tenant_id)
    _ALERTS[tenant_id].append(stored_alert)
    for queue in list(_ALERT_STREAMS.get(tenant_id, set())):
        queue.put_nowait(stored_alert)
    print(f"[WEBHOOK] received alert tenant_id={tenant_id}", flush=True)
    return {
        "status": "received",
        "tenant_id": tenant_id,
        "count": len(_ALERTS[tenant_id]),
    }


@app.post("/admin/clear-alerts")
async def clear_alerts() -> dict[str, str]:
    for tenant_id in list(_ALERTS):
        _ALERTS[tenant_id].clear()
    print("[WEBHOOK] cleared in-memory alerts", flush=True)
    return {
        "status": "cleared",
        "message": "in-memory alerts cleared",
    }


@app.get("/alerts/{tenant_id}")
def list_alerts(tenant_id: str) -> dict[str, Any]:
    return {"tenant_id": tenant_id, "alerts": _ALERTS.get(tenant_id, [])}


@app.get("/alerts/{tenant_id}/stream")
async def stream_alerts(tenant_id: str, request: Request) -> StreamingResponse:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _ALERT_STREAMS[tenant_id].add(queue)

    async def event_stream():
        try:
            yield "event: status\ndata: connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    alert = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                payload = json.dumps(alert, default=str)
                yield f"event: alert\ndata: {payload}\n\n"
        finally:
            _ALERT_STREAMS[tenant_id].discard(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
    <!doctype html>
    <html>
      <head><title>NIDSaaS Webhook Receiver</title></head>
      <body>
        <h1>NIDSaaS Webhook Receiver</h1>
        <p>Tenant alert views:</p>
        <ul>
          <li><a href="/alerts/tenant_A/view">tenant_A</a></li>
          <li><a href="/alerts/tenant_B/view">tenant_B</a></li>
        </ul>
      </body>
    </html>
    """


@app.get("/alerts/{tenant_id}/view", response_class=HTMLResponse)
def view_alerts(tenant_id: str) -> str:
    alerts = _ALERTS.get(tenant_id, [])
    rows = [_alert_row(alert, tenant_id) for alert in alerts]
    body = "\n".join(rows) or '<tr><td colspan="7">No alerts received yet.</td></tr>'
    tenant_json = json.dumps(tenant_id)
    return f"""
    <!doctype html>
    <html>
      <head>
        <title>NIDSaaS Alerts - {escape(tenant_id)}</title>
        <style>
          body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
          th {{ background: #f4f4f4; }}
          code {{ white-space: pre-wrap; overflow-wrap: anywhere; }}
          .muted {{ color: #666; }}
          .status {{ display: inline-block; padding: 4px 8px; border-radius: 4px; background: #eef4ff; }}
          .connected {{ color: #137333; }}
          .disconnected {{ color: #b3261e; }}
        </style>
      </head>
      <body>
        <h1>Alerts for {escape(tenant_id)}</h1>
        <p class="muted">Tenant webhook receiver storage. Alerts are held in memory for this local demo process.</p>
        <p><a href="/">All tenants</a> | <a href="/alerts/{escape(tenant_id)}">JSON</a> | <button type="button" onclick="window.location.reload()">Refresh manually</button> | <button type="button" id="clear-alerts">Clear alerts</button></p>
        <p><span id="live-status" class="status disconnected">Live connecting...</span> <span class="muted">Last updated: <span id="last-updated">initial load</span></span></p>
        <table>
          <thead>
            <tr>
              <th>Alert ID</th>
              <th>Tenant</th>
              <th>Severity</th>
              <th>Prediction</th>
              <th>Stage</th>
              <th>Timestamp</th>
              <th>Evidence Summary</th>
            </tr>
          </thead>
          <tbody id="alerts-body">{body}</tbody>
        </table>
        <script>
          const tenantId = {tenant_json};
          const statusEl = document.getElementById("live-status");
          const lastUpdatedEl = document.getElementById("last-updated");
          const tbody = document.getElementById("alerts-body");
          const clearButton = document.getElementById("clear-alerts");

          function summarizeEvidence(alert) {{
            const evidence = alert.evidence || {{}};
            if (typeof evidence !== "object" || Array.isArray(evidence)) {{
              return String(evidence || "");
            }}
            const keys = [
              "original_pcap_path",
              "matched_flow_csv_path",
              "evidence_source",
              "attack_label_count",
              "attack_prediction_count",
              "total_rows_sampled",
              "ids_artifacts_dir"
            ];
            const summary = {{}};
            for (const key of keys) {{
              if (evidence[key] !== undefined && evidence[key] !== null && evidence[key] !== "") {{
                summary[key] = evidence[key];
              }}
            }}
            return JSON.stringify(summary);
          }}

          function addCell(row, value, useCode) {{
            const cell = document.createElement("td");
            if (useCode) {{
              const code = document.createElement("code");
              code.textContent = value || "";
              cell.appendChild(code);
            }} else {{
              cell.textContent = value || "";
            }}
            row.appendChild(cell);
          }}

          function appendAlert(alert) {{
            if (tbody.children.length === 1 && tbody.children[0].children.length === 1) {{
              tbody.innerHTML = "";
            }}
            const row = document.createElement("tr");
            addCell(row, alert.alert_id);
            addCell(row, alert.tenant_id || tenantId);
            addCell(row, alert.severity);
            addCell(row, alert.prediction);
            addCell(row, alert.stage);
            addCell(row, alert.timestamp);
            addCell(row, summarizeEvidence(alert), true);
            tbody.appendChild(row);
            lastUpdatedEl.textContent = new Date().toLocaleTimeString();
          }}

          async function clearAlerts() {{
            clearButton.disabled = true;
            try {{
              const response = await fetch("/admin/clear-alerts", {{ method: "POST" }});
              if (!response.ok) {{
                throw new Error(`status ${{response.status}}`);
              }}
              tbody.innerHTML = '<tr><td colspan="7">No alerts received yet.</td></tr>';
              lastUpdatedEl.textContent = new Date().toLocaleTimeString();
            }} finally {{
              clearButton.disabled = false;
            }}
          }}

          clearButton.addEventListener("click", () => {{
            clearAlerts().catch((error) => {{
              console.error("failed to clear alerts", error);
            }});
          }});

          const events = new EventSource(`/alerts/${{encodeURIComponent(tenantId)}}/stream`);
          events.addEventListener("status", () => {{
            statusEl.textContent = "Live connected";
            statusEl.className = "status connected";
          }});
          events.addEventListener("alert", (event) => {{
            statusEl.textContent = "Live connected";
            statusEl.className = "status connected";
            appendAlert(JSON.parse(event.data));
          }});
          events.onerror = () => {{
            statusEl.textContent = "Live disconnected; refresh manually.";
            statusEl.className = "status disconnected";
          }};
        </script>
      </body>
    </html>
    """
