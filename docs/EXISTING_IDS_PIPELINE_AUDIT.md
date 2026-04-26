# Existing IDS Pipeline Audit

This audit covers only the original offline IDS and Snort implementation under `src/nidsaas/detection/`, `src/nidsaas/snort/`, `scripts/offline/run_pipeline.py`, `scripts/offline/run_snort.py`, `scripts/offline/run_baseline.py`, `requirements.txt`, and the default offline sample file `data/samples/signature_merged_predictions.csv`.

## A. Current Offline Pipeline Entry Point

Primary command:

```bash
python scripts/offline/run_pipeline.py \
  --data-dir data/csv/csv_CIC_IDS2017 \
  --snort-predictions data/samples/signature_merged_predictions.csv \
  --output-dir outputs/proposed_locked_a20_g50 \
  --alpha-escalate 0.20 \
  --calibration-fraction 0.50 \
  --split-strategy temporal_by_file \
  --seed 42
```

Entry point:

- Script: `scripts/offline/run_pipeline.py`
- Main function called: `nidsaas.detection.hybrid_cascade_splitcal_fastsnort.run_cascade`
- Default data path: `data/csv/csv_CIC_IDS2017`
- Default signature path: `data/samples/signature_merged_predictions.csv`
- Default output path: `outputs/proposed_locked_a20_g50`

Important arguments:

- `--data-dir`: directory of CICFlowMeter-style CSV files.
- `--snort-predictions`: row-level signature prediction CSV keyed by `row_id`.
- `--output-dir`: directory for metrics, predictions, and model artifacts.
- `--rf-model`: optional existing RF anomaly model. If absent or missing, a new RF model is trained.
- `--split-strategy`: `random`, `temporal`, or `temporal_by_file`; the wrapper defaults to `temporal_by_file`.
- `--alpha-conformal`, `--alpha-escalate`, `--gate-threshold`, `--gate-max-iter`, `--calibration-fraction`, `--seed`.

## B. Data Input Format

The offline cascade expects flow CSVs, not raw PCAP. It recursively reads all `.csv` files under `--data-dir` using `src/nidsaas/detection/load_data.py`.

The expected format is CICFlowMeter/CIC-IDS2017 style flow records. Required or important columns include:

- Label column: `Label`, `label`, `class`, or `Class`.
- Time and identity columns when available: `Timestamp`, `Flow ID`, `Source IP`, `Destination IP`, `Source Port`, `Destination Port`, `Protocol`.
- Flow statistics used by rules and models: `Flow Duration`, `Flow Packets/s`, `Flow Bytes/s`, `Total Fwd Packets`, `Total Backward Packets`, `SYN Flag Count`, `RST Flag Count`.
- Additional numeric CICFlowMeter features are accepted and used by ML models unless excluded.

Column names are canonicalized in `src/nidsaas/detection/utils.py`. Example mappings include `Flow Duration -> flow_duration`, `Destination Port -> destination_port`, and `Label -> label`.

Raw PCAP support:

- The main offline IDS pipeline does not accept PCAP directly.
- CICFlowMeter is not implemented in this repository.
- CICFlowMeter or equivalent PCAP-to-flow extraction is external/assumed.
- The repository contains Snort helpers that can run external Snort on PCAP, but that is separate from the main cascade entry point.

## C. Snort Integration

There are two Snort-related paths.

Offline cascade path:

- `run_cascade()` does not execute Snort.
- It reads a precomputed signature prediction CSV through `load_signature_table()`.
- The signature CSV must contain `row_id` and one prediction column such as `signature_pred`, `snort_pred`, `prediction`, or `pred`.
- Optional score columns are accepted: `signature_score`, `snort_score`, `score`, or `pred_score`.
- Optional tier-2 rate-rule columns are accepted: `rate_V`, `rate_L`, `rate_S`, `rate_R`, `rate_P`, `rate_B`.
- The loaded signature table is merged into validation/test flow rows by `row_id`.

Default signature file:

```text
data/samples/signature_merged_predictions.csv
```

Observed schema:

```text
row_id, signature_pred, signature_score, rule_fired,
rate_V, rate_L, rate_S, rate_R, rate_P, rate_B, rate_X
```

Snort helper path:

