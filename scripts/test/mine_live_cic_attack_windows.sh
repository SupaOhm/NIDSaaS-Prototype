#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PCAP_ROOT="${CIC_PCAP_SOURCE_DIR:-data/pcap/pcap_CIC_IDS2017}"
OUTPUT_DIR="${CIC_PCAP_SAMPLE_DIR:-data/samples/pcap}"
LIVE_FLOW_OUTPUT_DIR="${LIVE_FLOW_OUTPUT_DIR:-outputs/live_flows}"
TMP_DIR="${LIVE_ATTACK_MINE_TMP_DIR:-outputs/live_cic_window_mining}"
METADATA_JSONL="${OUTPUT_DIR}/live_mined_samples.jsonl"
WINDOW_SIZE="${WINDOW_SIZE:-5000}"
MAX_PACKETS="${MAX_PACKETS:-500000}"
STEP="${STEP:-5000}"

if ! command -v editcap >/dev/null 2>&1; then
  echo "[MINE] editcap is required." >&2
  exit 1
fi

for value_name in WINDOW_SIZE MAX_PACKETS STEP; do
  value="${!value_name}"
  if [[ ! "$value" =~ ^[0-9]+$ || "$value" -le 0 ]]; then
    echo "[MINE] ${value_name} must be a positive integer" >&2
    exit 1
  fi
done

if [[ ! -d "$PCAP_ROOT" ]]; then
  echo "[MINE] CIC PCAP root not found: ${PCAP_ROOT}" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR" "$LIVE_FLOW_OUTPUT_DIR" "$TMP_DIR"
rm -f \
  "${OUTPUT_DIR}/cic_attack_sample.pcap" \
  "${OUTPUT_DIR}/cic_benign_sample.pcap" \
  "${OUTPUT_DIR}/cic_highrate_sample.pcap" \
  "${OUTPUT_DIR}/cic_portscan_sample.pcap" \
  "${OUTPUT_DIR}/cic_ddos_sample.pcap" \
  "${OUTPUT_DIR}/cic_webattack_sample.pcap" \
  "${OUTPUT_DIR}/cic_infiltration_sample.pcap" \
  "$METADATA_JSONL"
rm -f "${TMP_DIR}"/candidate_*.pcap "${TMP_DIR}"/candidate_result.json

