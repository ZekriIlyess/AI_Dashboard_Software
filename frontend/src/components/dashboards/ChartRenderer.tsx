"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { formatCompactNumber, renderCustomPieLabel, getColorForLabel } from "@/lib/formatters";

interface Widget {
  id: string;
  title: string;
  widget_type: string; // 'table', 'bar', 'line'
  chart_config?: any;
}

// Premium Tooltip with Glassmorphism
const CustomTooltip = ({ active, payload, label, numberFormat = "standard" }: any) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        padding: '12px 16px',
        borderRadius: '12px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
        color: '#f8fafc'
      }}>
        <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8', marginBottom: '4px' }}>{label}</p>
        <p style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, color: '#38bdf8' }}>
          {formatCompactNumber(payload[0].value, numberFormat)}
        </p>
      </div>
    );
  }
  return null;
};

const gradientDefsElement = (
  <defs>
    <linearGradient id="colorIndigo" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor="#6366f1" stopOpacity={0.95}/>
      <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.3}/>
    </linearGradient>
    <linearGradient id="colorEmerald" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor="#10b981" stopOpacity={0.95}/>
      <stop offset="100%" stopColor="#14b8a6" stopOpacity={0.3}/>
    </linearGradient>
    <linearGradient id="colorCyan" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.95}/>
      <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.3}/>
    </linearGradient>
    <linearGradient id="colorOrange" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.95}/>
      <stop offset="100%" stopColor="#f97316" stopOpacity={0.3}/>
    </linearGradient>
  </defs>
);

