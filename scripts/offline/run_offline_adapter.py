#!/usr/bin/env python3
"""Run the offline IDS cascade through the adapter wrapper."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nidsaas.detection.offline_adapter import run_offline_ids_on_flow_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline IDS adapter.")
    parser.add_argument("--data-dir", default=str(PROJECT_ROOT / "data/csv/csv_CIC_IDS2017"))
    parser.add_argument(
        "--signature-predictions",
        default=str(PROJECT_ROOT / "data/samples/signature_merged_predictions.csv"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs/offline_adapter"),
    )
    parser.add_argument("--rf-model", default=None)
    parser.add_argument("--alpha-escalate", type=float, default=0.20)
    parser.add_argument("--calibration-fraction", type=float, default=0.50)
    parser.add_argument(
        "--split-strategy",
        default="temporal_by_file",
        choices=["random", "temporal", "temporal_by_file"],
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    summary = run_offline_ids_on_flow_csv(
        data_dir=args.data_dir,
        signature_predictions_path=args.signature_predictions,
        output_dir=args.output_dir,
        rf_model_path=args.rf_model,
        alpha_escalate=args.alpha_escalate,
        calibration_fraction=args.calibration_fraction,
        split_strategy=args.split_strategy,
        seed=args.seed,
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
