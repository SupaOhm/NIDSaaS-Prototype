# Gateway

FastAPI gateway for prototype PCAP/file upload ingestion. It applies mock API-key authentication, performs in-memory batch-level deduplication by tenant/source/file epoch, saves accepted uploads under `data/uploads/`, and publishes upload metadata to Kafka topic `raw.tenant.<tenant_id>`.

## Run

From the repository root:

```bash
./scripts/run_gateway.sh
```

The service listens on `http://127.0.0.1:8000` by default.

## Upload

```bash
curl -s -X POST http://127.0.0.1:8000/upload-pcap \
  -H "x-api-key: dev-secret" \
  -F tenant_id=acme \
  -F source_id=edge-1 \
  -F file_epoch=demo-001 \
  -F start_offset=0 \
  -F end_offset=1024 \
  -F file=@data/pcap/pcap_CIC_IDS2017/Monday-WorkingHours.pcap
```

If Kafka is unavailable, the gateway writes accepted upload events to
`outputs/gateway_events.jsonl` instead of failing the request.

## Dedup Decisions

- `forward`: new non-overlapping batch; save and publish.
- `drop_duplicate`: identical batch hash already seen for the tenant/source/epoch.
- `drop_stale`: `end_offset` is not newer than the committed end offset.
- `trim_overlap`: overlaps a previously committed range; the prototype still saves and publishes the full file, but marks `effective_start_offset` as the previous committed end offset.
