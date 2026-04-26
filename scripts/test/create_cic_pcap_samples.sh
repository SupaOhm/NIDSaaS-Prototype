#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SOURCE_DIR="${CIC_PCAP_SOURCE_DIR:-data/pcap/pcap_CIC_IDS2017}"
SAMPLE_DIR="${CIC_PCAP_SAMPLE_DIR:-data/samples/pcap}"
PACKET_COUNT="${CIC_PCAP_SAMPLE_PACKETS:-5000}"
ATTACK_REGEX='(DDos|DDoS|PortScan|Infilteration|WebAttacks|Friday)'

if ! command -v editcap >/dev/null 2>&1; then
  echo "[SAMPLES] editcap is required to create PCAP samples." >&2
  echo "[SAMPLES] Install Wireshark tools with: brew install wireshark" >&2
  exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "[SAMPLES] CIC PCAP source directory not found: ${SOURCE_DIR}" >&2
  exit 1
fi

mkdir -p "$SAMPLE_DIR"

first_matching_pcap() {
  local mode="$1"
  while IFS= read -r path; do
    local name
    name="$(basename "$path")"
    if [[ "$mode" == "attack" && "$name" =~ $ATTACK_REGEX ]]; then
      printf '%s\n' "$path"
      return 0
    fi
    if [[ "$mode" == "benign" && ! "$name" =~ $ATTACK_REGEX ]]; then
      printf '%s\n' "$path"
      return 0
    fi
  done < <(find "$SOURCE_DIR" -maxdepth 1 -type f -iname '*.pcap' | sort)
  return 1
}

sample_name_for() {
  local input="$1"
  local base
  base="$(basename "$input")"
  printf '%s.sample.pcap\n' "${base%.pcap}"
}

create_sample() {
  local label="$1"
  local input="$2"
  local output="$3"

  echo "[SAMPLES] creating ${label} sample"
  echo "[SAMPLES] input: ${input}"
  echo "[SAMPLES] output: ${output}"
  if editcap -c "$PACKET_COUNT" "$input" "$output"; then
    return 0
  fi

  echo "[SAMPLES] editcap -c failed; trying explicit range 1-${PACKET_COUNT}" >&2
  editcap -r "$input" "$output" "1-${PACKET_COUNT}"
}

if attack_input="$(first_matching_pcap attack)"; then
  attack_output="${SAMPLE_DIR}/$(sample_name_for "$attack_input")"
  create_sample "attack" "$attack_input" "$attack_output"
  ln -sf "$(basename "$attack_output")" "${SAMPLE_DIR}/cic_attack_sample.pcap"
else
  echo "[SAMPLES] no attack-ish CIC PCAP found in ${SOURCE_DIR}" >&2
fi

if benign_input="$(first_matching_pcap benign)"; then
  benign_output="${SAMPLE_DIR}/$(sample_name_for "$benign_input")"
  create_sample "benign" "$benign_input" "$benign_output"
  ln -sf "$(basename "$benign_output")" "${SAMPLE_DIR}/cic_benign_sample.pcap"
else
  echo "[SAMPLES] no benign-looking CIC PCAP found in ${SOURCE_DIR}" >&2
fi

echo "[SAMPLES] done"
