from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class LocalMLRunner:
    """Runs lightweight ML inference on the edge agent using serialised artifacts."""
    
    def __init__(self) -> None:
        self.models: Dict[str, Any] = {}  # model_name -> fitted model artifact
    
    def load_model(self, name: str, path: str) -> None:
        """Load a joblib-serialized model."""
        import joblib
        try:
            artifact = joblib.load(path)
            self.models[name] = artifact
            logger.info(f"Loaded ML model '{name}' from {path}")
        except Exception as e:
            logger.error(f"Failed to load ML model '{name}': {e}")
            raise
    
    def predict(self, name: str, data: List[Dict[str, Any]]) -> List[Any]:
        """Run prediction with a loaded model."""
        import pandas as pd
        artifact = self.models.get(name)
        if not artifact:
            raise ValueError(f"Model '{name}' is not loaded")
        
        model = artifact["model"]
        scaler = artifact["scaler"]
        feature_names = artifact["feature_names"]
        
        df = pd.DataFrame(data)
        # Ensure all columns exist
        for col in feature_names:
            if col not in df.columns:
                df[col] = 0.0
                
        df_features = df[feature_names]
        X_scaled = scaler.transform(df_features)
        
        preds = model.predict(X_scaled)
        return preds.tolist()
    
    def list_models(self) -> List[str]:
        """List loaded model names."""
        return list(self.models.keys())