- `src/nidsaas/snort/runner.py` can run an external Snort executable over PCAP files using `snort -r <pcap>`.
- `src/nidsaas/snort/parser.py` parses Snort `alert_fast.txt` files into CSV.
- `src/nidsaas/snort/policy_filter.py` filters parsed alerts by SID policy files under `src/nidsaas/snort/rules/policy/`.
- `src/nidsaas/snort/evaluator.py` matches filtered Snort alerts back to the CIC-IDS2017 test split using protocol, IPs, ports, inferred PCAP/day name, and optional timestamp windows. It outputs `snort_signature_predictions.csv`.
- `src/nidsaas/detection/signature_rate_rules.py` can OR-merge Snort predictions with deterministic flow-level rate rules to produce the cascade-compatible `signature_merged_predictions.csv`.

Bottom line: the main cascade consumes precomputed row-level signature predictions. Live Snort execution is available as a helper branch, not as part of `scripts/offline/run_pipeline.py`.

## D. Cleaning and Preprocessing

Loading and cleaning:

- File: `src/nidsaas/detection/load_data.py`
- Reads every CSV under `--data-dir`.
- Adds `source_file` from the CSV filename.
- Adds sequential `row_id` after concatenation.
- Canonicalizes column names.
- Normalizes labels into `multiclass_label`.
- Creates `binary_label`, where `BENIGN` is `0` and every non-benign class is `1`.
- Drops `UNKNOWN` labels by default.
- Replaces positive/negative infinity with `NaN`.
- Drops rows whose missing fraction is greater than `0.30` by default.
- Drops columns that are entirely missing.
- Drops duplicate rows, excluding `row_id` from the duplicate comparison.

Splitting:

- `random`: stratified train/validation/test.
- `temporal`: global chronological split using `timestamp` if present, otherwise `row_id`.
- `temporal_by_file`: chronological split within each `source_file`; this is the recommended CIC-IDS2017 split in the wrapper.

Feature generation:

- File: `src/nidsaas/detection/features.py`
- Non-feature columns excluded by default: `binary_label`, `multiclass_label`, `source_file`, `row_id`.
- RF/LSTM configs additionally exclude identifiers and high-cardinality columns such as flow ID, source/destination IP, timestamp, and `SimillarHTTP`.
- Numeric features are median-imputed and optionally standardized.
- Categorical features are most-frequent-imputed and one-hot encoded.

## E. Detection Models

Hybrid cascade:

- File: `src/nidsaas/detection/hybrid_cascade_splitcal_fastsnort.py`
- Combines signature fast-path predictions, RF anomaly scores, conformal p-values, and an escalation gate.

Random Forest anomaly model:

- File: `src/nidsaas/detection/rf_anomaly.py`
- Class: `SelfSupervisedRFAnomaly`
- Trained on benign training flows only.
- Pipeline: tabular preprocessor -> `TruncatedSVD` -> `RBFSampler` random Fourier features -> rotation-based self-supervised `RandomForestClassifier`.
- If `--rf-model` points to an existing file, the RF model is loaded.
- Otherwise it trains a fresh model and saves `rf_anomaly.joblib`.

Conformal wrapper:

- File: `src/nidsaas/detection/conformal_wrapper.py`
- Class: `ConformalAnomalyWrapper`
- Fits on held-out benign calibration scores.
- Produces p-values from anomaly scores.
- Saved as `conformal_wrapper.joblib`.
- The current cascade always fits a new conformal wrapper during the run.

GBDT/escalation gate:

- File: `src/nidsaas/detection/escalation_gate_fastsnort.py`
- Class: `EscalationGateFastSnort`
- Uses scikit-learn `HistGradientBoostingClassifier`.
- Trained on validation rows where `rf_pvalue <= alpha_escalate`.
- Input features are raw preprocessed flow features plus meta-features:
  - `rf_score`
  - `rf_pvalue`
  - optional rate-rule flags present in the signature CSV.
- Saved as `escalation_gate_fastsnort.joblib`.
- The current cascade always trains a new gate during the run.

Rate rules:

- File: `src/nidsaas/detection/signature_rate_rules.py`
- Deterministic flow-level rules: volumetric, slow HTTP, SYN flood, RST anomaly, port scan, brute force.
- Produces `row_id`, `signature_pred`, `signature_score`, `rule_fired`, and `rate_*` columns.
- Can merge an existing Snort prediction CSV into the same schema.

Baselines:

- `src/nidsaas/detection/compare_anomaly_baselines.py` and `_valcal.py`: Isolation Forest, One-Class SVM, and LSTM autoencoder comparisons.
- `src/nidsaas/detection/lstm_autoencoder_baseline.py`: PyTorch LSTM autoencoder trained on benign sequences.
- `src/nidsaas/detection/rf_baseline_valcal.py`: reuses saved cascade RF scores rather than retraining.
- `src/nidsaas/detection/rate_rules_baseline_valcal.py`: rate-rule-only and Snort-plus-rate-rule ablations.

