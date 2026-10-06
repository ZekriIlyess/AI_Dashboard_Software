import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";

import styles from "../../app/(dashboard)/explore/explore.module.css";

interface SaveWidgetModalProps {
  isOpen: boolean;
  onClose: () => void;
  sql: string;
  dataKeys: string[];
  chartConfig?: any;
  connectionId: string;
}

export default function SaveWidgetModal({ isOpen, onClose, sql, dataKeys, chartConfig, connectionId }: SaveWidgetModalProps) {
  const [dashboards, setDashboards] = useState<any[]>([]);
  const [selectedDashboardId, setSelectedDashboardId] = useState<string>("new");
  const [newDashboardTitle, setNewDashboardTitle] = useState("");
  
  const [widgetTitle, setWidgetTitle] = useState("");
  const [widgetType, setWidgetType] = useState<string>("table");
  const [xAxis, setXAxis] = useState<string>(dataKeys[0] || "");
  const [yAxis, setYAxis] = useState<string>(dataKeys[1] || dataKeys[0] || "");
  
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isOpen) {
      loadDashboards();
    }
  }, [isOpen]);

  useEffect(() => {
    if (chartConfig) {
      setWidgetType(chartConfig.type || "table");
      setXAxis(chartConfig.x || "");
      setYAxis(chartConfig.y || "");
    } else if (dataKeys.length > 0) {
      setWidgetType("table");
      setXAxis(dataKeys[0]);
      setYAxis(dataKeys[1] || dataKeys[0]);
    }
  }, [dataKeys, chartConfig]);

  const loadDashboards = async () => {
    try {
      const data: any = await api.get("/dashboards/");
      setDashboards(data || []);
      if (data && data.length > 0) {
        setSelectedDashboardId(data[0].id);
      }
    } catch (e) {
      console.error("Failed to load dashboards", e);
    }
  };

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");

    try {
      let dashId = selectedDashboardId;
      
      if (dashId === "new") {
        if (!newDashboardTitle.trim()) {
          throw new Error("Please enter a dashboard title");
        }
        const newDash: any = await api.post("/dashboards/", { title: newDashboardTitle, theme: "light" });
        dashId = newDash.id;
      }

      await api.post(`/dashboards/${dashId}/widgets`, {
        title: widgetTitle || "Untitled Chart",
        widget_type: widgetType,
        chart_config: {
          ...(chartConfig || {}),
          x_axis: xAxis,
          y_axis: yAxis,
          x: xAxis,
          y: yAxis
        },
        data_source: sql,
        connection_id: connectionId,
        position_x: 0,
        position_y: 0,
        width: 6,
        height: 4
      });

      onClose();
      alert("Successfully saved to dashboard!");
    } catch (err: any) {
      setError(err.message || "Failed to save widget");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <h2>Save to Dashboard</h2>
        
        <form onSubmit={handleSave}>
          
          <div className={styles.modalFormGroup}>
            <label>Dashboard</label>
            <select 
              value={selectedDashboardId} 
              onChange={(e) => setSelectedDashboardId(e.target.value)}
              className={styles.modalInput}
            >
              {dashboards.map(d => (
                <option key={d.id} value={d.id}>{d.title}</option>
              ))}
              <option value="new">+ Create New Dashboard</option>
            </select>
          </div>

          {selectedDashboardId === "new" && (
            <div className={styles.modalFormGroup}>
              <label>New Dashboard Title</label>
              <input 
                type="text" 
                value={newDashboardTitle} 
                onChange={(e) => setNewDashboardTitle(e.target.value)}
                className={styles.modalInput}
                required
              />
            </div>
          )}

          <div className={styles.modalFormGroup}>
            <label>Chart Title</label>
            <input 
              type="text" 
              value={widgetTitle} 
              onChange={(e) => setWidgetTitle(e.target.value)}
              placeholder="e.g. Daily Active Users"
              className={styles.modalInput}
              required
            />
          </div>

          {error && <div className={styles.errorBox}>{error}</div>}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.5rem' }}>
            <button 
              type="button" 
              onClick={onClose}
              className={styles.secondaryButton}
            >
              Cancel
            </button>
            <button 
              type="submit"
              disabled={saving}
              className={styles.sendButton}
            >
              {saving ? 'Saving...' : 'Save Chart'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
