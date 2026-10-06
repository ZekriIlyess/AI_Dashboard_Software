from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ModelType(str, Enum):
    regression = "regression"
    classification = "classification"
    time_series = "time_series"
    anomaly_detection = "anomaly_detection"


class TrainingConfig(BaseModel):
    dataset_id: str
    target_column: str
    model_type: ModelType
    features: Optional[List[str]] = None
    exclude_features: Optional[List[str]] = None
    test_split_ratio: float = 0.2
    time_column: Optional[str] = None
    auto_tune: bool = True


class FeatureImportance(BaseModel):
    feature: str
    importance: float
    impact: str  # positive, negative, mixed


class ModelResult(BaseModel):
    id: str
    name: str
    model_type: ModelType
    target_column: str
    status: str  # training, completed, failed
    metrics: Dict[str, float]
    feature_importance: List[FeatureImportance]
    training_time_ms: int
    created_at: str


class PredictionResult(BaseModel):
    prediction: Any
    confidence: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    local_explanations: Optional[Dict[str, float]] = None
