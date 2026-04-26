# TODO

## Completed Prototype Milestones

- [x] Repository cleanup and NIDSaaS project structure
- [x] Gateway upload API with tenant mock auth, deduplication, Kafka publishing, and JSONL fallback
- [x] Local Kafka infrastructure with Kafka UI
- [x] Simple Python Kafka consumer for upload-event debugging
- [x] Docker Spark Structured Streaming reader for upload events
- [x] Spark-first demo processor using saved offline IDS artifacts
- [x] Real CIC PCAP upload demo path using pre-extracted CICFlowMeter CSV evidence
- [x] Webhook receiver with tenant-specific alert pages
- [x] Multi-tenant demo verified for tenant_A and tenant_B
- [x] Offline IDS audit and thin adapter wrapper
- [x] Standardized demo script workflow

## Demo-Ready Checklist

- [ ] Practice clean startup from zero
- [ ] Confirm tenant_A alert appears
- [ ] Confirm tenant_B alert appears separately
- [ ] Confirm duplicate upload is dropped
- [ ] Confirm Kafka UI shows tenant topics
- [ ] Confirm Spark terminal shows processing logs
- [ ] Confirm real CIC PCAP upload resolves to matching flow CSV
- [ ] Prepare 2-minute demo narration

## Next Engineering Milestones

- [ ] Add live PCAP-to-flow extraction adapter using an external CICFlowMeter-compatible tool
- [ ] Add inference-only IDS adapter that loads saved RF/conformal/gate models without retraining
- [ ] Replace artifact-demo inference with true online inference over extracted CICFlowMeter flow CSVs
- [ ] Add durable alert dispatcher with tenant routing and retry policy
- [ ] Add minimal injector UI for tenant upload demonstrations

## Known Demo Limitations

- Current live demo uses trained IDS artifacts, not full model retraining
- Live CICFlowMeter PCAP-to-flow extraction is not implemented yet
- Real CIC PCAP uploads are resolved to corresponding pre-extracted CICFlowMeter CSVs
- Detection evidence comes from saved cascade prediction artifacts when source-file rows exist, otherwise from matched CICFlowMeter CSV labels
