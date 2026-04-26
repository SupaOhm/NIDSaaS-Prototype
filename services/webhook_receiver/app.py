"""Tenant-scoped webhook receiver for local alert demos."""

from __future__ import annotations

from collections import defaultdict
from html import escape
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


app = FastAPI(title="NIDSaaS Webhook Receiver")
_ALERTS: dict[str, list[dict[str, Any]]] = defaultdict(list)


@app.post("/webhook/{tenant_id}")
async def receive_webhook(tenant_id: str, request: Request) -> dict[str, Any]:
    alert = await request.json()
    if not isinstance(alert, dict):
        return {"status": "rejected", "tenant_id": tenant_id, "error": "JSON object required"}

    stored_alert = dict(alert)
    stored_alert.setdefault("tenant_id", tenant_id)
    _ALERTS[tenant_id].append(stored_alert)
    print(f"[WEBHOOK] received alert tenant_id={tenant_id}", flush=True)
    return {
        "status": "received",
        "tenant_id": tenant_id,
        "count": len(_ALERTS[tenant_id]),
    }


@app.get("/alerts/{tenant_id}")
def list_alerts(tenant_id: str) -> dict[str, Any]:
    return {"tenant_id": tenant_id, "alerts": _ALERTS.get(tenant_id, [])}


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
    rows = []
    for alert in alerts:
        rows.append(
            "<tr>"
            f"<td>{escape(str(alert.get('timestamp', '')))}</td>"
            f"<td>{escape(str(alert.get('alert_id', '')))}</td>"
            f"<td>{escape(str(alert.get('source_id', '')))}</td>"
            f"<td>{escape(str(alert.get('severity', '')))}</td>"
            f"<td>{escape(str(alert.get('prediction', '')))}</td>"
            f"<td>{escape(str(alert.get('attack_type', '')))}</td>"
            f"<td>{escape(str(alert.get('evidence', '')))}</td>"
            "</tr>"
        )

    body = "\n".join(rows) or '<tr><td colspan="7">No alerts received yet.</td></tr>'
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
        </style>
      </head>
      <body>
        <h1>Alerts for {escape(tenant_id)}</h1>
        <p><a href="/">All tenants</a> | <a href="/alerts/{escape(tenant_id)}">JSON</a></p>
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Alert ID</th>
              <th>Source</th>
              <th>Severity</th>
              <th>Prediction</th>
              <th>Attack Type</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>{body}</tbody>
        </table>
      </body>
    </html>
    """
