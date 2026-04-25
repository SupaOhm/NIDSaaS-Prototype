"""Thin adapter for calling the existing offline IDS cascade."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _main_metrics(metrics: Any) -> dict[str, Any] | None:
    """Return the hybrid-cascade metrics row when available."""
    if metrics is None or not hasattr(metrics, "to_dict"):
        return None

    try:
        if "model" in metrics.columns:
            selected = metrics.loc[metrics["model"] == "hybrid_cascade_fastsnort"]
            if not selected.empty:
                return selected.iloc[0].to_dict()
        if len(metrics) > 0:
            return metrics.iloc[-1].to_dict()
    except Exception:
        return None
    return None


def run_offline_ids_on_flow_csv(
    data_dir: str,
    signature_predictions_path: str,
    output_dir: str,
    rf_model_path: str | None = None,
    alpha_escalate: float = 0.20,
    calibration_fraction: float = 0.50,
    split_strategy: str = "temporal_by_file",
    seed: int = 42,
) -> dict[str, Any]:
    """Run the existing offline cascade against CICFlowMeter-style CSV flows.

    This adapter intentionally does not implement PCAP-to-flow extraction and
    does not change cascade behavior. It only normalizes invocation and return
    metadata for prototype callers.
    """
    out = Path(output_dir)
    metrics_path = out / "overall_metrics.csv"
    predictions_path = out / "cascade_predictions.csv"
    summary_path = out / "cascade_summary.json"

    try:
        from nidsaas.detection.hybrid_cascade_splitcal_fastsnort import run_cascade

        metrics = run_cascade(
            data_dir=data_dir,
            snort_predictions_path=signature_predictions_path,
            output_dir=output_dir,
            rf_model_path=rf_model_path,
            alpha_escalate=alpha_escalate,
            calibration_fraction=calibration_fraction,
            split_strategy=split_strategy,
            seed=seed,
        )
        return {
            "status": "success",
            "output_dir": str(out),
            "metrics_path": str(metrics_path),
            "predictions_path": str(predictions_path),
            "summary_path": str(summary_path),
            "best_or_main_metrics": _main_metrics(metrics),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "output_dir": str(out),
            "metrics_path": str(metrics_path),
            "predictions_path": str(predictions_path),
            "summary_path": str(summary_path),
            "best_or_main_metrics": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
