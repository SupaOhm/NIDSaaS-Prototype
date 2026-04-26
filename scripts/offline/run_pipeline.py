#!/usr/bin/env python3
"""Run the current offline Hybrid-Cascade IDS pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nidsaas.detection.hybrid_cascade_splitcal_fastsnort import run_cascade


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline NIDSaaS IDS pipeline.")
    parser.add_argument("--data-dir", default=str(PROJECT_ROOT / "data/csv/csv_CIC_IDS2017"))
    parser.add_argument(
        "--snort-predictions",
        default=str(PROJECT_ROOT / "data/samples/signature_merged_predictions.csv"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs/proposed_locked_a20_g50"),
    )
    parser.add_argument("--rf-model", default=None)
    parser.add_argument("--alpha-conformal", type=float, default=0.05)
    parser.add_argument("--alpha-escalate", type=float, default=0.20)
    parser.add_argument("--gate-threshold", type=float, default=0.5)
    parser.add_argument(
        "--split-strategy",
        default="temporal_by_file",
        choices=["random", "temporal", "temporal_by_file"],
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gate-max-iter", type=int, default=300)
    parser.add_argument("--calibration-fraction", type=float, default=0.50)
    parser.add_argument("--paper-model-name", default="Hybrid-Cascade-SplitCal-FastSnort")
    args = parser.parse_args()

    run_cascade(
        data_dir=args.data_dir,
        snort_predictions_path=args.snort_predictions,
        output_dir=args.output_dir,
        rf_model_path=args.rf_model,
        alpha_conformal=args.alpha_conformal,
        alpha_escalate=args.alpha_escalate,
        gate_threshold=args.gate_threshold,
        split_strategy=args.split_strategy,
        seed=args.seed,
        gate_max_iter=args.gate_max_iter,
        calibration_fraction=args.calibration_fraction,
        paper_model_name=args.paper_model_name,
    )


if __name__ == "__main__":
    main()
