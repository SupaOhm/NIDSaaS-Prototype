# TODO

## Completed Prototype Milestones

- Repository cleanup and NIDSaaS project structure.
- Gateway upload API with tenant mock auth, deduplication, Kafka publishing, and JSONL fallback.
- Local Kafka infrastructure with Kafka UI.
- Simple Python Kafka consumer for upload events.
- Docker Spark Structured Streaming reader for upload events.
- Spark demo processor path that uses saved offline IDS artifacts and dispatches webhook alerts without retraining.
- Offline IDS audit and thin adapter wrapper.
- Webhook receiver and fake alert delivery demo.
- Standardized demo script workflow for infrastructure, local services, Spark processor, tests, debug tools, and shutdown.

## Next Milestones

- Add PCAP-to-flow extraction adapter using an external CICFlowMeter-compatible tool.
- Replace artifact-demo inference with true online inference over extracted CICFlowMeter flow CSVs.
- Add a durable alert dispatcher with tenant routing and retry policy.
- Add inference-only IDS adapter that loads saved models instead of retraining the offline cascade.
- Add minimal injector UI for tenant upload demonstrations.
