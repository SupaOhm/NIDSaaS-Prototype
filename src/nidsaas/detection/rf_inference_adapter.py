from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from nidsaas.detection.utils import canonicalize_columns


REQUIRED_ARTIFACT_KEYS = {
    "feature_columns",
    "preprocessor",
    "svd",
    "rff",
    "rotations",
    "rf",
    "threshold",
}


def _error_result(
    flow_csv_path: str,
    feature_count: int,
    missing_columns: list[str],
    threshold: float | None,
    file_attack_ratio_threshold: float,
    message: str,
) -> dict[str, Any]:
    return {
        "status": "error",
        "flow_csv_path": flow_csv_path,
        "rows_scored": 0,
        "attack_ratio": 0.0,
        "file_attack_ratio_threshold": float(file_attack_ratio_threshold),
        "row_threshold": float(threshold) if threshold is not None else 0.0,
        "row_attack_count": 0,
        "row_benign_count": 0,
        "attack_count": 0,
        "benign_count": 0,
        "max_score": 0.0,
        "mean_score": 0.0,
        "threshold": float(threshold) if threshold is not None else 0.0,
        "prediction": "benign",
        "severity": "info",
        "missing_columns": missing_columns,
        "feature_count": int(feature_count),
        "evidence_source": "saved_rf_artifact_inference",
        "error": message,
    }


