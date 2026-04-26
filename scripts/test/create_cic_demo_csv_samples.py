#!/usr/bin/env python3
"""Create small labeled CIC-IDS2017 CSV samples for demo uploads."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


SAMPLES = {
    "benign": {
        "source": "Monday-WorkingHours.pcap_ISCX.csv",
        "output": "cic_benign_sample.csv",
        "labels": ("BENIGN",),
        "prefer_attack": False,
        "required": True,
    },
    "ddos": {
        "source": "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
        "output": "cic_ddos_sample.csv",
        "labels": ("DDoS",),
        "prefer_attack": True,
        "required": True,
    },
    "portscan": {
        "source": "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
        "output": "cic_portscan_sample.csv",
        "labels": ("PortScan",),
        "prefer_attack": True,
        "required": True,
    },
    "webattack": {
        "source": "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
        "output": "cic_webattack_sample.csv",
        "labels": ("Web Attack",),
        "prefer_attack": True,
        "required": True,
    },
    "infiltration": {
        "source": "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
        "output": "cic_infiltration_sample.csv",
        "labels": ("Infiltration",),
        "prefer_attack": True,
        "required": False,
    },
}


def _label_column(fieldnames: list[str]) -> str:
    for name in fieldnames:
        if name.strip().lower() == "label":
            return name
    raise ValueError("source CSV has no Label column")


def _matches_label(label: str, wanted: tuple[str, ...], prefer_attack: bool) -> bool:
    normalized = label.strip()
    if prefer_attack:
        return normalized != "BENIGN" and any(part in normalized for part in wanted)
    return normalized in wanted


def create_sample(
    *,
    category: str,
    source_path: Path,
    output_path: Path,
    labels: tuple[str, ...],
    prefer_attack: bool,
    max_rows: int,
) -> None:
    selected: list[dict[str, str]] = []
    distribution: Counter[str] = Counter()

    with source_path.open(newline="", encoding="cp1252") as source_file:
        reader = csv.DictReader(source_file)
        if reader.fieldnames is None:
            raise ValueError(f"{source_path} is empty or missing a header")
        fieldnames = reader.fieldnames
        label_column = _label_column(fieldnames)

        for row in reader:
            label = row.get(label_column, "").strip()
            if _matches_label(label, labels, prefer_attack):
                selected.append(row)
                distribution[label] += 1
                if len(selected) >= max_rows:
                    break

    if not selected:
        raise ValueError(
            f"{source_path} contains no rows matching {category} labels: {', '.join(labels)}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    print(f"[CSV] {category}: {source_path} -> {output_path}")
    print(f"[CSV] {category}: wrote {len(selected)} rows")
    print(f"[CSV] {category}: label distribution")
    for label, count in distribution.most_common():
        print(f"[CSV]   {label}: {count}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-root", default="data/csv/csv_CIC_IDS2017")
    parser.add_argument("--output-dir", default="data/samples/csv")
    parser.add_argument("--max-rows", type=int, default=5000)
    args = parser.parse_args()

    csv_root = Path(args.csv_root)
    output_dir = Path(args.output_dir)

    if args.max_rows <= 0:
        raise SystemExit("[CSV] --max-rows must be positive")
    if not csv_root.is_dir():
        raise SystemExit(f"[CSV] source CSV root not found: {csv_root}")

    for category, config in SAMPLES.items():
        source_path = csv_root / str(config["source"])
        if not source_path.is_file():
            message = f"[CSV] source CSV missing for {category}: {source_path}"
            if config["required"]:
                raise SystemExit(message)
            print(f"{message}; skipping optional sample")
            continue

        create_sample(
            category=category,
            source_path=source_path,
            output_path=output_dir / str(config["output"]),
            labels=tuple(config["labels"]),
            prefer_attack=bool(config["prefer_attack"]),
            max_rows=args.max_rows,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
