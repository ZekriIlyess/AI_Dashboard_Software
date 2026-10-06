from __future__ import annotations

"""Anomaly detection module.

Supports three detection strategies — **Z-Score**, **Isolation Forest**,
and **IQR** — with automatic method selection based on the number of
numeric columns.  Handles edge cases such as constant columns, all-NaN
columns, and very small datasets gracefully.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AnomalyPoint:
    """A single detected anomaly.

    Attributes:
        row_index: Zero-based index of the anomalous row.
        values: Mapping of analysed column names to their values in this row.
        score: Anomaly score (interpretation depends on *method*).
        severity: ``"critical"`` or ``"warning"``.
    """

    row_index: int
    values: Dict[str, float]
    score: float
    severity: str  # "critical" or "warning"


@dataclass
class AnomalyResult:
    """Aggregated anomaly-detection output.

    Attributes:
        anomalies: List of individual anomaly points.
        total_rows: Number of rows in the input data.
        anomaly_count: Total anomalies detected.
        anomaly_rate: ``anomaly_count / total_rows`` as a fraction.
        method: Detection method used.
        columns_analyzed: Columns included in the analysis.
        column_stats: Per-column descriptive statistics.
        thresholds: Method-specific threshold information.
    """

    anomalies: List[AnomalyPoint] = field(default_factory=list)
    total_rows: int = 0
    anomaly_count: int = 0
    anomaly_rate: float = 0.0
    method: str = ""
    columns_analyzed: List[str] = field(default_factory=list)
    column_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    thresholds: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class AnomalyDetector:
    """Detect anomalous rows in tabular data."""

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def detect(
        self,
        data: List[Dict[str, Any]],
        columns: List[str] | None = None,
        method: str = "auto",
        contamination: float = 0.05,
    ) -> AnomalyResult:
        """Run anomaly detection on *data*.

        Parameters
        ----------
        data:
            Row-oriented records.
        columns:
            Numeric columns to analyse.  When *None*, all numeric columns
            are selected automatically.
        method:
            ``"zscore"``, ``"isolation_forest"``, ``"iqr"``, or ``"auto"``
            (picks Z-Score for single-column data, Isolation Forest
            otherwise).
        contamination:
            Expected proportion of anomalies — used by Isolation Forest.

        Returns
        -------
        AnomalyResult
        """
        df = pd.DataFrame(data)

        # ---- select & validate columns --------------------------------- #
        columns = self._resolve_columns(df, columns)

        # ---- resolve method -------------------------------------------- #
        method = self._resolve_method(method, columns, len(df))

        # ---- prepare numeric matrix ------------------------------------ #
        X, valid_columns = self._prepare_data(df, columns)

        if len(valid_columns) == 0:
            logger.warning("No usable numeric columns after cleaning")
            return AnomalyResult(
                total_rows=len(df),
                method=method,
                columns_analyzed=[],
            )

        # ---- column stats ---------------------------------------------- #
        column_stats = self._column_stats(X, valid_columns)

        # ---- detect ----------------------------------------------------- #
        if method == "zscore":
            anomalies, thresholds = self._zscore(X, valid_columns)
        elif method == "isolation_forest":
            anomalies, thresholds = self._isolation_forest(X, valid_columns, contamination)
        elif method == "iqr":
            anomalies, thresholds = self._iqr(X, valid_columns)
        else:
            raise ValueError(f"Unknown method: {method!r}")

        anomaly_count = len(anomalies)
        anomaly_rate = float(anomaly_count / len(df)) if len(df) > 0 else 0.0

        return AnomalyResult(
            anomalies=anomalies,
            total_rows=len(df),
            anomaly_count=anomaly_count,
            anomaly_rate=anomaly_rate,
            method=method,
            columns_analyzed=valid_columns,
            column_stats=column_stats,
            thresholds=thresholds,
        )

    # --------------------------------------------------------------------- #
    # Column / data helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _resolve_columns(
        df: pd.DataFrame,
        columns: List[str] | None,
    ) -> List[str]:
        """Return validated list of numeric column names."""
        if columns is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        else:
            numeric_cols = [
                c for c in columns
                if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
            ]
            missing = set(columns or []) - set(numeric_cols)
            if missing:
                logger.warning("Skipping non-numeric or missing columns: %s", missing)

        if len(numeric_cols) < 1:
            raise ValueError("At least one numeric column is required for anomaly detection.")

        return numeric_cols

    @staticmethod
    def _resolve_method(method: str, columns: List[str], n_rows: int) -> str:
        """Pick the detection method when *method* is ``'auto'``."""
        if method != "auto":
            # Small datasets → force zscore instead of isolation_forest
            if method == "isolation_forest" and n_rows < 10:
                logger.info(
                    "Dataset has < 10 rows; switching from isolation_forest to zscore"
                )
                return "zscore"
            return method

        if len(columns) == 1:
            return "zscore"
        # Small datasets → zscore is more stable than IF
        if n_rows < 10:
            return "zscore"
        return "isolation_forest"

    @staticmethod
    def _prepare_data(
        df: pd.DataFrame,
        columns: List[str],
    ) -> tuple[np.ndarray, List[str]]:
        """Extract numeric matrix, impute NaNs with median, drop constant cols."""
        valid_columns: List[str] = []
        arrays: List[np.ndarray] = []

        for col in columns:
            series = pd.to_numeric(df[col], errors="coerce")
            # Skip all-NaN columns
            if series.isna().all():
                logger.warning("Column '%s' is entirely NaN – skipping", col)
                continue
            # Fill remaining NaNs with median
            median_val = series.median()
            series = series.fillna(median_val)
            # Skip constant columns (std == 0)
            if series.std() == 0:
                logger.warning("Column '%s' is constant – skipping", col)
                continue
            valid_columns.append(col)
            arrays.append(series.values)

        if len(arrays) == 0:
            return np.empty((0, 0)), []

        X = np.column_stack(arrays)
        return X, valid_columns

    @staticmethod
    def _column_stats(
        X: np.ndarray,
        columns: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Compute descriptive statistics per column."""
        stats: Dict[str, Dict[str, Any]] = {}
        for i, col in enumerate(columns):
            vals = X[:, i]
            stats[col] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "median": float(np.median(vals)),
                "q1": float(np.percentile(vals, 25)),
                "q3": float(np.percentile(vals, 75)),
            }
        return stats

    # --------------------------------------------------------------------- #
    # Detection strategies
    # --------------------------------------------------------------------- #

    @staticmethod
    def _zscore(
        X: np.ndarray,
        columns: List[str],
    ) -> tuple[List[AnomalyPoint], Dict[str, Any]]:
        """Z-Score-based detection.

        * ``|z| > 3.0`` → **critical**
        * ``2.5 < |z| ≤ 3.0`` → **warning**
        """
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0, ddof=1)
        # Guard against zero std (shouldn't happen after _prepare_data, but be safe)
        stds = np.where(stds == 0, 1.0, stds)

        z_scores = (X - means) / stds
        abs_z = np.abs(z_scores)

        critical_mask = np.any(abs_z > 3.0, axis=1)
        warning_mask = np.any(abs_z > 2.5, axis=1) & ~critical_mask

        anomalies: List[AnomalyPoint] = []

        for idx in np.where(critical_mask)[0]:
            max_z = float(np.max(abs_z[idx]))
            anomalies.append(
                AnomalyPoint(
                    row_index=int(idx),
                    values={col: float(X[idx, j]) for j, col in enumerate(columns)},
                    score=max_z,
                    severity="critical",
                )
            )

        for idx in np.where(warning_mask)[0]:
            max_z = float(np.max(abs_z[idx]))
            anomalies.append(
                AnomalyPoint(
                    row_index=int(idx),
                    values={col: float(X[idx, j]) for j, col in enumerate(columns)},
                    score=max_z,
                    severity="warning",
                )
            )

        # Sort by score descending for convenience
        anomalies.sort(key=lambda a: a.score, reverse=True)

        thresholds: Dict[str, Any] = {
            "critical_threshold": 3.0,
            "warning_threshold": 2.5,
            "method_detail": "z-score: |z| > 3.0 critical, 2.5 < |z| <= 3.0 warning",
        }
        return anomalies, thresholds

    @staticmethod
    def _isolation_forest(
        X: np.ndarray,
        columns: List[str],
        contamination: float,
    ) -> tuple[List[AnomalyPoint], Dict[str, Any]]:
        """Isolation-Forest-based detection."""
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
            n_jobs=-1,
        )
        predictions = model.fit_predict(X_scaled)  # -1 = anomaly
        scores = model.decision_function(X_scaled)  # lower = more anomalous

        anomalies: List[AnomalyPoint] = []
        anomaly_indices = np.where(predictions == -1)[0]

        if len(anomaly_indices) > 0:
            anomaly_scores = scores[anomaly_indices]
            score_median = float(np.median(anomaly_scores))

            for idx in anomaly_indices:
                severity = "critical" if scores[idx] < score_median else "warning"
                anomalies.append(
                    AnomalyPoint(
                        row_index=int(idx),
                        values={col: float(X[idx, j]) for j, col in enumerate(columns)},
                        score=float(-scores[idx]),  # negate so higher = more anomalous
                        severity=severity,
                    )
                )

        anomalies.sort(key=lambda a: a.score, reverse=True)

        thresholds: Dict[str, Any] = {
            "contamination": float(contamination),
            "n_estimators": 100,
            "decision_threshold": float(model.offset_),
            "method_detail": "isolation_forest with contamination={:.2f}".format(contamination),
        }
        return anomalies, thresholds

    @staticmethod
    def _iqr(
        X: np.ndarray,
        columns: List[str],
    ) -> tuple[List[AnomalyPoint], Dict[str, Any]]:
        """IQR (Inter-Quartile Range) detection.

        A row is anomalous if **any** column's value falls outside
        ``[Q1 - 1.5·IQR, Q3 + 1.5·IQR]``.
        """
        q1 = np.percentile(X, 25, axis=0)
        q3 = np.percentile(X, 75, axis=0)
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outlier_mask = (X < lower) | (X > upper)  # per-element
        row_is_anomaly = np.any(outlier_mask, axis=1)

        anomalies: List[AnomalyPoint] = []

        for idx in np.where(row_is_anomaly)[0]:
            # Score: max normalised distance beyond the fence
            distances = np.zeros(X.shape[1])
            for j in range(X.shape[1]):
                if iqr[j] == 0:
                    continue
                if X[idx, j] < lower[j]:
                    distances[j] = (lower[j] - X[idx, j]) / iqr[j]
                elif X[idx, j] > upper[j]:
                    distances[j] = (X[idx, j] - upper[j]) / iqr[j]

            max_dist = float(np.max(distances))
            severity = "critical" if max_dist > 3.0 else "warning"

            anomalies.append(
                AnomalyPoint(
                    row_index=int(idx),
                    values={col: float(X[idx, j]) for j, col in enumerate(columns)},
                    score=max_dist,
                    severity=severity,
                )
            )

        anomalies.sort(key=lambda a: a.score, reverse=True)

        thresholds: Dict[str, Any] = {
            "iqr_multiplier": 1.5,
            "per_column": {
                col: {
                    "q1": float(q1[j]),
                    "q3": float(q3[j]),
                    "iqr": float(iqr[j]),
                    "lower_fence": float(lower[j]),
                    "upper_fence": float(upper[j]),
                }
                for j, col in enumerate(columns)
            },
            "method_detail": "IQR: anomaly if value < Q1-1.5*IQR or > Q3+1.5*IQR",
        }
        return anomalies, thresholds
