#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PCAP_PATH="${1:-data/samples/pcap/cic_benign_sample.pcap}"
TENANT_ID="${TENANT_ID:-tenant_A}"
SOURCE_ID="${SOURCE_ID:-live_pcap_test}"
GATEWAY_URL="${GATEWAY_BASE_URL:-http://localhost:8000}"
API_KEY="${GATEWAY_API_KEY:-dev-secret}"
LIVE_FLOW_OUTPUT_DIR="${LIVE_FLOW_OUTPUT_DIR:-outputs/live_flows}"

if [[ ! -f "$PCAP_PATH" ]]; then
  echo "[TEST] PCAP not found: ${PCAP_PATH}" >&2
  echo "[TEST] Create demo samples with: ./scripts/test/create_cic_demo_dataset.sh" >&2
  exit 1
fi

if curl -fsS --connect-timeout 2 --max-time 5 "${GATEWAY_URL%/}/health" >/dev/null 2>&1; then
  file_size="$(wc -c <"$PCAP_PATH" | tr -d ' ')"
  file_epoch="live_test_$(date -u +"%Y%m%dT%H%M%SZ")"
  echo "[TEST] uploading PCAP to gateway: ${PCAP_PATH}"
  curl -sS --connect-timeout 5 --max-time 60 \
    -X POST "${GATEWAY_URL%/}/upload-pcap" \
    -H "x-api-key: ${API_KEY}" \
    -F tenant_id="${TENANT_ID}" \
    -F source_id="${SOURCE_ID}" \
    -F file_epoch="${file_epoch}" \
    -F start_offset="0" \
    -F end_offset="${file_size}" \
    -F file=@"${PCAP_PATH}"
  printf '\n'
else
  echo "[TEST] gateway not reachable at ${GATEWAY_URL}; running extractor/classifier check only"
fi

python3 - "$PCAP_PATH" "$LIVE_FLOW_OUTPUT_DIR" <<'PY'
import json
import sys
from pathlib import Path

project_root = Path.cwd()
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
from nidsaas.detection.demo_inference_adapter import run_demo_ids_inference
from nidsaas.detection.live_flow_extractor import extract_flows_from_pcap

pcap_path = sys.argv[1]
output_dir = sys.argv[2]

extraction = extract_flows_from_pcap(pcap_path, output_dir=output_dir)
result = run_demo_ids_inference(
    tenant_id="tenant_A",
    source_id="live_pcap_test",
    file_path=pcap_path,
    extracted_flow_csv_path=extraction["extracted_flow_csv_path"],
    extraction_metadata=extraction,
)
evidence = result.get("evidence", {})
print(json.dumps({
    "prediction": result.get("prediction"),
    "severity": result.get("severity"),
    "attack_type": result.get("attack_type"),
    "extracted_flow_csv_path": evidence.get("extracted_flow_csv_path"),
    "number_of_flows": evidence.get("number_of_flows"),
    "detection_reason": evidence.get("detection_reason"),
    "evidence_source": evidence.get("evidence_source"),
}, indent=2))

if extraction.get("status") != "success":
    raise SystemExit("[TEST] flow extraction failed")
if not extraction.get("extracted_flow_csv_path"):
    raise SystemExit("[TEST] missing extracted flow CSV path")
if int(extraction.get("number_of_flows") or 0) <= 0:
    raise SystemExit("[TEST] expected at least one extracted flow")
if evidence.get("evidence_source") != "live_extracted_flow_rules":
    raise SystemExit("[TEST] expected live_extracted_flow_rules evidence")
if result.get("prediction") not in {"attack", "benign"}:
    raise SystemExit("[TEST] invalid prediction")
PY
