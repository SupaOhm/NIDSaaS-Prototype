#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SAMPLE_FILE="data/samples/pcap/cic_benign_sample.pcap"
if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "[TEST] Missing demo PCAP sample: ${SAMPLE_FILE}" >&2
  echo "[TEST] Create samples with: ./scripts/test/create_cic_pcap_samples.sh" >&2
  exit 1
fi

echo "[TEST] first upload should be forward/published true"
./scripts/test/pcap_upload.sh -d "$SAMPLE_FILE" -t tenant_A -e duplicate_demo_epoch

printf '\n[TEST] second upload should be drop_duplicate/published false\n'
./scripts/test/pcap_upload.sh -d "$SAMPLE_FILE" -t tenant_A -e duplicate_demo_epoch
printf '\n'
