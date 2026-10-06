"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer
} from "recharts";

interface SHAPFeature {
  feature: string;
  value: number | string;
  shap_value: number;
}

interface SHAPWaterfallProps {
  baseValue: number;
  features: SHAPFeature[];
  height?: number;
}

export function SHAPWaterfall({ baseValue, features, height = 350 }: SHAPWaterfallProps) {
  // Sort features by absolute SHAP value descending
  const sorted = [...features].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value));

  // Transform data for Recharts horizontal bars
  const chartData = sorted.map(f => ({
    name: f.feature,
    val: f.shap_value,
    displayVal: f.shap_value.toFixed(5),
    featureVal: typeof f.value === "number" ? f.value.toFixed(3) : String(f.value)
  }));

  return (
    <div style={{ width: "100%", height }}>
      <div style={{ fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "0.5rem" }}>
        Base model expected value: <span style={{ color: "#fff", fontFamily: "var(--font-family-mono)" }}>{baseValue.toFixed(4)}</span>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 10, right: 30, left: 40, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
          <XAxis type="number" stroke="#94a3b8" fontSize={11} />
          <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} width={80} />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div style={{
                    background: "rgba(15, 23, 42, 0.95)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: "8px",
                    padding: "10px",
                    color: "#fff",
                    fontSize: "12px"
                  }}>
                    <div style={{ fontWeight: 700, marginBottom: "4px" }}>{data.name}</div>
                    <div>Actual Value: <span style={{ color: "#f59e0b" }}>{data.featureVal}</span></div>
                    <div>SHAP Impact: <span style={{ color: data.val > 0 ? "#f87171" : "#34d399", fontWeight: 600 }}>
                      {data.val > 0 ? "+" : ""}{data.displayVal}
                    </span></div>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar dataKey="val">
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.val > 0 ? "#f87171" : "#34d399"} // Red for positive impact, Green for negative impact
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
