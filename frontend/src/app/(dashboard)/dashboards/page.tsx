"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { 
  Pencil, 
  Trash2, 
  LayoutDashboard, 
  Check, 
  X, 
  BarChart3, 
  ChevronLeft, 
  ChevronRight, 
  Maximize2, 
  Minimize2,
  Settings
} from "lucide-react";
import ChartRenderer from "@/components/dashboards/ChartRenderer";

export default function DashboardsPage() {
  const [dashboards, setDashboards] = useState<any[]>([]);
  const [selectedDashboard, setSelectedDashboard] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingDashboardId, setEditingDashboardId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  // Widget editing states
  const [editingWidget, setEditingWidget] = useState<any | null>(null);
  const [widgetTitle, setWidgetTitle] = useState("");
  const [widgetSQL, setWidgetSQL] = useState("");

  useEffect(() => {
    loadDashboards();
  }, []);

  const loadDashboards = async () => {
    try {
      setLoading(true);
      const data: any = await api.get("/dashboards/");
      setDashboards(data || []);
      if (data && data.length > 0) {
        fetchDashboard(data[0].id);
      } else {
        setSelectedDashboard(null);
      }
    } catch (e) {
      console.error("Failed to load dashboards", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchDashboard = async (id: string) => {
    try {
      const data: any = await api.get(`/dashboards/${id}`);
      // Sort widgets by position_x / position_y locally to ensure consistency
      if (data && data.widgets) {
        data.widgets.sort((a: any, b: any) => (a.position_x ?? 0) - (b.position_x ?? 0));
      }
      setSelectedDashboard(data);
    } catch (e) {
      console.error("Failed to fetch dashboard", e);
    }
  };

  const handleDeleteDashboard = async (e: React.MouseEvent, dashboardId: string) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this entire dashboard? This will permanently delete all charts inside it.")) return;
    try {
      await api.delete(`/dashboards/${dashboardId}`);
      if (selectedDashboard?.id === dashboardId) {
        setSelectedDashboard(null);
      }
      loadDashboards();
    } catch (err) {
      console.error("Failed to delete dashboard", err);
    }
  };

  const handleDeleteWidget = async (widgetId: string) => {
    if (!confirm("Are you sure you want to delete this chart?")) return;
    try {
      await api.delete(`/dashboards/widgets/${widgetId}`);
      if (selectedDashboard) {
        fetchDashboard(selectedDashboard.id);
      }
    } catch (e) {
      console.error("Failed to delete widget", e);
    }
  };

  const handleEditDashboard = (e: React.MouseEvent, dashboard: any) => {
    e.stopPropagation();
    setEditingDashboardId(dashboard.id);
    setEditTitle(dashboard.title);
  };

  const handleSaveDashboardTitle = async (dashboardId: string) => {
    if (!editTitle.trim() || editTitle.trim() === "") {
      setEditingDashboardId(null);
      return;
    }
    try {
      await api.put(`/dashboards/${dashboardId}`, { title: editTitle });
      setEditingDashboardId(null);
      loadDashboards();
      if (selectedDashboard?.id === dashboardId) {
        setSelectedDashboard({ ...selectedDashboard, title: editTitle });
      }
    } catch (err) {
      console.error("Failed to update dashboard title", err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, dashboardId: string) => {
    if (e.key === "Enter") {
      handleSaveDashboardTitle(dashboardId);
    } else if (e.key === "Escape") {
      setEditingDashboardId(null);
    }
  };

  // Dynamic Box Resizing
  const handleResizeWidget = async (widget: any, widthDelta: number, heightDelta: number) => {
    let newWidth = widget.width + widthDelta;
    let newHeight = widget.height + heightDelta;

    // Bounds constraint check
    if (newWidth < 3) newWidth = 3;
    if (newWidth > 12) newWidth = 12;
    if (newHeight < 3) newHeight = 3;
    if (newHeight > 8) newHeight = 8;

    if (newWidth === widget.width && newHeight === widget.height) return;

    // Optimistic Local State Update
    const updatedWidgets = selectedDashboard.widgets.map((w: any) => {
      if (w.id === widget.id) {
        return { ...w, width: newWidth, height: newHeight };
      }
      return w;
    });
    setSelectedDashboard({ ...selectedDashboard, widgets: updatedWidgets });

    // Persist changes in backend
    try {
      await api.put(`/dashboards/widgets/${widget.id}`, {
        width: newWidth,
        height: newHeight
      });
    } catch (err) {
      console.error("Failed to persist widget resizing", err);
    }
  };

  // Switch / Reorder boxes as needed
  const handleMoveWidget = async (widget: any, direction: number) => {
    const idx = selectedDashboard.widgets.findIndex((w: any) => w.id === widget.id);
    if (idx === -1) return;

    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= selectedDashboard.widgets.length) return;

    // Swap positions locally
    const newWidgets = [...selectedDashboard.widgets];
    const temp = newWidgets[idx];
    newWidgets[idx] = newWidgets[newIdx];
    newWidgets[newIdx] = temp;

    // Re-assign position_x order indexes
    const updatedWidgets = newWidgets.map((w: any, index: number) => ({
      ...w,
      position_x: index
    }));

    setSelectedDashboard({ ...selectedDashboard, widgets: updatedWidgets });

    // Persist position swaps in background
    try {
      await api.put(`/dashboards/widgets/${widget.id}`, { position_x: newIdx });
      const swappedWidget = newWidgets[idx];
      await api.put(`/dashboards/widgets/${swappedWidget.id}`, { position_x: idx });
    } catch (err) {
      console.error("Failed to persist widget reorder", err);
    }
  };

  // Open inline modal editor
  const handleOpenEditModal = (widget: any) => {
    setEditingWidget(widget);
    setWidgetTitle(widget.title);
    setWidgetSQL(widget.data_source || "");
  };

  // Save changes from editor modal
  const handleSaveWidgetEdits = async () => {
    if (!editingWidget) return;
    try {
      await api.put(`/dashboards/widgets/${editingWidget.id}`, {
        title: widgetTitle,
        data_source: widgetSQL
      });
      setEditingWidget(null);
      // Refresh the dashboard queries to reload charts
      fetchDashboard(selectedDashboard.id);
    } catch (err) {
      console.error("Failed to save widget configuration edits", err);
      alert("Failed to save widget properties.");
    }
  };

  if (loading) {
    return <div style={{ padding: '2rem', color: 'var(--color-text-muted)', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>Loading Dashboards...</div>;
  }

  return (
    <div style={{ display: 'flex', height: '100%', backgroundColor: 'var(--color-bg-dark)', overflow: 'hidden' }}>
      {/* Left Sidebar for Dashboards */}
      <div style={{ 
        width: '280px', 
        borderRight: '1px solid rgba(255,255,255,0.04)', 
        padding: '1.75rem 1.25rem', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '1.5rem',
        background: 'rgba(10,14,26,0.35)',
        backdropFilter: 'blur(20px)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', paddingLeft: '0.5rem' }}>
          <LayoutDashboard size={16} style={{ color: 'var(--color-primary-accent)' }} />
          <h2 style={{ color: '#fff', fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', margin: 0 }}>My Dashboards</h2>
        </div>
        
        {dashboards.length === 0 ? (
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', padding: '0 0.5rem', lineHeight: 1.5 }}>
            No dashboards yet. Save a query from Explore to create one!
          </p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {dashboards.map((d) => {
              const isActive = selectedDashboard?.id === d.id;
              const isEditing = editingDashboardId === d.id;

              return (
                <li key={d.id}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.65rem 0.85rem',
                      borderRadius: '8px',
                      backgroundColor: isActive ? 'rgba(99, 102, 241, 0.08)' : 'transparent',
                      border: isActive ? '1px solid rgba(99, 102, 241, 0.15)' : '1px solid transparent',
                      transition: 'all 0.2s ease',
                      cursor: isEditing ? 'default' : 'pointer',
                      boxShadow: isActive ? 'inset 3px 0 0 var(--color-primary-accent)' : 'none'
                    }}
                    onClick={() => !isEditing && fetchDashboard(d.id)}
                    onMouseEnter={(e) => { if (!isActive && !isEditing) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.02)'; }}
                    onMouseLeave={(e) => { if (!isActive && !isEditing) e.currentTarget.style.backgroundColor = 'transparent'; }}
                  >
                    {isEditing ? (
                      <input
                        autoFocus
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => handleKeyDown(e, d.id)}
                        onBlur={() => handleSaveDashboardTitle(d.id)}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          flex: 1,
                          padding: '0.3rem 0.5rem',
                          borderRadius: '6px',
                          border: '1px solid var(--color-primary-accent)',
                          backgroundColor: 'rgba(3,7,18,0.5)',
                          color: '#fff',
                          outline: 'none',
                          width: '100%',
                          fontSize: '0.9rem'
                        }}
                      />
                    ) : (
                      <div
                        style={{
                          flex: 1,
                          color: isActive ? '#f8fafc' : 'var(--color-text-muted)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontSize: '0.925rem',
                          fontWeight: isActive ? 600 : 500,
                          paddingLeft: '0.25rem'
                        }}
                      >
                        {d.title}
                      </div>
                    )}
                    
                    {!isEditing && (
                      <div style={{ display: 'flex', gap: '0.15rem', alignItems: 'center' }}>
                        <button
                          onClick={(e) => handleEditDashboard(e, d)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: isActive ? '#818cf8' : 'var(--color-text-muted)',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            borderRadius: '4px',
                            transition: 'all 0.2s',
                            opacity: isActive ? 0.95 : 0.4
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = '#fff'; e.currentTarget.style.opacity = '1'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = isActive ? '#818cf8' : 'var(--color-text-muted)'; e.currentTarget.style.opacity = isActive ? '0.95' : '0.4'; }}
                          title="Rename Dashboard"
                        >
                          <Pencil size={12} />
                        </button>
                        <button
                          onClick={(e) => handleDeleteDashboard(e, d.id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: isActive ? '#fca5a5' : 'var(--color-text-muted)',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            borderRadius: '4px',
                            transition: 'all 0.2s',
                            opacity: isActive ? 0.95 : 0.4
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)'; e.currentTarget.style.color = '#f87171'; e.currentTarget.style.opacity = '1'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = isActive ? '#fca5a5' : 'var(--color-text-muted)'; e.currentTarget.style.opacity = isActive ? '0.95' : '0.4'; }}
                          title="Delete Dashboard"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Main Dashboard Area */}
      <div style={{ flex: 1, padding: '2.5rem', overflowY: 'auto' }}>
        {selectedDashboard ? (
          <>
            <div style={{ marginBottom: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <h1 style={{ color: '#fff', fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
                  {selectedDashboard.title}
                </h1>
              </div>
              {selectedDashboard.description && (
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem', marginTop: '0.5rem', marginBottom: 0 }}>
                  {selectedDashboard.description}
                </p>
              )}
            </div>

            {selectedDashboard.widgets && selectedDashboard.widgets.length > 0 ? (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(12, 1fr)', 
                gap: '1.5rem',
                gridAutoRows: '80px'
              }}>
                {selectedDashboard.widgets.map((w: any, widgetIndex: number) => (
                  <div 
                    key={w.id} 
                    style={{
                      gridColumn: `span ${w.width}`,
                      gridRow: `span ${w.height}`,
                      backgroundColor: 'rgba(15, 23, 42, 0.45)',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                      borderRadius: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      overflow: 'hidden',
                      boxShadow: '0 8px 30px rgba(0, 0, 0, 0.25)',
                      transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.2)';
                      e.currentTarget.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.35), 0 0 20px rgba(99, 102, 241, 0.03)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                      e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.25)';
                    }}
                  >
                    {/* Widget Header Controls */}
                    <div style={{ 
                      padding: '0.85rem 1.15rem', 
                      borderBottom: '1px solid rgba(255,255,255,0.04)', 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      background: 'rgba(255,255,255,0.01)',
                      gap: '0.5rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden', flex: 1 }}>
                        <BarChart3 size={14} style={{ color: 'var(--color-primary-accent)', flexShrink: 0 }} />
                        <h3 style={{ margin: 0, color: '#fff', fontSize: '0.85rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {w.title}
                        </h3>
                      </div>

                      {/* Dynamic Dashboard Action controls */}
                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexShrink: 0 }}>
                        {/* Reorder / Box switching chevrons */}
                        <button
                          disabled={widgetIndex === 0}
                          onClick={() => handleMoveWidget(w, -1)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--color-text-muted)',
                            cursor: widgetIndex === 0 ? 'not-allowed' : 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            opacity: widgetIndex === 0 ? 0.2 : 0.6,
                            borderRadius: '4px',
                            transition: 'all 0.2s'
                          }}
                          onMouseEnter={(e) => { if (widgetIndex !== 0) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; }}
                          onMouseLeave={(e) => { if (widgetIndex !== 0) e.currentTarget.style.backgroundColor = 'transparent'; }}
                          title="Move Left"
                        >
                          <ChevronLeft size={13} />
                        </button>
                        <button
                          disabled={widgetIndex === selectedDashboard.widgets.length - 1}
                          onClick={() => handleMoveWidget(w, 1)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--color-text-muted)',
                            cursor: widgetIndex === selectedDashboard.widgets.length - 1 ? 'not-allowed' : 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            opacity: widgetIndex === selectedDashboard.widgets.length - 1 ? 0.2 : 0.6,
                            borderRadius: '4px',
                            transition: 'all 0.2s'
                          }}
                          onMouseEnter={(e) => { if (widgetIndex !== selectedDashboard.widgets.length - 1) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; }}
                          onMouseLeave={(e) => { if (widgetIndex !== selectedDashboard.widgets.length - 1) e.currentTarget.style.backgroundColor = 'transparent'; }}
                          title="Move Right"
                        >
                          <ChevronRight size={13} />
                        </button>

                        <span style={{ width: '1px', height: '12px', backgroundColor: 'rgba(255,255,255,0.08)', margin: '0 2px' }} />

                        {/* Scaling controls */}
                        <button
                          onClick={() => handleResizeWidget(w, -1, 0)}
                          disabled={w.width <= 3}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--color-text-muted)',
                            cursor: w.width <= 3 ? 'not-allowed' : 'pointer',
                            padding: '4px',
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            borderRadius: '4px',
                            transition: 'all 0.2s',
                            opacity: w.width <= 3 ? 0.2 : 0.6
                          }}
                          onMouseEnter={(e) => { if (w.width > 3) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; }}
                          onMouseLeave={(e) => { if (w.width > 3) e.currentTarget.style.backgroundColor = 'transparent'; }}
                          title="Shrink Width"
                        >
                          <Minimize2 size={12} />
                        </button>
                        <button
                          onClick={() => handleResizeWidget(w, 1, 0)}
                          disabled={w.width >= 12}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--color-text-muted)',
                            cursor: w.width >= 12 ? 'not-allowed' : 'pointer',
                            padding: '4px',
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            borderRadius: '4px',
                            transition: 'all 0.2s',
                            opacity: w.width >= 12 ? 0.2 : 0.6
                          }}
                          onMouseEnter={(e) => { if (w.width < 12) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; }}
                          onMouseLeave={(e) => { if (w.width < 12) e.currentTarget.style.backgroundColor = 'transparent'; }}
                          title="Expand Width"
                        >
                          <Maximize2 size={12} />
                        </button>

                        <button
                          onClick={() => handleResizeWidget(w, 0, -1)}
                          disabled={w.height <= 3}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--color-text-muted)',
                            cursor: w.height <= 3 ? 'not-allowed' : 'pointer',
                            padding: '4px 6px',
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            borderRadius: '4px',
                            transition: 'all 0.2s',
                            opacity: w.height <= 3 ? 0.2 : 0.6
                          }}
                          onMouseEnter={(e) => { if (w.height > 3) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; }}
                          onMouseLeave={(e) => { if (w.height > 3) e.currentTarget.style.backgroundColor = 'transparent'; }}
                          title="Shrink Height"
                        >
                          H-
                        </button>
                        <button
                          onClick={() => handleResizeWidget(w, 0, 1)}
                          disabled={w.height >= 8}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--color-text-muted)',
                            cursor: w.height >= 8 ? 'not-allowed' : 'pointer',
                            padding: '4px 6px',
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            borderRadius: '4px',
                            transition: 'all 0.2s',
                            opacity: w.height >= 8 ? 0.2 : 0.6
                          }}
                          onMouseEnter={(e) => { if (w.height < 8) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; }}
                          onMouseLeave={(e) => { if (w.height < 8) e.currentTarget.style.backgroundColor = 'transparent'; }}
                          title="Expand Height"
                        >
                          H+
                        </button>

                        <span style={{ width: '1px', height: '12px', backgroundColor: 'rgba(255,255,255,0.08)', margin: '0 2px' }} />

                        {/* Edit properties & Delete */}
                        <button
                          onClick={() => handleOpenEditModal(w)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--color-text-muted)',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            borderRadius: '4px',
                            opacity: 0.6,
                            transition: 'all 0.2s'
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = '#fff'; e.currentTarget.style.opacity = '1'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-muted)'; e.currentTarget.style.opacity = '0.6'; }}
                          title="Edit Title & SQL Query"
                        >
                          <Settings size={13} />
                        </button>

                        <button 
                          onClick={() => handleDeleteWidget(w.id)} 
                          style={{ 
                            background: 'transparent', 
                            border: 'none', 
                            color: 'var(--color-text-muted)', 
                            cursor: 'pointer', 
                            padding: '4px', 
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            borderRadius: '4px',
                            opacity: 0.6,
                            transition: 'all 0.2s'
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)'; e.currentTarget.style.color = '#f87171'; e.currentTarget.style.opacity = '1'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-muted)'; e.currentTarget.style.opacity = '0.6'; }}
                          title="Delete Chart"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    </div>
                    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', position: 'relative' }}>
                      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, width: '100%', height: '100%' }}>
                        <ChartRenderer widget={w} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ 
                padding: '4rem 2rem', 
                textAlign: 'center', 
                color: 'var(--color-text-muted)', 
                backgroundColor: 'rgba(15, 23, 42, 0.45)', 
                border: '1px solid rgba(255,255,255,0.05)',
                borderRadius: '16px',
                boxShadow: '0 8px 30px rgba(0, 0, 0, 0.2)'
              }}>
                <LayoutDashboard size={36} style={{ color: 'rgba(255,255,255,0.1)', marginBottom: '1rem' }} />
                <h3 style={{ color: '#fff', fontSize: '1rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>This dashboard is empty</h3>
                <p style={{ margin: 0, fontSize: '0.9rem' }}>Go to Explore, write a query, and save the chart to populate it!</p>
              </div>
            )}
          </>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-muted)', gap: '0.5rem' }}>
            <LayoutDashboard size={40} style={{ color: 'rgba(255,255,255,0.05)' }} />
            <span>Select a dashboard to view</span>
          </div>
        )}
      </div>

      {/* Glassmorphic Edit properties modal */}
      {editingWidget && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(3,7,18,0.75)',
          backdropFilter: 'blur(12px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 999,
          padding: '2rem'
        }}>
          <div className="glass" style={{
            width: '100%',
            maxWidth: '640px',
            padding: '2.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
            boxShadow: '0 20px 50px rgba(0,0,0,0.5)'
          }}>
            <div>
              <h3 style={{ margin: 0, color: '#fff', fontSize: '1.25rem', fontWeight: 700 }}>Adjust Chart Properties</h3>
              <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Modify widget headers or customize the underlying SQL query directly.</p>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: '#fff', fontSize: '0.85rem', fontWeight: 600 }}>Chart Title</label>
              <input 
                type="text" 
                value={widgetTitle}
                onChange={(e) => setWidgetTitle(e.target.value)}
                style={{
                  padding: '0.75rem',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: '#fff',
                  outline: 'none',
                  fontSize: '0.9rem'
                }}
              />
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: '#fff', fontSize: '0.85rem', fontWeight: 600 }}>SQL Data Source Query</label>
              <textarea 
                value={widgetSQL}
                onChange={(e) => setWidgetSQL(e.target.value)}
                rows={8}
                style={{
                  padding: '0.75rem',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: '#f1f5f9',
                  fontFamily: 'var(--font-family-mono)',
                  fontSize: '0.85rem',
                  outline: 'none',
                  resize: 'vertical',
                  lineHeight: 1.5
                }}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
              <button 
                onClick={() => setEditingWidget(null)}
                className="btn-secondary"
                style={{ padding: '0.6rem 1.25rem', fontSize: '0.875rem' }}
              >
                Cancel
              </button>
              <button 
                onClick={handleSaveWidgetEdits}
                className="btn-primary"
                style={{ padding: '0.6rem 1.25rem', fontSize: '0.875rem' }}
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
