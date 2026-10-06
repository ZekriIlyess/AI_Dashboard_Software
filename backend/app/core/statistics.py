from __future__ import annotations

import json
import typing as t
from typing import List, Dict

import pandas as pd
import numpy as np

class StatsCalculator:
    """Static helper class – all methods are `@staticmethod` because no state is required."""

    @staticmethod
    def _df_from_raw(data: List[Dict], column: str) -> pd.DataFrame:
        """
        Helper that turns a list of dict-rows into a ``pandas`` DataFrame and forces
        the target *column* to a numeric dtype.  Rows where conversion fails are dropped.
        """
        df = pd.DataFrame(data)

        if column not in df.columns:
            raise KeyError(f"Column '{column}' is not present in the data rows.")
        numeric_series = pd.to_numeric(df[column], errors="coerce")
        df = df.loc[numeric_series.notna()].copy()                
        df[column] = numeric_series.loc[numeric_series.notna()]  
        return df

    @staticmethod
    def calculate_distribution(
        data: List[Dict], column: str, n_bins: t.Optional[int] = None
    ) -> Dict:
        """
        Compute a set of descriptive statistics for *column* and also return a
        histogram (bin edges + counts) that can be serialised to JSON.
        """
        df = StatsCalculator._df_from_raw(data, column)
        series: pd.Series = df[column]

        mean_val = float(series.mean())
        median_val = float(series.median())
        std_dev_val = float(series.std())
        min_val = int(np.floor(series.min()))
        max_val = int(np.ceil(series.max()))

        if n_bins is None:
            counts, bin_edges = np.histogram(series, bins="auto")
        else:
            counts, bin_edges = np.histogram(series, bins=n_bins)

        histogram = [
            {"lower": int(float(e)), "upper": int(np.round(nxt)), "count": int(c)}
            for c, e, nxt in zip(counts, bin_edges[:-1], bin_edges[1:])
        ]

        return {
            "mean": mean_val,
            "median": median_val,
            "std_dev": std_dev_val,
            "min": min_val,
            "max": max_val,
            "histogram": histogram,
        }

    @staticmethod
    def calculate_correlation(
        data: List[Dict], col1: str, col2: str
    ) -> Dict:
        """
        Compute the Pearson correlation coefficient between *col1* and *col2*.
        """
        df = pd.DataFrame(data)

        for c in (col1, col2):
            if c not in df.columns:
                raise KeyError(f"Column '{c}' is missing from data rows.")

        series_a = pd.to_numeric(df[col1], errors="coerce")
        series_b = pd.to_numeric(df[col2], errors="coerce")

        mask = series_a.notna() & series_b.notna()
        a_clean = series_a[mask]
        b_clean = series_b[mask]

        if len(a_clean) < 2:
            corr_val = None
        else:
            corr_val = float(np.corrcoef(a_clean, b_clean)[0, 1])

        return {"pearson_correlation": corr_val}
