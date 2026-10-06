"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { 
  ChevronLeft, 
  RefreshCw, 
  Cpu, 
  AlertTriangle,
  LineChart as LucideLineChart
} from "lucide-react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from "recharts";
import styles from "../models.module.css";
import { api } from "@/lib/api";

type TabType = "metrics" | "importance" | "waterfall" | "predict";

interface ModelMetric {
  name: string;
  metrics: Record<string, number>;
  training_time: number;
  rank: number;
}

interface FeatureImportance {
  feature: string;
  importance: number;
}

interface MLModelDetail {
  id: string;
  name: string;
  model_type: string;
  task_type: string;
  target_column: string;
  feature_columns: string[];
  status: string;
  metrics: {
    tournament?: ModelMetric[];
    cv_scores?: { mean: number; std: number };
    total_time?: number;
  };
  feature_importance?: FeatureImportance[];
  hyperparameters?: {
    shap_method?: string;
    shap_global_importance?: any[];
    shap_waterfall?: { base_value: number; features: any[] };
    shap_summary?: any[];
    fe_stats?: Record<string, any>;
  };
  training_time_seconds?: number;
  error_message?: string;
  created_at?: string;
}

export default function ModelDetailPage() {
  const params = useParams();
  const router = useRouter();
  const modelId = params.id as string;

  const [model, setModel] = useState<MLModelDetail | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("metrics");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Prediction state
  const [predictInputs, setPredictInputs] = useState<Record<string, string>>({});
  const [predictResult, setPredictResult] = useState<string | null>(null);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictError, setPredictError] = useState("");

  const loadModelDetails = async () => {
    try {
      setLoading(true);
      const detail: any = await api.get(`/ml/models/${modelId}`);
      setModel(detail);
      
      // Setup prediction inputs
      const initialInputs: Record<string, string> = {};
      if (detail.feature_columns) {
        detail.feature_columns.forEach((col: string) => {
          initialInputs[col] = "";
        });
      }
      setPredictInputs(initialInputs);
      setPredictResult(null);
      setPredictError("");
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to load model details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (modelId) {
      loadModelDetails();
    }
  }, [modelId]);

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!model) return;
    setPredictLoading(true);
    setPredictError("");
    setPredictResult(null);

    // Convert inputs to numeric or leave as string
    const formattedData: Record<string, any> = {};
    Object.keys(predictInputs).forEach((key) => {
      const val = predictInputs[key];
      const numVal = parseFloat(val);
      formattedData[key] = isNaN(numVal) ? val : numVal;
    });

    try {
      const response: any = await api.post(`/ml/models/${model.id}/predict`, {
        data: [formattedData]
      });
      if (response.predictions && response.predictions.length > 0) {
        setPredictResult(String(response.predictions[0]));
      } else {
        setPredictError("No predictions returned");
      }
    } catch (err: any) {
      setPredictError(err.message || "Prediction failed");
    } finally {
      setPredictLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
        <RefreshCw size={32} style={{ animation: "spin 2s linear infinite" }} />
      </div>
    );
  }

  if (error || !model) {
    return (
      <div style={{ padding: "2rem", maxWidth: "600px", margin: "0 auto" }}>
        <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", padding: "1.5rem", borderRadius: "8px", color: "#f87171" }}>
          <AlertTriangle size={24} style={{ marginBottom: "0.5rem" }} />
          <h3>Failed to Load Model</h3>
          <p>{error || "Model details could not be found."}</p>
          <button className="btn btn-secondary" onClick={() => router.push("/models")} style={{ marginTop: "1rem" }}>
            Back to Models List
          </button>
        </div>
      </div>
    );
  }

  const primaryMetric = model.task_type === "regression" ? "r2" : "f1";

  return (
    <div className={styles.container}>
      <div className={styles.detailHeader}>
        <div>
          <button 
            className="btn btn-secondary" 
            onClick={() => router.push("/models")} 
            style={{ padding: "0.5rem 1rem", fontSize: "0.85rem", marginBottom: "1rem" }}
          >
            <ChevronLeft size={16} style={{ marginRight: "0.25rem" }} />
            Back to Models
          </button>
          <h2 style={{ fontSize: "1.75rem", color: "#fff", fontWeight: 800 }}>{model.name}</h2>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
            Target: {model.target_column} • Algorithm: {model.model_type} • Type: {model.task_type.toUpperCase()}
          </p>
        </div>
        <button className="btn btn-secondary" onClick={loadModelDetails}>
          <RefreshCw size={16} />
        </button>
      </div>

      <div className={styles.tabList}>
        <button className={`${styles.tabButton} ${activeTab === "metrics" ? styles.activeTab : ""}`} onClick={() => setActiveTab("metrics")}>
          Tournament Leaderboard
        </button>
        <button className={`${styles.tabButton} ${activeTab === "importance" ? styles.activeTab : ""}`} onClick={() => setActiveTab("importance")}>
          Global Feature Importance
        </button>
        <button className={`${styles.tabButton} ${activeTab === "waterfall" ? styles.activeTab : ""}`} onClick={() => setActiveTab("waterfall")}>
          SHAP Waterfall (Sample #1)
        </button>
        <button className={`${styles.tabButton} ${activeTab === "predict" ? styles.activeTab : ""}`} onClick={() => setActiveTab("predict")}>
          Make Predictions
        </button>
      </div>

      <div className={styles.tabContent}>
        {activeTab === "metrics" && model.metrics.tournament && (
          <div>
            <div style={{ height: "300px", marginBottom: "2rem" }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={model.metrics.tournament.map(d => ({ name: d.name, score: d.metrics[primaryMetric] }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" domain={[0, 1]} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                  <Bar dataKey="score" fill="#6366f1">
                    {model.metrics.tournament.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? "#8b5cf6" : "#6366f1"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <table className={styles.leaderboardTable}>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Algorithm</th>
                  <th>{primaryMetric.toUpperCase()} Score</th>
                  <th>Training Time</th>
                </tr>
              </thead>
              <tbody>
                {model.metrics.tournament.map((r) => (
                  <tr key={r.name} style={r.rank === 1 ? { background: "rgba(139, 92, 246, 0.08)" } : undefined}>
                    <td style={{ fontWeight: 700 }}>#{r.rank}</td>
                    <td style={{ color: "#fff", fontWeight: 600 }}>{r.name}</td>
                    <td style={{ fontFamily: "var(--font-family-mono)", color: r.rank === 1 ? "#a78bfa" : "#34d399" }}>
                      {r.metrics[primaryMetric]?.toFixed(5)}
                    </td>
                    <td style={{ color: "var(--color-text-muted)" }}>{r.training_time}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "importance" && model.feature_importance && (
          <div style={{ height: "400px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={model.feature_importance.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" stroke="#94a3b8" />
                <YAxis dataKey="feature" type="category" stroke="#94a3b8" width={90} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                <Bar dataKey="importance" fill="#818cf8" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {activeTab === "waterfall" && model.hyperparameters?.shap_waterfall?.features && (
          <div>
            <div style={{ marginBottom: "1.5rem" }}>
              <p style={{ color: "var(--color-text-muted)" }}>
                Expected base value: <span style={{ fontFamily: "var(--font-family-mono)", color: "#fff" }}>{model.hyperparameters.shap_waterfall.base_value.toFixed(4)}</span>
              </p>
            </div>
            <table className={styles.leaderboardTable}>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Actual Value</th>
                  <th>SHAP Contribution</th>
                  <th>Impact Direction</th>
                </tr>
              </thead>
              <tbody>
                {model.hyperparameters.shap_waterfall.features.slice(0, 10).map((f: any) => (
                  <tr key={f.feature}>
                    <td style={{ color: "#fff" }}>{f.feature}</td>
                    <td style={{ fontFamily: "var(--font-family-mono)" }}>{typeof f.feature_value === "number" ? f.feature_value.toFixed(4) : String(f.feature_value)}</td>
                    <td style={{ fontFamily: "var(--font-family-mono)", color: f.shap_value > 0 ? "#f87171" : "#34d399", fontWeight: 600 }}>
                      {f.shap_value > 0 ? "+" : ""}{f.shap_value.toFixed(5)}
                    </td>
                    <td>
                      <span style={{
                        fontSize: "0.75rem",
                        fontWeight: 700,
                        padding: "0.2rem 0.5rem",
                        borderRadius: "4px",
                        background: f.shap_value > 0 ? "rgba(239, 68, 68, 0.12)" : "rgba(16, 185, 129, 0.12)",
                        color: f.shap_value > 0 ? "#ef4444" : "#10b981",
                      }}>
                        {f.shap_value > 0 ? "INCREASE TARGET" : "DECREASE TARGET"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "predict" && (
          <div className={styles.predictContainer}>
            <div>
              <h3 style={{ color: "#fff", marginBottom: "1.25rem" }}>Input Feature Values</h3>
              <form onSubmit={handlePredict}>
                <div style={{ maxHeight: "400px", overflowY: "auto", paddingRight: "0.5rem" }}>
                  {model.feature_columns?.map((col) => (
                    <div key={col} className={styles.formGroup}>
                      <label className={styles.formLabel}>{col}</label>
                      <input 
                        type="text" 
                        className={styles.formInput} 
                        placeholder="Enter value..." 
                        value={predictInputs[col] || ""}
                        onChange={(e) => setPredictInputs((prev) => ({ ...prev, [col]: e.target.value }))}
                      />
                    </div>
                  ))}
                </div>
                <button type="submit" className="btn btn-primary" style={{ marginTop: "1.5rem", width: "100%" }} disabled={predictLoading}>
                  {predictLoading ? "Computing Prediction..." : "Run Prediction Model"}
                </button>
              </form>
            </div>

            <div>
              <h3 style={{ color: "#fff", marginBottom: "1.25rem" }}>Prediction Result</h3>
              <div className={styles.resultPanel}>
                {predictResult ? (
                  <div style={{ textAlign: "center" }}>
                    <div style={{ color: "var(--color-text-muted)", fontSize: "0.85rem", textTransform: "uppercase", marginBottom: "0.5rem" }}>Predicted Value</div>
                    <div className={styles.resultValue}>{predictResult}</div>
                  </div>
                ) : predictError ? (
                  <div style={{ color: "#f87171", textAlign: "center" }}>
                    <AlertTriangle size={32} style={{ marginBottom: "0.5rem" }} />
                    <div>{predictError}</div>
                  </div>
                ) : (
                  <div style={{ color: "var(--color-text-muted)", textAlign: "center" }}>
                    <Cpu size={32} style={{ marginBottom: "0.5rem", opacity: 0.5 }} />
                    <div>Fill out input features and run prediction model.</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
