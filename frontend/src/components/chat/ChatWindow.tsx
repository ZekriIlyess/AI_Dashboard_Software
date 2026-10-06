import React, { useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import styles from "../../app/(dashboard)/explore/explore.module.css";

interface ChatMessage {
  id?: string;
  isUser: boolean;
  text: string;
  sql: string | null;
  data: any[] | null;
  error: string | null;
  status?: "pending" | "success" | "error";
  summary?: string | null;
  chartConfig?: { type: string, x: string, y: string } | null;
  progressMessage?: string;
}

interface ChatWindowProps {
  messages: ChatMessage[];
  onCancel: (id: string) => void;
  onOpenModal: (sql: string, data: any[], chartConfig?: any) => void;
}

export default function ChatWindow({ messages, onCancel, onOpenModal }: ChatWindowProps) {
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className={styles.emptyState}>
        <h2>Start a conversation</h2>
        <p>Ask a question about your data to get started.</p>
      </div>
    );
  }

  return (
    <div className={styles.messageContainer}>
      {messages.map((msg, idx) => (
        <MessageBubble 
          key={msg.id || idx} 
          msg={msg} 
          onCancel={onCancel}
          onOpenModal={onOpenModal} 
        />
      ))}
      <div ref={endOfMessagesRef} />
    </div>
  );
}
