"""Live PCAP-to-flow extraction for demo uploads."""

from __future__ import annotations

import csv
import hashlib
import os
import shlex
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "outputs/live_flows"


@dataclass
class ExtractionResult:
    status: str
    tool: str
    input_pcap_path: str
    extracted_flow_csv_path: str
    number_of_flows: int
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "tool": self.tool,
            "input_pcap_path": self.input_pcap_path,
            "extracted_flow_csv_path": self.extracted_flow_csv_path,
            "number_of_flows": self.number_of_flows,
            "reason": self.reason,
        }


def _safe_stem(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]
    return f"{path.stem}_{digest}"


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def _run_cicflowmeter_command(
    pcap_path: Path,
    output_dir: Path,
    output_csv: Path,
) -> ExtractionResult | None:
    configured = os.getenv("CICFLOWMETER_CMD", "").strip()
    jar = os.getenv("CICFLOWMETER_JAR", "").strip()
    command: list[str] | None = None

    if configured:
        command = [
            part.format(
                pcap=str(pcap_path),
                output=str(output_csv),
                output_dir=str(output_dir),
            )
            for part in shlex.split(configured)
        ]
    elif jar:
        jar_path = Path(jar)
        if not jar_path.exists():
            raise RuntimeError(f"CICFLOWMETER_JAR does not exist: {jar}")
        command = ["java", "-jar", str(jar_path), str(pcap_path), str(output_dir)]
    elif shutil.which("cicflowmeter"):
        command = ["cicflowmeter", "-f", str(pcap_path), "-c", str(output_dir)]

    if command is None:
        return None

    before = set(output_dir.glob("*.csv"))
    subprocess.run(command, check=True, capture_output=True, text=True)

    if output_csv.exists():
        extracted = output_csv
    else:
        after = set(output_dir.glob("*.csv"))
        candidates = sorted(after - before, key=lambda item: item.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError("CICFlowMeter completed but produced no CSV output")
        extracted = candidates[0]
        if extracted != output_csv:
            output_csv.write_bytes(extracted.read_bytes())

    return ExtractionResult(
        status="success",
        tool="cicflowmeter",
        input_pcap_path=str(pcap_path),
        extracted_flow_csv_path=str(output_csv),
        number_of_flows=_count_csv_rows(output_csv),
    )


def _packet_rows_from_tshark(pcap_path: Path) -> list[dict[str, str]]:
    tshark = shutil.which("tshark")
    if not tshark:
        raise RuntimeError(
            "No live flow extraction tool found. Set CICFLOWMETER_CMD, "
            "CICFLOWMETER_JAR, or install tshark."
        )

    command = [
        tshark,
        "-r",
        str(pcap_path),
        "-T",
        "fields",
        "-E",
        "header=y",
        "-E",
        "separator=,",
        "-E",
        "quote=d",
        "-e",
        "frame.time_epoch",
        "-e",
        "ip.src",
        "-e",
        "ip.dst",
        "-e",
        "ip.proto",
        "-e",
        "tcp.srcport",
        "-e",
        "tcp.dstport",
        "-e",
        "udp.srcport",
        "-e",
        "udp.dstport",
        "-e",
        "frame.len",
        "-e",
        "tcp.flags.syn",
        "-e",
        "tcp.flags.ack",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    lines = completed.stdout.splitlines()
    if not lines:
        return []
    return list(csv.DictReader(lines))


def _field(row: dict[str, str], name: str) -> str:
    return str(row.get(name, "")).strip()


def _int_field(row: dict[str, str], name: str) -> int:
    value = _field(row, name)
    try:
        return int(float(value))
    except ValueError:
        return 0


def _float_field(row: dict[str, str], name: str) -> float:
    value = _field(row, name)
    try:
        return float(value)
    except ValueError:
        return 0.0


def _write_tshark_flows(pcap_path: Path, output_csv: Path) -> ExtractionResult:
    packets = _packet_rows_from_tshark(pcap_path)
    flows: dict[tuple[str, str, str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "start_time": 0.0,
            "end_time": 0.0,
            "packet_count": 0,
            "byte_count": 0,
            "syn_count": 0,
            "ack_count": 0,
        }
    )

    for row in packets:
        src_ip = _field(row, "ip.src")
        dst_ip = _field(row, "ip.dst")
        proto = _field(row, "ip.proto")
        if not src_ip or not dst_ip or not proto:
            continue
        src_port = _field(row, "tcp.srcport") or _field(row, "udp.srcport") or "0"
        dst_port = _field(row, "tcp.dstport") or _field(row, "udp.dstport") or "0"
        key = (src_ip, dst_ip, src_port, dst_port, proto)
        timestamp = _float_field(row, "frame.time_epoch")
        flow = flows[key]
        if flow["packet_count"] == 0:
            flow["start_time"] = timestamp
            flow["end_time"] = timestamp
        else:
            flow["start_time"] = min(flow["start_time"], timestamp)
            flow["end_time"] = max(flow["end_time"], timestamp)
        flow["packet_count"] += 1
        flow["byte_count"] += _int_field(row, "frame.len")
        if _int_field(row, "tcp.flags.syn") == 1:
            flow["syn_count"] += 1
        if _int_field(row, "tcp.flags.ack") == 1:
            flow["ack_count"] += 1

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "flow_id",
        "src_ip",
        "dst_ip",
        "src_port",
        "dst_port",
        "protocol",
        "start_time",
        "end_time",
        "duration_sec",
        "packet_count",
        "byte_count",
        "syn_count",
        "ack_count",
        "packets_per_sec",
        "bytes_per_sec",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, (key, flow) in enumerate(flows.items(), start=1):
            duration = max(float(flow["end_time"]) - float(flow["start_time"]), 0.000001)
            packet_count = int(flow["packet_count"])
            byte_count = int(flow["byte_count"])
            writer.writerow(
                {
                    "flow_id": index,
                    "src_ip": key[0],
                    "dst_ip": key[1],
                    "src_port": key[2],
                    "dst_port": key[3],
                    "protocol": key[4],
                    "start_time": f"{float(flow['start_time']):.6f}",
                    "end_time": f"{float(flow['end_time']):.6f}",
                    "duration_sec": f"{duration:.6f}",
                    "packet_count": packet_count,
                    "byte_count": byte_count,
                    "syn_count": int(flow["syn_count"]),
                    "ack_count": int(flow["ack_count"]),
                    "packets_per_sec": f"{packet_count / duration:.6f}",
                    "bytes_per_sec": f"{byte_count / duration:.6f}",
                }
            )

    return ExtractionResult(
        status="success",
        tool="tshark_fallback",
        input_pcap_path=str(pcap_path),
        extracted_flow_csv_path=str(output_csv),
        number_of_flows=len(flows),
    )


def extract_flows_from_pcap(
    pcap_path: str,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Extract flow features from a PCAP and return metadata for the CSV output."""
    source = Path(pcap_path)
    if not source.exists():
        raise FileNotFoundError(f"PCAP not found: {pcap_path}")

    target_dir = Path(output_dir or os.getenv("LIVE_FLOW_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
    target_dir.mkdir(parents=True, exist_ok=True)
    output_csv = target_dir / f"{_safe_stem(source)}_flows.csv"

    cic_result = _run_cicflowmeter_command(source, target_dir, output_csv)
    if cic_result is not None:
        return cic_result.to_dict()
    return _write_tshark_flows(source, output_csv).to_dict()
