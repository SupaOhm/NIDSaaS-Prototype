"""Resolve CIC-IDS2017 PCAP names to pre-extracted CICFlowMeter CSVs.

Live CICFlowMeter extraction is not part of the current demo runtime. This
resolver bridges a real CIC PCAP upload to the corresponding checked-in
CICFlowMeter CSV so Spark can use real flow labels and saved IDS evidence.
"""

from __future__ import annotations

import re
from pathlib import Path


ATTACK_NAME_HINTS = (
    "ddos",
    "portscan",
    "infilteration",
    "webattacks",
    "webattack",
    "bot",
    "bruteforce",
    "heartbleed",
)


def _normalize_name(value: str) -> str:
    return (
        value.lower()
        .replace("_iscx.csv", "")
        .replace(".pcap", "")
        .replace("_", "-")
        .replace(" ", "")
    )


def _candidate_score(pcap_name: str, csv_path: Path) -> tuple[int, str]:
    pcap_norm = _normalize_name(pcap_name)
    csv_norm = _normalize_name(csv_path.name)
    score = 0

    if csv_path.name == f"{pcap_name}_ISCX.csv":
        score += 1000
    if csv_norm == pcap_norm:
        score += 800
    if csv_norm.startswith(pcap_norm):
        score += 500
    if pcap_norm.startswith(csv_norm):
        score += 250
    if any(hint in csv_norm for hint in ATTACK_NAME_HINTS):
        score += 50

    return score, csv_path.name


def _pcap_name_candidates(pcap_name: str) -> list[str]:
    candidates = [pcap_name]
    stripped = re.sub(r"^[0-9a-fA-F]{12}_", "", pcap_name)
    if stripped != pcap_name:
        candidates.append(stripped)
    return candidates


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
    pcap_name = pcap.name
    pcap_candidates = _pcap_name_candidates(pcap_name)

    if not pcap_name:
        return {
            "status": "not_found",
            "pcap_path": pcap_path,
            "flow_csv_path": "",
            "reason": "empty PCAP basename",
        }

    if not root.exists():
        return {
            "status": "not_found",
            "pcap_path": pcap_path,
            "flow_csv_path": "",
            "reason": f"CSV root not found: {csv_root}",
        }

    for candidate_name in pcap_candidates:
        exact = root / f"{candidate_name}_ISCX.csv"
        if exact.exists():
            return {
                "status": "matched",
                "pcap_path": pcap_path,
                "flow_csv_path": str(exact),
                "reason": f"exact CICFlowMeter CSV match for {candidate_name}",
            }

    csv_files = sorted(root.glob("*.csv"))
    scored = []
    for candidate_name in pcap_candidates:
        for csv_path in csv_files:
            score = _candidate_score(candidate_name, csv_path)
            if score[0] > 0:
                scored.append((score, candidate_name, csv_path))
    if scored:
        scored.sort(key=lambda item: item[0], reverse=True)
        best_candidate = scored[0][1]
        best = scored[0][2]
        return {
            "status": "matched",
            "pcap_path": pcap_path,
            "flow_csv_path": str(best),
            "reason": f"prefix/normalized CICFlowMeter CSV match for {best_candidate}",
        }

    return {
        "status": "not_found",
        "pcap_path": pcap_path,
        "flow_csv_path": "",
        "reason": f"no CICFlowMeter CSV matched {pcap_name} under {csv_root}",
    }
