#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PCAP_ROOT="${CIC_PCAP_SOURCE_DIR:-data/pcap/pcap_CIC_IDS2017}"
CSV_ROOT="${CIC_CSV_SOURCE_DIR:-data/csv/csv_CIC_IDS2017}"
PCAP_OUTPUT_DIR="${CIC_PCAP_SAMPLE_DIR:-data/samples/pcap}"
CSV_OUTPUT_DIR="${CIC_CSV_SAMPLE_DIR:-data/samples/csv}"
PACKET_COUNT="${CIC_PCAP_SAMPLE_PACKETS:-5000}"
CSV_ROW_COUNT="${CIC_CSV_SAMPLE_ROWS:-5000}"

if ! command -v editcap >/dev/null 2>&1; then
  echo "[SAMPLES] editcap is required to create PCAP samples." >&2
  echo "[SAMPLES] Install Wireshark tools with: brew install wireshark" >&2
  exit 1
fi

if [[ ! "$PACKET_COUNT" =~ ^[0-9]+$ || "$PACKET_COUNT" -le 0 ]]; then
  echo "[SAMPLES] CIC_PCAP_SAMPLE_PACKETS must be a positive integer" >&2
  exit 1
fi

if [[ ! -d "$PCAP_ROOT" ]]; then
  echo "[SAMPLES] CIC PCAP source directory not found: ${PCAP_ROOT}" >&2
  exit 1
fi

if [[ ! -d "$CSV_ROOT" ]]; then
  echo "[SAMPLES] CIC CSV source directory not found: ${CSV_ROOT}" >&2
  exit 1
fi

mkdir -p "$PCAP_OUTPUT_DIR" "$CSV_OUTPUT_DIR"

rm -f \
  "${PCAP_OUTPUT_DIR}/cic_attack_sample.pcap" \
  "${PCAP_OUTPUT_DIR}/cic_benign_sample.pcap" \
  "${PCAP_OUTPUT_DIR}/cic_ddos_sample.pcap" \
  "${PCAP_OUTPUT_DIR}/cic_portscan_sample.pcap" \
  "${PCAP_OUTPUT_DIR}/cic_webattack_sample.pcap" \
  "${PCAP_OUTPUT_DIR}/cic_infiltration_sample.pcap"

created_pcap_outputs=()
skipped_pcap_categories=()

create_pcap_sample() {
  local category="$1"
  local input="$2"
  local output="$3"
  local note="$4"

  if [[ ! -f "$input" ]]; then
    echo "[SAMPLES] WARNING: broad-source ${category} PCAP missing; skipping: ${input}" >&2
    skipped_pcap_categories+=("$category")
    return 0
  fi

  echo "[SAMPLES] creating ${category} broad-day PCAP demo sample"
  echo "[SAMPLES] input: ${input}"
  echo "[SAMPLES] output: ${output}"
  echo "[SAMPLES] note: ${note}"
  editcap -r "$input" "$output" "1-${PACKET_COUNT}"

  if [[ ! -s "$output" ]]; then
    echo "[SAMPLES] failed to create non-empty ${category} sample: ${output}" >&2
    exit 1
  fi

  created_pcap_outputs+=("$output")
}

first_existing() {
  for path in "$@"; do
    if [[ -f "$path" ]]; then
      printf '%s\n' "$path"
      return 0
    fi
  done
  return 1
}

create_pcap_sample "benign" \
  "${PCAP_ROOT}/Monday-WorkingHours.pcap" \
  "${PCAP_OUTPUT_DIR}/cic_benign_sample.pcap" \
  "broad Monday PCAP trigger; benign CSV sample provides label evidence"

if [[ -f "${PCAP_ROOT}/Friday-WorkingHours.pcap" ]]; then
  echo "[SAMPLES] finding Friday packet window for live attack sample"
  ./scripts/test/find_live_attack_pcap_window.sh \
    "${PCAP_ROOT}/Friday-WorkingHours.pcap" \
    "${PCAP_OUTPUT_DIR}/cic_attack_sample.pcap"
  created_pcap_outputs+=("${PCAP_OUTPUT_DIR}/cic_attack_sample.pcap")
