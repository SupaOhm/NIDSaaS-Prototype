#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SAMPLE_FILE="data/samples/pcap/cic_attack_sample.pcap"

if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "[TEST] Missing demo PCAP sample: ${SAMPLE_FILE}" >&2
  echo "[TEST] Create samples with: ./scripts/test/create_cic_pcap_samples.sh" >&2
  exit 1
fi

exec ./scripts/test/pcap_upload.sh -d "$SAMPLE_FILE" -t tenant_A -e "demo_attack_$(date -u +"%Y%m%dT%H%M%SZ")"
