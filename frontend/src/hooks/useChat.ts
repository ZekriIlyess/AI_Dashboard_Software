"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function useChat() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSession = async (connectionId: string): Promise<any> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/chat-sessions/", { connection_id: connectionId });
      return res;
    } catch (e: any) {
      setError(e.message || "Failed to create chat session");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (sessionId: string, message: string): Promise<any> => {
    setLoading(true);
    setError(null);
    try {
      // The queries.py process_query_task expects a body payload
      const res = await api.post(`/chat-sessions/${sessionId}/query`, {
        query: message
      });
      return res;
    } catch (e: any) {
      setError(e.message || "Failed to send message");
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    createSession,
    sendMessage,
    loading,
    error
  };
}
