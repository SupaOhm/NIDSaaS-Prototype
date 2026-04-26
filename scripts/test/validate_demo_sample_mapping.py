#!/usr/bin/env python3
"""Validate deterministic CIC demo sample mapping and label-based decisions."""

from __future__ import annotations

import os
import sys
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nidsaas.detection.demo_inference_adapter import run_demo_ids_inference


SAMPLES = {
    "benign": {
        "path": "data/samples/pcap/cic_benign_sample.pcap",
        "required": True,
        "expected_prediction": "benign",
    },
    "ddos": {
        "path": "data/samples/pcap/cic_ddos_sample.pcap",
        "required": False,
        "expected_prediction": "attack",
    },
    "portscan": {
        "path": "data/samples/pcap/cic_portscan_sample.pcap",
        "required": False,
        "expected_prediction": "attack",
    },
    "webattack": {
        "path": "data/samples/pcap/cic_webattack_sample.pcap",
        "required": False,
        "expected_prediction": "attack_if_labels",
    },
    "infiltration": {
        "path": "data/samples/pcap/cic_infiltration_sample.pcap",
        "required": False,
        "expected_prediction": "attack_if_labels",
    },
}


def _fail(message: str) -> None:
    raise SystemExit(f"[VALIDATE] {message}")


def _validate_result(category: str, result: dict, expected_prediction: str) -> None:
    prediction = result.get("prediction")
    attack_type = result.get("attack_type")
    evidence = result.get("evidence", {})
    attack_label_count = int(evidence.get("attack_label_count") or 0)
    matched_csv = evidence.get("matched_flow_csv_path", "")

    print(
        f"[VALIDATE] {category}: prediction={prediction} "
        f"attack_type={attack_type} attack_label_count={attack_label_count} "
        f"csv={matched_csv}"
    )

    if prediction == "attack" and str(attack_type).strip().upper() == "BENIGN":
        _fail(f"{category} returned prediction=attack with attack_type=BENIGN")

    if expected_prediction == "benign" and prediction != "benign":
        _fail(f"{category} expected benign prediction, got {prediction}")
    if expected_prediction == "attack" and prediction != "attack":
        _fail(f"{category} expected attack prediction, got {prediction}")

    if expected_prediction == "attack_if_labels":
        expected = "attack" if attack_label_count > 0 else "benign"
        if prediction != expected:
            _fail(
                f"{category} expected {expected} prediction for "
                f"attack_label_count={attack_label_count}, got {prediction}"
            )

    if prediction == "attack" and attack_label_count == 0:
        _fail(f"{category} returned attack with attack_label_count=0")


def _report_hashes(existing_samples: dict[str, Path]) -> None:
    hashes: dict[str, str] = {}
    for category, path in existing_samples.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"[VALIDATE] {category}: sha256={digest}")
        if digest in hashes:
            print(
                f"[VALIDATE] broad-source duplicate PCAP content: {hashes[digest]} and {category} "
                f"share sha256={digest}"
            )
            continue
        hashes[digest] = category


def main() -> int:
    os.environ.pop("DEMO_FORCE_ATTACK", None)
    existing_samples: dict[str, Path] = {}

    for category, config in SAMPLES.items():
        sample_path = PROJECT_ROOT / str(config["path"])
        if not sample_path.exists():
            if config["required"]:
                _fail(f"required sample missing: {sample_path}")
            print(f"[VALIDATE] {category}: sample missing, skipping")
            continue

        existing_samples[category] = sample_path
        result = run_demo_ids_inference(
            tenant_id="validation",
            source_id=category,
            file_path=str(sample_path),
        )
        _validate_result(category, result, str(config["expected_prediction"]))

    _report_hashes(existing_samples)
    print("[VALIDATE] demo sample mapping checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