## F. Output Format

Main cascade outputs under `--output-dir`:

- `overall_metrics.csv`: rows for RF, Signature-Snort, RF-Conformal, and Hybrid-Cascade. Metrics include accuracy, precision, recall, F1, FAR, ROC-AUC, PR-AUC, TP, TN, FP, FN, and operating-point metadata.
- `cascade_predictions.csv`: test-set rows plus `rf_score`, `rf_pvalue`, `rf_pred`, `conformal_pred`, `snort_pred`, `snort_score`, `gate_prob`, `escalated`, `cascade_pred`, `cascade_score`.
- `val_cascade_predictions.csv`: validation/gate pool export with flow columns and cascade score columns.
- `test_cascade_predictions.csv`: test split export with flow columns and cascade score columns.
- `cascade_summary.json`: split sizes, calibration sizes, signature coverage, escalation pool sizes, and gate meta-column details.
- `rf_anomaly.joblib`: saved RF anomaly model when trained.
- `conformal_wrapper.joblib`: saved conformal calibration wrapper.
- `escalation_gate_fastsnort.joblib`: saved GBDT escalation gate.

Snort helper outputs:

- `runner.py`: raw per-PCAP Snort output directories containing `alert_fast.txt` and console logs.
- `parser.py`: parsed alert CSV with timestamp, gid, sid, rev, message, priority, protocol, endpoints, source file, and PCAP name.
- `policy_filter.py`: filtered alert CSV.
- `evaluator.py`: `snort_signature_metrics.csv` and `snort_signature_predictions.csv`.

Rate-rule outputs:

- Signature prediction CSV compatible with the cascade.
- Per-class diagnostic CSV named like `<output_stem>_per_class.csv`.

## G. Integration Recommendation

Safest reuse path for the prototype:

1. Do not feed raw PCAP directly into the existing IDS cascade.
2. Keep Kafka upload events pointing to uploaded PCAP paths for ingestion/audit.
3. Add a separate extraction adapter that turns PCAP into CICFlowMeter-compatible flow CSV using an external CICFlowMeter command or service.
4. Optionally run the Snort helper branch against the same PCAP and convert alerts into a row-level `snort_signature_predictions.csv`.
5. Generate or merge rate-rule/signature predictions into a cascade-compatible CSV keyed by `row_id`.
6. Call the existing offline cascade on a directory of extracted flow CSVs plus the matching signature prediction CSV.

Spark recommendation:

- Spark should not call the current full training pipeline directly inside every `foreachBatch()` for production-like streaming. The current pipeline is batch-oriented and trains or calibrates models during a run.
- For an early demo, Spark `foreachBatch()` can call an adapter for small batches after PCAP-to-flow extraction, but this should be treated as batch orchestration, not real streaming inference.
- The next robust step is to create an adapter module, for example `src/nidsaas/detection/offline_adapter.py`, with a narrow function such as:

```python
run_offline_ids_on_flow_csv(
    data_dir: str,
    signature_predictions_path: str,
    output_dir: str,
    rf_model_path: str | None = None,
) -> dict
```

Implemented adapter:

- Module: `src/nidsaas/detection/offline_adapter.py`
- CLI: `scripts/offline/run_offline_adapter.py`

Adapter command:

```bash
python scripts/offline/run_offline_adapter.py \
  --data-dir data/csv/csv_CIC_IDS2017 \
  --signature-predictions data/samples/signature_merged_predictions.csv \
  --output-dir outputs/offline_adapter \
  --alpha-escalate 0.20 \
  --calibration-fraction 0.50 \
  --split-strategy temporal_by_file \
  --seed 42
```

The adapter is intentionally a thin wrapper around `run_cascade()`. It returns a normalized dictionary containing status, output paths, the main cascade metrics row when available, and an error string if the run fails.

Better long-term adapter:

- Add an inference-only adapter that loads saved `rf_anomaly.joblib`, `conformal_wrapper.joblib`, and `escalation_gate_fastsnort.joblib`, accepts already-cleaned flow rows, and emits predictions without retraining.
- Kafka messages should eventually include both:
  - `pcap_file_path`: original uploaded file path.
  - `flow_csv_path`: path produced by PCAP-to-flow extraction.
- The IDS adapter should consume `flow_csv_path`, not the raw PCAP path.

Honest current-state summary:

- Raw PCAP is not supported by the main offline IDS pipeline.
- CICFlowMeter is external/assumed and not implemented here.
- Snort execution exists as helper utilities but is not invoked by `scripts/offline/run_pipeline.py`.
- The default cascade uses precomputed row-level signature predictions keyed by `row_id`.
