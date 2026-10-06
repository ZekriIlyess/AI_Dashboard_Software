from __future__ import annotations

import logging
import joblib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class SimulationResult:
    """Aggregated output of scenario simulations."""
    mean: float
    std: float
    min: float
    max: float
    p5: float
    p25: float
    median: float
    p75: float
    p95: float
    simulated_values: List[float]
    target_probability: Optional[float] = None  # Prob of output > target threshold


class ScenarioSimulator:
    """Runs Monte Carlo simulations on saved AutoML models."""

    def simulate(
        self,
        model_artifact_path: str,
        base_data: List[Dict[str, Any]],
        variations: Dict[str, Dict[str, Any]],  # {"feat_name": {"dist": "normal", "mean": x, "std": y}}
        n_iterations: int = 1000,
        target_threshold: Optional[float] = None
    ) -> SimulationResult:
        """Run simulation drawing random samples for varied columns."""
        # 1. Load model artifact
        artifact = joblib.load(model_artifact_path)
        model = artifact["model"]
        scaler = artifact["scaler"]
        feature_names = artifact["feature_names"]

        # 2. Build baseline dataframe
        df_base = pd.DataFrame(base_data)
        
        # Ensure we have all necessary features
        for col in feature_names:
            if col not in df_base.columns:
                df_base[col] = 0.0

        # Draw a single baseline profile (we use mean of numeric fields, mode of categorical as base)
        baseline = {}
        for col in feature_names:
            if pd.api.types.is_numeric_dtype(df_base[col]):
                baseline[col] = float(df_base[col].mean())
            else:
                mode_res = df_base[col].mode()
                baseline[col] = mode_res.iloc[0] if not mode_res.empty else 0.0

        # 3. Perform Monte Carlo draws
        simulated_inputs = {col: np.full(n_iterations, baseline[col]) for col in feature_names}

        for col, config in variations.items():
            if col not in feature_names:
                continue
            dist_type = config.get("dist", "normal")
            
            if dist_type == "normal":
                mean = float(config.get("mean", baseline[col]))
                std = float(config.get("std", 1.0))
                simulated_inputs[col] = np.random.normal(mean, std, n_iterations)
            elif dist_type == "uniform":
                low = float(config.get("min", baseline[col] - 1.0))
                high = float(config.get("max", baseline[col] + 1.0))
                simulated_inputs[col] = np.random.uniform(low, high, n_iterations)
            elif dist_type == "constant":
                val = float(config.get("value", baseline[col]))
                simulated_inputs[col] = np.full(n_iterations, val)
            elif dist_type == "choice":
                choices = config.get("choices", [baseline[col]])
                probs = config.get("probabilities", None)
                simulated_inputs[col] = np.random.choice(choices, size=n_iterations, p=probs)

        # 4. Run predictions
        df_sim = pd.DataFrame(simulated_inputs)
        X_scaled = scaler.transform(df_sim[feature_names])
        predictions = model.predict(X_scaled)

        # 5. Aggregate metrics
        pred_array = np.array(predictions, dtype=float)
        mean_val = float(np.mean(pred_array))
        std_val = float(np.std(pred_array))
        min_val = float(np.min(pred_array))
        max_val = float(np.max(pred_array))
        
        p5 = float(np.percentile(pred_array, 5))
        p25 = float(np.percentile(pred_array, 25))
        median = float(np.percentile(pred_array, 50))
        p75 = float(np.percentile(pred_array, 75))
        p95 = float(np.percentile(pred_array, 95))

        # Calculate target probability (if threshold given)
        prob = None
        if target_threshold is not None:
            prob = float(np.mean(pred_array >= target_threshold))

        # Return sample values (limit to 100 values to keep response size light)
        sample_values = [float(v) for v in pred_array[:100]]

        return SimulationResult(
            mean=mean_val,
            std=std_val,
            min=min_val,
            max=max_val,
            p5=p5,
            p25=p25,
            median=median,
            p75=p75,
            p95=p95,
            simulated_values=sample_values,
            target_probability=prob
        )
