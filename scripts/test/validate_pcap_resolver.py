#!/usr/bin/env python3
"""Validate short demo PCAP names resolve to the intended CICFlowMeter CSVs."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nidsaas.detection.pcap_flow_resolver import resolve_pcap_to_flow_csv


def _fail(message: str) -> None:
    raise SystemExit(f"[VALIDATE] {message}")


def _assert_match(pcap_name: str, expected_csv_name: str) -> None:
    result = resolve_pcap_to_flow_csv(pcap_name)
    flow_csv_path = result.get("flow_csv_path", "")
    status = result.get("status")
    print(
        f"[VALIDATE] {pcap_name}: status={status} flow_csv_path={flow_csv_path} reason={result.get('reason')}"
    )
    if status != "matched":
        _fail(f"{pcap_name} did not resolve to a CSV")
    if Path(flow_csv_path).name != expected_csv_name:
        _fail(
            f"{pcap_name} resolved to {Path(flow_csv_path).name}, expected {expected_csv_name}"
        )


def main() -> int:
    cases = {
        "122e53b44d8b_ddos.pcap": "ddos.csv",
        "4e34bbaa46fd_benign.pcap": "benign.csv",
        "720620826e7a_bot.pcap": "bot.csv",
    }

    for pcap_name, expected_csv_name in cases.items():
        _assert_match(pcap_name, expected_csv_name)

    unknown = resolve_pcap_to_flow_csv("random_unknown.pcap")
    print(
        f"[VALIDATE] random_unknown.pcap: status={unknown.get('status')} reason={unknown.get('reason')}"
    )
    if unknown.get("status") != "not_found":
        _fail("random_unknown.pcap should return not_found")

    print("[VALIDATE] pcap resolver checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
