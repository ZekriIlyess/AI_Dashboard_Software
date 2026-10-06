import { create } from "zustand";
import { api } from "@/lib/api";

export interface Widget {
  id: string;
  title: string;
  widget_type: string;
  chart_config?: any;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
}

export interface Dashboard {
  id: string;
  title: string;
  description?: string;
  theme: string;
  widgets: Widget[];
}

interface DashboardState {
  dashboards: Dashboard[];
  selectedDashboard: Dashboard | null;
  loading: boolean;
  error: string | null;
  fetchDashboards: () => Promise<void>;
  fetchDashboard: (id: string) => Promise<void>;
  createDashboard: (data: { title: string; description?: string; theme?: string }) => Promise<Dashboard | null>;
  deleteDashboard: (id: string) => Promise<void>;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  dashboards: [],
  selectedDashboard: null,
  loading: false,
  error: null,

  fetchDashboards: async () => {
    set({ loading: true, error: null });
    try {
      const data: any = await api.get("/dashboards/");
      set({ dashboards: data || [], loading: false });
    } catch (e: any) {
      set({ error: e.message || "Failed to fetch dashboards", loading: false });
    }
  },

  fetchDashboard: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const data: any = await api.get(`/dashboards/${id}`);
      if (data && data.widgets) {
        data.widgets.sort((a: any, b: any) => (a.position_y ?? 0) - (b.position_y ?? 0));
      }
      set({ selectedDashboard: data, loading: false });
    } catch (e: any) {
      set({ error: e.message || "Failed to fetch dashboard details", loading: false });
    }
  },

  createDashboard: async (data) => {
    set({ loading: true, error: null });
    try {
      const newDash: any = await api.post("/dashboards/", data);
      set((state) => ({
        dashboards: [newDash, ...state.dashboards],
        selectedDashboard: newDash,
        loading: false
      }));
      return newDash;
    } catch (e: any) {
      set({ error: e.message || "Failed to create dashboard", loading: false });
      return null;
    }
  },

  deleteDashboard: async (id: string) => {
    set({ loading: true, error: null });
    try {
      await api.delete(`/dashboards/${id}`);
      set((state) => ({
        dashboards: state.dashboards.filter((d) => d.id !== id),
        selectedDashboard: state.selectedDashboard?.id === id ? null : state.selectedDashboard,
        loading: false
      }));
    } catch (e: any) {
      set({ error: e.message || "Failed to delete dashboard", loading: false });
    }
  }
}));
