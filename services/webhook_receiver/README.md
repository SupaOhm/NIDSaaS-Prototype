# Webhook Receiver

Demo FastAPI service for tenant-scoped alert delivery. It stores alerts in memory and exposes both JSON and a small HTML view for local prototype presentations.

Run:

```bash
./scripts/run_webhook_receiver.sh
```

Open:

```text
http://localhost:9001/alerts/tenant_A/view
```
