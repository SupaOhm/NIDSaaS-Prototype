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


MAIN_MODEL = "hybrid_cascade_fastsnort"


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


def run_demo_ids_inference(
    tenant_id: str,
    source_id: str,
    file_path: str,
    artifacts_dir: str = "outputs/offline_adapter_test",
) -> dict[str, Any]:
    """Return an IDS-style demo result using saved offline cascade artifacts."""
    artifacts = Path(artifacts_dir)
    summary = _load_summary(artifacts / "cascade_summary.json")
    metrics = _load_main_metrics(artifacts / "overall_metrics.csv")

    prediction = _prediction_from_demo_rule(file_path)
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
            "artifacts_dir": str(artifacts),
            "metrics_used": metrics_used,
            "summary_used": {
                "split_strategy": summary.get("split_strategy"),
                "n_total": summary.get("n_total"),
                "n_train": summary.get("n_train"),
                "n_val": summary.get("n_val"),
                "n_test": summary.get("n_test"),
                "test_escalation_pool_size": summary.get("test_escalation_pool_size"),
            },
            "file_path": file_path,
            "sample_row_id": sample.get("row_id"),
            "note": "uses precomputed trained IDS artifacts; no retraining",
        },
    }
