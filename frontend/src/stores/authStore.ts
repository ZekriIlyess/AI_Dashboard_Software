import { create } from 'zustand';
import { api } from '@/lib/api';

interface User {
  id: string;
  email: string;
  name: string | null;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post<{ access_token: string }>("/auth/login", { email, password });
      localStorage.setItem("nexus_token", response.access_token);
      
      // Fetch user profile immediately after login
      const user = await api.get<User>("/auth/me");
      set({ isAuthenticated: true, user, isLoading: false });
    } catch (error: any) {
      set({ error: error.message, isLoading: false, isAuthenticated: false });
      throw error;
    }
  },

  register: async (name, email, password) => {
    set({ isLoading: true, error: null });
    try {
      // 1. Register the user
      await api.post("/auth/register", { name, email, password });
      
      // 2. Automatically log them in
      const response = await api.post<{ access_token: string }>("/auth/login", { email, password });
      localStorage.setItem("nexus_token", response.access_token);
      
      const user = await api.get<User>("/auth/me");
      set({ isAuthenticated: true, user, isLoading: false });
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem("nexus_token");
    set({ isAuthenticated: false, user: null });
  },

  checkAuth: async () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("nexus_token") : null;
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }
    
    set({ isLoading: true });
    try {
      const user = await api.get<User>("/auth/me");
      set({ isAuthenticated: true, user, isLoading: false });
    } catch (error) {
      // Token expired or invalid
      localStorage.removeItem("nexus_token");
      set({ isAuthenticated: false, user: null, isLoading: false });
    }
  }
}));
