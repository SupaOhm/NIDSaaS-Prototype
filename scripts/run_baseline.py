#!/usr/bin/env python3
"""Run baseline entry points from the packaged detection modules."""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


BASELINE_MODULES = {
    "rf": "nidsaas.detection.rf_baseline_valcal",
    "rate": "nidsaas.detection.rate_rules_baseline_valcal",
    "anomaly": "nidsaas.detection.compare_anomaly_baselines_valcal",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an offline IDS baseline module.")
    parser.add_argument("baseline", choices=sorted(BASELINE_MODULES))
    args, passthrough = parser.parse_known_args()
    sys.argv = [f"run_baseline.py {args.baseline}", *passthrough]
    runpy.run_module(BASELINE_MODULES[args.baseline], run_name="__main__")


if __name__ == "__main__":
    main()
