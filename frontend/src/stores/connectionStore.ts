import { create } from "zustand";
import { api } from "@/lib/api";

export interface DatabaseConnection {
  id: string;
  db_type: string;
  name?: string;
  database?: string;
  host?: string;
}

interface ConnectionState {
  connections: DatabaseConnection[];
  loading: boolean;
  error: string | null;
  fetchConnections: () => Promise<void>;
  deleteConnection: (id: string) => Promise<void>;
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  connections: [],
  loading: false,
  error: null,

  fetchConnections: async () => {
    set({ loading: true, error: null });
    try {
      const data: any = await api.get("/connections/");
      set({ connections: data || [], loading: false });
    } catch (e: any) {
      set({ error: e.message || "Failed to fetch connections", loading: false });
    }
  },

  deleteConnection: async (id: string) => {
    set({ loading: true, error: null });
    try {
      await api.delete(`/connections/${id}`);
      set((state) => ({
        connections: state.connections.filter((c) => c.id !== id),
        loading: false
      }));
    } catch (e: any) {
      set({ error: e.message || "Failed to delete connection", loading: false });
    }
  }
}));
