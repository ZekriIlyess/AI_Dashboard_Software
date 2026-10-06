// =============================================================================
// Nexus AI — Shared TypeScript Types: Visualization
// =============================================================================

export type ChartType = 
  | "bar" 
  | "line" 
  | "scatter" 
  | "pie" 
  | "heatmap" 
  | "histogram" 
  | "area" 
  | "table"
  | "metric"; // Single number display

/** Configuration for rendering a specific chart */
export interface ChartConfig {
  type: ChartType;
  title?: string;
  description?: string;
  xAxis?: string;
  yAxis?: string;
  groupBy?: string;
  colorScale?: string[];
  showLegend: boolean;
  isStacked?: boolean;
}

/** Dashboard configuration */
export interface DashboardConfig {
  id: string;
  title: string;
  description?: string;
  widgets: WidgetConfig[];
  layout: DashboardLayout;
  createdAt: string;
  updatedAt: string;
}

/** Layout settings for the dashboard grid */
export interface DashboardLayout {
  columns: number;
  rowHeight: number;
}

/** Individual widget within a dashboard */
export interface WidgetConfig {
  id: string;
  /** Query ID that powers this widget */
  queryId?: string;
  /** SQL used to power this widget (if not referencing a saved query) */
  sql?: string;
  chartConfig: ChartConfig;
  grid: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
}
