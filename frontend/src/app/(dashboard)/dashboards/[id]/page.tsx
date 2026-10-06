"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChevronLeft, RefreshCw, LayoutDashboard, Download, AlertTriangle } from "lucide-react";
import ChartRenderer from "@/components/dashboards/ChartRenderer";
import { api } from "@/lib/api";
import styles from "./page.module.css";

interface Widget {
  id: string;
  title: string;
  widget_type: string;
  chart_config?: any;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
}

interface Dashboard {
  id: string;
  title: string;
  description?: string;
  theme: string;
  widgets: Widget[];
}

export default function DashboardDetailPage() {
  const params = useParams();
  const router = useRouter();
  const dashboardId = params.id as string;

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const data: any = await api.get(`/dashboards/${dashboardId}`);
      if (data && data.widgets) {
        // Sort widgets by grid layout order
        data.widgets.sort((a: any, b: any) => (a.position_y ?? 0) - (b.position_y ?? 0) || (a.position_x ?? 0) - (b.position_x ?? 0));
      }
      setDashboard(data);
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (dashboardId) {
      loadDashboard();
    }
  }, [dashboardId]);

  const handleExportPDF = () => {
    if (!dashboard) return;
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    window.open(`${apiBaseUrl}/api/exports/pdf/dashboard/${dashboard.id}`, "_blank");
  };

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <RefreshCw className={styles.spinner} size={32} />
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className={styles.errorWrapper}>
        <div className={styles.errorCard}>
          <AlertTriangle size={24} style={{ marginBottom: "0.5rem" }} />
          <h3>Dashboard Not Found</h3>
          <p>{error || "The requested dashboard could not be loaded."}</p>
          <button className="btn btn-secondary" onClick={() => router.push("/dashboards")} style={{ marginTop: "1rem" }}>
            Back to Dashboards
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <button className="btn btn-secondary" onClick={() => router.push("/dashboards")} style={{ marginBottom: "1rem", padding: "0.5rem 1rem", fontSize: "0.85rem" }}>
            <ChevronLeft size={16} style={{ marginRight: "0.25rem" }} />
            Back to list
          </button>
          <div className={styles.titleArea}>
            <LayoutDashboard className={styles.icon} size={28} />
            <h2 className={styles.title}>{dashboard.title}</h2>
          </div>
          {dashboard.description && <p className={styles.description}>{dashboard.description}</p>}
        </div>

        <div className={styles.actions}>
          <button className="btn btn-secondary" onClick={loadDashboard} style={{ marginRight: "0.5rem" }}>
            <RefreshCw size={16} />
          </button>
          <button className="btn btn-primary" onClick={handleExportPDF}>
            <Download size={16} style={{ marginRight: "0.5rem" }} />
            Export PDF
          </button>
        </div>
      </div>

      <div className={styles.grid}>
        {dashboard.widgets.length === 0 ? (
          <div className={styles.emptyState}>
            <p>This dashboard has no widgets yet. Use the dashboard builder page to add charts.</p>
          </div>
        ) : (
          dashboard.widgets.map((widget) => {
            const gridStyle = {
              gridColumn: `span ${widget.width || 6}`,
              minHeight: `${(widget.height || 4) * 80}px`
            };
            return (
              <div key={widget.id} className={styles.widgetCard} style={gridStyle}>
                <div className={styles.widgetHeader}>
                  <h4 className={styles.widgetTitle}>{widget.title}</h4>
                </div>
                <div className={styles.widgetBody}>
                  <ChartRenderer widget={widget} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