classify_candidate() {
  local candidate="$1"
  local source_pcap="$2"
  local packet_range="$3"
  local result_json="$4"

  python3 - "$candidate" "$LIVE_FLOW_OUTPUT_DIR" "$source_pcap" "$packet_range" "$result_json" <<'PY'
import json
import sys
from pathlib import Path

project_root = Path.cwd()
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from nidsaas.detection.demo_inference_adapter import run_demo_ids_inference
from nidsaas.detection.live_flow_extractor import extract_flows_from_pcap

candidate, output_dir, source_pcap, packet_range, result_json = sys.argv[1:6]
extraction = extract_flows_from_pcap(candidate, output_dir=output_dir)
result = run_demo_ids_inference(
    tenant_id="mining",
    source_id=Path(source_pcap).stem,
    file_path=candidate,
    extracted_flow_csv_path=extraction["extracted_flow_csv_path"],
    extraction_metadata=extraction,
)
evidence = result.get("evidence", {})
live = evidence.get("live_flow_rule_evidence", {})
observed = live.get("observed", {})
payload = {
    "source_pcap": source_pcap,
    "packet_range": packet_range,
    "prediction": result.get("prediction"),
    "attack_type": result.get("attack_type"),
    "number_of_flows": evidence.get("number_of_flows"),
    "detection_reason": evidence.get("detection_reason"),
    "max_packets_per_sec": observed.get("max_sustained_packets_per_sec", 0),
    "max_bytes_per_sec": observed.get("max_sustained_bytes_per_sec", 0),
    "total_syn_count": observed.get("total_syn_count", 0),
    "high_rate_flow_count": observed.get("high_rate_flow_count", 0),
}
Path(result_json).write_text(json.dumps(payload), encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
}

json_value() {
  local path="$1"
  local key="$2"
  python3 - "$path" "$key" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    value = json.load(handle).get(sys.argv[2], "")
print(value)
PY
}

save_sample() {
  local sample_name="$1"
  local candidate="$2"
  local result_json="$3"
  local output_path="${OUTPUT_DIR}/${sample_name}"

  if [[ -f "$output_path" && "$candidate" != "$output_path" ]]; then
    return 0
  fi

  if [[ "$candidate" != "$output_path" ]]; then
    cp "$candidate" "$output_path"
  fi
  python3 - "$sample_name" "$output_path" "$result_json" "$METADATA_JSONL" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

sample_name, output_path, result_json, metadata_jsonl = sys.argv[1:5]
payload = json.loads(Path(result_json).read_text(encoding="utf-8"))
payload["sample_name"] = sample_name
payload["output_path"] = output_path
payload["sha256"] = hashlib.sha256(Path(output_path).read_bytes()).hexdigest()
with open(metadata_jsonl, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(payload, sort_keys=True) + "\n")
PY
  echo "[MINE] saved ${sample_name}"
}

classify_saved_sample() {
  local sample_path="$1"
  local source_pcap="$2"
  local packet_range="$3"
  local result_json="$4"
  classify_candidate "$sample_path" "$source_pcap" "$packet_range" "$result_json"
}

echo "[MINE] creating benign sample from Monday packets 1-${WINDOW_SIZE}"
MONDAY_PCAP="${PCAP_ROOT}/Monday-WorkingHours.pcap"
if [[ ! -f "$MONDAY_PCAP" ]]; then
  echo "[MINE] required benign source missing: ${MONDAY_PCAP}" >&2
  exit 1
fi
editcap -r "$MONDAY_PCAP" "${OUTPUT_DIR}/cic_benign_sample.pcap" "1-${WINDOW_SIZE}"
classify_saved_sample \
  "${OUTPUT_DIR}/cic_benign_sample.pcap" \
  "$MONDAY_PCAP" \
  "1-${WINDOW_SIZE}" \
  "${TMP_DIR}/benign_result.json" >/dev/null
if [[ "$(json_value "${TMP_DIR}/benign_result.json" prediction)" != "benign" ]]; then
  echo "[MINE] benign sample did not classify benign" >&2
  cat "${TMP_DIR}/benign_result.json" >&2
  exit 1
fi
save_sample "cic_benign_sample.pcap" "${OUTPUT_DIR}/cic_benign_sample.pcap" "${TMP_DIR}/benign_result.json"

while IFS= read -r source_pcap; do
  source_name="$(basename "$source_pcap")"
  if [[ "$source_name" == "Monday-WorkingHours.pcap" ]]; then
    echo "[MINE] skipping ${source_name} for attack mining; Monday is reserved for benign sample"
    continue
  fi
  echo "[MINE] scanning ${source_name}"
  start=1
  while [[ "$start" -le "$MAX_PACKETS" ]]; do
    end=$((start + WINDOW_SIZE - 1))
    candidate="${TMP_DIR}/candidate_${source_name//[^A-Za-z0-9_.-]/_}_${start}_${end}.pcap"
    result_json="${TMP_DIR}/candidate_result.json"
    editcap -r "$source_pcap" "$candidate" "${start}-${end}"
    if [[ ! -s "$candidate" ]]; then
      echo "[MINE] empty candidate at ${source_name} ${start}-${end}; stopping source"
      break
    fi

    classify_candidate "$candidate" "$source_pcap" "${start}-${end}" "$result_json"
    prediction="$(json_value "$result_json" prediction)"
    attack_type="$(json_value "$result_json" attack_type)"

    if [[ "$prediction" == "attack" && "$attack_type" == "HighRateFlow" && ! -f "${OUTPUT_DIR}/cic_highrate_sample.pcap" ]]; then
      save_sample "cic_highrate_sample.pcap" "$candidate" "$result_json"
    fi

    if [[ "$prediction" == "attack" && "$attack_type" == "PortScanLike" && ! -f "${OUTPUT_DIR}/cic_portscan_sample.pcap" ]]; then
      save_sample "cic_portscan_sample.pcap" "$candidate" "$result_json"
    fi

    source_lower="$(printf '%s' "$source_name" | tr '[:upper:]' '[:lower:]')"
    reason_lower="$(json_value "$result_json" detection_reason | tr '[:upper:]' '[:lower:]')"
    if [[ "$prediction" == "attack" && "$source_lower" == *ddos* && "$reason_lower" == *high-rate* && ! -f "${OUTPUT_DIR}/cic_ddos_sample.pcap" ]]; then
      save_sample "cic_ddos_sample.pcap" "$candidate" "$result_json"
    fi
    if [[ "$prediction" == "attack" && "$source_lower" == *webattack* && ! -f "${OUTPUT_DIR}/cic_webattack_sample.pcap" ]]; then
      save_sample "cic_webattack_sample.pcap" "$candidate" "$result_json"
    fi
    if [[ "$prediction" == "attack" && "$source_lower" == *infil* && ! -f "${OUTPUT_DIR}/cic_infiltration_sample.pcap" ]]; then
      save_sample "cic_infiltration_sample.pcap" "$candidate" "$result_json"
    fi

    start=$((start + STEP))
  done
done < <(find "$PCAP_ROOT" -maxdepth 1 -type f -name '*.pcap' | sort)

python3 - "$OUTPUT_DIR" "$METADATA_JSONL" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
metadata_path = Path(sys.argv[2])
if not metadata_path.exists():
    raise SystemExit("[MINE] no metadata file written")

rows = [json.loads(line) for line in metadata_path.read_text(encoding="utf-8").splitlines() if line.strip()]
by_hash: dict[str, dict] = {}
kept: list[dict] = []
removed: list[dict] = []
for row in rows:
    sample_path = Path(row["output_path"])
    digest = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    row["sha256"] = digest
    if digest in by_hash:
        sample_path.unlink(missing_ok=True)
        removed.append(row)
        continue
    by_hash[digest] = row
    kept.append(row)

metadata_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in kept), encoding="utf-8")

print("[MINE] final samples")
print("sample_name | source_pcap | packet_range | prediction | attack_type | number_of_flows | detection_reason | sha256")
for row in kept:
    print(
        f"{row['sample_name']} | {Path(row['source_pcap']).name} | {row['packet_range']} | "
        f"{row['prediction']} | {row['attack_type']} | {row['number_of_flows']} | "
        f"{row['detection_reason']} | {row['sha256']}"
    )

if removed:
    print("[MINE] removed duplicate-content samples")
    for row in removed:
        print(f"[MINE] removed {row['sample_name']} duplicate sha256={row['sha256']}")

expected = {
    "cic_highrate_sample.pcap": "HighRateFlow",
    "cic_portscan_sample.pcap": "PortScanLike",
    "cic_ddos_sample.pcap": "DDoS-supported live attack",
    "cic_webattack_sample.pcap": "WebAttack source-supported live attack",
    "cic_infiltration_sample.pcap": "Infiltration source-supported live attack",
}
found = {row["sample_name"] for row in kept}
for sample_name, reason in expected.items():
    if sample_name not in found:
        print(f"[MINE] unavailable locally: {sample_name} ({reason} not found by live rules)")
PY
