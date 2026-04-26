"""Alert dispatch helper for tenant webhook delivery."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def dispatch_alert(alert: dict, webhook_url: str) -> bool:
    """POST an alert JSON payload to a tenant webhook URL."""
    data = json.dumps(alert).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            ok = 200 <= response.status < 300
            if ok:
                print(f"[DISPATCHER] delivered alert to {webhook_url}", flush=True)
            else:
                print(f"[DISPATCHER] webhook returned status={response.status}", flush=True)
            return ok
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"[DISPATCHER] failed to deliver alert to {webhook_url}: {exc}", flush=True)
        return False
