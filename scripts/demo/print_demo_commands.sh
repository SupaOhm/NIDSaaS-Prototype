#!/usr/bin/env bash
set -euo pipefail

cat <<'COMMANDS'
Terminal 1 - Infra/services:
  ./scripts/demo/start_infra.sh
  ./scripts/demo/start_services.sh

Terminal 2 - Spark:
  ./scripts/demo/run_spark_processor.sh

Terminal 3 - Alert delivery:
  ./scripts/demo/run_alert_delivery.sh

Terminal 4 - Upload/test:
  ./scripts/demo/reset_demo_state.sh
  ./scripts/test/pcap_upload.sh -d data/samples/pcap/benign.pcap -t tenant_A
  ./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_A
COMMANDS
