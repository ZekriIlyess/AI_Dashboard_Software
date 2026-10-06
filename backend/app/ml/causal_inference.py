from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)

@dataclass
class CausalResult:
    """Container for causal inference analysis."""
    treatment: str
    outcome: str
    estimated_effect: float
    confidence_interval: List[float]  # [lower, upper]
    p_value: float
    method_used: str  # "dowhy" or "fallback_ols"
    refutation_status: Dict[str, Any]


class CausalAnalyzer:
    """Analyzes causal effects of a treatment variable on an outcome variable."""

    def analyze(
        self,
        data: List[Dict[str, Any]],
        treatment_col: str,
        outcome_col: str,
        common_causes: List[str]
    ) -> CausalResult:
        """Estimate causal effect using DoWhy or fallback OLS."""
        df = pd.DataFrame(data)
        
        # Validate columns
        required_cols = [treatment_col, outcome_col] + common_causes
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in dataset")
            # Ensure numeric
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # Drop rows with NaNs in analysis columns
        df = df.dropna(subset=required_cols)
        
        if len(df) < 10:
            raise ValueError("Insufficient data points after cleaning (need at least 10)")

        try:
            import dowhy
            return self._run_dowhy(df, treatment_col, outcome_col, common_causes)
        except ImportError:
            logger.info("DoWhy package not found. Falling back to OLS bootstrap regression.")
            return self._run_fallback_ols(df, treatment_col, outcome_col, common_causes)

    def _run_dowhy(
        self,
        df: pd.DataFrame,
        treatment: str,
        outcome: str,
        common_causes: List[str]
    ) -> CausalResult:
        """Run full causal pipeline using DoWhy library."""
        import dowhy
        
        # 1. Model
        model = dowhy.CausalModel(
            data=df,
            treatment=treatment,
            outcome=outcome,
            common_causes=common_causes
        )
        
        # 2. Identify
        identified_estimand = model.identify_effect(proceed_when_unidentified=True)
        
        # 3. Estimate
        estimate = model.estimate_effect(
            identified_estimand,
            method_name="backdoor.linear_regression"
        )
        
        # 4. Refute
        refutation_results = {}
        try:
            # Placebo treatment refutation
            refute = model.refute_estimate(
                identified_estimand,
                estimate,
                method_name="placebo_treatment_refuter"
            )
            refutation_results["placebo_treatment"] = {
                "new_effect": float(refute.new_effect),
                "p_value": float(refute.refutation_result.get("p_value", 0.0) if hasattr(refute, "refutation_result") else 0.0)
            }
        except Exception as e:
            logger.warning(f"DoWhy refutation failed: {e}")
            refutation_results["placebo_treatment"] = {"error": str(e)}

        # Extract confidence interval
        ci = [0.0, 0.0]
        if hasattr(estimate, "interpreter") and hasattr(estimate.interpreter, "confidence_intervals"):
            try:
                ci = [float(val) for val in estimate.interpreter.confidence_intervals[0]]
            except Exception:
                pass

        return CausalResult(
            treatment=treatment,
            outcome=outcome,
            estimated_effect=float(estimate.value),
            confidence_interval=ci,
            p_value=0.0,  # DoWhy LR doesn't always expose p-value directly in estimate object
            method_used="dowhy",
            refutation_status=refutation_results
        )

    def _run_fallback_ols(
        self,
        df: pd.DataFrame,
        treatment: str,
        outcome: str,
        common_causes: List[str]
    ) -> CausalResult:
        """Estimate causal effect using bootstrap OLS regression with control variables."""
        X = df[[treatment] + common_causes]
        y = df[outcome]
        
        # Fit OLS
        lr = LinearRegression()
        lr.fit(X, y)
        ate = float(lr.coef_[0])  # Coefficient of treatment is the ATE under linear assumption
        
        # Bootstrap for Confidence Interval and p-value
        n_bootstraps = 200
        boot_ates = []
        for _ in range(n_bootstraps):
            sample_idx = np.random.choice(df.index, size=len(df), replace=True)
            sample_df = df.loc[sample_idx]
            
            try:
                lr_boot = LinearRegression()
                lr_boot.fit(sample_df[[treatment] + common_causes], sample_df[outcome])
                boot_ates.append(lr_boot.coef_[0])
            except Exception:
                continue

        boot_ates = np.array(boot_ates)
        ci_lower = float(np.percentile(boot_ates, 2.5))
        ci_upper = float(np.percentile(boot_ates, 97.5))
        
        # Simple p-value (proportion of bootstraps of opposite sign or crossing 0)
        if ate > 0:
            p_val = float(np.mean(boot_ates <= 0) * 2)
        else:
            p_val = float(np.mean(boot_ates >= 0) * 2)
        p_val = min(max(p_val, 0.0), 1.0)

        # Placebo refutation (shuffle treatment column)
        shuffled_df = df.copy()
        shuffled_df[treatment] = np.random.permutation(shuffled_df[treatment].values)
        lr_placebo = LinearRegression()
        lr_placebo.fit(shuffled_df[[treatment] + common_causes], shuffled_df[outcome])
        placebo_ate = float(lr_placebo.coef_[0])

        return CausalResult(
            treatment=treatment,
            outcome=outcome,
            estimated_effect=ate,
            confidence_interval=[ci_lower, ci_upper],
            p_value=p_val,
            method_used="fallback_ols",
            refutation_status={
                "placebo_treatment": {
                    "new_effect": placebo_ate,
                    "status": "passed" if abs(placebo_ate) < abs(ate) * 0.5 else "warning"
                }
            }
        )
