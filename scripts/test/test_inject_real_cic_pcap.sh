#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PCAP_PATH="data/samples/pcap/cic_attack_sample.pcap"
if [[ ! -f "$PCAP_PATH" ]]; then
  echo "[TEST] Missing demo PCAP sample: ${PCAP_PATH}" >&2
  echo "[TEST] Create samples with: ./scripts/test/create_cic_pcap_samples.sh" >&2
  exit 1
fi

exec ./scripts/test/pcap_upload.sh -d "$PCAP_PATH" -t tenant_A -e "real_cic_$(date -u +"%Y%m%dT%H%M%SZ")"
