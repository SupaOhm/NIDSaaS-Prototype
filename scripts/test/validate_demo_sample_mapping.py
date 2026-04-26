#!/usr/bin/env python3
"""Validate mined CIC demo PCAP samples against live flow classification."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nidsaas.detection.demo_inference_adapter import run_demo_ids_inference
from nidsaas.detection.live_flow_extractor import extract_flows_from_pcap


SAMPLES = {
    "benign": {
        "path": "data/samples/pcap/cic_benign_sample.pcap",
        "required": True,
        "expected_prediction": "benign",
    },
    "highrate": {
        "path": "data/samples/pcap/cic_highrate_sample.pcap",
        "required": False,
        "expected_prediction": "attack",
    },
    "portscan": {
        "path": "data/samples/pcap/cic_portscan_sample.pcap",
        "required": False,
        "expected_prediction": "attack",
    },
    "ddos": {
        "path": "data/samples/pcap/cic_ddos_sample.pcap",
        "required": False,
        "expected_prediction": "attack",
    },
    "webattack": {
        "path": "data/samples/pcap/cic_webattack_sample.pcap",
        "required": False,
        "expected_prediction": "attack",
    },
    "infiltration": {
        "path": "data/samples/pcap/cic_infiltration_sample.pcap",
        "required": False,
        "expected_prediction": "attack",
    },
}


def _fail(message: str) -> None:
    raise SystemExit(f"[VALIDATE] {message}")


def _classify_sample(category: str, sample_path: Path) -> dict:
    extraction = extract_flows_from_pcap(str(sample_path))
    result = run_demo_ids_inference(
        tenant_id="validation",
        source_id=category,
        file_path=str(sample_path),
        extracted_flow_csv_path=extraction["extracted_flow_csv_path"],
        extraction_metadata=extraction,
    )
    return result


def _validate_result(category: str, sample_path: Path, result: dict, expected_prediction: str) -> None:
    prediction = result.get("prediction")
    attack_type = str(result.get("attack_type") or "")
    evidence = result.get("evidence", {})
    live = evidence.get("live_flow_rule_evidence", {})

    print(
        f"[VALIDATE] {category}: prediction={prediction} attack_type={attack_type} "
        f"flows={evidence.get('number_of_flows')} reason={evidence.get('detection_reason')}"
    )

    if evidence.get("evidence_source") != "live_extracted_flow_rules":
        _fail(f"{category} did not use live extracted flow rules")
    if prediction != expected_prediction:
        _fail(f"{category} expected {expected_prediction}, got {prediction}")
    if prediction == "attack" and attack_type.upper() == "BENIGN":
        _fail(f"{category} returned attack with attack_type=BENIGN")
    if prediction == "attack" and not live.get("detection_reason"):
        _fail(f"{category} attack result missing detection reason")
    if not sample_path.exists():
        _fail(f"{category} sample disappeared during validation")


def _validate_unique_hashes(existing_samples: dict[str, Path]) -> None:
    hashes: dict[str, str] = {}
    for category, path in existing_samples.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"[VALIDATE] {category}: sha256={digest}")
        if digest in hashes:
            _fail(
                f"duplicate PCAP content: {hashes[digest]} and {category} "
                f"share sha256={digest}"
            )
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
        result = _classify_sample(category, sample_path)
        _validate_result(category, sample_path, result, str(config["expected_prediction"]))

    _validate_unique_hashes(existing_samples)
    print("[VALIDATE] mined demo sample checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
