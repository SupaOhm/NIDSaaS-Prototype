#!/usr/bin/env python3
"""Run Snort utility modules from the packaged snort namespace."""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


SNORT_MODULES = {
    "runner": "nidsaas.snort.runner",
    "parser": "nidsaas.snort.parser",
    "policy-filter": "nidsaas.snort.policy_filter",
    "evaluator": "nidsaas.snort.evaluator",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Snort helper module.")
    parser.add_argument("tool", choices=sorted(SNORT_MODULES))
    args, passthrough = parser.parse_known_args()
    sys.argv = [f"run_snort.py {args.tool}", *passthrough]
    runpy.run_module(SNORT_MODULES[args.tool], run_name="__main__")


if __name__ == "__main__":
    main()
