#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

GATEWAY_BASE_URL="${GATEWAY_BASE_URL:-http://localhost:8000}"
WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-http://localhost:9001}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

find_pcap() {
  local sample="data/samples/pcap/cic_attack_sample.pcap"
  local roots=("data/pcap" "data/pcap_CIC_IDS2017")
  local preferred_regex='(DDos|DDoS|PortScan|Infilteration|WebAttacks|Friday)'

  if [[ -f "$sample" ]]; then
    printf '%s\n' "$sample"
    return 0
  fi

  for root in "${roots[@]}"; do
    [[ -d "$root" ]] || continue
    while IFS= read -r path; do
      if [[ "$(basename "$path")" =~ $preferred_regex ]]; then
        printf '%s\n' "$path"
        return 0
      fi
    done < <(find "$root" -type f -iname '*.pcap' | sort)
  done

  for root in "${roots[@]}"; do
    [[ -d "$root" ]] || continue
    while IFS= read -r path; do
      printf '%s\n' "$path"
      return 0
    done < <(find "$root" -type f -iname '*.pcap' | sort)
  done

  return 1
}

if ! PCAP_PATH="$(find_pcap)"; then
  echo "[TEST] No CIC PCAP found under data/pcap or data/pcap_CIC_IDS2017" >&2
  echo "[TEST] To create small demo samples, run: ./scripts/test/create_cic_pcap_samples.sh" >&2
  exit 1
fi

if ! curl -sS --connect-timeout 5 --max-time 10 "${GATEWAY_BASE_URL}/health" >/dev/null; then
  echo "[TEST] Gateway not reachable at ${GATEWAY_BASE_URL}" >&2
  exit 1
fi

PCAP_SIZE="$(wc -c <"$PCAP_PATH" | tr -d ' ')"
if [[ "$PCAP_SIZE" -le 0 ]]; then
  echo "[TEST] PCAP is empty: ${PCAP_PATH}" >&2
  exit 1
fi

UPLOAD_FILENAME="$(basename "$PCAP_PATH")"
if [[ "$PCAP_PATH" == data/samples/pcap/cic_attack_sample.pcap && -L "$PCAP_PATH" ]]; then
  SAMPLE_TARGET="$(readlink "$PCAP_PATH")"
  UPLOAD_FILENAME="$(basename "$SAMPLE_TARGET")"
fi

echo "[TEST] uploading real CIC PCAP to gateway"
echo "[TEST] uploaded PCAP path: ${PCAP_PATH}"
echo "[TEST] upload filename: ${UPLOAD_FILENAME}"
if [[ "$PCAP_PATH" != data/samples/pcap/* ]]; then
  echo "[TEST] WARNING: using a full CIC PCAP because data/samples/pcap/cic_attack_sample.pcap was not found."
  echo "[TEST] Create small samples with: ./scripts/test/create_cic_pcap_samples.sh"
fi
curl -sS --connect-timeout 5 --max-time 60 \
  -X POST "${GATEWAY_BASE_URL}/upload-pcap" \
  -H "x-api-key: dev-secret" \
  -F tenant_id=tenant_A \
  -F source_id=source_1 \
  -F file_epoch="real_cic_${TIMESTAMP}" \
  -F start_offset=0 \
  -F end_offset="${PCAP_SIZE}" \
  -F file=@"$PCAP_PATH;filename=${UPLOAD_FILENAME}"

printf '\n[TEST] expected Kafka topic: raw.tenant.tenant_A\n'
printf '[TEST] Spark should resolve this PCAP to a CICFlowMeter CSV and print evidence logs.\n'
printf '[TEST] Alert page URL: %s/alerts/tenant_A/view\n' "$WEBHOOK_BASE_URL"
