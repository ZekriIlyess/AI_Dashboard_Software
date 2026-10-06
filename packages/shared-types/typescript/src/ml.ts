// =============================================================================
// Nexus AI — Shared TypeScript Types: ML
// =============================================================================

/** Types of ML models supported */
export type ModelType = 
  | "regression"
  | "classification"
  | "time_series"
  | "anomaly_detection";

/** Configuration for training an ML model */
export interface TrainingConfig {
  datasetId: string;
  targetColumn: string;
  modelType: ModelType;
  /** Features to include (if empty, auto-select) */
  features?: string[];
  /** Features to explicitly exclude */
  excludeFeatures?: string[];
  testSplitRatio: number;
  timeColumn?: string; // Required for time_series
  autoTune: boolean;
}

/** Result of an ML model training process */
export interface ModelResult {
  id: string;
  name: string;
  modelType: ModelType;
  targetColumn: string;
  status: "training" | "completed" | "failed";
  metrics: Record<string, number>;
  featureImportance: FeatureImportance[];
  trainingTimeMs: number;
  createdAt: string;
}

/** Feature importance score */
export interface FeatureImportance {
  feature: string;
  importance: number; // 0 to 1
  impact: "positive" | "negative" | "mixed";
}

/** Prediction result */
export interface PredictionResult {
  prediction: number | string | boolean;
  confidence: number;
  lowerBound?: number;
  upperBound?: number;
  /** SHAP values explaining this specific prediction */
  localExplanations?: Record<string, number>;
}
