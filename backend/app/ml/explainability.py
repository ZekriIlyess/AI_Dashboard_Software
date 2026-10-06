from __future__ import annotations

"""SHAP-based model explainability module.

Provides feature-importance explanations for trained ML models using SHAP
(SHapley Additive exPlanations).  Automatically selects the most efficient
SHAP explainer based on the model type and falls back gracefully when SHAP
is unavailable or fails.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ExplainabilityResult:
    """Container for SHAP explainability outputs.

    Attributes:
        global_importance: Feature names with their mean |SHAP| values,
            sorted descending.
        waterfall_data: Base value and per-feature SHAP contributions for
            the first sample (suitable for waterfall charts).
        summary_data: Top-10 features with full arrays of SHAP values and
            corresponding feature values (suitable for beeswarm / summary
            plots).
        method: The SHAP explainer type used – ``"tree"``, ``"linear"``,
            ``"kernel"``, or ``"fallback"``.
    """

    global_importance: List[Dict[str, Any]] = field(default_factory=list)
    waterfall_data: Dict[str, Any] = field(default_factory=dict)
    summary_data: List[Dict[str, Any]] = field(default_factory=list)
    method: str = "fallback"


# ---------------------------------------------------------------------------
# Explainer
# ---------------------------------------------------------------------------

class Explainer:
    """Generate SHAP-based explanations for a trained model."""

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def explain(
        self,
        model: Any,
        X_test: pd.DataFrame,
        feature_names: List[str],
        max_samples: int = 100,
    ) -> ExplainabilityResult:
        """Compute SHAP explanations for *model* on *X_test*.

        Parameters
        ----------
        model:
            A trained scikit-learn-compatible model.
        X_test:
            Test features as a DataFrame.
        feature_names:
            Ordered list of feature names corresponding to *X_test* columns.
        max_samples:
            Maximum number of rows to use for SHAP computation (to keep
            runtime reasonable).  Rows are sampled randomly when *X_test*
            exceeds this limit.

        Returns
        -------
        ExplainabilityResult
            Structured explanation data ready for JSON serialisation.
        """
        try:
            import shap  # noqa: F811 – lazy import keeps module loadable even without shap
        except ImportError:
            logger.warning("shap package is not installed – falling back to feature_importances_")
            return self._fallback_importance(model, feature_names)

        try:
            # ---- sample ------------------------------------------------- #
            if len(X_test) > max_samples:
                X_sample = X_test.sample(n=max_samples, random_state=42)
            else:
                X_sample = X_test.copy()

            # ---- choose explainer --------------------------------------- #
            explainer, method = self._select_explainer(shap, model, X_sample)

            # ---- compute SHAP values ------------------------------------ #
            raw_shap = explainer.shap_values(X_sample)
            shap_values = self._normalise_shap_values(raw_shap)

            # ---- ensure 2-D numpy array --------------------------------- #
            shap_values = np.array(shap_values)
            if shap_values.ndim == 1:
                shap_values = shap_values.reshape(1, -1)

            # ---- base value --------------------------------------------- #
            base_value = self._extract_base_value(explainer)

            # ---- build outputs ------------------------------------------ #
            global_importance = self._global_importance(shap_values, feature_names)
            waterfall_data = self._waterfall(shap_values, feature_names, X_sample, base_value)
            summary_data = self._summary(shap_values, feature_names, X_sample)

            return ExplainabilityResult(
                global_importance=global_importance,
                waterfall_data=waterfall_data,
                summary_data=summary_data,
                method=method,
            )

        except Exception:
            logger.exception("SHAP explanation failed – falling back to feature_importances_")
            return self._fallback_importance(model, feature_names)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _select_explainer(shap_mod: Any, model: Any, X_sample: pd.DataFrame):
        """Pick the best SHAP explainer for *model*.

        Returns
        -------
        tuple[shap.Explainer, str]
            The instantiated explainer and a human-readable method name.
        """
        # Tree-based models (RF, GBT, XGBoost, LightGBM, …)
        if hasattr(model, "feature_importances_"):
            try:
                explainer = shap_mod.TreeExplainer(model)
                return explainer, "tree"
            except Exception:
                logger.debug("TreeExplainer failed – trying alternatives")

        # Linear models (LogisticRegression, LinearRegression, …)
        if hasattr(model, "coef_"):
            try:
                explainer = shap_mod.LinearExplainer(model, X_sample)
                return explainer, "linear"
            except Exception:
                logger.debug("LinearExplainer failed – trying KernelExplainer")

        # Fallback – model-agnostic but slow
        background = X_sample.iloc[:10]
        explainer = shap_mod.KernelExplainer(model.predict, background)
        return explainer, "kernel"

    @staticmethod
    def _normalise_shap_values(raw_shap: Any) -> np.ndarray:
        """Convert raw SHAP output to a plain 2-D numpy array.

        Handles:
        * ``shap.Explanation`` objects (newer SHAP versions).
        * Lists of arrays (multi-class output) – picks class-1 when
          available, else class-0.
        * Plain numpy arrays (binary / regression).
        """
        # shap.Explanation → numpy
        if hasattr(raw_shap, "values"):
            raw_shap = raw_shap.values

        # Multi-class list of arrays
        if isinstance(raw_shap, list):
            if len(raw_shap) > 1:
                return np.array(raw_shap[1])
            return np.array(raw_shap[0])

        return np.array(raw_shap)

    @staticmethod
    def _extract_base_value(explainer: Any) -> float:
        """Retrieve the base (expected) value from a SHAP explainer."""
        try:
            ev = explainer.expected_value
            if isinstance(ev, (list, np.ndarray)):
                ev = ev[1] if len(ev) > 1 else ev[0]
            return float(ev)
        except Exception:
            return 0.0

    # ---- output builders ------------------------------------------------ #

    @staticmethod
    def _global_importance(
        shap_values: np.ndarray,
        feature_names: List[str],
    ) -> List[Dict[str, Any]]:
        """Mean |SHAP| per feature, sorted descending."""
        mean_abs = np.mean(np.abs(shap_values), axis=0)
        indices = np.argsort(mean_abs)[::-1]
        return [
            {"feature": feature_names[i], "importance": float(mean_abs[i])}
            for i in indices
            if i < len(feature_names)
        ]

    @staticmethod
    def _waterfall(
        shap_values: np.ndarray,
        feature_names: List[str],
        X_sample: pd.DataFrame,
        base_value: float,
    ) -> Dict[str, Any]:
        """Waterfall decomposition for the first sample."""
        if shap_values.shape[0] == 0:
            return {"base_value": float(base_value), "features": []}

        first_shap = shap_values[0]
        first_row = X_sample.iloc[0]

        order = np.argsort(np.abs(first_shap))[::-1]
        features = []
        for idx in order:
            if idx >= len(feature_names):
                continue
            features.append(
                {
                    "feature": feature_names[idx],
                    "shap_value": float(first_shap[idx]),
                    "feature_value": float(first_row.iloc[idx])
                    if np.issubdtype(type(first_row.iloc[idx]), np.number)
                    else str(first_row.iloc[idx]),
                }
            )
        return {"base_value": float(base_value), "features": features}

    @staticmethod
    def _summary(
        shap_values: np.ndarray,
        feature_names: List[str],
        X_sample: pd.DataFrame,
    ) -> List[Dict[str, Any]]:
        """Top-10 features with full SHAP + feature-value arrays."""
        mean_abs = np.mean(np.abs(shap_values), axis=0)
        top_indices = np.argsort(mean_abs)[::-1][:10]
        result: List[Dict[str, Any]] = []
        for idx in top_indices:
            if idx >= len(feature_names):
                continue
            col_shap = shap_values[:, idx]
            col_vals = X_sample.iloc[:, idx]
            result.append(
                {
                    "feature": feature_names[idx],
                    "importance": float(mean_abs[idx]),
                    "shap_values": [float(v) for v in col_shap],
                    "feature_values": [
                        float(v) if np.issubdtype(type(v), np.number) else str(v)
                        for v in col_vals
                    ],
                }
            )
        return result

    # ---- fallback ------------------------------------------------------- #

    @staticmethod
    def _fallback_importance(
        model: Any,
        feature_names: List[str],
    ) -> ExplainabilityResult:
        """Use ``model.feature_importances_`` when SHAP is unavailable."""
        global_importance: List[Dict[str, Any]] = []
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1]
            global_importance = [
                {"feature": feature_names[i], "importance": float(importances[i])}
                for i in indices
                if i < len(feature_names)
            ]

        return ExplainabilityResult(
            global_importance=global_importance,
            waterfall_data={"base_value": 0.0, "features": []},
            summary_data=[],
            method="fallback",
        )
