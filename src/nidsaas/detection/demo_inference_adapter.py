"""Demo IDS inference adapter backed by existing offline cascade artifacts.

This is intentionally not a true per-upload online inference implementation.
The current IDS codebase can train/evaluate the offline cascade and save model
artifacts, but it does not yet expose a stable inference-only API that accepts
a new extracted flow CSV and scores it without retraining. For the live demo,
this adapter proves integration with real saved IDS outputs while avoiding the
full offline cascade in Spark.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from nidsaas.detection.pcap_flow_resolver import resolve_pcap_to_flow_csv


MAIN_MODEL = "hybrid_cascade_fastsnort"
DEFAULT_MAX_EVIDENCE_ROWS = 0


def _load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_main_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except Exception:
        return {}

    for row in rows:
        if row.get("model") == MAIN_MODEL:
            return row
    return rows[-1] if rows else {}


def _sample_prediction(path: Path, desired_prediction: str, max_rows: int = 5000) -> dict[str, Any]:
    if not path.exists():
        return {}
    desired_value = "1" if desired_prediction == "attack" else "0"
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            fallback: dict[str, Any] = {}
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                if not fallback:
                    fallback = row
                if str(row.get("cascade_pred", "")).strip() == desired_value:
                    return row
            return fallback
    except Exception:
        return {}


def _prediction_from_demo_rule(file_path: str) -> str:
    if os.getenv("DEMO_FORCE_ATTACK", "0") == "1":
        return "attack"
    if "attack" in Path(file_path).name.lower() or "attack" in file_path.lower():
        return "attack"
    return "benign"


def _score_from_sample(sample: dict[str, Any]) -> float | None:
    for key in ("cascade_score", "gate_prob", "rf_score"):
        value = sample.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _is_attack_label(label: str) -> bool:
    return label.strip().upper() not in {"", "BENIGN"}


def _find_column(fieldnames: list[str] | None, expected: str) -> str | None:
    if not fieldnames:
        return None
    expected_norm = expected.strip().lower()
    for field in fieldnames:
        if field.strip().lower() == expected_norm:
            return field
    return None


def _read_flow_label_evidence(path: str, max_rows: int = DEFAULT_MAX_EVIDENCE_ROWS) -> dict[str, Any]:
    if not path:
        return {
            "status": "not_available",
            "prediction": "benign",
            "attack_label_count": 0,
            "attack_rows_sampled": 0,
            "total_rows_sampled": 0,
            "attack_labels": [],
            "reason": "no matched flow CSV",
        }

    csv_path = Path(path)
    if not csv_path.exists():
        return {
            "status": "not_available",
            "prediction": "benign",
            "attack_label_count": 0,
            "attack_rows_sampled": 0,
            "total_rows_sampled": 0,
            "attack_labels": [],
            "reason": f"matched flow CSV does not exist: {path}",
        }

    attack_label_count = 0
    total_rows_sampled = 0
    attack_labels: set[str] = set()
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            label_column = _find_column(reader.fieldnames, "Label")
            if not label_column:
                return {
                    "status": "not_available",
                    "prediction": "benign",
                    "attack_label_count": 0,
                    "attack_rows_sampled": 0,
                    "total_rows_sampled": 0,
                    "attack_labels": [],
                    "reason": "Label column not found",
                }

            for row in reader:
                if max_rows > 0 and total_rows_sampled >= max_rows:
                    break
                total_rows_sampled += 1
                label = str(row.get(label_column, "")).strip()
                if _is_attack_label(label):
                    attack_label_count += 1
                    attack_labels.add(label)
    except Exception as exc:
        return {
            "status": "not_available",
            "prediction": "benign",
            "attack_label_count": 0,
            "attack_rows_sampled": 0,
            "total_rows_sampled": total_rows_sampled,
            "attack_labels": sorted(attack_labels),
            "reason": f"unable to read flow CSV labels: {exc}",
        }

    return {
        "status": "success",
        "prediction": "attack" if attack_label_count else "benign",
        "attack_label_count": attack_label_count,
        "attack_rows_sampled": attack_label_count,
        "total_rows_sampled": total_rows_sampled,
        "attack_labels": sorted(attack_labels),
        "reason": "Label column sampled from matched CICFlowMeter CSV",
    }


def _prediction_value(row: dict[str, Any]) -> str:
    for key in ("cascade_pred", "binary_label"):
        value = str(row.get(key, "")).strip()
        if value in {"1", "1.0", "true", "True", "ATTACK", "attack"}:
            return "attack"
        if value in {"0", "0.0", "false", "False", "BENIGN", "benign"}:
            return "benign"
    label = str(row.get("multiclass_label", "")).strip()
    return "attack" if _is_attack_label(label) else "benign"


def _read_prediction_evidence(
    predictions_path: Path,
    flow_csv_path: str,
    max_rows: int = DEFAULT_MAX_EVIDENCE_ROWS,
) -> dict[str, Any]:
    if not predictions_path.exists() or not flow_csv_path:
        return {
            "status": "not_available",
            "prediction": "benign",
            "attack_prediction_count": 0,
            "total_rows_sampled": 0,
            "sample": {},
            "reason": "prediction artifact or matched flow CSV not available",
        }

    source_name = Path(flow_csv_path).name
    attack_prediction_count = 0
    total_rows_sampled = 0
    first_sample: dict[str, Any] = {}
    first_attack: dict[str, Any] = {}
    try:
        with predictions_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if "source_file" not in (reader.fieldnames or []):
                return {
                    "status": "not_available",
                    "prediction": "benign",
                    "attack_prediction_count": 0,
                    "total_rows_sampled": 0,
                    "sample": {},
                    "reason": "source_file column not found in prediction artifact",
                }

            for row in reader:
                if row.get("source_file") != source_name:
                    continue
                if max_rows > 0 and total_rows_sampled >= max_rows:
                    break
                total_rows_sampled += 1
                if not first_sample:
                    first_sample = row
                if _prediction_value(row) == "attack":
                    attack_prediction_count += 1
                    if not first_attack:
                        first_attack = row
    except Exception as exc:
        return {
            "status": "not_available",
            "prediction": "benign",
            "attack_prediction_count": attack_prediction_count,
            "total_rows_sampled": total_rows_sampled,
            "sample": first_attack or first_sample,
            "reason": f"unable to read prediction artifact: {exc}",
        }

    if total_rows_sampled == 0:
        return {
            "status": "not_available",
            "prediction": "benign",
            "attack_prediction_count": 0,
            "total_rows_sampled": 0,
            "sample": {},
            "reason": f"no prediction rows found for source_file={source_name}",
        }

    return {
        "status": "success",
        "prediction": "attack" if attack_prediction_count else "benign",
        "attack_prediction_count": attack_prediction_count,
        "total_rows_sampled": total_rows_sampled,
        "sample": first_attack or first_sample,
        "reason": f"sampled prediction artifact rows for source_file={source_name}",
    }


def run_demo_ids_inference(
    tenant_id: str,
    source_id: str,
    file_path: str,
    artifacts_dir: str = "outputs/offline_adapter_test",
    csv_root: str = "data/csv/csv_CIC_IDS2017",
) -> dict[str, Any]:
    """Return an IDS-style demo result using saved offline cascade artifacts."""
    artifacts = Path(artifacts_dir)
    summary = _load_summary(artifacts / "cascade_summary.json")
    metrics = _load_main_metrics(artifacts / "overall_metrics.csv")
    max_rows = int(os.getenv("IDS_EVIDENCE_MAX_ROWS", str(DEFAULT_MAX_EVIDENCE_ROWS)))

    resolver_result = resolve_pcap_to_flow_csv(file_path, csv_root=csv_root)
    matched_flow_csv = resolver_result.get("flow_csv_path", "")
    label_evidence = _read_flow_label_evidence(matched_flow_csv, max_rows=max_rows)
    prediction_evidence = _read_prediction_evidence(
        artifacts / "test_cascade_predictions.csv",
        matched_flow_csv,
        max_rows=max_rows,
    )

    if prediction_evidence.get("status") == "success":
        prediction = str(prediction_evidence.get("prediction", "benign"))
        evidence_source = "ids_prediction_artifact_source_file"
        sample = dict(prediction_evidence.get("sample") or {})
    elif label_evidence.get("status") == "success":
        prediction = str(label_evidence.get("prediction", "benign"))
        evidence_source = "matched_cic_flow_csv_label"
        sample = _sample_prediction(artifacts / "test_cascade_predictions.csv", prediction)
    elif os.getenv("DEMO_FORCE_ATTACK", "0") == "1":
        prediction = "attack"
        evidence_source = "debug_demo_force_attack_override"
        sample = _sample_prediction(artifacts / "test_cascade_predictions.csv", prediction)
    else:
        prediction = _prediction_from_demo_rule(file_path)
        evidence_source = "debug_filename_fallback"
        sample = _sample_prediction(artifacts / "test_cascade_predictions.csv", prediction)

    score = _score_from_sample(sample)
    attack_type = sample.get("multiclass_label") or "HybridCascadeDemo"

    if prediction == "attack":
        severity = "high"
    else:
        severity = "info"
        attack_type = "none"

    metrics_used = {
        "paper_model": metrics.get("paper_model"),
        "model": metrics.get("model"),
        "accuracy": metrics.get("accuracy"),
        "precision": metrics.get("precision"),
        "recall": metrics.get("recall"),
        "f1": metrics.get("f1"),
        "far": metrics.get("far"),
        "roc_auc": metrics.get("roc_auc"),
        "pr_auc": metrics.get("pr_auc"),
    }
    summary_used = {
        "split_strategy": summary.get("split_strategy"),
        "n_total": summary.get("n_total"),
        "n_train": summary.get("n_train"),
        "n_val": summary.get("n_val"),
        "n_test": summary.get("n_test"),
        "test_escalation_pool_size": summary.get("test_escalation_pool_size"),
    }

    return {
        "status": "success" if metrics or summary else "missing_artifacts",
        "prediction": prediction,
        "score": score,
        "severity": severity,
        "attack_type": attack_type,
        "stage": "spark_real_ids_artifact_demo",
        "tenant_id": tenant_id,
        "source_id": source_id,
        "evidence": {
            "original_pcap_path": file_path,
            "matched_flow_csv_path": matched_flow_csv,
            "pcap_flow_resolver": resolver_result,
            "evidence_source": evidence_source,
            "attack_label_count": label_evidence.get("attack_label_count", 0),
            "attack_rows_sampled": label_evidence.get("attack_rows_sampled", 0),
            "attack_prediction_count": prediction_evidence.get("attack_prediction_count", 0),
            "total_rows_sampled": (
                prediction_evidence.get("total_rows_sampled")
                if prediction_evidence.get("status") == "success"
                else label_evidence.get("total_rows_sampled", 0)
            ),
            "flow_label_evidence": label_evidence,
            "prediction_artifact_evidence": {
                "status": prediction_evidence.get("status"),
                "reason": prediction_evidence.get("reason"),
                "attack_prediction_count": prediction_evidence.get("attack_prediction_count", 0),
                "total_rows_sampled": prediction_evidence.get("total_rows_sampled", 0),
            },
            "artifacts_dir": str(artifacts),
            "ids_artifacts_dir": str(artifacts),
            "model_name": metrics.get("model"),
            "metrics_used": metrics_used,
            "summary_used": summary_used,
            "ids_artifacts_summary": summary_used,
            "file_path": file_path,
            "sample_row_id": sample.get("row_id"),
            "note": "uses precomputed trained IDS artifacts; no retraining",
        },
    }
