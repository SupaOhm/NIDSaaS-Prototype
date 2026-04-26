# Webhook Receiver

Demo FastAPI service for tenant-scoped alert delivery. It stores alerts in memory and exposes both JSON and a small HTML view for local prototype presentations.

Run:

```bash
./scripts/demo/start_services.sh
```

The webhook receiver is started by `start_services.sh` alongside the gateway.

Open:

```text
http://localhost:9001/alerts/tenant_A/view
```
