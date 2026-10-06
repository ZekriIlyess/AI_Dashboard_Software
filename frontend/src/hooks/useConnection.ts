"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";

export function useConnection() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const testConnection = useCallback(async (connectionData: any): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const res: any = await api.post("/connections/test", connectionData);
      return Boolean(res && (res.status === "success" || res.success));
    } catch (e: any) {
      setError(e.message || "Connection test failed");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    testConnection,
    loading,
    error
  };
}
