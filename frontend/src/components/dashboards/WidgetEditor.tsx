"use client";

import React, { useState } from "react";
import { Play, Save, X, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import styles from "./WidgetEditor.module.css";

interface WidgetEditorProps {
  widget?: any;
  connectionId: string;
  onSave: (widgetData: any) => void;
  onCancel: () => void;
}

export function WidgetEditor({ widget, connectionId, onSave, onCancel }: WidgetEditorProps) {
  const [title, setTitle] = useState(widget?.title || "");
  const [widgetType, setWidgetType] = useState(widget?.widget_type || "table");
  const [dataSource, setDataSource] = useState(widget?.data_source || "");
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState<any[] | null>(null);
  const [previewError, setPreviewError] = useState("");

  const handleRunPreview = async () => {
    if (!dataSource) {
      setPreviewError("Please enter a SQL query first.");
      return;
    }
    setLoading(true);
    setPreviewError("");
    setPreviewData(null);
    try {
      // Execute the query using the connection
      const response: any = await api.post("/queries/execute", {
        connection_id: connectionId,
        query: dataSource
      });
      if (response && response.data) {
        setPreviewData(response.data);
      } else {
        setPreviewError("Query completed but returned no rows.");
      }
    } catch (e: any) {
      setPreviewError(e.message || "Failed to execute query preview.");
    } finally {
      setLoading(false);
    }
  };

  const handleFormSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) {
      alert("Please enter a chart title.");
      return;
    }
    if (!dataSource) {
      alert("Please enter a SQL query source.");
      return;
    }
    onSave({
      id: widget?.id,
      title,
      widget_type: widgetType,
      data_source: dataSource,
      chart_config: widget?.chart_config || { x: "", y: "" }
    });
  };

  return (
    <div className={styles.editor}>
      <form onSubmit={handleFormSave} className={styles.form}>
        <div className={styles.formGroup}>
          <label className={styles.label}>Chart Title</label>
          <input
            type="text"
            className={styles.input}
            placeholder="e.g. Total Revenue by Month"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label}>Widget Visual Type</label>
          <select
            className={styles.select}
            value={widgetType}
            onChange={(e) => setWidgetType(e.target.value)}
          >
            <option value="table">Data Table</option>
            <option value="bar">Bar Chart</option>
            <option value="line">Line Chart</option>
            <option value="pie">Pie Chart</option>
          </select>
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label}>SQL Data Source Query</label>
          <textarea
            className={styles.textarea}
            rows={6}
            placeholder="SELECT month, SUM(revenue) FROM sales GROUP BY month..."
            value={dataSource}
            onChange={(e) => setDataSource(e.target.value)}
          />
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleRunPreview}
            disabled={loading}
          >
            {loading ? <RefreshCw className={styles.spinner} size={16} /> : <Play size={16} style={{ marginRight: "0.25rem" }} />}
            Run Preview
          </button>
          
          <div className={styles.rightActions}>
            <button type="button" className="btn btn-secondary" onClick={onCancel} style={{ marginRight: "0.5rem" }}>
              <X size={16} style={{ marginRight: "0.25rem" }} />
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              <Save size={16} style={{ marginRight: "0.25rem" }} />
              Save Chart
            </button>
          </div>
        </div>
      </form>

      {/* Preview Section */}
      <div className={styles.preview}>
        <h4 className={styles.previewHeader}>Data Preview Panel</h4>
        <div className={styles.previewBox}>
          {previewData ? (
            <div className={styles.previewTableWrapper}>
              <table className={styles.previewTable}>
                <thead>
                  <tr>
                    {Object.keys(previewData[0] || {}).map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewData.slice(0, 5).map((row, rIdx) => (
                    <tr key={rIdx}>
                      {Object.values(row).map((val: any, cIdx) => (
                        <td key={cIdx}>{String(val)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {previewData.length > 5 && (
                <div className={styles.previewMore}>+ {previewData.length - 5} more rows</div>
              )}
            </div>
          ) : previewError ? (
            <div className={styles.previewError}>{previewError}</div>
          ) : (
            <div className={styles.previewPlaceholder}>Click "Run Preview" to execute query.</div>
          )}
        </div>
      </div>
    </div>
  );
}