export default function ChartRenderer({ widget }: { widget: Widget }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const fetchedData: any = await api.get(`/dashboards/widgets/${widget.id}/data`);
        
        // Ensure Y-axis values are numbers so Recharts can plot them
        const yAxisKey = widget.chart_config?.y || widget.chart_config?.y_axis;
        const formattedData = (fetchedData || []).map((item: any) => {
          if (yAxisKey && item[yAxisKey] !== undefined) {
             const val = Number(item[yAxisKey]);
             item[yAxisKey] = isNaN(val) ? item[yAxisKey] : val;
          }
          return item;
        });

        setData(formattedData);
      } catch (err: any) {
        setError(err.message || "Failed to load widget data");
      } finally {
        setLoading(false);
      }
    })();
  }, [widget.id, widget.chart_config]);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', width: '100%', padding: '1.25rem' }}>
        <div className="shimmer" style={{ height: '18px', width: '35%', borderRadius: '4px' }} />
        <div className="shimmer" style={{ flex: 1, borderRadius: '8px', marginTop: '0.5rem' }} />
      </div>
    );
  }
  if (error) return <div style={{ color: '#ef4444', padding: '1rem', textAlign: 'center' }}>{error}</div>;
  if (data.length === 0) return <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>No data returned</div>;

  const xAxis = widget.chart_config?.x || widget.chart_config?.x_axis;
  const yAxis = widget.chart_config?.y || widget.chart_config?.y_axis;
  const COLORS = ['#6366f1', '#10b981', '#06b6d4', '#f59e0b', '#8b5cf6'];

  if (widget.widget_type === "table") {
    const cols = Object.keys(data[0]);
    return (
      <div style={{ overflow: 'auto', maxHeight: '100%', padding: '1rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', color: 'var(--color-text)' }}>
          <thead>
            <tr>
              {cols.map((c, i) => (
                <th key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', padding: '0.5rem', textAlign: 'left', color: '#60a5fa' }}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rIdx) => (
              <tr key={rIdx}>
                {cols.map((colKey, cIdx) => (
                  <td key={cIdx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '0.5rem' }}>{String(row[colKey] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (!xAxis || !yAxis) {
    return <div style={{ padding: '1rem', color: '#ef4444' }}>Missing X or Y axis configuration</div>;
  }

  const layout = widget.chart_config?.layout || {};
  const showLegend = layout.show_legend !== false;
  const numberFormat = layout.number_format === "compact" ? "compact" : "standard";

  if (widget.widget_type === "bar") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          {gradientDefsElement}
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            dataKey={xAxis} 
            stroke="#64748b" 
            tick={{ fill: '#64748b', fontSize: 12 }} 
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis 
            stroke="#64748b" 
            tick={{ fill: '#64748b', fontSize: 12 }} 
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            tickFormatter={(v) => formatCompactNumber(v, numberFormat)}
          />
          <Tooltip content={<CustomTooltip numberFormat={numberFormat} />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
          {showLegend && <Legend wrapperStyle={{ paddingTop: '20px' }} />}
          <Bar 
            dataKey={yAxis} 
            name={yAxis} 
            radius={[6, 6, 0, 0]} 
            isAnimationActive={true}
            animationDuration={1000}
            animationEasing="ease-out"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColorForLabel(String(entry[xAxis]), layout.color_mapping) || 'url(#colorIndigo)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (widget.widget_type === "line") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          {gradientDefsElement}
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            dataKey={xAxis} 
            stroke="#64748b" 
            tick={{ fill: '#64748b', fontSize: 12 }} 
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
          />
          <YAxis 
            stroke="#64748b" 
            tick={{ fill: '#64748b', fontSize: 12 }} 
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            tickFormatter={(v) => formatCompactNumber(v, numberFormat)}
          />
          <Tooltip content={<CustomTooltip numberFormat={numberFormat} />} />
          {showLegend && <Legend wrapperStyle={{ paddingTop: '20px' }} />}
          <Line 
            type="monotone" 
            dataKey={yAxis} 
            stroke="url(#colorEmerald)" 
            strokeWidth={3.5} 
            dot={{ r: 4, fill: '#030712', stroke: '#10b981', strokeWidth: 2 }}
            activeDot={{ r: 7, fill: '#10b981', stroke: '#fff', strokeWidth: 2 }}
            isAnimationActive={true}
            animationDuration={1500}
            animationEasing="ease-out"
          />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (widget.widget_type === "pie") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 20, bottom: 20, left: 20, right: 20 }}>
          <Tooltip content={<CustomTooltip numberFormat={numberFormat} />} />
          {showLegend && <Legend wrapperStyle={{ color: '#94a3b8' }} />}
          <Pie 
            data={data} 
            dataKey={yAxis} 
            nameKey={xAxis} 
            cx="50%" 
            cy="50%" 
            innerRadius="60%"
            outerRadius="80%" 
            label={(entry) => renderCustomPieLabel(entry, numberFormat)}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColorForLabel(String(entry[xAxis]), layout.color_mapping) || COLORS[index % COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (widget.widget_type === "scatter") {
    // Convert string values to numbers for scatter
    const scatterData = data.map(d => ({
      ...d,
      [xAxis]: Number(d[xAxis]) || 0,
      [yAxis]: Number(d[yAxis]) || 0
    }));

    return (
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 20, right: 30, left: 60, bottom: 40 }}>
          {gradientDefsElement}
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            type="number"
            dataKey={xAxis} 
            name={xAxis} 
            stroke="#64748b" 
            tick={{ fill: '#64748b', fontSize: 12 }} 
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            tickFormatter={(v) => formatCompactNumber(v, numberFormat)}
            label={{ value: xAxis, position: 'insideBottom', offset: -20, fill: '#64748b', fontSize: 14 }}
          />
          <YAxis 
            type="number"
            dataKey={yAxis} 
            name={yAxis} 
            stroke="#64748b" 
            tick={{ fill: '#64748b', fontSize: 12 }} 
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            tickFormatter={(v) => formatCompactNumber(v, numberFormat)}
            label={{ value: yAxis, angle: -90, position: 'insideLeft', dx: -30, fill: '#64748b', fontSize: 14, style: { textAnchor: 'middle' } }}
          />
          <Tooltip content={<CustomTooltip numberFormat={numberFormat} />} cursor={{ strokeDasharray: '3 3' }} />
          {showLegend && <Legend wrapperStyle={{ paddingTop: '20px' }} />}
          <Scatter name={yAxis} data={scatterData} fill="url(#colorOrange)" />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  return <div>Unsupported widget type: {widget.widget_type}</div>;
}
