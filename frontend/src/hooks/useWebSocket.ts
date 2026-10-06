"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export type WebSocketStatus = "connecting" | "open" | "closed";

interface UseWebSocketOptions {
  onMessage?: (data: any) => void;
  autoConnect?: boolean;
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const { onMessage, autoConnect = true } = options;
  const [status, setStatus] = useState<WebSocketStatus>("closed");
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      return;
    }

    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("open");
      console.log(`WebSocket connected to ${url}`);
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (onMessage) {
          onMessage(parsed);
        }
      } catch (e) {
        if (onMessage) {
          onMessage(event.data);
        }
      }
    };

    ws.onclose = () => {
      setStatus("closed");
      console.log("WebSocket disconnected");
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [url, onMessage]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setStatus("closed");
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof message === "string" ? message : JSON.stringify(message));
    } else {
      console.warn("WebSocket is not open. Message not sent.");
    }
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    status,
    connect,
    disconnect,
    sendMessage,
  };
}
