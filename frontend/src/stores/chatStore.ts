import { create } from "zustand";

export interface ChatMessage {
  id: string;
  sender: "user" | "agent";
  content: string;
  timestamp: string;
  query_id?: string;
  query_result?: any;
}

interface ChatState {
  sessionId: string | null;
  messages: ChatMessage[];
  chatLoading: boolean;
  setSessionId: (id: string | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  setChatLoading: (loading: boolean) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  sessionId: null,
  messages: [],
  chatLoading: false,

  setSessionId: (id) => set({ sessionId: id }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setChatLoading: (loading) => set({ chatLoading: loading }),
  clearChat: () => set({ messages: [], sessionId: null, chatLoading: false })
}));
