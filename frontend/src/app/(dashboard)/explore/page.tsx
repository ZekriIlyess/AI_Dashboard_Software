"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import styles from "./explore.module.css";
import SaveWidgetModal from "@/components/dashboards/SaveWidgetModal";
import ChatWindow from "@/components/chat/ChatWindow";
import QuestionQueue from "@/components/chat/QuestionQueue";

interface DatabaseConnection {
  id: string;
  name?: string;
  database?: string;
}

interface ChatMessage {
  id?: string;
  isUser: boolean;
  text: string;
  sql: string | null;
  data: any[] | null;
  error: string | null;
  status?: "pending" | "success" | "error";
  summary?: string | null;
  narrative?: string | null;
  chartConfig?: { type: string, x: string, y: string } | null;
  progressMessage?: string;
}

export default function ExplorePage() {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [selectedConnId, setSelectedConnId] = useState<string>("");
  
  const [chatSessions, setChatSessions] = useState<any[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(false);
  const [isSessionsLoaded, setIsSessionsLoaded] = useState(false);
  const [isHistoryLoaded, setIsHistoryLoaded] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const isPostingRef = React.useRef(false);
  const lastPostTimeRef = React.useRef(0);
  
  const [editingQueueIndex, setEditingQueueIndex] = useState<number | null>(null);
  const [editingQueueText, setEditingQueueText] = useState("");

  const [inFlightQuestion, setInFlightQuestion] = useState<string | null>(null);
  const [questionQueueState, setQuestionQueueState] = useState<string[]>([]);
  const [isStorageLoaded, setIsStorageLoaded] = useState(false);

  // Robust persistence for question queue
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const savedQueue = localStorage.getItem('ai_dashboard_queue');
        if (savedQueue) {
          const parsed = JSON.parse(savedQueue);
          if (Array.isArray(parsed)) setQuestionQueueState(parsed);
        }

        const savedInFlight = localStorage.getItem('ai_dashboard_inflight');
        if (savedInFlight) setInFlightQuestion(savedInFlight);
      } catch (e) {
        console.error("Storage error", e);
      }
    }
    setIsStorageLoaded(true);
  }, []);

  const setQuestionQueue = (val: React.SetStateAction<string[]>) => {
    setQuestionQueueState(prev => {
      const next = typeof val === 'function' ? (val as any)(prev) : val;
      localStorage.setItem("ai_dashboard_queue", JSON.stringify(next));
      return next;
    });
  };
  
  const setInFlight = (val: string | null) => {
    setInFlightQuestion(val);
    if (val) {
      localStorage.setItem("ai_dashboard_inflight", val);
    } else {
      localStorage.removeItem("ai_dashboard_inflight");
    }
  };
  
  const questionQueue = questionQueueState;

  const [modalOpen, setModalOpen] = useState(false);
  const [modalSql, setModalSql] = useState("");
  const [modalKeys, setModalKeys] = useState<string[]>([]);
  const [modalChartConfig, setModalChartConfig] = useState<any>(null);

  // Add event listener to close modal on escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setModalOpen(false);
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, []);

  const handleOpenModal = (sql: string, data: any[], chartConfig?: any) => {
    setModalSql(sql);
    setModalKeys(Object.keys(data[0] || {}));
    setModalChartConfig(chartConfig || null);
    setModalOpen(true);
  };

  // Initial load of connections
  useEffect(() => {
    (async () => {
      try {
        const payload: any = await api.get("/connections/");
        setConnections(payload || []);
        if (payload && payload.length > 0) {
          setSelectedConnId(payload[0].id);
        }
      } catch (e) {
        console.error("Failed to load DB connections", e);
      }
    })();
  }, []);

  // Fetch sessions on connection change
  useEffect(() => {
    if (!selectedConnId) return;
    setIsSessionsLoaded(false);
    (async () => {
      try {
        const payload: any = await api.get(`/chat-sessions/?connection_id=${selectedConnId}`);
        setChatSessions(payload || []);
        if (payload && payload.length > 0) {
          setSelectedSessionId(payload[0].id);
        } else {
          setSelectedSessionId(null);
        }
      } catch (e) {
        console.error("Failed to load chat sessions", e);
      } finally {
        setIsSessionsLoaded(true);
      }
    })();
  }, [selectedConnId]);
  // Fetch history on session change
  useEffect(() => {
    if (!isStorageLoaded) return;
    
    if (!selectedSessionId) {
      setMessages([]);
      if (isSessionsLoaded) {
        setIsHistoryLoaded(true);
        // If there's no session, any inFlightQuestion couldn't possibly be on the server. NACK it immediately to prevent infinite lock.
        if (inFlightQuestion) {
          setQuestionQueue(prev => [inFlightQuestion, ...prev]);
          setInFlight(null);
        }
      }
      return;
    }
    
    setIsHistoryLoaded(false);
    (async () => {
      try {
        setLoading(true);
        await fetchHistory(selectedSessionId);
      } catch (e) {
        console.error("Failed to load history", e);
      } finally {
        setLoading(false);
        setIsHistoryLoaded(true);
      }
    })();
  }, [selectedSessionId, isSessionsLoaded, isStorageLoaded, inFlightQuestion]);

  // WebSocket mechanism replacing polling
  useEffect(() => {
    if (!selectedSessionId) return;

    let ws: WebSocket;
    const connectWs = () => {
      // In production, this would use wss:// and dynamic host
      ws = new WebSocket(`ws://localhost:8000/ws/chat/${selectedSessionId}`);
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "progress") {
            setMessages(prev => prev.map(m => {
              if (m.status === "pending") {
                return { ...m, progressMessage: data.message };
              }
              return m;
            }));
          } else if (data.type === "success" || data.type === "error") {
            fetchHistory(selectedSessionId);
          }
        } catch (e) {
          console.error("WS Parse error", e);
        }
      };

      ws.onerror = (e) => console.error("WS error", e);
    };

    connectWs();

    return () => {
      if (ws) ws.close();
    };
  }, [selectedSessionId]);

  const fetchHistory = async (sessionId: string) => {
    const fetchStartTime = Date.now();
    if (isPostingRef.current) return; // Prevent stale overwrites during in-flight posts
    
    const history: any = await api.get(`/queries/history/session/${sessionId}`);
    
    // ABA Race Condition check: If a new query was posted while we were awaiting this network response, discard this stale data!
    if (lastPostTimeRef.current > fetchStartTime || isPostingRef.current) {
      return;
    }
    
    // ACK/NACK for in-flight queue questions
    if (inFlightQuestion) {
      const serverHasIt = history.some((h: any) => h.text === inFlightQuestion);
      if (serverHasIt) {
        // ACK: Server safely received it
        setInFlight(null);
      } else {
        // NACK: Server missed it (e.g. double-refresh cancelled the POST request)
        setQuestionQueue(prev => [inFlightQuestion!, ...prev]);
        setInFlight(null);
      }
    }
    
    const formattedMessages: ChatMessage[] = [];
    history.forEach((h: any) => {
      // User bubble
      formattedMessages.push({
        isUser: true,
        text: h.text,
        sql: null,
        data: null,
        error: null,
      });
      // Bot bubble
      formattedMessages.push({
        id: h.id,
        isUser: false,
        text: "",
        sql: h.sql,
        data: h.data,
        error: h.error,
        status: h.status,
        summary: h.summary,
        narrative: h.narrative,
        chartConfig: h.chartConfig,
      });
    });
    setMessages(formattedMessages);
  };

  const handleCancel = async (historyId: string) => {
    try {
      await api.delete(`/queries/history/${historyId}`);
      if (selectedSessionId) {
        await fetchHistory(selectedSessionId);
      }
    } catch (e) {
      console.error("Failed to cancel query", e);
    }
  };

  const handleNewChat = () => {
    setSelectedSessionId(null);
    setMessages([]);
    setQuestionQueue([]);
    setShowSidebar(false);
  };

  const handleDeleteSession = async (id: string) => {
    if (!confirm("Delete this chat?")) return;
    try {
      await api.delete(`/chat-sessions/${id}`);
      setChatSessions(prev => prev.filter(s => s.id !== id));
      if (selectedSessionId === id) {
        setSelectedSessionId(null);
        setMessages([]);
      }
    } catch (e) {
      console.error("Failed to delete session", e);
    }
  };



  const isPending = messages.some((m) => !m.isUser && m.status === "pending") || !!inFlightQuestion;

  const sendToBackend = async (text: string) => {
    try {
      isPostingRef.current = true;
      lastPostTimeRef.current = Date.now();
      let activeSessionId = selectedSessionId;
      let isNewSession = false;
      
      if (!activeSessionId) {
        const newSession: any = await api.post("/chat-sessions/", {
          connection_id: selectedConnId
        });
        activeSessionId = newSession.id;
        isNewSession = true;
        setChatSessions(prev => [newSession, ...prev]);
      }

      await api.post("/queries/chat", {
        connection_id: selectedConnId,
        session_id: activeSessionId,
        message: text,
      });
      
      isPostingRef.current = false;

      // Safely trigger history fetch now that DB is consistent
      if (isNewSession) {
        setSelectedSessionId(activeSessionId);
      } else {
        fetchHistory(activeSessionId!);
      }
    } catch (e) {
      isPostingRef.current = false;
      setInFlight(null); // FIX: Clear inFlightQuestion on error so it doesn't lock UI
      const errMsg = (e as any).error || "Failed to dispatch task to server";
      setMessages((prev) => {
        const newArr = [...prev];
        newArr[newArr.length - 1] = {
          ...newArr[newArr.length - 1],
          status: "error",
          error: `Error: ${errMsg}`,
        };
        return newArr;
      });
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || !selectedConnId) return;

    if (isPending) {
      setQuestionQueue(prev => [...prev, inputValue]);
      setInputValue("");
      return;
    }

    const currentInput = inputValue;
    setInputValue("");
    setMessages((prev) => [
      ...prev,
      { isUser: true, text: currentInput, sql: null, data: null, error: null },
      { isUser: false, text: "", sql: null, data: null, error: null, status: "pending" },
    ]);

    sendToBackend(currentInput);
  };

  const isQueueProcessingRef = React.useRef(false);

  // Sync unlock when pending is officially false
  useEffect(() => {
    if (!isPending) {
      isQueueProcessingRef.current = false;
    }
  }, [isPending]);

  // Auto-process queue
  useEffect(() => {
    if (isSessionsLoaded && isHistoryLoaded && !isPending && !isQueueProcessingRef.current && questionQueue.length > 0 && selectedConnId) {
      isQueueProcessingRef.current = true; // Lock synchronously!
      
      const nextQuestion = questionQueue[0];
      setQuestionQueue(prev => prev.slice(1));
      setInFlight(nextQuestion); // Mark as in-flight
      
      setMessages((prev) => [
        ...prev,
        { isUser: true, text: nextQuestion, sql: null, data: null, error: null },
        { isUser: false, text: "", sql: null, data: null, error: null, status: "pending" },
      ]);
      
      sendToBackend(nextQuestion);
    }
  }, [isSessionsLoaded, isHistoryLoaded, isPending, questionQueue, selectedConnId]);

  // Determine if the global loading spinner should be locked
  const isInputLocked = loading || !selectedConnId;

  return (
    <div className={styles.themeRoot} style={{ display: 'flex', height: '100%', width: '100%', overflow: 'hidden', position: 'relative' }}>
      
      {/* Mobile Backdrop */}
      {showSidebar && (
        <div 
          style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 40 }}
          onClick={() => setShowSidebar(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`${styles.sidebar} ${showSidebar ? styles.sidebarOpen : ''}`}>
        <div style={{ padding: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <button onClick={handleNewChat} className={styles.newChatBtn}>
            + New Chat
          </button>
        </div>
        <div className={styles.sessionList}>
          {chatSessions.length === 0 ? (
            <div style={{ padding: '1rem', color: '#64748b', fontSize: '0.9rem', textAlign: 'center' }}>No recent chats</div>
          ) : (
            chatSessions.map(session => (
              <div 
                key={session.id} 
                className={`${styles.sessionItem} ${selectedSessionId === session.id ? styles.activeSession : ''}`}
                onClick={() => {
                  setSelectedSessionId(session.id);
                  setShowSidebar(false);
                }}
              >
                <div className={styles.sessionTitle}>{session.title || "New Chat"}</div>
                <button 
                  onClick={(e) => { e.stopPropagation(); handleDeleteSession(session.id); }} 
                  className={styles.deleteSessionBtn}
                  title="Delete Chat"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className={styles.chatWrapper}>
        {/* Top Bar with Connection Selector */}
        <div className={styles.topBar}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button className={styles.mobileMenuBtn} onClick={() => setShowSidebar(!showSidebar)}>
              ☰ Chats
            </button>
            <h2>Data Explorer</h2>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <select
              className={styles.connSelect}
              value={selectedConnId}
              onChange={(e) => setSelectedConnId(e.target.value)}
              disabled={isInputLocked}
            >
              <option value="" disabled>Select Database...</option>
              {connections.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name || c.database}
                </option>
              ))}
            </select>
          </div>
        </div>

      {/* Message History */}
      <ChatWindow 
        messages={messages} 
        onCancel={handleCancel} 
        onOpenModal={handleOpenModal} 
      />

      {/* Queue UI */}
      <QuestionQueue 
        queue={questionQueue} 
        setQueue={setQuestionQueue}
        editingQueueIndex={editingQueueIndex}
        setEditingQueueIndex={setEditingQueueIndex}
        editingQueueText={editingQueueText}
        setEditingQueueText={setEditingQueueText}
      />

      {/* Input */}
      <div className={styles.controls}>
        <form onSubmit={handleSend} style={{ display: 'flex', width: '100%', gap: '0.5rem' }}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isInputLocked}
            placeholder={selectedConnId ? "Ask a question..." : "Select a database first"}
            className={styles.inputField}
          />
          <button
            type="submit"
            disabled={isInputLocked || !inputValue.trim()}
            className={styles.sendButton}
          >
            {isPending ? "Queue" : "Send"}
          </button>
        </form>
      </div>
      <SaveWidgetModal 
        isOpen={modalOpen} 
        onClose={() => setModalOpen(false)} 
        sql={modalSql} 
        dataKeys={modalKeys} 
        chartConfig={modalChartConfig}
        connectionId={selectedConnId} 
      />
    </div>
    </div>
  );
}