else
  echo "[SAMPLES] WARNING: Friday source PCAP missing; skipping live attack sample: ${PCAP_ROOT}/Friday-WorkingHours.pcap" >&2
  skipped_pcap_categories+=("attack")
fi

create_pcap_sample "ddos" \
  "${PCAP_ROOT}/Friday-WorkingHours.pcap" \
  "${PCAP_OUTPUT_DIR}/cic_ddos_sample.pcap" \
  "broad Friday PCAP trigger; DDoS CSV sample provides category evidence"

create_pcap_sample "portscan" \
  "${PCAP_ROOT}/Friday-WorkingHours.pcap" \
  "${PCAP_OUTPUT_DIR}/cic_portscan_sample.pcap" \
  "broad Friday PCAP trigger; PortScan CSV sample provides category evidence"

create_pcap_sample "webattack" \
  "$(first_existing "${PCAP_ROOT}/Thursday-WorkingHours.pcap" "${PCAP_ROOT}/Friday-WorkingHours.pcap" || true)" \
  "${PCAP_OUTPUT_DIR}/cic_webattack_sample.pcap" \
  "broad Thursday PCAP trigger when available, otherwise Friday; WebAttack CSV sample provides category evidence"

create_pcap_sample "infiltration" \
  "$(first_existing "${PCAP_ROOT}/Thursday-WorkingHours.pcap" "${PCAP_ROOT}/Friday-WorkingHours.pcap" || true)" \
  "${PCAP_OUTPUT_DIR}/cic_infiltration_sample.pcap" \
  "broad Thursday PCAP trigger when available, otherwise Friday; Infiltration CSV sample provides category evidence"

echo "[SAMPLES] NOTE: PCAP outputs are broad-day demo triggers, not category-isolated PCAP captures."
echo "[SAMPLES] NOTE: Matching CSV samples under ${CSV_OUTPUT_DIR} provide deterministic category label evidence."
echo "[SAMPLES] NOTE: Duplicate PCAP hashes are expected when multiple demo categories use the same broad source PCAP."

python3 scripts/test/create_cic_demo_csv_samples.py \
  --csv-root "$CSV_ROOT" \
  --output-dir "$CSV_OUTPUT_DIR" \
  --max-rows "$CSV_ROW_COUNT"

echo "[SAMPLES] final PCAP sample sizes:"
if [[ "${#created_pcap_outputs[@]}" -gt 0 ]]; then
  wc -c "${created_pcap_outputs[@]}"
else
  echo "[SAMPLES] no category PCAP samples created"
fi

echo "[SAMPLES] category PCAP SHA256:"
if [[ "${#created_pcap_outputs[@]}" -gt 0 ]]; then
  shasum -a 256 "${created_pcap_outputs[@]}"
fi

if [[ "${#skipped_pcap_categories[@]}" -gt 0 ]]; then
  echo "[SAMPLES] skipped PCAP categories: ${skipped_pcap_categories[*]}"
fi

echo "[SAMPLES] final CSV sample sizes:"
csv_outputs=(
  "${CSV_OUTPUT_DIR}/cic_benign_sample.csv"
  "${CSV_OUTPUT_DIR}/cic_ddos_sample.csv"
  "${CSV_OUTPUT_DIR}/cic_portscan_sample.csv"
  "${CSV_OUTPUT_DIR}/cic_webattack_sample.csv"
)
if [[ -f "${CSV_OUTPUT_DIR}/cic_infiltration_sample.csv" ]]; then
  csv_outputs+=("${CSV_OUTPUT_DIR}/cic_infiltration_sample.csv")
fi
wc -c "${csv_outputs[@]}"
