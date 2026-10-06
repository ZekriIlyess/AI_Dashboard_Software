from __future__ import annotations

"""Time-series forecasting module powered by Facebook Prophet.

Automatically detects date and value columns, fits a Prophet model,
produces a forecast with confidence intervals, and returns trend
decomposition components together with in-sample accuracy metrics.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# ---- Suppress noisy Prophet / cmdstanpy logging BEFORE import ----------- #
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

from prophet import Prophet  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ForecastResult:
    """Container for time-series forecast outputs.

    Attributes:
        forecast_data: Combined historical + future rows with ``yhat``,
            ``yhat_lower``, ``yhat_upper``, and an ``is_forecast`` flag.
        historical_data: Original observed data points (``ds``, ``y``).
        components: Decomposition arrays keyed by component name
            (``"trend"``, ``"yearly"``, ``"weekly"``).
        metrics: In-sample accuracy metrics and bookkeeping counts.
        date_column: Name of the detected / provided date column.
        value_column: Name of the detected / provided value column.
    """

    forecast_data: List[Dict[str, Any]] = field(default_factory=list)
    historical_data: List[Dict[str, Any]] = field(default_factory=list)
    components: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    date_column: str = ""
    value_column: str = ""


# ---------------------------------------------------------------------------
# Forecaster
# ---------------------------------------------------------------------------

class TimeSeriesForecaster:
    """Fit a Prophet model and produce a forecast with diagnostics."""

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def forecast(
        self,
        data: List[Dict[str, Any]],
        date_column: str | None = None,
        value_column: str | None = None,
        periods: int = 30,
        frequency: str = "D",
    ) -> ForecastResult:
        """Generate a time-series forecast.

        Parameters
        ----------
        data:
            Row-oriented records (e.g. from ``DataFrame.to_dict('records')``).
        date_column:
            Name of the datetime column.  Auto-detected when *None*.
        value_column:
            Name of the numeric target column.  Auto-detected when *None*.
        periods:
            Number of future time-steps to forecast.
        frequency:
            Pandas frequency alias for the time series (``'D'``, ``'W'``,
            ``'M'``, ``'H'``, …).

        Returns
        -------
        ForecastResult
            Forecast, history, components, and accuracy metrics.

        Raises
        ------
        ValueError
            If date/value columns cannot be detected or if fewer than 10
            data points remain after cleaning.
        """
        df = pd.DataFrame(data)

        # ---- auto-detect columns --------------------------------------- #
        date_column = date_column or self._detect_date_column(df)
        value_column = value_column or self._detect_value_column(df, date_column)

        # ---- prepare Prophet format ------------------------------------ #
        prophet_df = self._prepare_dataframe(df, date_column, value_column)

        if len(prophet_df) < 10:
            raise ValueError(
                f"Need at least 10 data points after cleaning, got {len(prophet_df)}."
            )

        # ---- fit model ------------------------------------------------- #
        model = Prophet(
            yearly_seasonality="auto",
            weekly_seasonality="auto",
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
        )
        model.fit(prophet_df)

        # ---- forecast -------------------------------------------------- #
        future = model.make_future_dataframe(periods=periods, freq=frequency)
        forecast_df = model.predict(future)

        # ---- historical data ------------------------------------------- #
        historical_data = [
            {"ds": row["ds"].isoformat(), "y": float(row["y"])}
            for _, row in prophet_df.iterrows()
        ]

        # ---- forecast data --------------------------------------------- #
        historical_dates = set(prophet_df["ds"])
        forecast_data: List[Dict[str, Any]] = []
        for _, row in forecast_df.iterrows():
            forecast_data.append(
                {
                    "ds": row["ds"].isoformat(),
                    "yhat": float(row["yhat"]),
                    "yhat_lower": float(row["yhat_lower"]),
                    "yhat_upper": float(row["yhat_upper"]),
                    "is_forecast": row["ds"] not in historical_dates,
                }
            )

        # ---- components ------------------------------------------------ #
        components = self._extract_components(forecast_df)

        # ---- in-sample metrics ----------------------------------------- #
        metrics = self._compute_metrics(prophet_df, forecast_df, periods)

        return ForecastResult(
            forecast_data=forecast_data,
            historical_data=historical_data,
            components=components,
            metrics=metrics,
            date_column=date_column,
            value_column=value_column,
        )

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _detect_date_column(df: pd.DataFrame) -> str:
        """Return the first column whose values are ≥80 % parseable as dates."""
        for col in df.columns:
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
                valid_ratio = parsed.notna().mean()
                if valid_ratio >= 0.8:
                    return str(col)
            except Exception:
                continue
        raise ValueError(
            "Could not auto-detect a date column. "
            "Please specify the 'date_column' parameter explicitly."
        )

    @staticmethod
    def _detect_value_column(df: pd.DataFrame, date_column: str) -> str:
        """Return the first numeric column that is NOT *date_column*."""
        for col in df.columns:
            if col == date_column:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                return str(col)
        raise ValueError(
            "Could not auto-detect a numeric value column. "
            "Please specify the 'value_column' parameter explicitly."
        )

    @staticmethod
    def _prepare_dataframe(
        df: pd.DataFrame,
        date_column: str,
        value_column: str,
    ) -> pd.DataFrame:
        """Build the ``ds`` / ``y`` DataFrame that Prophet expects."""
        prophet_df = pd.DataFrame(
            {
                "ds": pd.to_datetime(df[date_column], errors="coerce"),
                "y": pd.to_numeric(df[value_column], errors="coerce"),
            }
        )
        prophet_df = prophet_df.dropna(subset=["ds", "y"])
        prophet_df = prophet_df.sort_values("ds")
        prophet_df = prophet_df.drop_duplicates(subset=["ds"], keep="last")
        prophet_df = prophet_df.reset_index(drop=True)
        return prophet_df

    @staticmethod
    def _extract_components(forecast_df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """Pull trend and seasonality components from Prophet's output."""
        components: Dict[str, List[Dict[str, Any]]] = {}

        if "trend" in forecast_df.columns:
            components["trend"] = [
                {"ds": row["ds"].isoformat(), "value": float(row["trend"])}
                for _, row in forecast_df.iterrows()
            ]

        if "yearly" in forecast_df.columns:
            components["yearly"] = [
                {"ds": row["ds"].isoformat(), "value": float(row["yearly"])}
                for _, row in forecast_df.iterrows()
            ]

        if "weekly" in forecast_df.columns:
            components["weekly"] = [
                {"ds": row["ds"].isoformat(), "value": float(row["weekly"])}
                for _, row in forecast_df.iterrows()
            ]

        return components

    @staticmethod
    def _compute_metrics(
        prophet_df: pd.DataFrame,
        forecast_df: pd.DataFrame,
        forecast_periods: int,
    ) -> Dict[str, float]:
        """Calculate in-sample MAPE and RMSE."""
        # Align on historical dates only
        merged = prophet_df.merge(
            forecast_df[["ds", "yhat"]],
            on="ds",
            how="inner",
        )

        actual = merged["y"].values
        predicted = merged["yhat"].values

        # MAPE – guard against zero actuals
        safe_actual = np.where(actual == 0, 1e-9, actual)
        mape = float(np.mean(np.abs((actual - predicted) / safe_actual)) * 100)

        # RMSE
        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

        return {
            "mape": mape,
            "rmse": rmse,
            "data_points": float(len(prophet_df)),
            "forecast_periods": float(forecast_periods),
        }
