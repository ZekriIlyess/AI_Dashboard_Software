"""Feature engineering pipeline for the Nexus AI ML engine.

Handles automatic type detection, missing-value imputation, categorical
encoding, datetime feature extraction, and numeric scaling so that raw
user-uploaded data can be fed straight into the model tournament.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class FeatureEngineResult:
    """Container returned by :meth:`FeatureEngineer.prepare`."""

    X: pd.DataFrame
    y: pd.Series
    task_type: str  # "classification" or "regression"
    feature_names: List[str]
    scaler: StandardScaler
    label_encoder: LabelEncoder | None  # Only for classification
    label_mapping: Dict[int, str] | None  # {0: "low", 1: "high"}
    dropped_columns: List[str]
    encoding_map: Dict[str, str]  # {col: "onehot" | "dropped"}
    stats: Dict[str, Any]  # {"n_rows", "n_features_original", "n_features_final", "missing_pct"}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class FeatureEngineer:
    """Stateless feature-engineering pipeline.

    Usage::

        result = FeatureEngineer().prepare(records, target_column="price")
    """

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def prepare(
        self,
        data: List[Dict[str, Any]],
        target_column: str,
        task_type: str | None = None,
    ) -> FeatureEngineResult:
        """Transform raw records into a model-ready ``(X, y)`` pair.

        Parameters
        ----------
        data:
            List of row-dicts (e.g. from ``df.to_dict(orient='records')``).
        target_column:
            Name of the column to predict.
        task_type:
            ``"classification"`` or ``"regression"``.  Auto-detected when
            *None*.

        Returns
        -------
        FeatureEngineResult
        """

        # 1. Convert to DataFrame ----------------------------------------
        df = pd.DataFrame(data)
        n_rows = len(df)
        n_features_original = df.shape[1] - 1  # exclude target

        if target_column not in df.columns:
            raise ValueError(
                f"Target column '{target_column}' not found. "
                f"Available columns: {list(df.columns)}"
            )

        # 2. Separate target ----------------------------------------------
        y: pd.Series = df[target_column].copy()
        X: pd.DataFrame = df.drop(columns=[target_column]).copy()

        # 3. Auto-detect task type & encode target -------------------------
        task_type, label_encoder, label_mapping = self._resolve_task_type(
            y, task_type
        )

        # 4. Drop useless columns -----------------------------------------
        X, dropped_columns = self._drop_useless(X)

        # Compute missing-value percentage *before* imputation
        total_cells = X.size
        missing_cells = int(X.isna().sum().sum())
        missing_pct = float(round(missing_cells / total_cells * 100, 2)) if total_cells > 0 else 0.0

        # 5. Handle missing values ----------------------------------------
        X = self._impute_missing(X)

        # 6. Encode categoricals ------------------------------------------
        X, encoding_map = self._encode_categoricals(X)

        # 7. Extract datetime features ------------------------------------
        X = self._extract_datetime_features(X)

        # 8. Scale numeric features ---------------------------------------
        scaler = StandardScaler()
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            X[numeric_cols] = scaler.fit_transform(X[numeric_cols])

        # 9. Build result -------------------------------------------------
        feature_names = X.columns.tolist()

        stats: Dict[str, Any] = {
            "n_rows": n_rows,
            "n_features_original": n_features_original,
            "n_features_final": len(feature_names),
            "missing_pct": missing_pct,
        }

        return FeatureEngineResult(
            X=X,
            y=y,
            task_type=task_type,
            feature_names=feature_names,
            scaler=scaler,
            label_encoder=label_encoder,
            label_mapping=label_mapping,
            dropped_columns=dropped_columns,
            encoding_map=encoding_map,
            stats=stats,
        )

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve_task_type(
        y: pd.Series,
        task_type: str | None,
    ) -> tuple[str, LabelEncoder | None, Dict[int, str] | None]:
        """Detect classification vs regression and label-encode if needed."""

        if task_type is None:
            is_string_or_bool = y.dtype == object or pd.api.types.is_bool_dtype(y)
            few_unique = y.nunique() <= 20
            task_type = "classification" if (few_unique or is_string_or_bool) else "regression"

        label_encoder: LabelEncoder | None = None
        label_mapping: Dict[int, str] | None = None

        if task_type == "classification":
            label_encoder = LabelEncoder()
            y_raw = y.astype(str)
            y[:] = label_encoder.fit_transform(y_raw)
            y = y.astype(int)
            label_mapping = {
                int(code): str(cls) for code, cls in enumerate(label_encoder.classes_)
            }

        return task_type, label_encoder, label_mapping

    @staticmethod
    def _drop_useless(X: pd.DataFrame) -> tuple[pd.DataFrame, List[str]]:
        """Drop columns that carry no predictive signal."""

        dropped: List[str] = []

        for col in X.columns.tolist():
            series = X[col]

            # >50 % missing
            if series.isna().mean() > 0.50:
                dropped.append(col)
                continue

            # Zero variance (single unique value, excluding NaN)
            if series.nunique(dropna=True) <= 1:
                dropped.append(col)
                continue

            # ID-like column
            col_lower = col.lower()
            is_id_name = col_lower == "id" or col_lower.endswith("_id")
            all_unique = series.nunique(dropna=True) == series.dropna().shape[0]
            is_int_or_str = pd.api.types.is_integer_dtype(series) or series.dtype == object
            if is_id_name and all_unique and is_int_or_str:
                dropped.append(col)
                continue

        X = X.drop(columns=dropped)
        return X, dropped

    @staticmethod
    def _impute_missing(X: pd.DataFrame) -> pd.DataFrame:
        """Fill missing values — median for numeric, mode for categorical."""

        for col in X.columns:
            if X[col].isna().any():
                if pd.api.types.is_numeric_dtype(X[col]):
                    X[col] = X[col].fillna(X[col].median())
                else:
                    mode_val = X[col].mode()
                    fill = mode_val.iloc[0] if not mode_val.empty else "missing"
                    X[col] = X[col].fillna(fill)

        return X

    @staticmethod
    def _encode_categoricals(
        X: pd.DataFrame,
    ) -> tuple[pd.DataFrame, Dict[str, str]]:
        """One-hot encode low-cardinality categoricals, drop the rest."""

        encoding_map: Dict[str, str] = {}
        cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

        cols_to_drop: List[str] = []
        for col in cat_cols:
            n_unique = X[col].nunique()
            if n_unique <= 10:
                encoding_map[col] = "onehot"
            else:
                encoding_map[col] = "dropped"
                cols_to_drop.append(col)

        X = X.drop(columns=cols_to_drop)

        onehot_cols = [c for c in cat_cols if encoding_map.get(c) == "onehot"]
        if onehot_cols:
            X = pd.get_dummies(X, columns=onehot_cols, drop_first=True)
            # Ensure all dummy columns are numeric
            for c in X.columns:
                if X[c].dtype == bool:
                    X[c] = X[c].astype(int)

        return X, encoding_map

    @staticmethod
    def _extract_datetime_features(X: pd.DataFrame) -> pd.DataFrame:
        """Parse datetime-like columns and expand to calendar parts."""

        cols_to_drop: List[str] = []

        for col in X.columns.tolist():
            if pd.api.types.is_numeric_dtype(X[col]):
                continue
            try:
                dt = pd.to_datetime(X[col], infer_datetime_format=True)
            except (ValueError, TypeError, pd.errors.ParserError):
                continue

            # Successfully parsed — extract features
            X[f"{col}_year"] = dt.dt.year.astype(float)
            X[f"{col}_month"] = dt.dt.month.astype(float)
            X[f"{col}_day"] = dt.dt.day.astype(float)
            X[f"{col}_day_of_week"] = dt.dt.dayofweek.astype(float)

            # Add hour only when a time component is present
            has_time = (dt.dt.hour != 0).any() or (dt.dt.minute != 0).any() or (dt.dt.second != 0).any()
            if has_time:
                X[f"{col}_hour"] = dt.dt.hour.astype(float)

            cols_to_drop.append(col)

        if cols_to_drop:
            X = X.drop(columns=cols_to_drop)

        return X
