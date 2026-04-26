#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SOURCE_DIR="${CIC_PCAP_SOURCE_DIR:-data/pcap/pcap_CIC_IDS2017}"
SAMPLE_DIR="${CIC_PCAP_SAMPLE_DIR:-data/samples/pcap}"
PACKET_COUNT="${CIC_PCAP_SAMPLE_PACKETS:-5000}"
ATTACK_REGEX='(DDos|DDoS|PortScan|WebAttacks|Infilteration|Friday)'
ATTACK_OUTPUT="${SAMPLE_DIR}/cic_attack_sample.pcap"
BENIGN_OUTPUT="${SAMPLE_DIR}/cic_benign_sample.pcap"

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

find "$SAMPLE_DIR" -maxdepth 1 -type f -name '*.sample_*.pcap' -delete
for link in "$ATTACK_OUTPUT" "$BENIGN_OUTPUT"; do
  if [[ -L "$link" && ! -e "$link" ]]; then
    echo "[SAMPLES] removing broken symlink: ${link}"
    rm -f "$link"
  fi
done

first_existing() {
  for path in "$@"; do
    if [[ -f "$path" ]]; then
      printf '%s\n' "$path"
      return 0
    fi
  done
  return 1
}

select_attack_source() {
  while IFS= read -r path; do
    local name
    name="$(basename "$path")"
    if [[ "$name" =~ $ATTACK_REGEX ]]; then
      printf '%s\n' "$path"
      return 0
    fi
  done < <(find "$SOURCE_DIR" -maxdepth 1 -type f -iname '*.pcap' | sort)

  first_existing "${SOURCE_DIR}/Friday-WorkingHours.pcap"
}

select_benign_source() {
  first_existing "${SOURCE_DIR}/Monday-WorkingHours.pcap"
}

create_sample() {
  local label="$1"
  local input="$2"
  local output="$3"

  if [[ -z "$input" || ! -f "$input" ]]; then
    echo "[SAMPLES] ${label} source PCAP not found" >&2
    exit 1
  fi

  rm -f "$output"
  echo "[SAMPLES] creating ${label} sample"
  echo "[SAMPLES] input: ${input}"
  echo "[SAMPLES] output: ${output}"
  editcap -r "$input" "$output" "1-${PACKET_COUNT}"

  if [[ ! -s "$output" ]]; then
    echo "[SAMPLES] failed to create non-empty ${label} sample: ${output}" >&2
    exit 1
  fi
}

attack_input="$(select_attack_source || true)"
benign_input="$(select_benign_source || true)"

create_sample "attack" "$attack_input" "$ATTACK_OUTPUT"
create_sample "benign" "$benign_input" "$BENIGN_OUTPUT"

echo "[SAMPLES] final sample sizes:"
wc -c "$ATTACK_OUTPUT" "$BENIGN_OUTPUT"
