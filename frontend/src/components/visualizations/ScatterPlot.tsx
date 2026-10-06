"use client";

import React from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

interface ScatterPlotProps {
  data: any[];
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
}

export function ScatterPlot({ data, xKey, yKey, color = "#06b6d4", height = 300 }: ScatterPlotProps) {
  // ScatterChart expects objects with x and y numeric values
  const formattedData = data.map(item => ({
    x: Number(item[xKey]),
    y: Number(item[yKey])
  })).filter(item => !isNaN(item.x) && !isNaN(item.y));

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
          <XAxis type="number" dataKey="x" name={xKey} stroke="#94a3b8" fontSize={11} />
          <YAxis type="number" dataKey="y" name={yKey} stroke="#94a3b8" fontSize={11} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            contentStyle={{
              background: "rgba(15, 23, 42, 0.95)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "8px",
              color: "#fff"
            }}
          />
          <Scatter name="Data points" data={formattedData} fill={color} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
