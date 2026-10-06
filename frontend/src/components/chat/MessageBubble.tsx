import React from "react";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { formatCompactNumber, renderCustomPieLabel, getColorForLabel } from '@/lib/formatters';
import styles from "../../app/(dashboard)/explore/explore.module.css";

const formatMarkdown = (text: string) => {
  if (!text) return "";
  const lines = text.split("\n");
  
  return lines.map((line, idx) => {
    let cleanLine = line.trim();
    if (!cleanLine) return <div key={idx} style={{ height: '0.5rem' }} />;
    
    const isBullet = cleanLine.startsWith("* ") || cleanLine.startsWith("- ");
    if (isBullet) {
      cleanLine = cleanLine.substring(2);
    }
    
    const parts = cleanLine.split(/\*\*([^*]+)\*\*/g);
    const content = parts.map((part, pIdx) => {
      if (pIdx % 2 === 1) {
        return <strong key={pIdx} style={{ color: '#fff', fontWeight: 650 }}>{part}</strong>;
      }
      return part;
    });

    if (isBullet) {
      return (
        <li key={idx} style={{ marginLeft: '1.25rem', listStyleType: 'disc', paddingLeft: '0.25rem', marginBottom: '0.4rem', color: '#cbd5e1' }}>
          {content}
        </li>
      );
    }
    
    return (
      <p key={idx} style={{ margin: '0 0 0.75rem 0', color: '#cbd5e1', lineHeight: 1.6 }}>
        {content}
      </p>
    );
  });
};

interface ChatMessage {
  id?: string;
  isUser: boolean;
  text: string;
  sql: string | null;
  data: any[] | null;
  error: string | null;
  status?: "pending" | "success" | "error";
  summary?: string | null;
  narrative?: string | null;
  chartConfig?: { type: string, x: string, y: string, layout?: any } | null;
  progressMessage?: string;
}

interface MessageBubbleProps {
  msg: ChatMessage;
  onCancel: (id: string) => void;
  onOpenModal: (sql: string, data: any[], chartConfig?: any) => void;
}

