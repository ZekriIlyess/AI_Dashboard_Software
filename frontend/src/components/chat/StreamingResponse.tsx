"use client";

import React, { useEffect, useState } from "react";
import styles from "./StreamingResponse.module.css";

interface StreamingResponseProps {
  text: string;
  isStreaming: boolean;
}

export function StreamingResponse({ text, isStreaming }: StreamingResponseProps) {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    // For local streaming simulation, we just sync with incoming props
    setDisplayedText(text);
  }, [text]);

  return (
    <div className={styles.container}>
      <span className={styles.text}>{displayedText}</span>
      {isStreaming && <span className={styles.cursor} />}
    </div>
  );
}
