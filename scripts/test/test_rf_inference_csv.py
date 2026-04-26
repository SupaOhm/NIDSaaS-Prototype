#!/usr/bin/env python3
"""Run inference-only RF scoring on a CICFlowMeter-compatible flow CSV."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nidsaas.detection.rf_inference_adapter import run_rf_inference_on_flow_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("flow_csv_path")
    parser.add_argument(
        "--artifact-path",
        default="outputs/offline_adapter_test/rf_anomaly.joblib",
    )
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument(
        "--file-attack-ratio-threshold",
        type=float,
        default=0.20,
    )
    args = parser.parse_args()

    result = run_rf_inference_on_flow_csv(
        flow_csv_path=args.flow_csv_path,
        artifact_path=args.artifact_path,
        max_rows=args.max_rows,
        file_attack_ratio_threshold=args.file_attack_ratio_threshold,
    )

    if result.get("status") == "success":
        ratio = float(result.get("attack_ratio", 0.0)) * 100.0
        threshold_ratio = float(result.get("file_attack_ratio_threshold", 0.0)) * 100.0
        print(f"attack_ratio={ratio:.2f}% file_threshold={threshold_ratio:.2f}%")

    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
