"""Resolve CIC-IDS2017 PCAP names to matching CICFlowMeter CSVs.

The local demo supports direct CSV upload and PCAP upload. For CIC-IDS2017 PCAP
uploads, this resolver maps known sample names to the corresponding flow CSV so
Spark can run saved RF inference on CICFlowMeter-compatible features.
"""

from __future__ import annotations

import re
from pathlib import Path


SAMPLE_PCAP_CSV_MAP = {
    "cic_benign_sample.pcap": (
        "cic_benign_sample.csv",
        "Monday-WorkingHours.pcap_ISCX.csv",
    ),
    "cic_ddos_sample.pcap": (
        "cic_ddos_sample.csv",
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    ),
    "cic_portscan_sample.pcap": (
        "cic_portscan_sample.csv",
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    ),
    "cic_webattack_sample.pcap": (
        "cic_webattack_sample.csv",
        "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    ),
    "cic_infiltration_sample.pcap": (
        "cic_infiltration_sample.csv",
        "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    ),
}

SHORT_DEMO_PCAP_CSV_MAP = {
    "ddos.pcap": (
        "data/samples/csv/ddos.csv",
        "data/samples/csv/cic_ddos_true_sample.csv",
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    ),
    "portscan.pcap": (
        "data/samples/csv/portscan.csv",
        "data/samples/csv/cic_portscan_true_sample.csv",
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    ),
    "bot.pcap": (
        "data/samples/csv/bot.csv",
        "data/samples/csv/cic_bot_true_sample.csv",
        "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    ),
    "benign.pcap": (
        "data/samples/csv/benign.csv",
        "data/samples/csv/cic_benign_true_sample.csv",
        "Monday-WorkingHours.pcap_ISCX.csv",
    ),
    "webattack.pcap": (
        "data/samples/csv/webattack.csv",
        "data/samples/csv/cic_webattack_true_sample.csv",
        "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    ),
    "infiltration.pcap": (
        "data/samples/csv/infiltration.csv",
        "data/samples/csv/cic_infiltration_true_sample.csv",
        "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    ),
}


def _normalize_name(value: str) -> str:
    return (
        value.lower()
        .replace("_iscx.csv", "")
        .replace(".pcap", "")
        .replace("_", "-")
        .replace(" ", "")
    )


def _strip_gateway_prefix(pcap_name: str) -> str:
    return re.sub(r"^[0-9a-fA-F]{12}_", "", pcap_name).strip().lower()


def _first_existing(root: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = root / name
        if path.exists():
            return path
    return None


def _sample_csv_match(pcap_name: str, full_csv_root: Path) -> tuple[Path, str] | None:
    csv_names = SAMPLE_PCAP_CSV_MAP.get(pcap_name)
    if csv_names is None:
        return None

    sample_csv = Path("data/samples/csv") / csv_names[0]
    if sample_csv.exists():
        return sample_csv, "demo sample PCAP mapped to matching sample CSV"

    fallback_csv = full_csv_root / csv_names[1]
    if fallback_csv.exists():
        return fallback_csv, "demo sample PCAP mapped to exact full CICFlowMeter CSV fallback"
    return None


def _short_demo_csv_match(pcap_name: str, full_csv_root: Path) -> tuple[Path, str] | None:
    csv_names = SHORT_DEMO_PCAP_CSV_MAP.get(pcap_name)
    if csv_names is None:
        return None

    for csv_name in csv_names[:2]:
        sample_csv = Path(csv_name)
        if sample_csv.exists():
            return sample_csv, "short demo PCAP mapped to matching sample CSV"

    fallback_csv = full_csv_root / csv_names[2]
    if fallback_csv.exists():
        return fallback_csv, "short demo PCAP mapped to exact full CICFlowMeter CSV fallback"
    return None


def resolve_pcap_to_flow_csv(
    pcap_path: str,
    csv_root: str = "data/csv/csv_CIC_IDS2017",
) -> dict:
    """Map an uploaded CIC PCAP path to an existing CICFlowMeter CSV.

    The primary CIC-IDS2017 convention is:
    `Friday-WorkingHours-Afternoon-DDos.pcap` ->
    `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`.

    Some local demo PCAPs are broader day-level captures, for example
    `Friday-WorkingHours.pcap`; for those, this function falls back to the
    best prefix match and prefers attack-specific CSVs for demo visibility.
    """
    pcap = Path(pcap_path)
    root = Path(csv_root)
    pcap_name = _strip_gateway_prefix(pcap.name)

    if not pcap_name:
        return {
            "status": "not_found",
            "pcap_path": pcap_path,
            "flow_csv_path": "",
            "reason": "empty PCAP basename",
        }

    sample_match = _sample_csv_match(pcap_name, root)
    if sample_match is not None:
        csv_path, reason = sample_match
        return {
            "status": "matched",
            "pcap_path": pcap_path,
            "flow_csv_path": str(csv_path),
            "reason": reason,
        }

    short_demo_match = _short_demo_csv_match(pcap_name, root)
    if short_demo_match is not None:
        csv_path, reason = short_demo_match
        return {
            "status": "matched",
            "pcap_path": pcap_path,
            "flow_csv_path": str(csv_path),
            "reason": reason,
        }

    if not root.exists():
        return {
            "status": "not_found",
            "pcap_path": pcap_path,
            "flow_csv_path": "",
            "reason": f"CSV root not found: {csv_root}",
        }

    return {
        "status": "not_found",
        "pcap_path": pcap_path,
        "flow_csv_path": "",
        "reason": f"no exact CICFlowMeter CSV mapping matched {pcap_name} under {csv_root}",
    }
