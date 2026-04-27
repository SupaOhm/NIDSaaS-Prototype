# RF Inference Compatibility: Saved Model vs Live Flow Extraction

Date: 2026-04-27
Artifact: `outputs/offline_adapter_test/rf_anomaly.joblib`

## 1) Saved Artifact Type and Available Methods

`rf_anomaly.joblib` loads as a **Python `dict` payload**, not as a direct `SelfSupervisedRFAnomaly` instance.

Payload keys:
- `config`
- `feature_columns`
- `preprocessor`
- `svd`
- `rff`
- `rotations`
- `rf`
- `threshold`
- `derived_threshold`

Observed object types inside payload:
- `rf`: `sklearn.ensemble.RandomForestClassifier`
- `preprocessor`: `sklearn.compose.ColumnTransformer`
- `svd`: `sklearn.decomposition.TruncatedSVD`
- `rff`: `sklearn.kernel_approximation.RBFSampler`

Available APIs (selected):
- `rf`: `predict`, `predict_proba`, `predict_log_proba`, `fit`, `score`
- `preprocessor`: `fit`, `transform`, `fit_transform`, `get_feature_names_out`
- `svd`: `fit`, `transform`, `fit_transform`, `inverse_transform`
- `rff`: `fit`, `transform`, `fit_transform`

Model metadata from artifact:
- `feature_columns` count: **80**
- `threshold`: **0.8065075701475143**
- `derived_threshold`: **0.8065075701475143**

## 2) RF Wrapper Contract (`src/nidsaas/detection/rf_anomaly.py`)

### Expected Feature Columns
The loaded artifact expects exactly the serialized `feature_columns` list (80 columns). Representative required columns include:
- `source_port`, `destination_port`, `Protocol`, `flow_duration`
- `total_fwd_packets`, `total_backward_packets`
- `flow_bytes_s`, `flow_packets_s`
- `syn_flag_count`, `rst_flag_count`
- many CIC-style statistical columns such as `Flow IAT Mean`, `Packet Length Std`, `Idle Max`, etc.

### Preprocessing / Transform Chain
`score_samples` applies this sequence:
1. `df[self.feature_columns]` exact column selection
2. `preprocessor.transform(...)` (numeric median-impute + scale, categorical most-frequent-impute + one-hot)
3. `svd.transform(...)`
4. `rff.transform(...)`
5. rotational self-supervised scoring with `rf.predict_proba(...)`

### Inference API
- `score_samples(df) -> np.ndarray` (anomaly score, higher means more anomalous)
- `predict(df) -> (preds, scores)` where `preds = (scores > threshold)`

Important: no column canonicalization/mapping happens inside `score_samples` before `df[self.feature_columns]`; missing or mismatched names will fail at column selection.

## 3) Column Compatibility Comparison

## 3.1 Against CICFlowMeter CSV Columns
Representative CSV checked:
- `data/csv/csv_CIC_IDS2017/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`
- Header count: **85**

After applying repo canonical aliases (as in detection utilities), overlap with expected RF columns:
- Expected RF columns: **80**
- Present in canonicalized CIC header: **79**
- Missing from this sample header: **1** (`Fwd Header Length.1`)

Interpretation:
- CICFlowMeter schema is **very close** to RF requirements.
- At least one required column may still be absent depending on exact exporter/header variant.
- Because RF scoring does strict `df[self.feature_columns]`, even one missing column can break direct inference unless a compatibility adapter injects/fixes missing fields.

## 3.2 Against Current tshark Fallback Live Extractor Output
Observed live output header (from `outputs/live_flows/..._flows.csv`):
- `flow_id`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`, `start_time`, `end_time`, `duration_sec`, `packet_count`, `byte_count`, `syn_count`, `ack_count`, `packets_per_sec`, `bytes_per_sec`
- Column count: **15**

Overlap with RF expected columns:
- Overlap: **0 / 80**
- Missing: **80 / 80**

Interpretation:
- The current tshark fallback flow schema is **not compatible** with the saved RF model input contract.
- Even semantically similar fields do not match required names or granularity.

## 4) Can Live RF Inference Run Now?

Short answer: **Yes for CICFlowMeter-compatible CSV input, no for tshark fallback CSV input.**

Implemented inference-only adapter:
- `src/nidsaas/detection/rf_inference_adapter.py`
- Function: `run_rf_inference_on_flow_csv(...)`
- CLI: `scripts/test/test_rf_inference_csv.py`

Adapter behavior:
- Loads saved `rf_anomaly.joblib` payload components (no retraining).
- Canonicalizes input columns with detection utility aliases.
- Replaces `+/-inf` with `NaN` before transform.
- Adds `Fwd Header Length.1` from `Fwd Header Length` when needed.
- Validates required `feature_columns` and returns `status="error"` with `missing_columns` when incompatible.
- Runs `preprocessor -> svd -> rff -> RF predict_proba` and computes anomaly scores/predictions using saved threshold.

Important:
- This adapter supports **CICFlowMeter-compatible flow CSV input**.
- The tshark flow extractor is used for rule-based runtime evidence; saved RF inference uses the CICFlowMeter-compatible CSV contract.

## 5) Do We Need CICFlowMeter Instead of tshark?

For this saved RF model: **Yes, effectively** (or an equivalent feature-engineering layer that reproduces the same 80-column contract).

Practical conclusion:
- To run this artifact on live uploads, the extraction path must provide CICFlowMeter-compatible features (and column names), including handling header variants such as duplicated `Fwd Header Length` vs `Fwd Header Length.1`.
- Use direct CSV upload or a CICFlowMeter-compatible extraction path for saved RF inference.

Quick usage:

```bash
python3 scripts/test/test_rf_inference_csv.py data/samples/csv/benign.csv
python3 scripts/test/test_rf_inference_csv.py data/samples/csv/ddos.csv
```

## 6) Runtime-Behavior Change Status

The adapter and CLI provide an explicit inference-only entry point for saved RF artifacts on compatible CSVs.
