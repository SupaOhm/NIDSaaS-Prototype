#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

INPUT_PCAP="${1:-data/pcap/pcap_CIC_IDS2017/Friday-WorkingHours.pcap}"
OUTPUT_PCAP="${2:-data/samples/pcap/cic_attack_sample.pcap}"
WINDOW_SIZE="${LIVE_ATTACK_WINDOW_SIZE:-5000}"
MAX_PACKETS="${LIVE_ATTACK_SEARCH_MAX_PACKETS:-200000}"
LIVE_FLOW_OUTPUT_DIR="${LIVE_FLOW_OUTPUT_DIR:-outputs/live_flows}"
TMP_DIR="${LIVE_ATTACK_SEARCH_TMP_DIR:-outputs/live_attack_window_search}"

if ! command -v editcap >/dev/null 2>&1; then
  echo "[ATTACK-WINDOW] editcap is required." >&2
  exit 1
fi

if [[ ! -f "$INPUT_PCAP" ]]; then
  echo "[ATTACK-WINDOW] source PCAP not found: ${INPUT_PCAP}" >&2
  exit 1
fi

if [[ ! "$WINDOW_SIZE" =~ ^[0-9]+$ || "$WINDOW_SIZE" -le 0 ]]; then
  echo "[ATTACK-WINDOW] LIVE_ATTACK_WINDOW_SIZE must be a positive integer" >&2
  exit 1
fi

if [[ ! "$MAX_PACKETS" =~ ^[0-9]+$ || "$MAX_PACKETS" -le 0 ]]; then
  echo "[ATTACK-WINDOW] LIVE_ATTACK_SEARCH_MAX_PACKETS must be a positive integer" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_PCAP")" "$TMP_DIR" "$LIVE_FLOW_OUTPUT_DIR"
rm -f "${TMP_DIR}"/candidate_*.pcap

echo "[ATTACK-WINDOW] searching ${INPUT_PCAP}"
echo "[ATTACK-WINDOW] window_size=${WINDOW_SIZE} max_packets=${MAX_PACKETS}"

start=1
while [[ "$start" -le "$MAX_PACKETS" ]]; do
  end=$((start + WINDOW_SIZE - 1))
  if [[ "$end" -gt "$MAX_PACKETS" ]]; then
    end="$MAX_PACKETS"
  fi

  candidate="${TMP_DIR}/candidate_${start}_${end}.pcap"
  echo "[ATTACK-WINDOW] testing packet range ${start}-${end}"
  editcap -r "$INPUT_PCAP" "$candidate" "${start}-${end}"

  if [[ ! -s "$candidate" ]]; then
    echo "[ATTACK-WINDOW] candidate is empty, stopping at ${start}-${end}"
    break
  fi

  if python3 - "$candidate" "$LIVE_FLOW_OUTPUT_DIR" "$start" "$end" <<'PY'
import json
import sys
from pathlib import Path

project_root = Path.cwd()
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from nidsaas.detection.demo_inference_adapter import run_demo_ids_inference
from nidsaas.detection.live_flow_extractor import extract_flows_from_pcap

candidate = sys.argv[1]
output_dir = sys.argv[2]
start = sys.argv[3]
end = sys.argv[4]

extraction = extract_flows_from_pcap(candidate, output_dir=output_dir)
result = run_demo_ids_inference(
    tenant_id="demo_search",
    source_id="friday_window",
    file_path=candidate,
    extracted_flow_csv_path=extraction["extracted_flow_csv_path"],
    extraction_metadata=extraction,
)
evidence = result.get("evidence", {})
summary = {
    "range": f"{start}-{end}",
    "prediction": result.get("prediction"),
    "attack_type": result.get("attack_type"),
    "number_of_flows": evidence.get("number_of_flows"),
    "detection_reason": evidence.get("detection_reason"),
    "extracted_flow_csv_path": evidence.get("extracted_flow_csv_path"),
}
print(json.dumps(summary, sort_keys=True))
raise SystemExit(0 if result.get("prediction") == "attack" else 1)
PY
  then
    cp "$candidate" "$OUTPUT_PCAP"
    echo "[ATTACK-WINDOW] selected packet range ${start}-${end}"
    echo "[ATTACK-WINDOW] output: ${OUTPUT_PCAP}"
    exit 0
  fi

  start=$((end + 1))
done

echo "[ATTACK-WINDOW] ERROR: no candidate up to packet ${MAX_PACKETS} triggered live flow rules" >&2
exit 1