def _validate_artifact(payload: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "artifact payload is not a dict"

    missing_keys = sorted(REQUIRED_ARTIFACT_KEYS - set(payload.keys()))
    if missing_keys:
        return None, f"artifact missing required keys: {missing_keys}"

    feature_columns = payload.get("feature_columns")
    if not isinstance(feature_columns, list) or not feature_columns:
        return None, "artifact feature_columns must be a non-empty list"

    if payload.get("threshold") is None:
        return None, "artifact threshold is missing"

    return payload, None


def _to_dense(x: Any) -> np.ndarray:
    return x.toarray() if hasattr(x, "toarray") else np.asarray(x)


def _score_from_saved_components(
    x_features: pd.DataFrame,
    preprocessor: Any,
    svd: Any,
    rff: Any,
    rotations: np.ndarray,
    rf: Any,
) -> np.ndarray:
    x = preprocessor.transform(x_features)
    x = _to_dense(x)
    x = svd.transform(x)
    x = rff.transform(x)
    x = np.asarray(x, dtype=np.float32)

    normality_sum = np.zeros(x.shape[0], dtype=np.float32)

    for class_idx, rot in enumerate(rotations):
        x_rot = x @ rot
        probs = rf.predict_proba(x_rot)[:, class_idx]
        normality_sum += probs.astype(np.float32, copy=False)

    normality = normality_sum / len(rotations)
    anomaly_scores = 1.0 - normality
    return anomaly_scores.astype(float)


def run_rf_inference_on_flow_csv(
    flow_csv_path: str,
    artifact_path: str = "outputs/offline_adapter_test/rf_anomaly.joblib",
    max_rows: int | None = None,
    file_attack_ratio_threshold: float = 0.20,
) -> dict[str, Any]:
    """Run inference-only scoring for CICFlowMeter-compatible flow CSV input.

    This adapter never calls fit() and does not retrain any model components.
    """
    csv_path = Path(flow_csv_path)
    if not csv_path.exists():
        return _error_result(
            flow_csv_path=flow_csv_path,
            feature_count=0,
            missing_columns=[],
            threshold=None,
            file_attack_ratio_threshold=file_attack_ratio_threshold,
            message=f"flow CSV not found: {flow_csv_path}",
        )

    if file_attack_ratio_threshold < 0.0 or file_attack_ratio_threshold > 1.0:
        return _error_result(
            flow_csv_path=flow_csv_path,
            feature_count=0,
            missing_columns=[],
            threshold=None,
            file_attack_ratio_threshold=file_attack_ratio_threshold,
            message="file_attack_ratio_threshold must be between 0.0 and 1.0",
        )

    try:
        payload = joblib.load(artifact_path)
    except Exception as exc:
        return _error_result(
            flow_csv_path=flow_csv_path,
            feature_count=0,
            missing_columns=[],
            threshold=None,
            file_attack_ratio_threshold=file_attack_ratio_threshold,
            message=f"failed to load artifact: {exc}",
        )

    validated, validation_error = _validate_artifact(payload)
    if validated is None:
        return _error_result(
            flow_csv_path=flow_csv_path,
            feature_count=0,
            missing_columns=[],
            threshold=None,
            file_attack_ratio_threshold=file_attack_ratio_threshold,
            message=f"invalid artifact: {validation_error}",
        )

    feature_columns = validated["feature_columns"]
    threshold = float(validated["threshold"])

    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_path, low_memory=False, encoding="latin-1")
        except Exception as exc:
            return _error_result(
                flow_csv_path=flow_csv_path,
                feature_count=len(feature_columns),
                missing_columns=[],
                threshold=threshold,
                file_attack_ratio_threshold=file_attack_ratio_threshold,
                message=f"failed to read CSV: {exc}",
            )
    except Exception as exc:
        return _error_result(
            flow_csv_path=flow_csv_path,
            feature_count=len(feature_columns),
            missing_columns=[],
            threshold=threshold,
            file_attack_ratio_threshold=file_attack_ratio_threshold,
            message=f"failed to read CSV: {exc}",
        )

    if max_rows is not None:
        if max_rows <= 0:
            return _error_result(
                flow_csv_path=flow_csv_path,
                feature_count=len(feature_columns),
                missing_columns=[],
                threshold=threshold,
                file_attack_ratio_threshold=file_attack_ratio_threshold,
                message="max_rows must be positive when provided",
            )
        df = df.head(max_rows).copy()

    if df.empty:
        return _error_result(
            flow_csv_path=flow_csv_path,
            feature_count=len(feature_columns),
            missing_columns=[],
            threshold=threshold,
            file_attack_ratio_threshold=file_attack_ratio_threshold,
            message="input CSV has no data rows",
        )

    df = canonicalize_columns(df)
    df = df.replace([np.inf, -np.inf], np.nan)

    # Handle common CICFlowMeter header variants where duplicated headers may be absent.
    if "Fwd Header Length.1" not in df.columns and "Fwd Header Length" in df.columns:
        df["Fwd Header Length.1"] = df["Fwd Header Length"]

    missing_columns = [col for col in feature_columns if col not in df.columns]
    if missing_columns:
        return _error_result(
            flow_csv_path=flow_csv_path,
            feature_count=len(feature_columns),
            missing_columns=missing_columns,
            threshold=threshold,
            file_attack_ratio_threshold=file_attack_ratio_threshold,
            message="required CICFlowMeter-compatible feature columns are missing",
        )

    try:
        x_features = df[feature_columns]
        scores = _score_from_saved_components(
            x_features=x_features,
            preprocessor=validated["preprocessor"],
            svd=validated["svd"],
            rff=validated["rff"],
            rotations=np.asarray(validated["rotations"]),
            rf=validated["rf"],
        )
    except Exception as exc:
        return _error_result(
            flow_csv_path=flow_csv_path,
            feature_count=len(feature_columns),
            missing_columns=[],
            threshold=threshold,
            file_attack_ratio_threshold=file_attack_ratio_threshold,
            message=f"inference failed: {exc}",
        )

    preds = (scores > threshold).astype(int)

    rows_scored = int(len(scores))
    attack_count = int(preds.sum())
    benign_count = int(rows_scored - attack_count)
    attack_ratio = float(attack_count / rows_scored) if rows_scored else 0.0
    max_score = float(np.max(scores)) if rows_scored else 0.0
    mean_score = float(np.mean(scores)) if rows_scored else 0.0
    file_prediction_is_attack = attack_ratio >= file_attack_ratio_threshold

    return {
        "status": "success",
        "flow_csv_path": str(csv_path),
        "rows_scored": rows_scored,
        "attack_ratio": attack_ratio,
        "file_attack_ratio_threshold": float(file_attack_ratio_threshold),
        "row_threshold": threshold,
        "row_attack_count": attack_count,
        "row_benign_count": benign_count,
        "attack_count": attack_count,
        "benign_count": benign_count,
        "max_score": max_score,
        "mean_score": mean_score,
        "threshold": threshold,
        "prediction": "attack" if file_prediction_is_attack else "benign",
        "severity": "high" if file_prediction_is_attack else "info",
        "missing_columns": [],
        "feature_count": int(len(feature_columns)),
        "evidence_source": "saved_rf_artifact_inference",
    }