export default function MessageBubble({ msg, onCancel, onOpenModal }: MessageBubbleProps) {
  // ... (keep rendering functions as they are until the main render)
  const renderData = (rows: any[]) => {
    if (!Array.isArray(rows) || rows.length === 0) return null;
    const cols = Object.keys(rows[0]);

    // Render standard table
    return (
      <div className={styles.tableWrapper}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              {cols.map((c, i) => (
                <th key={i}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rIdx) => (
              <tr key={rIdx}>
                {cols.map((colKey, cIdx) => (
                  <td key={cIdx}>{String(row[colKey] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const CustomTooltip = ({ active, payload, label, numberFormat = "standard" }: any) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '10px 14px',
          borderRadius: '10px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          color: '#f8fafc'
        }}>
          <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8', marginBottom: '2px', fontWeight: 500 }}>{label}</p>
          <p style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#6366f1' }}>
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

  const renderChart = (data: any[], config: any) => {
    if (!config || !config.type || !config.x || !config.y) return null;
    const { type, x, y } = config;
    
    // Convert y (and x if scatter) to numbers
    const chartData = data.map(d => ({
      ...d,
      [y]: Number(d[y]) || 0,
      ...(type === 'scatter' ? { [x]: Number(d[x]) || 0 } : {})
    }));

    const COLORS = ['#6366f1', '#10b981', '#06b6d4', '#f59e0b', '#8b5cf6'];

    const layout = config.layout || {};
    const showLegend = layout.show_legend !== false;
    const numberFormat = layout.number_format === 'compact' ? 'compact' : 'standard';
    const chartHeight = layout.height || 320;

    return (
      <div className={styles.chartWrapper} style={{ height: `${chartHeight}px`, padding: '1rem 0.5rem 0.5rem 0.5rem' }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === 'bar' ? (
            <BarChart data={chartData} margin={{ bottom: 50, top: 10, left: 10, right: 10 }}>
              {gradientDefsElement}
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis dataKey={x} stroke="#64748b" angle={-45} textAnchor="end" height={60} tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} />
              <YAxis stroke="#64748b" tickFormatter={(v) => formatCompactNumber(v, numberFormat)} tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} />
              <Tooltip content={<CustomTooltip numberFormat={numberFormat} />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
              {showLegend && <Legend wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }} />}
              <Bar dataKey={y} radius={[5, 5, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getColorForLabel(String(entry[x]), layout.color_mapping) || 'url(#colorIndigo)'} />
                ))}
              </Bar>
            </BarChart>
          ) : type === 'line' ? (
            <LineChart data={chartData} margin={{ bottom: 20, top: 10, left: 10, right: 20 }}>
              {gradientDefsElement}
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis dataKey={x} stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} />
              <YAxis stroke="#64748b" tickFormatter={(v) => formatCompactNumber(v, numberFormat)} tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} />
              <Tooltip content={<CustomTooltip numberFormat={numberFormat} />} />
              {showLegend && <Legend wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }} />}
              <Line type="monotone" dataKey={y} stroke="url(#colorEmerald)" strokeWidth={3.5} dot={{ r: 4, fill: '#030712', stroke: '#10b981', strokeWidth: 2 }} activeDot={{ r: 7, fill: '#10b981', stroke: '#fff', strokeWidth: 2 }} isAnimationActive={true} animationDuration={1000} />
            </LineChart>
          ) : type === 'pie' ? (
            <PieChart margin={{ top: 10, bottom: 10, left: 10, right: 10 }}>
              <Tooltip content={<CustomTooltip numberFormat={numberFormat} />} />
              {showLegend && <Legend wrapperStyle={{ fontSize: '12px' }} />}
              <Pie
                data={chartData}
                dataKey={y}
                nameKey={x}
                cx="50%"
                cy="50%"
                innerRadius="60%"
                outerRadius="80%"
                label={(entry) => renderCustomPieLabel(entry, numberFormat)}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getColorForLabel(String(entry[x]), layout.color_mapping) || COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : type === 'scatter' ? (
            <ScatterChart data={chartData} margin={{ top: 15, right: 20, bottom: 25, left: 20 }}>
              {gradientDefsElement}
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis 
                type="number" 
                dataKey={x} 
                name={x} 
                stroke="#64748b" 
                label={{ value: x, position: 'insideBottom', offset: -10, fill: '#64748b', fontSize: 12, fontWeight: 600 }}
                tickFormatter={(v) => formatCompactNumber(v, numberFormat)} 
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
              />
              <YAxis 
                type="number" 
                dataKey={y} 
                name={y} 
                stroke="#64748b" 
                label={{ value: y, angle: -90, position: 'insideLeft', dx: -5, fill: '#64748b', fontSize: 12, fontWeight: 600, style: { textAnchor: 'middle' } }}
                tickFormatter={(v) => formatCompactNumber(v, numberFormat)} 
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
              />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip numberFormat={numberFormat} />} />
              {showLegend && <Legend wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }} />}
              <Scatter name="Data" data={chartData} fill="url(#colorOrange)" />
            </ScatterChart>
          ) : (
            <div style={{ color: 'white' }}>Unsupported chart type</div>
          )}
        </ResponsiveContainer>
      </div>
    );
  };

  return (
    <div className={`${styles.message} ${msg.isUser ? styles.userMessage : styles.botMessage} chat-bubble`}>
      <div className={styles.messageContent}>
        {msg.isUser ? (
          <p className={styles.messageText}>{msg.text}</p>
        ) : (
          <>
            {msg.status === "error" && (
              <div className={styles.errorBox}>
                <strong>Error: </strong> {msg.error}
              </div>
            )}
            
            {msg.status === "pending" && !msg.isUser && (
              <div className="thinking-state" style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                <span className="loading-dots" style={{ flex: 1 }}>{msg.progressMessage || 'Thinking'}</span>
                {msg.id && (
                  <button 
                    onClick={() => onCancel(msg.id!)}
                    style={{ 
                      background: 'rgba(239, 68, 68, 0.08)', 
                      border: '1px solid rgba(239, 68, 68, 0.25)', 
                      color: '#f87171', 
                      padding: '0.3rem 0.75rem', 
                      borderRadius: '6px', 
                      cursor: 'pointer', 
                      fontSize: '0.8rem', 
                      fontWeight: 650,
                      transition: 'all 0.2s ease',
                      outline: 'none'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'; e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.4)'; e.currentTarget.style.color = '#ef4444'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)'; e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.25)'; e.currentTarget.style.color = '#f87171'; }}
                  >
                    Cancel
                  </button>
                )}
              </div>
            )}

            {msg.status === "success" && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
                
                {/* 1. Generated SQL Block */}
                {msg.sql && (
                  <div className={styles.sqlBox}>
                    <div className={styles.sqlHeader}>GENERATED SQL</div>
                    <pre className={styles.sqlPre}>{msg.sql}</pre>
                  </div>
                )}

                {/* 2. Premium Narrative Block */}
                {msg.narrative && (
                  <div className="insight-banner">
                    <h4>✨ Executive Summary</h4>
                    <div style={{ marginTop: '0.75rem' }}>{formatMarkdown(msg.narrative)}</div>
                  </div>
                )}
                
                {/* 3. Statistical Summary Block (Fallback or Detail) */}
                {msg.summary && (
                  <div className={styles.insightBox}>
                    <div className={styles.insightHeader}>📊 Statistical Insight</div>
                    <div className={styles.insightText} style={{ marginTop: '0.5rem' }}>{formatMarkdown(msg.summary)}</div>
                  </div>
                )}

                {/* 3. Data / Chart Block */}
                {msg.chartConfig && msg.data && msg.data.length > 0 && renderChart(msg.data, msg.chartConfig)}
                {msg.data && msg.data.length > 0 && !msg.chartConfig && renderData(msg.data)}
                
                {/* 4. Save Button */}
                {msg.data && msg.data.length > 0 && (
                  <div>
                    <button 
                      className={styles.sendButton}
                      onClick={() => onOpenModal(msg.sql!, msg.data!, msg.chartConfig)}
                      style={{ marginTop: '0.5rem' }}
                    >
                      Save to Dashboard
                    </button>
                  </div>
                )}

              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
