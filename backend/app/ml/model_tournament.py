"""AutoML model tournament for the Nexus AI ML engine.

Trains multiple candidate estimators in parallel, evaluates them on a
hold-out set, performs cross-validation on the winner, and returns a
ranked leaderboard with feature importances.
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)

try:
    from xgboost import XGBClassifier, XGBRegressor
except ImportError:  # pragma: no cover
    XGBClassifier = None  # type: ignore[assignment,misc]
    XGBRegressor = None  # type: ignore[assignment,misc]

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
except ImportError:  # pragma: no cover
    LGBMClassifier = None  # type: ignore[assignment,misc]
    LGBMRegressor = None  # type: ignore[assignment,misc]

warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ModelResult:
    """Metrics and metadata for a single trained model."""

    name: str
    metrics: Dict[str, float]
    training_time: float
    rank: int


@dataclass
class TournamentResult:
    """Full output of :meth:`ModelTournament.run`."""

    task_type: str
    results: List[ModelResult]
    best_model_name: str
    best_model: Any  # The fitted model object
    feature_importance: List[Dict[str, Any]]
    cv_scores: Dict[str, float]  # {"mean": 0.87, "std": 0.03}
    X_test: pd.DataFrame
    y_test: pd.Series
    total_time: float


# ---------------------------------------------------------------------------
# Tournament
# ---------------------------------------------------------------------------

class ModelTournament:
    """Train, evaluate and rank multiple ML models automatically.

    Usage::

        result = ModelTournament().run(X, y, task_type="regression")
    """

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def run(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        task_type: str,
        max_time_seconds: int = 300,
    ) -> TournamentResult:
        """Execute the tournament and return ranked results.

        Parameters
        ----------
        X:
            Feature matrix (already scaled / encoded).
        y:
            Target vector.
        task_type:
            ``"classification"`` or ``"regression"``.
        max_time_seconds:
            Wall-clock budget in seconds.  Models whose cumulative
            training time would exceed this are skipped.

        Returns
        -------
        TournamentResult
        """

        tournament_start = time.time()

        # 1. Train / test split -------------------------------------------
        X_train, X_test, y_train, y_test = self._safe_split(X, y, task_type)

        # 2. Define candidate estimators ----------------------------------
        candidates = self._build_candidates(task_type)

        # 3. Train each candidate -----------------------------------------
        trained_results: List[Dict[str, Any]] = []
        fitted_models: Dict[str, Any] = {}
        cumulative_time = 0.0

        for name, estimator in candidates:
            if cumulative_time > max_time_seconds:
                break
            try:
                t0 = time.time()
                estimator.fit(X_train, y_train)
                elapsed = time.time() - t0
                cumulative_time += elapsed

                y_pred = estimator.predict(X_test)
                metrics = self._evaluate(y_test, y_pred, task_type)

                fitted_models[name] = estimator
                trained_results.append(
                    {"name": name, "metrics": metrics, "training_time": float(round(elapsed, 4))}
                )
            except Exception:
                # Skip models that fail (e.g. convergence issues)
                continue

        if not trained_results:
            raise RuntimeError("All candidate models failed during training.")

        # 4. Rank ----------------------------------------------------------
        ranking_key = "r2" if task_type == "regression" else "f1"
        trained_results.sort(key=lambda r: r["metrics"][ranking_key], reverse=True)

        model_results: List[ModelResult] = []
        for rank_idx, entry in enumerate(trained_results, start=1):
            model_results.append(
                ModelResult(
                    name=entry["name"],
                    metrics=entry["metrics"],
                    training_time=entry["training_time"],
                    rank=rank_idx,
                )
            )

        best_name = trained_results[0]["name"]
        best_model = fitted_models[best_name]

        # 5. Cross-validation on best model --------------------------------
        cv_scores = self._cross_validate(best_model, X, y, task_type)

        # 6. Feature importance -------------------------------------------
        feature_importance = self._extract_feature_importance(
            best_model, X.columns.tolist()
        )

        total_time = float(round(time.time() - tournament_start, 4))

        return TournamentResult(
            task_type=task_type,
            results=model_results,
            best_model_name=best_name,
            best_model=best_model,
            feature_importance=feature_importance,
            cv_scores=cv_scores,
            X_test=X_test,
            y_test=y_test,
            total_time=total_time,
        )

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _safe_split(
        X: pd.DataFrame,
        y: pd.Series,
        task_type: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Train/test split with graceful stratify fallback."""

        stratify = y if task_type == "classification" else None
        try:
            return train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=stratify
            )
        except ValueError:
            # Stratification fails when a class has only 1 sample
            return train_test_split(X, y, test_size=0.2, random_state=42)

    @staticmethod
    def _build_candidates(task_type: str) -> List[tuple[str, Any]]:
        """Return ``(name, unfitted_estimator)`` pairs."""

        candidates: List[tuple[str, Any]] = []

        if task_type == "regression":
            candidates.append(("LinearRegression", LinearRegression()))
            candidates.append((
                "RandomForest",
                RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42),
            ))
            if XGBRegressor is not None:
                candidates.append((
                    "XGBoost",
                    XGBRegressor(n_estimators=100, verbosity=0, random_state=42),
                ))
            if LGBMRegressor is not None:
                candidates.append((
                    "LightGBM",
                    LGBMRegressor(n_estimators=100, verbose=-1, random_state=42),
                ))
        else:
            candidates.append((
                "LogisticRegression",
                LogisticRegression(max_iter=1000, random_state=42),
            ))
            candidates.append((
                "RandomForest",
                RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42),
            ))
            if XGBClassifier is not None:
                candidates.append((
                    "XGBoost",
                    XGBClassifier(
                        n_estimators=100,
                        verbosity=0,
                        eval_metric="logloss",
                        random_state=42,
                    ),
                ))
            if LGBMClassifier is not None:
                candidates.append((
                    "LightGBM",
                    LGBMClassifier(n_estimators=100, verbose=-1, random_state=42),
                ))

        return candidates

    @staticmethod
    def _evaluate(
        y_true: pd.Series,
        y_pred: np.ndarray,
        task_type: str,
    ) -> Dict[str, float]:
        """Compute task-appropriate metrics."""

        if task_type == "regression":
            r2 = float(r2_score(y_true, y_pred))
            rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            mae = float(mean_absolute_error(y_true, y_pred))

            # MAPE — guard against zero denominators
            mask = y_true != 0
            if mask.any():
                mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
            else:
                mape = float("inf")

            return {"r2": round(r2, 6), "rmse": round(rmse, 6), "mae": round(mae, 6), "mape": round(mape, 6)}

        # Classification
        accuracy = float(accuracy_score(y_true, y_pred))
        f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
        precision = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
        recall = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))

        return {
            "accuracy": round(accuracy, 6),
            "f1": round(f1, 6),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
        }

    @staticmethod
    def _cross_validate(
        model: Any,
        X: pd.DataFrame,
        y: pd.Series,
        task_type: str,
    ) -> Dict[str, float]:
        """5-fold CV on the best model and return mean ± std."""

        if task_type == "regression":
            cv = KFold(n_splits=5, shuffle=True, random_state=42)
            scoring = "r2"
        else:
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            scoring = "f1_weighted"

        try:
            scores = cross_val_score(model, X, y, cv=cv, scoring=scoring)
        except ValueError:
            # Fallback to plain KFold if stratified fails
            cv = KFold(n_splits=5, shuffle=True, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring=scoring)

        return {
            "mean": float(round(np.mean(scores), 6)),
            "std": float(round(np.std(scores), 6)),
        }

    @staticmethod
    def _extract_feature_importance(
        model: Any,
        feature_names: List[str],
    ) -> List[Dict[str, Any]]:
        """Extract and normalise feature importances from the best model.

        Tree-based models expose ``feature_importances_``; linear models
        use the absolute coefficient values (averaged across classes for
        multi-class problems).

        Returns a list of ``{"feature": str, "importance": float}``
        sorted descending by importance.
        """

        importances: np.ndarray | None = None

        # Tree-based models
        if hasattr(model, "feature_importances_"):
            importances = np.array(model.feature_importances_, dtype=float)

        # Linear models
        elif hasattr(model, "coef_"):
            coef = np.array(model.coef_, dtype=float)
            if coef.ndim > 1:
                # Multi-class: average absolute coefficients across classes
                coef = np.mean(np.abs(coef), axis=0)
            else:
                coef = np.abs(coef).flatten()
            importances = coef

        if importances is None:
            return []

        # Normalise to sum = 1
        total = importances.sum()
        if total > 0:
            importances = importances / total

        pairs = list(zip(feature_names, importances))
        pairs.sort(key=lambda p: p[1], reverse=True)

        return [
            {"feature": name, "importance": float(round(imp, 6))}
            for name, imp in pairs
        ]
